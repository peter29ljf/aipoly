"""portfolio MCP：持仓 CRUD（端口 8102）。"""

import json
import os
import sys

sys.path.insert(0, "/root/aipolymarket")

from fastmcp import FastMCP
from mcp_servers._common import api_get, api_post, api_patch, api_delete, sid as _env_sid

mcp = FastMCP("portfolio")


def _sid(strategy_id: str) -> str:
    """优先用显式传入的 strategy_id，否则回退到环境变量。"""
    return strategy_id.strip() or _env_sid()


@mcp.tool()
def list_positions(strategy_id: str = "") -> str:
    """列出当前策略的所有本地持仓记录。strategy_id 为策略目录名（如 'strategy-2'）。"""
    try:
        result = api_get(f"/_internal/portfolio/{_sid(strategy_id)}")
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def add_position(token_id: str, outcome: str, shares: float, cost_usdc: float,
                 note: str = "", strategy_id: str = "") -> str:
    """添加持仓记录。
    - strategy_id: 策略目录名（如 'strategy-2'），必须传入
    - outcome: 结果名称（如 'Yes' / 'No'）
    - shares: token 数量
    - cost_usdc: 买入 USDC 成本
    """
    try:
        result = api_post("/_internal/portfolio", {
            "sid": _sid(strategy_id),
            "token_id": token_id,
            "outcome": outcome,
            "shares": shares,
            "cost_usdc": cost_usdc,
            "note": note,
        })
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def update_position(token_id: str, strategy_id: str = "",
                    shares: float | None = None, cost_usdc: float | None = None,
                    note: str | None = None) -> str:
    """更新持仓记录（部分字段）。strategy_id 为策略目录名。"""
    try:
        payload: dict = {"sid": _sid(strategy_id), "token_id": token_id}
        if shares is not None:
            payload["shares"] = shares
        if cost_usdc is not None:
            payload["cost_usdc"] = cost_usdc
        if note is not None:
            payload["note"] = note
        result = api_patch("/_internal/portfolio", payload)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def remove_position(token_id: str, strategy_id: str = "") -> str:
    """从本地记录中删除持仓。strategy_id 为策略目录名。"""
    try:
        result = api_delete(f"/_internal/portfolio/{_sid(strategy_id)}/{token_id}")
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    port = int(os.environ.get("MCP_PORT", "8102"))
    mcp.run(transport="sse", host="0.0.0.0", port=port)
