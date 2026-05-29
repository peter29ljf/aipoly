"""strategy_doc MCP：策略文档读写（端口 8105）。AI 可完整读写 strategy.md。"""

import json
import os
import sys

sys.path.insert(0, "/root/aipolymarket")

from fastmcp import FastMCP
from mcp_servers._common import api_get, api_post, api_put, sid as _env_sid

mcp = FastMCP("strategy_doc")


def _sid(strategy_id: str) -> str:
    return strategy_id.strip() or _env_sid()


@mcp.tool()
def read_strategy_doc(strategy_id: str = "") -> str:
    """读取当前策略的 strategy.md 全文内容。strategy_id 为策略目录名（如 'strategy-2'）。"""
    try:
        result = api_get(f"/_internal/doc/{_sid(strategy_id)}")
        return result.get("content", "")
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def write_strategy_doc(content: str, strategy_id: str = "") -> str:
    """覆盖写入 strategy.md（适合 AI 从零制定策略或全面重构策略说明）。
    strategy_id 为策略目录名（如 'strategy-2'），写入后 UI 侧边栏自动刷新。"""
    try:
        result = api_put("/_internal/doc", {"sid": _sid(strategy_id), "content": content})
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def append_strategy_doc(content: str, strategy_id: str = "") -> str:
    """在 strategy.md 末尾追加内容（适合记录决策日志、参数变更说明等）。
    strategy_id 为策略目录名，写入后 UI 侧边栏自动刷新。"""
    try:
        result = api_post("/_internal/doc/append", {"sid": _sid(strategy_id), "content": content})
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    port = int(os.environ.get("MCP_PORT", "8105"))
    mcp.run(transport="sse", host="0.0.0.0", port=port)
