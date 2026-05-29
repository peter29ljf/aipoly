from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend import alerts_db, strategies as strat

router = APIRouter(prefix="/api/strategies/{sid}/alerts", tags=["alerts"])


class CreateAlertRequest(BaseModel):
    token_id: str
    target: float
    direction: str  # "above" | "below"
    note: str = ""


@router.get("")
def list_alerts(sid: str):
    if not strat.get_strategy(sid):
        raise HTTPException(404, "Strategy not found")
    return alerts_db.list_alerts(sid)


@router.post("")
def create_alert(sid: str, req: CreateAlertRequest):
    if not strat.get_strategy(sid):
        raise HTTPException(404, "Strategy not found")
    if req.direction not in ("above", "below"):
        raise HTTPException(400, "direction must be 'above' or 'below'")
    return alerts_db.create_alert(sid, req.token_id, req.target, req.direction, req.note)


@router.delete("/{alert_id}")
def cancel_alert(sid: str, alert_id: int):
    ok = alerts_db.cancel_alert(alert_id)
    if not ok:
        raise HTTPException(404, "Alert not found or already inactive")
    return {"ok": True}
