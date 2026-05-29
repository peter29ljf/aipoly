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
