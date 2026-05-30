"""策略 CRUD：创建/列出/删除策略目录及其文件。"""

import json
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path

from backend.portfolio_io import save as save_portfolio
from backend.strategy_doc_io import write as write_doc

STRATEGIES_DIR = Path(__file__).resolve().parent.parent / "strategies"
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "8010"))


def _get_token() -> str:
    token = os.environ.get("AIPM_TOKEN", "")
    if not token:
        token_file = Path(__file__).resolve().parent.parent / "data" / ".token"
        if token_file.exists():
            token = token_file.read_text().strip()
    return token

MCP_TEMPLATE = {
    "mcpServers": {
        "poly_trade": {
            "type": "sse",
            "url": f"http://127.0.0.1:8101/sse",
            "env": {"STRATEGY_ID": "{sid}", "AIPM_TOKEN": "{token}", "API_BASE": f"http://127.0.0.1:{BACKEND_PORT}"}
        },
        "portfolio": {
            "type": "sse",
            "url": "http://127.0.0.1:8102/sse",
            "env": {"STRATEGY_ID": "{sid}", "AIPM_TOKEN": "{token}", "API_BASE": f"http://127.0.0.1:{BACKEND_PORT}"}
        },
        "scheduler": {
            "type": "sse",
            "url": "http://127.0.0.1:8103/sse",
            "env": {"STRATEGY_ID": "{sid}", "AIPM_TOKEN": "{token}", "API_BASE": f"http://127.0.0.1:{BACKEND_PORT}"}
        },
        "sweep": {
            "type": "sse",
            "url": "http://127.0.0.1:8104/sse",
            "env": {}
        },
        "strategy_doc": {
            "type": "sse",
            "url": "http://127.0.0.1:8105/sse",
            "env": {"STRATEGY_ID": "{sid}", "AIPM_TOKEN": "{token}", "API_BASE": f"http://127.0.0.1:{BACKEND_PORT}"}
        },
    }
}


def _slugify(name: str) -> str:
    # Keep only ASCII alphanumeric, spaces, hyphens; strip non-ASCII (incl. Chinese)
    s = name.lower()
    s = re.sub(r"[^\x00-\x7f]", "-", s)  # replace non-ASCII with dash
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s[:40] or "strategy"


def _unique_sid(base: str) -> str:
    p = STRATEGIES_DIR / base
    if not p.exists():
        return base
    for i in range(2, 100):
        candidate = f"{base}-{i}"
        if not (STRATEGIES_DIR / candidate).exists():
            return candidate
    return base + "-" + secrets.token_hex(3)


def list_strategies() -> list[dict]:
    if not STRATEGIES_DIR.exists():
        return []
    result = []
    for d in sorted(STRATEGIES_DIR.iterdir()):
        if not d.is_dir():
            continue
        meta_path = d / "_meta.json"
        if meta_path.exists():
            try:
                with open(meta_path, encoding="utf-8") as f:
                    meta = json.load(f)
                meta["id"] = d.name
                result.append(meta)
            except Exception:
                pass
    return result


def create_strategy(name: str, description: str = "") -> dict:
    sid = _unique_sid(_slugify(name))
    sid_dir = STRATEGIES_DIR / sid
    sid_dir.mkdir(parents=True, exist_ok=True)
    (sid_dir / "logs").mkdir(exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    meta = {"name": name, "description": description, "kind": "strategy", "created_at": now}
    with open(sid_dir / "_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    save_portfolio(sid, {"positions": []})
    write_doc(sid, f"# {name}\n\n{description}\n\n- 目标：[由 AI 填写]\n- 扫描参数：days=7, min_p=0.90, max_p=0.97\n- 单笔金额：$50 USDC\n- 每日目标：最多 5 笔新仓\n")

    mcp_cfg = json.loads(
        json.dumps(MCP_TEMPLATE)
        .replace("{sid}", sid)
        .replace("{token}", _get_token())
    )
    with open(sid_dir / ".mcp.json", "w", encoding="utf-8") as f:
        json.dump(mcp_cfg, f, ensure_ascii=False, indent=2)

    _rebuild_claude_md(sid)
    meta["id"] = sid
    return meta


def get_strategy(sid: str) -> dict | None:
    meta_path = STRATEGIES_DIR / sid / "_meta.json"
    if not meta_path.exists():
        return None
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    meta["id"] = sid
    return meta


def delete_strategy(sid: str) -> bool:
    """删除策略目录，并清理所有关联的定时任务和价格警报，防止孤儿任务继续触发。"""
    import shutil
    import logging
    from backend import scheduler as _sched, alerts_db as _alerts
    p = STRATEGIES_DIR / sid
    if not p.exists():
        return False
    # 1. 清理 APScheduler 定时任务（防止孤儿任务触发 Claude）
    removed_jobs = _sched.remove_jobs_for_sid(sid)
    # 2. 取消所有活跃价格警报
    cancelled_alerts = _alerts.cancel_all_for_strategy(sid)
    logging.getLogger(__name__).info(
        "Deleted strategy %s: removed %d jobs, cancelled %d alerts",
        sid, removed_jobs, cancelled_alerts,
    )
    # 3. 删除文件系统目录
    shutil.rmtree(p)
    return True


def _rebuild_claude_md(sid: str, user_message: str = ""):
    from backend import strategy_doc_io, portfolio_io, chat_log, alerts_db
    from backend.memory_compressor import read_memory
    doc = strategy_doc_io.read(sid)
    positions = portfolio_io.list_positions(sid)
    active_alerts = alerts_db.get_active_alerts(sid)

    pos_str = json.dumps(positions, ensure_ascii=False, indent=2) if positions else "（无持仓）"
    alerts_str = json.dumps(active_alerts, ensure_ascii=False, indent=2) if active_alerts else "（无活跃警报）"

    # 优先使用 AI 压缩记忆，fallback 到最近 5 条原始记录
    compressed = read_memory(sid)
    if compressed:
        history_str = compressed
    else:
        recent = chat_log.read_recent(sid, 5)
        history_str = "\n".join(
            f"[{e.get('kind','?')}] {str(e.get('content', e.get('text', '')))[:400]}"
            for e in recent
        ) if recent else "（无历史）"

    user_msg_section = f"\n## 用户当前消息\n{user_message}\n" if user_message else ""

    claude_md = f"""# aipolymarket 策略上下文

## 策略 ID（调用 MCP 工具时必须传入 strategy_id 参数）
**strategy_id = "{sid}"**

## 策略说明
{doc}

## 当前持仓
```json
{pos_str}
```

## 活跃价格警报
```json
{alerts_str}
```

## 记忆摘要（AI 压缩历史）
{history_str}
{user_msg_section}
---
你是一个 Polymarket 自动交易 AI。根据上述策略说明和当前状态，决定下一步操作。

## ⚠️ 状态变更必须通过 MCP 工具，不能只写入 strategy.md

下面这些**状态变化**必须用对应 MCP 工具实际操作（不能只是在 strategy.md 里描述）：

| 用户意图 | 必须调用的 MCP 工具 | 不能仅做 |
|----------|---------------------|----------|
| 设置价格警报 | `mcp__poly_trade__subscribe_price_alert` | ❌ 只写进 strategy.md |
| 添加/更新/删除持仓 | `mcp__portfolio__add_position` / `update_position` / `remove_position` | ❌ 只写进 strategy.md |
| 创建定时任务 | `mcp__scheduler__schedule_task` / `schedule_once` | ❌ 只写进 strategy.md |
| 买卖交易 | `mcp__poly_trade__market_buy` / `market_sell` | ❌ 只写进 strategy.md |
| 修改策略说明文档 | `mcp__strategy_doc__write_strategy_doc` / `append_strategy_doc` | ❌ 直接修改本地文件 |

**调用任何 MCP 工具时**：传入参数 `strategy_id="{sid}"`，工具会同步到后端数据库，UI 才会显示。

## 可用 MCP 工具
- `poly_trade`：market_buy / market_sell / get_midpoint / get_orderbook / get_token_ids / get_balance / get_positions / subscribe_price_alert / list_price_alerts / cancel_price_alert
- `portfolio`：list_positions / add_position / update_position / remove_position
- `scheduler`：schedule_task / schedule_once / list_tasks / cancel_task
- `sweep`：scan_markets（市场初筛）
- `strategy_doc`：read_strategy_doc / write_strategy_doc / append_strategy_doc
"""
    path = STRATEGIES_DIR / sid / "CLAUDE.md"
    path.write_text(claude_md, encoding="utf-8")


def rebuild_claude_md(sid: str, user_message: str = ""):
    _rebuild_claude_md(sid, user_message)


# ── Global agent ───────────────────────────────────────────────────────────────

GLOBAL_AGENT_SID = "_agent"

_GLOBAL_CLAUDE_MD = """# aipolymarket 全局助手

你是 aipolymarket 的全局 Polymarket 交易助手，可以帮助用户：
- 使用 sweep MCP 扫描 Polymarket 市场，进行初筛和评分
- 使用 poly_trade MCP 查询价格、订单簿、账户余额
- 使用 portfolio MCP 查看和管理持仓
- 解释市场动态、回答 Polymarket 相关问题
- 帮助制定或优化交易策略

你无需绑定某个特定策略，可以自由探索和回答用户的问题。
"""


def ensure_global_agent():
    """确保全局助手目录存在（在后端启动时调用）。"""
    sid = GLOBAL_AGENT_SID
    sid_dir = STRATEGIES_DIR / sid
    if sid_dir.exists():
        return

    sid_dir.mkdir(parents=True, exist_ok=True)
    (sid_dir / "logs").mkdir(exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    meta = {"name": "全局助手", "description": "通用 Polymarket AI 助手", "kind": "global", "created_at": now}
    with open(sid_dir / "_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    save_portfolio(sid, {"positions": []})

    mcp_cfg = json.loads(
        json.dumps(MCP_TEMPLATE)
        .replace("{sid}", sid)
        .replace("{token}", _get_token())
    )
    with open(sid_dir / ".mcp.json", "w", encoding="utf-8") as f:
        json.dump(mcp_cfg, f, ensure_ascii=False, indent=2)

    path = sid_dir / "CLAUDE.md"
    path.write_text(_GLOBAL_CLAUDE_MD, encoding="utf-8")
