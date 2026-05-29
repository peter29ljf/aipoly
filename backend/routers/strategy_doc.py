from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend import strategy_doc_io, strategies as strat, event_bus as eb

router = APIRouter(prefix="/api/strategies/{sid}/doc", tags=["strategy_doc"])


class WriteDocRequest(BaseModel):
    content: str


class AppendDocRequest(BaseModel):
    content: str


@router.get("")
def get_doc(sid: str):
    if not strat.get_strategy(sid):
        raise HTTPException(404, "Strategy not found")
    return {"content": strategy_doc_io.read(sid)}


@router.put("")
async def write_doc(sid: str, req: WriteDocRequest):
    if not strat.get_strategy(sid):
        raise HTTPException(404, "Strategy not found")
    strategy_doc_io.write(sid, req.content)
    await eb.event_bus.publish(sid, {"kind": "doc_updated", "content": req.content})
    return {"ok": True}


@router.post("/append")
async def append_doc(sid: str, req: AppendDocRequest):
    if not strat.get_strategy(sid):
        raise HTTPException(404, "Strategy not found")
    strategy_doc_io.append(sid, req.content)
    content = strategy_doc_io.read(sid)
    await eb.event_bus.publish(sid, {"kind": "doc_updated", "content": content})
    return {"ok": True}
