"""aipoly v2 后端入口 —— 替换 backend/main.py。

与 v1 的差别就是这次重构的全部要点：

1. **不挂 chat 路由。** v1 的 POST /api/strategies/{sid}/chat/send 把用户文本
   直接喂给带 Bash 工具、以 root 运行的 CLI —— 一条消息等于 root 任意命令。
   v2 里 agent 只能由 aipoly-run-agent 在沙箱中拉起，后端不再是入口。
2. **不再有 CORS 通配符。** v1 是 allow_origins=["*"]，配合 SSH 隧道，
   浏览器里任何网站都能跨域驱动后端，且不需要任何凭证。v2 没有浏览器客户端，
   直接不装 CORS 中间件。
3. **不服务任何静态文件。** 没有前端，没有 SPA fallback。
4. **/api/* 全部要求 token。** v1 的 .token 只守 /_internal，/api/* 裸奔。

结果：这个进程只监听 127.0.0.1:8010，只接受带正确 token 的请求，
调用方只有本机的 MCP 服务。
"""

import asyncio
import logging
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException

from backend import alerts_db, scheduler as sched
from backend.market_data import price_monitor_loop
from backend.routers import (
    activity,
    alerts,
    health,
    internal,
    portfolio,
    schedules,
    strategies,
    strategy_doc,
)
from backend.strategies import ensure_global_agent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_TOKEN_FILE = Path(os.environ.get("AIPOLY_STATE", "/var/lib/aipoly")) / "data" / ".token"


def _ensure_token() -> str:
    """token 优先取自 mcp.env（由 systemd 注入），缺失才落盘生成。

    v1 把 token 写进 data/.token 且模式 644，还把同一个值 commit 进了公开仓库的
    strategies/_agent/.mcp.json。v2 的正规来源是 /etc/aipoly/mcp.env(640)。
    """
    token = os.environ.get("AIPM_TOKEN", "").strip()
    if token:
        return token

    _TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _TOKEN_FILE.exists():
        token = _TOKEN_FILE.read_text().strip()
        if token:
            os.environ["AIPM_TOKEN"] = token
            return token
    token = secrets.token_hex(32)
    _TOKEN_FILE.write_text(token)
    _TOKEN_FILE.chmod(0o600)          # v1 这里是 644
    os.environ["AIPM_TOKEN"] = token
    return token


def require_token(x_aipm_token: str = Header(default="")) -> None:
    """所有路由的统一闸门。用 compare_digest 避免计时侧信道。"""
    expected = os.environ.get("AIPM_TOKEN", "")
    if not expected or not secrets.compare_digest(x_aipm_token, expected):
        raise HTTPException(status_code=401, detail="unauthorized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    token = _ensure_token()
    logger.info("token 已加载 (%s...)，监听 loopback", token[:8])
    alerts_db.init_db()
    ensure_global_agent()
    sched.start()
    monitor_task = asyncio.create_task(price_monitor_loop())
    yield
    monitor_task.cancel()
    sched.shutdown()


app = FastAPI(title="aipoly-core", lifespan=lifespan, docs_url=None, redoc_url=None)

# 没有 CORSMiddleware：v2 没有浏览器客户端。
# 没有 StaticFiles / SPA fallback：v2 没有前端。
# 没有 chat 路由：agent 不再能从 HTTP 入口被任意文本驱动。
_GUARDED = [strategies, alerts, portfolio, schedules, strategy_doc, internal, activity]
for mod in _GUARDED:
    app.include_router(mod.router, dependencies=[Depends(require_token)])

# health 不设防，供 systemd / 监控探活，且不返回任何业务信息。
app.include_router(health.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
