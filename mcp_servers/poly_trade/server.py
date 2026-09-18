"""poly_trade MCP：交易执行 + 价格查询 + 价格警报（端口 8101）。"""

import json
import sys
import os

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
sys.path.insert(0, "/root/aipolymarket")

from fastmcp import FastMCP
from mcp_servers._common import api_post, api_get, api_delete, sid as _env_sid, TRADE_TIMEOUT


def _sid(strategy_id: str) -> str:
    return strategy_id.strip() or _env_sid()

# 只导入不需要私钥的行情函数——它们打的是 Polymarket 公开接口。
# 凡是要签名的（下单、撤单、查余额/持仓）一律转发到 aipoly-core：本进程以
# aipoly-mcp 身份运行，unit 里 InaccessiblePaths=/etc/aipoly/wallet.env 明确
# 挡掉了私钥。早先这里直接 `from backend.trader import ...` 本地执行，于是那条
# 隔离声明形同虚设——进程根本拿不到密钥，所有交易工具静默失效。
from backend.api_client import get_midpoint as _get_mid, get_token_ids as _get_tids, get_book

mcp = FastMCP("poly_trade")

# ── 交易模式 ──────────────────────────────────────────────────────────────
# sim/live 的判定已移到 aipoly-core（真正持私钥、真正下单的那一层）。这里不再
# 自己判断：同一个开关有两处真源，不一致时没人知道哪个算数。本进程只如实转述。


def _mode() -> str:
    try:
        return (api_get("/_internal/trade_mode") or {}).get("mode", "unknown")
    except Exception:
        return "unknown"


@mcp.tool()
def market_buy(token_id: str, amount_usdc: float) -> str:
    """市价买入。token_id 为 outcome token ID，amount_usdc 为 USDC 金额。应用滑点保护。
    ⚠️ 模拟模式下不执行真实交易，返回模拟结果（AIPM_TRADE_MODE=live 才真实买入）。"""
    return json.dumps(api_post("/_internal/trade/market_buy",
                               {"token_id": token_id, "amount": amount_usdc},
                               timeout=TRADE_TIMEOUT),
                      ensure_ascii=False)

@mcp.tool()
def market_sell(token_id: str, shares: float) -> str:
    """市价卖出。shares 为持仓数量（非 USDC）。
    ⚠️ 模拟模式下不执行真实交易，返回模拟结果（AIPM_TRADE_MODE=live 才真实卖出）。"""
    return json.dumps(api_post("/_internal/trade/market_sell",
                               {"token_id": token_id, "amount": shares},
                               timeout=TRADE_TIMEOUT),
                      ensure_ascii=False)

@mcp.tool()
def limit_buy(token_id: str, price: float, size: float) -> str:
    """挂限价买单（GTC，一直挂到成交或撤单为止，不会像市价单立即成交）。
    - token_id: outcome token ID
    - price: 出价，0-1 之间（如 0.35 表示每股 $0.35）
    - size: 购买 shares 数量
    ⚠️ 模拟模式下不执行真实挂单，返回模拟结果（AIPM_TRADE_MODE=live 才真实挂单）。"""
    return json.dumps(api_post("/_internal/trade/limit_buy",
                               {"token_id": token_id, "price": price, "size": size},
                               timeout=TRADE_TIMEOUT),
                      ensure_ascii=False)

@mcp.tool()
def limit_sell(token_id: str, price: float, size: float) -> str:
    """挂限价卖单（GTC，一直挂到成交或撤单为止，不会像市价单立即成交）。
    - token_id: outcome token ID
    - price: 要价，0-1 之间（如 0.65 表示每股 $0.65）
    - size: 卖出 shares 数量
    ⚠️ 模拟模式下不执行真实挂单，返回模拟结果（AIPM_TRADE_MODE=live 才真实挂单）。"""
    return json.dumps(api_post("/_internal/trade/limit_sell",
                               {"token_id": token_id, "price": price, "size": size},
                               timeout=TRADE_TIMEOUT),
                      ensure_ascii=False)

@mcp.tool()
def list_open_orders(token_id: str = "") -> str:
    """列出当前所有未成交的限价挂单，可选按 token_id 过滤。"""
    return json.dumps(api_get("/_internal/orders", params={"token_id": token_id}),
                      ensure_ascii=False)


@mcp.tool()
def cancel_limit_order(order_id: str) -> str:
    """撤销指定 order_id 的限价挂单。"""
    return json.dumps(api_delete(f"/_internal/orders/{order_id}"), ensure_ascii=False)


@mcp.tool()
def get_midpoint(token_id: str) -> str:
    """查询 token 当前中间价（概率），返回 0-1 之间的浮点数。"""
    mid = _get_mid(token_id)
    if mid is None:
        return json.dumps({"error": "无法获取中间价", "token_id": token_id})
    return json.dumps({"token_id": token_id, "mid": mid, "probability": f"{mid:.2%}"})


@mcp.tool()
def get_orderbook(token_id: str) -> str:
    """查询买卖盘深度（asks/bids），最优档在前。"""
    book = get_book(token_id)
    if book is None:
        return json.dumps({"error": "无法获取订单簿", "token_id": token_id})
    # CLOB 返回的 asks 是价格**降序**、bids 是**升序**——两边都是最差档在前。
    # 原来直接 [:5] 取前五，于是把最差的五档当成盘口报给 agent：买方看到的
    # "最优卖价"是 0.995 而真实是 0.97，中间还显出一大段假的真空。agent 据此
    # 判定数据自相矛盾、拒绝下单（判断没错，是这里在骗它）。
    # trader.py 的下单路径各自排过序，所以真实成交价不受影响，只有这个展示工具错。
    asks = sorted(book.get("asks") or [], key=lambda x: float(x.get("price") or 0))
    bids = sorted(book.get("bids") or [], key=lambda x: float(x.get("price") or 0), reverse=True)
    out = {
        "token_id": token_id,
        "asks": asks[:5],           # 升序：最低卖价在前
        "bids": bids[:5],           # 降序：最高买价在前
        "best_ask": float(asks[0]["price"]) if asks else None,
        "best_bid": float(bids[0]["price"]) if bids else None,
    }
    if out["best_ask"] is not None and out["best_bid"] is not None:
        out["spread"] = round(out["best_ask"] - out["best_bid"], 4)
    return json.dumps(out, ensure_ascii=False)


@mcp.tool()
def get_token_ids(slug: str) -> str:
    """从市场 slug 获取 token 列表（含 Yes/No 等 outcome）。"""
    result = _get_tids(slug)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def get_balance() -> str:
    """查询钱包抵押品（pUSD）余额和授权额度，以及当前交易模式。"""
    try:
        r = api_get("/_internal/balance")
    except Exception as e:
        return json.dumps({"error": f"无法获取余额：{e}"}, ensure_ascii=False)
    r["trade_mode"] = _mode()
    return json.dumps(r, ensure_ascii=False)


@mcp.tool()
def get_positions() -> str:
    """查询钱包当前全部持仓。"""
    try:
        return json.dumps(api_get("/_internal/positions"), ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"无法获取持仓：{e}"}, ensure_ascii=False)


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
    # 默认只监听回环。这些服务没有任何认证，任何能连上的人都能
    # 以服务自带的 AIPM_TOKEN 调用内部 API。远程访问请用 SSH 隧道：
    #   ssh -L 8101:127.0.0.1:8101 root@<host>
    host = os.environ.get("MCP_HOST", "127.0.0.1")
    mcp.run(transport="sse", host=host, port=port)
