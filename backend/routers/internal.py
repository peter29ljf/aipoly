"""MCP 回调 webhook：内部 token 鉴权，供 MCP 服务器回调。"""

import os
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from backend import alerts_db, portfolio_io, strategy_doc_io, event_bus as eb

router = APIRouter(prefix="/_internal", tags=["internal"])

def _get_internal_token() -> str:
    token = os.environ.get("AIPM_TOKEN", "")
    if not token:
        from pathlib import Path
        tf = Path(__file__).resolve().parents[2] / "data" / ".token"
        if tf.exists():
            token = tf.read_text().strip()
    return token


def _auth(x_aipm_token: str | None = Header(default=None)):
    expected = _get_internal_token()
    if expected and x_aipm_token != expected:
        raise HTTPException(403, "Forbidden")


# ── 价格警报 ──────────────────────────────────────────────────────────────────

class CreateAlertPayload(BaseModel):
    sid: str
    token_id: str
    target: float
    direction: str
    note: str = ""


@router.post("/alerts")
def internal_create_alert(payload: CreateAlertPayload, x_aipm_token: str | None = Header(default=None)):
    _auth(x_aipm_token)
    return alerts_db.create_alert(payload.sid, payload.token_id, payload.target, payload.direction, payload.note)


@router.get("/alerts/{sid}")
def internal_list_alerts(sid: str, x_aipm_token: str | None = Header(default=None)):
    _auth(x_aipm_token)
    return alerts_db.get_active_alerts(sid)


@router.delete("/alerts/{alert_id}")
def internal_cancel_alert(alert_id: int, x_aipm_token: str | None = Header(default=None)):
    _auth(x_aipm_token)
    return {"ok": alerts_db.cancel_alert(alert_id)}


# ── 持仓管理 ──────────────────────────────────────────────────────────────────

class AddPositionPayload(BaseModel):
    sid: str
    token_id: str
    outcome: str
    shares: float
    cost_usdc: float
    note: str = ""


class UpdatePositionPayload(BaseModel):
    sid: str
    token_id: str
    shares: float | None = None
    cost_usdc: float | None = None
    note: str | None = None


@router.get("/portfolio/{sid}")
def internal_list_portfolio(sid: str, x_aipm_token: str | None = Header(default=None)):
    _auth(x_aipm_token)
    return portfolio_io.list_positions(sid)


@router.post("/portfolio")
def internal_add_position(payload: AddPositionPayload, x_aipm_token: str | None = Header(default=None)):
    _auth(x_aipm_token)
    return portfolio_io.add_position(payload.sid, payload.token_id, payload.outcome, payload.shares, payload.cost_usdc, payload.note)


@router.patch("/portfolio")
def internal_update_position(payload: UpdatePositionPayload, x_aipm_token: str | None = Header(default=None)):
    _auth(x_aipm_token)
    updates = {k: v for k, v in payload.model_dump().items() if k not in ("sid", "token_id") and v is not None}
    return portfolio_io.update_position(payload.sid, payload.token_id, **updates)


@router.delete("/portfolio/{sid}/{token_id:path}")
def internal_remove_position(sid: str, token_id: str, x_aipm_token: str | None = Header(default=None)):
    _auth(x_aipm_token)
    return {"ok": portfolio_io.remove_position(sid, token_id)}


# ── 策略文档 ──────────────────────────────────────────────────────────────────

class WriteDocPayload(BaseModel):
    sid: str
    content: str


class AppendDocPayload(BaseModel):
    sid: str
    content: str


@router.get("/doc/{sid}")
def internal_read_doc(sid: str, x_aipm_token: str | None = Header(default=None)):
    _auth(x_aipm_token)
    return {"content": strategy_doc_io.read(sid)}


@router.put("/doc")
async def internal_write_doc(payload: WriteDocPayload, x_aipm_token: str | None = Header(default=None)):
    _auth(x_aipm_token)
    strategy_doc_io.write(payload.sid, payload.content)
    await eb.event_bus.publish(payload.sid, {"kind": "doc_updated", "content": payload.content})
    return {"ok": True}


@router.post("/doc/append")
async def internal_append_doc(payload: AppendDocPayload, x_aipm_token: str | None = Header(default=None)):
    _auth(x_aipm_token)
    strategy_doc_io.append(payload.sid, payload.content)
    content = strategy_doc_io.read(payload.sid)
    await eb.event_bus.publish(payload.sid, {"kind": "doc_updated", "content": content})
    return {"ok": True}


# ── 定时任务 ──────────────────────────────────────────────────────────────────

class CronPayload(BaseModel):
    sid: str
    cron: str
    job_id: str | None = None


class OncePayload(BaseModel):
    sid: str
    run_at: str
    job_id: str | None = None


@router.post("/schedule/cron")
def internal_add_cron(payload: CronPayload, x_aipm_token: str | None = Header(default=None)):
    _auth(x_aipm_token)
    from backend import scheduler
    try:
        jid = scheduler.add_cron_job(payload.sid, payload.cron, payload.job_id)
        return {"job_id": jid}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/schedule/once")
def internal_add_once(payload: OncePayload, x_aipm_token: str | None = Header(default=None)):
    _auth(x_aipm_token)
    from backend import scheduler
    try:
        jid = scheduler.add_once_job(payload.sid, payload.run_at, payload.job_id)
        return {"job_id": jid}
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/schedule/{sid}")
def internal_list_schedule(sid: str, x_aipm_token: str | None = Header(default=None)):
    _auth(x_aipm_token)
    from backend import scheduler
    return scheduler.list_jobs(sid)


@router.delete("/schedule/{job_id}")
def internal_cancel_schedule(job_id: str, x_aipm_token: str | None = Header(default=None)):
    _auth(x_aipm_token)
    from backend import scheduler
    return {"ok": scheduler.cancel_job(job_id)}


# ── 余额 / 持仓 / 交易 ────────────────────────────────────────────────────────
#
# 这些端点只在 aipoly-core 里跑，它是唯一能读 /etc/aipoly/wallet.env 的组件。
# MCP 层（aipoly-mcp）被 InaccessiblePaths 挡在私钥之外，所以它不能自己下单，
# 只能把请求转发到这里。sim/live 闸门也在这一层——闸门必须和真正执行下单的
# 代码在同一个进程里，否则就是个摆设。

def _load_wallet_env():
    from backend.poly_config import load_app_env
    load_app_env()


@router.get("/balance")
def internal_balance(x_aipm_token: str | None = Header(default=None)):
    _auth(x_aipm_token)
    _load_wallet_env()
    from backend.api_client import get_balance_via_client
    result = get_balance_via_client()
    if result is None:
        raise HTTPException(503, "无法获取余额：钱包凭据缺失或 CLOB 不可达")
    return result


@router.get("/positions")
def internal_positions(size_threshold: str = "0", x_aipm_token: str | None = Header(default=None)):
    _auth(x_aipm_token)
    _load_wallet_env()
    from backend.api_client import get_positions
    from backend.poly_config import get_funder_address
    try:
        wallet = get_funder_address()
    except ValueError as e:
        raise HTTPException(503, str(e))
    return {"wallet": wallet, "positions": get_positions(wallet, size_threshold)}


class MarketOrderPayload(BaseModel):
    token_id: str
    amount: float          # BUY 时是 USDC 金额，SELL 时是 shares 数量


class LimitOrderPayload(BaseModel):
    token_id: str
    price: float
    size: float


def _sim_note(**extra):
    d = {
        "mode": "SIMULATION",
        "status": "simulated_success",
        "note": "⚠️ 模拟交易，未执行真实链上交易。改 AIPM_TRADE_MODE=live 启用真实交易。",
    }
    d.update(extra)
    return d


def _trade_mode():
    from backend.poly_config import get_trade_mode
    try:
        return get_trade_mode()
    except ValueError as e:
        raise HTTPException(500, str(e))


@router.post("/trade/market_buy")
def internal_market_buy(payload: MarketOrderPayload, x_aipm_token: str | None = Header(default=None)):
    _auth(x_aipm_token)
    _load_wallet_env()
    from backend.api_client import get_midpoint
    if _trade_mode() == "sim":
        mid = get_midpoint(payload.token_id)
        return _sim_note(
            token_id=payload.token_id, amount_usdc=payload.amount, price=mid,
            shares_received=round(payload.amount / mid, 4) if mid else 0,
        )
    from backend.trader import market_buy
    from backend.poly_config import Config
    return market_buy(payload.token_id, payload.amount, Config.from_file())


@router.post("/trade/market_sell")
def internal_market_sell(payload: MarketOrderPayload, x_aipm_token: str | None = Header(default=None)):
    _auth(x_aipm_token)
    _load_wallet_env()
    from backend.api_client import get_midpoint
    if _trade_mode() == "sim":
        mid = get_midpoint(payload.token_id)
        return _sim_note(
            token_id=payload.token_id, shares=payload.amount, price=mid,
            usdc_received=round(payload.amount * mid, 4) if mid else 0,
        )
    from backend.trader import market_sell
    from backend.poly_config import Config
    return market_sell(payload.token_id, payload.amount, Config.from_file())


@router.post("/trade/limit_buy")
def internal_limit_buy(payload: LimitOrderPayload, x_aipm_token: str | None = Header(default=None)):
    _auth(x_aipm_token)
    _load_wallet_env()
    if _trade_mode() == "sim":
        return _sim_note(token_id=payload.token_id, price=payload.price, size=payload.size, side="BUY")
    from backend.trader import limit_buy
    return limit_buy(payload.token_id, payload.price, payload.size)


@router.post("/trade/limit_sell")
def internal_limit_sell(payload: LimitOrderPayload, x_aipm_token: str | None = Header(default=None)):
    _auth(x_aipm_token)
    _load_wallet_env()
    if _trade_mode() == "sim":
        return _sim_note(token_id=payload.token_id, price=payload.price, size=payload.size, side="SELL")
    from backend.trader import limit_sell
    return limit_sell(payload.token_id, payload.price, payload.size)


@router.get("/orders")
def internal_list_orders(token_id: str = "", x_aipm_token: str | None = Header(default=None)):
    _auth(x_aipm_token)
    _load_wallet_env()
    from backend.trader import list_open_orders
    return list_open_orders(token_id or None)


@router.delete("/orders/{order_id}")
def internal_cancel_order(order_id: str, x_aipm_token: str | None = Header(default=None)):
    _auth(x_aipm_token)
    _load_wallet_env()
    from backend.trader import cancel_limit_order
    return cancel_limit_order(order_id)


@router.get("/trade_mode")
def internal_trade_mode(x_aipm_token: str | None = Header(default=None)):
    _auth(x_aipm_token)
    return {"mode": _trade_mode()}
