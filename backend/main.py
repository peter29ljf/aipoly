"""FastAPI 后端入口。"""

import asyncio
import logging
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend import alerts_db, scheduler as sched
from backend.market_data import price_monitor_loop
from backend.routers import strategies, chat, alerts, portfolio, schedules, strategy_doc, internal
from backend.strategies import ensure_global_agent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# 生成或加载内部 token
_TOKEN_FILE = Path(__file__).resolve().parent.parent / "data" / ".token"


def _ensure_token() -> str:
    _TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _TOKEN_FILE.exists():
        token = _TOKEN_FILE.read_text().strip()
        if token:
            os.environ["AIPM_TOKEN"] = token
            return token
    token = secrets.token_hex(32)
    _TOKEN_FILE.write_text(token)
    os.environ["AIPM_TOKEN"] = token
    return token


@asynccontextmanager
async def lifespan(app: FastAPI):
    token = _ensure_token()
    logger.info("Internal token loaded (%s...)", token[:8])
    alerts_db.init_db()
    ensure_global_agent()
    sched.start()
    monitor_task = asyncio.create_task(price_monitor_loop())
    yield
    monitor_task.cancel()
    sched.shutdown()


app = FastAPI(title="aipolymarket", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(strategies.router)
app.include_router(chat.router)
app.include_router(alerts.router)
app.include_router(portfolio.router)
app.include_router(schedules.router)
app.include_router(strategy_doc.router)
app.include_router(internal.router)


@app.get("/health")
def health():
    return {"status": "ok"}


# 生产模式：服务 React 构建产物
_frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    from fastapi.responses import FileResponse
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request as StarletteRequest

    class SPAMiddleware(BaseHTTPMiddleware):
        """非 API 路径且无对应文件时，返回 index.html 支持前端路由刷新。"""
        async def dispatch(self, request: StarletteRequest, call_next):
            response = await call_next(request)
            path = request.url.path
            # 只对前端路由路径做 fallback（非 API、非内部、非静态资源）
            if (response.status_code == 404
                    and not path.startswith("/api/")
                    and not path.startswith("/_internal/")
                    and not path.startswith("/health")
                    and "." not in path.split("/")[-1]):  # 排除有扩展名的文件
                return FileResponse(str(_frontend_dist / "index.html"))
            return response

    app.add_middleware(SPAMiddleware)
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="static")
