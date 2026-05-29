from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend import portfolio_io, strategies as strat

router = APIRouter(prefix="/api/strategies/{sid}/portfolio", tags=["portfolio"])


class AddPositionRequest(BaseModel):
    token_id: str
    outcome: str
    shares: float
    cost_usdc: float
    note: str = ""


class UpdatePositionRequest(BaseModel):
    shares: float | None = None
    cost_usdc: float | None = None
    note: str | None = None


@router.get("")
def list_positions(sid: str):
    if not strat.get_strategy(sid):
        raise HTTPException(404, "Strategy not found")
    return portfolio_io.list_positions(sid)


@router.post("")
def add_position(sid: str, req: AddPositionRequest):
    if not strat.get_strategy(sid):
        raise HTTPException(404, "Strategy not found")
    return portfolio_io.add_position(sid, req.token_id, req.outcome, req.shares, req.cost_usdc, req.note)


@router.patch("/{token_id:path}")
def update_position(sid: str, token_id: str, req: UpdatePositionRequest):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    pos = portfolio_io.update_position(sid, token_id, **updates)
    if not pos:
        raise HTTPException(404, "Position not found")
    return pos


@router.delete("/{token_id:path}")
def remove_position(sid: str, token_id: str):
    ok = portfolio_io.remove_position(sid, token_id)
    if not ok:
        raise HTTPException(404, "Position not found")
    return {"ok": True}
