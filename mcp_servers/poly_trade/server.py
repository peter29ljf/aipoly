"""poly_trade MCP：交易执行 + 价格查询 + 价格警报（端口 8101）。"""

import json
import sys
import os

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
sys.path.insert(0, "/root/aipolymarket")

from fastmcp import FastMCP
from mcp_servers._common import api_post, api_get, api_delete, sid as _env_sid


def _sid(strategy_id: str) -> str:
    return strategy_id.strip() or _env_sid()

# 加载 poly-trader 凭据
from backend.poly_config import load_app_env, Config
load_app_env()

from backend.api_client import get_midpoint as _get_mid, get_token_ids as _get_tids, get_positions as _get_pos, get_balance_via_client, get_book
from backend.trader import (
    market_buy as _buy, market_sell as _sell,
    limit_buy as _limit_buy, limit_sell as _limit_sell,
    list_open_orders as _list_open_orders, cancel_limit_order as _cancel_limit_order,
)

mcp = FastMCP("poly_trade")

# ── 交易模式 ──────────────────────────────────────────────────────────────
# 必须显式设置 AIPM_TRADE_MODE=sim 或 =live，未设置/拼写错误一律拒绝启动
# （宁可启动失败，也不能静默跑在错误的模式下）
_TRADE_MODE = os.environ.get("AIPM_TRADE_MODE", "").strip().lower()
if _TRADE_MODE not in ("sim", "live"):
    raise RuntimeError(
        f"AIPM_TRADE_MODE must be 'sim' or 'live', got {_TRADE_MODE!r}. "
        "Use restart_mcp.sh poly_trade or start.sh, which set this via data/mcp.env."
    )
_IS_SIM = (_TRADE_MODE == "sim")

if _IS_SIM:
    import logging
    logging.getLogger(__name__).warning(
        "⚠️  poly_trade 运行在【模拟交易模式】，market_buy/market_sell 不执行真实交易。"
        " 设置环境变量 AIPM_TRADE_MODE=live 启用真实交易。"
    )


@mcp.tool()
def market_buy(token_id: str, amount_usdc: float) -> str:
    """市价买入。token_id 为 outcome token ID，amount_usdc 为 USDC 金额。应用滑点保护。
    ⚠️ 模拟模式下不执行真实交易，返回模拟结果（AIPM_TRADE_MODE=live 才真实买入）。"""
    if _IS_SIM:
        mid = _get_mid(token_id)
        sim_shares = round(amount_usdc / mid, 4) if mid and mid > 0 else 0
        return json.dumps({
            "mode": "SIMULATION",
            "status": "simulated_success",
            "token_id": token_id,
            "amount_usdc": amount_usdc,
            "price": mid,
            "shares_received": sim_shares,
            "note": "⚠️ 模拟交易，未执行真实链上交易。设置 AIPM_TRADE_MODE=live 启用真实交易。",
        }, ensure_ascii=False)
    cfg = Config.from_file()
    result = _buy(token_id, amount_usdc, cfg)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def market_sell(token_id: str, shares: float) -> str:
    """市价卖出。shares 为持仓数量（非 USDC）。
    ⚠️ 模拟模式下不执行真实交易，返回模拟结果（AIPM_TRADE_MODE=live 才真实卖出）。"""
    if _IS_SIM:
        mid = _get_mid(token_id)
        sim_usdc = round(shares * mid, 4) if mid and mid > 0 else 0
        return json.dumps({
            "mode": "SIMULATION",
            "status": "simulated_success",
            "token_id": token_id,
            "shares": shares,
            "price": mid,
            "usdc_received": sim_usdc,
            "note": "⚠️ 模拟交易，未执行真实链上交易。设置 AIPM_TRADE_MODE=live 启用真实交易。",
        }, ensure_ascii=False)
    cfg = Config.from_file()
    result = _sell(token_id, shares, cfg)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def limit_buy(token_id: str, price: float, size: float) -> str:
    """挂限价买单（GTC，一直挂到成交或撤单为止，不会像市价单立即成交）。
    - token_id: outcome token ID
    - price: 出价，0-1 之间（如 0.35 表示每股 $0.35）
    - size: 购买 shares 数量
    ⚠️ 模拟模式下不执行真实挂单，返回模拟结果（AIPM_TRADE_MODE=live 才真实挂单）。"""
    if _IS_SIM:
        return json.dumps({
            "mode": "SIMULATION",
            "status": "simulated_success",
            "token_id": token_id,
            "price": price,
            "size": size,
            "side": "BUY",
            "note": "⚠️ 模拟挂单，未提交真实链上限价单。设置 AIPM_TRADE_MODE=live 启用真实交易。",
        }, ensure_ascii=False)
    result = _limit_buy(token_id, price, size)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def limit_sell(token_id: str, price: float, size: float) -> str:
    """挂限价卖单（GTC，一直挂到成交或撤单为止，不会像市价单立即成交）。
    - token_id: outcome token ID
    - price: 要价，0-1 之间（如 0.65 表示每股 $0.65）
    - size: 卖出 shares 数量
    ⚠️ 模拟模式下不执行真实挂单，返回模拟结果（AIPM_TRADE_MODE=live 才真实挂单）。"""
    if _IS_SIM:
        return json.dumps({
            "mode": "SIMULATION",
            "status": "simulated_success",
            "token_id": token_id,
            "price": price,
            "size": size,
            "side": "SELL",
            "note": "⚠️ 模拟挂单，未提交真实链上限价单。设置 AIPM_TRADE_MODE=live 启用真实交易。",
        }, ensure_ascii=False)
    result = _limit_sell(token_id, price, size)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def list_open_orders(token_id: str = "") -> str:
    """列出当前所有未成交的限价挂单，可选按 token_id 过滤。"""
    if _IS_SIM:
        return json.dumps({"mode": "SIMULATION", "orders": [], "note": "模拟模式下无真实挂单"}, ensure_ascii=False)
    result = _list_open_orders(token_id or None)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def cancel_limit_order(order_id: str) -> str:
    """撤销指定 order_id 的限价挂单。"""
    if _IS_SIM:
        return json.dumps({"mode": "SIMULATION", "status": "simulated_success", "order_id": order_id}, ensure_ascii=False)
    result = _cancel_limit_order(order_id)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def get_midpoint(token_id: str) -> str:
    """查询 token 当前中间价（概率），返回 0-1 之间的浮点数。"""
    mid = _get_mid(token_id)
    if mid is None:
        return json.dumps({"error": "无法获取中间价", "token_id": token_id})
    return json.dumps({"token_id": token_id, "mid": mid, "probability": f"{mid:.2%}"})


@mcp.tool()
def get_orderbook(token_id: str) -> str:
    """查询买卖盘深度（asks/bids）。"""
    book = get_book(token_id)
    if book is None:
        return json.dumps({"error": "无法获取订单簿", "token_id": token_id})
    asks = book.get("asks", [])[:5]
    bids = book.get("bids", [])[:5]
    return json.dumps({"token_id": token_id, "asks": asks, "bids": bids})


@mcp.tool()
def get_token_ids(slug: str) -> str:
    """从市场 slug 获取 token 列表（含 Yes/No 等 outcome）。"""
    result = _get_tids(slug)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def get_balance() -> str:
    """查询钱包 USDC.e 余额和授权额度。"""
    result = get_balance_via_client()
    if result is None:
        return json.dumps({"error": "无法获取余额，请检查 .env 配置"})
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def get_positions() -> str:
    """查询钱包当前全部持仓。"""
    import os
    wallet = os.environ.get("WALLET_ADDRESS", "").strip()
    if not wallet:
        return json.dumps({"error": "未配置 WALLET_ADDRESS"})
    positions = _get_pos(wallet, "0")
    return json.dumps({"wallet": wallet, "positions": positions}, ensure_ascii=False)


@mcp.tool()
def subscribe_price_alert(token_id: str, target: float, direction: str,
                          note: str = "", strategy_id: str = "") -> str:
    """⚠️ 设置真实价格警报（必须调用此工具，不能只写入 strategy.md）。
    - strategy_id: 策略目录名（如 'strategy-2'），必须传入
    - token_id: outcome token ID
    - target: 触发价格（0-1）
    - direction: 'above' 或 'below'
    触发后自动启动 Claude 运行本策略。UI 警报页面会显示设置的警报。"""
    try:
        result = api_post("/_internal/alerts", {
            "sid": _sid(strategy_id),
            "token_id": token_id,
            "target": target,
            "direction": direction,
            "note": note,
        })
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def list_price_alerts(strategy_id: str = "") -> str:
    """列出当前策略的所有活跃价格警报。strategy_id 为策略目录名。"""
    try:
        result = api_get(f"/_internal/alerts/{_sid(strategy_id)}")
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def cancel_price_alert(alert_id: int) -> str:
    """取消指定价格警报。"""
    try:
        result = api_delete(f"/_internal/alerts/{alert_id}")
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    port = int(os.environ.get("MCP_PORT", "8101"))
    mcp.run(transport="sse", host="0.0.0.0", port=port)
