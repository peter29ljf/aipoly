"""MCP 服务器健康检查。"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/health", tags=["health"])

# ── Cache ─────────────────────────────────────────────────────────────────────
_cache: dict[str, Any] = {}
_CACHE_TTL = 30  # seconds


def _cached(key: str) -> dict | None:
    entry = _cache.get(key)
    if entry and time.time() - entry["ts"] < _CACHE_TTL:
        return entry["data"]
    return None


def _store(key: str, data: dict) -> dict:
    _cache[key] = {"ts": time.time(), "data": data}
    return data


# ── MCP SSE server ping ───────────────────────────────────────────────────────

MCP_SERVERS = {
    "poly-trade":    8101,
    "portfolio":     8102,
    "scheduler":     8103,
    "sweep":         8104,
    "strategy-doc":  8105,
}


async def _ping_port(name: str, port: int, timeout: float = 3.0) -> dict:
    cached = _cached(f"mcp_{name}")
    if cached:
        return cached

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection("127.0.0.1", port),
            timeout=timeout,
        )
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return _store(f"mcp_{name}", {"status": "ok", "detail": f":{port}"})
    except (ConnectionRefusedError, asyncio.TimeoutError, OSError):
        return _store(f"mcp_{name}", {"status": "error", "detail": f":{port} 未响应"})
    except Exception as e:
        return _store(f"mcp_{name}", {"status": "error", "detail": str(e)[:80]})


# ── Scheduler job count ───────────────────────────────────────────────────────

def _check_scheduler_jobs() -> dict:
    cached = _cached("scheduler_jobs")
    if cached:
        return cached
    try:
        from backend import scheduler as _sch
        jobs = _sch.list_jobs()
        return _store("scheduler_jobs", {"jobs": len(jobs)})
    except Exception:
        return _store("scheduler_jobs", {"jobs": None})


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.get("/mcp")
async def mcp_health():
    """并发 ping 所有 MCP 服务器，返回各自状态（30s 缓存）。"""
    results = await asyncio.gather(*[
        _ping_port(name, port) for name, port in MCP_SERVERS.items()
    ])
    sched_info = _check_scheduler_jobs()

    out: dict[str, Any] = {}
    for (name, _), res in zip(MCP_SERVERS.items(), results):
        entry = dict(res)
        if name == "scheduler":
            entry["jobs"] = sched_info.get("jobs")
        out[name] = entry
    return out
