"""每策略异步锁：保证同一时间只有一个 Claude 在运行。"""

import asyncio
from contextlib import asynccontextmanager
from collections import defaultdict

_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


@asynccontextmanager
async def strategy_lock(sid: str):
    lock = _locks[sid]
    async with lock:
        yield


def is_locked(sid: str) -> bool:
    lock = _locks.get(sid)
    return lock is not None and lock.locked()
