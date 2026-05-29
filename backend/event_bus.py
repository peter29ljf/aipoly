"""Pub/Sub 事件总线：按策略 ID 分发事件给所有 SSE 订阅者。"""

import asyncio
from collections import defaultdict
from typing import AsyncIterator


class EventBus:
    def __init__(self):
        self._queues: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, sid: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._queues[sid].append(q)
        return q

    def unsubscribe(self, sid: str, q: asyncio.Queue):
        try:
            self._queues[sid].remove(q)
        except ValueError:
            pass

    async def publish(self, sid: str, event: dict):
        dead = []
        for q in self._queues.get(sid, []):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self.unsubscribe(sid, q)

    async def stream(self, sid: str) -> AsyncIterator[dict]:
        q = self.subscribe(sid)
        try:
            while True:
                event = await q.get()
                yield event
        finally:
            self.unsubscribe(sid, q)


event_bus = EventBus()
