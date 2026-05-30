import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from backend import strategies as strat
from backend.event_bus import event_bus

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
async def delete_strategy(sid: str):
    """启动 AI 辅助异步清理，立即返回 cleaning=True，前端订阅 cleanup-stream 查看进度。"""
    s = strat.get_strategy(sid)
    # 策略目录可能已被手动删除，但仍需清理 DB 孤儿数据
    if not s and not (strat.STRATEGIES_DIR / sid).exists():
        # 尝试清理 DB 孤儿数据
        asyncio.create_task(strat.async_cleanup_and_delete(sid))
        return {"ok": True, "cleaning": True}
    if not s:
        raise HTTPException(404, "Strategy not found")
    asyncio.create_task(strat.async_cleanup_and_delete(sid))
    return {"ok": True, "cleaning": True}


@router.get("/{sid}/cleanup-stream")
async def cleanup_stream(sid: str):
    """SSE 流：推送策略清理进度，直到收到 deleted 或 error 事件。"""
    async def generate():
        q = event_bus.subscribe(f"cleanup:{sid}")
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=60)
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    if event.get("type") in ("deleted", "error"):
                        break
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        finally:
            event_bus.unsubscribe(f"cleanup:{sid}", q)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
