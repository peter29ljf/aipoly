from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend import strategies as strat

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


class CreateStrategyRequest(BaseModel):
    name: str
    description: str = ""


@router.get("")
def list_strategies():
    return strat.list_strategies()


@router.post("")
def create_strategy(req: CreateStrategyRequest):
    return strat.create_strategy(req.name, req.description)


@router.get("/{sid}")
def get_strategy(sid: str):
    s = strat.get_strategy(sid)
    if not s:
        raise HTTPException(404, "Strategy not found")
    return s


@router.delete("/{sid}")
def delete_strategy(sid: str):
    ok = strat.delete_strategy(sid)
    if not ok:
        raise HTTPException(404, "Strategy not found")
    return {"ok": True}
