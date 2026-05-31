import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from backend.claude_runner import run_claude
from backend.event_bus import event_bus
from backend import chat_log, strategies as strat

router = APIRouter(prefix="/api/strategies/{sid}/chat", tags=["chat"])


class SendMessageRequest(BaseModel):
    message: str


@router.get("/history")
def get_history(sid: str, n: int = 50):
    if not strat.get_strategy(sid):
        raise HTTPException(404, "Strategy not found")
    return chat_log.read_recent(sid, n)


@router.post("/run")
async def run(sid: str):
    if not strat.get_strategy(sid):
        raise HTTPException(404, "Strategy not found")
    started = await run_claude(sid, trigger="manual")
    return {"started": started}


@router.post("/send")
async def send_message(sid: str, req: SendMessageRequest):
    if not strat.get_strategy(sid):
        raise HTTPException(404, "Strategy not found")
    now = datetime.now(timezone.utc).isoformat()
    user_event = {"kind": "user", "content": req.message, "ts": now}
    chat_log.append(sid, user_event)
    await event_bus.publish(sid, user_event)
    started = await run_claude(sid, trigger="chat", extra={"user_message": req.message})
    return {"started": started}


@router.delete("/history")
async def clear_history(sid: str):
    """清空该策略的全部聊天记录（删除所有 chat-*.jsonl 文件）。"""
    if not strat.get_strategy(sid):
        raise HTTPException(404, "Strategy not found")
    deleted = chat_log.clear_all(sid)
    await event_bus.publish(sid, {
        "kind": "history_cleared",
        "ts": datetime.now(timezone.utc).isoformat(),
        "deleted_files": deleted,
    })
    return {"ok": True, "deleted_files": deleted}


@router.get("/stream")
async def stream(sid: str):
    if not strat.get_strategy(sid):
        raise HTTPException(404, "Strategy not found")

    async def generate():
        async for event in event_bus.stream(sid):
            data = json.dumps(event, ensure_ascii=False)
            yield f"data: {data}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
