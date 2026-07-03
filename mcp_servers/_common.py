"""共享 HTTP/auth 工具，供所有 MCP 服务器使用。"""

import os
import httpx

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8010")
AIPM_TOKEN = os.environ.get("AIPM_TOKEN", "")
STRATEGY_ID = os.environ.get("STRATEGY_ID", "")

if not AIPM_TOKEN:
    raise RuntimeError(
        "AIPM_TOKEN not set — do not launch MCP servers directly; "
        "use restart_mcp.sh <name> or start.sh, which source data/mcp.env"
    )

TIMEOUT = 15.0


def _headers() -> dict:
    h = {"Content-Type": "application/json"}
    if AIPM_TOKEN:
        h["x-aipm-token"] = AIPM_TOKEN
    return h


def api_get(path: str, params: dict | None = None) -> dict:
    r = httpx.get(f"{API_BASE}{path}", params=params, headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def api_post(path: str, payload: dict) -> dict:
    r = httpx.post(f"{API_BASE}{path}", json=payload, headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def api_put(path: str, payload: dict) -> dict:
    r = httpx.put(f"{API_BASE}{path}", json=payload, headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def api_patch(path: str, payload: dict) -> dict:
    r = httpx.patch(f"{API_BASE}{path}", json=payload, headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def api_delete(path: str) -> dict:
    r = httpx.delete(f"{API_BASE}{path}", headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def sid() -> str:
    return STRATEGY_ID
