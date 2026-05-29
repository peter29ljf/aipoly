# aipolymarket 策略上下文

## 策略 ID（调用 MCP 工具时必须传入 strategy_id 参数）
**strategy_id = "btc"**

## 策略说明
# btc 期权

## 当前持仓
```json
（无持仓）
```

## 活跃价格警报
```json
[
  {
    "market_slug": "will-bitcoin-dip-to-70k-in-may-2026-438-356-919",
    "side": "no",
    "trigger_price": 0.05,
    "added": "2026-05-28",
    "action": {
      "type": "buy",
      "market_slug": "what-price-will-bitcoin-hit-before-2027",
      "outcome": "55000",
      "side": "no",
      "amount_usdc": 50,
      "note": "当 will-bitcoin-dip-to-70k No 价格跌至 0.05 时，立即买入 what-price-will-bitcoin-hit-before-2027 55000 No"
    },
    "note": "监控 will-bitcoin-dip-to-70k No 价格，触达 0.05 后执行条件买入"
  }
]
```

## 最近对话记录
[user] 监控will-bitcoin-dip-to-70k-in-may-2026-438-356-919，no
[ai] 已将该市场 No 方向加入活跃价格警报
[user] 修改策略，监控will-bitcoin-dip-to-70k-in-may-2026-438-356-919，no 的价格到 0.05 的时候，立即买入what-price-will-bitcoin-hit-before-2027 的 55000 的no
[ai] 已更新为条件买入警报：当 will-bitcoin-dip-to-70k No 价格 ≤ 0.05 时，立即买入 what-price-will-bitcoin-hit-before-2027 55000 No（$50 USDC）


## 当前持仓
```json
（无持仓）
```

## 活跃价格警报
```json
（无活跃警报）
```

## 最近对话记录
[run_done] 
[user] 重新用mcp重新设置警报，购买数量改成 300usdc
[run_started] 
[text] 无法设置此警报。`will-bitcoin-dip-to-70k-in-may-2026-438-356-919` 返回 **"未找到开放赛事"**，原因是：

- 今天是 2026-05-28，该市场（"BTC 5月内跌至70k"）**已临近到期或已结算**，不再是开放市场
- Polymarket 只能对开放交易中的市场设置价格警报

**需要你决定下一步：**

1. **放弃该警报** — 市场已过期，逻辑失效
2. **换一个监控标的** — 如果你想继续条件买入 `what-price-will-bitcoin-hit-before-2027 55000 No`，可以改为监控另一个 BTC 相关市场的价格信号
3. **直接查当前价格后手动决定** — 我可以立刻查 `what-price-will-bitcoin-hit-before-2027 55000 No` 的现价，你看是否值得直接入场

请告诉我如何处理？
[run_done] 
[user] 查what-price-will-bitcoin-hit-in-may-2026 70000 no 这个token
[run_started] 
[text] 找到了。`↓ 70,000 (No)` 的 token 信息如下：

| 字段 | 值 |
|------|-----|
| **Token ID** | `95485861341380608519980927436620979639471363690968268890982766249775308601106` |
| **Outcome** | No |
| **Market Slug** | `will-bitcoin-dip-to-70k-in-may-2026-438-356-919` |
| **Market ID** | `2132779` |
| **事件含义** | BTC 5月内是否会跌至 70,000（No = 不会跌到） |

需要查这个 token 的当前价格或挂单簿吗？
[run_done] 
[user] 修改策略并设置警报：当what-price-will-bitcoin-hit-in-may-2026 70000 no 这个token 价格到了0.05，买入what-price-will-bitcoin-hit-before-2027 55000 No 300usdc

## 用户当前消息
修改策略并设置警报：当what-price-will-bitcoin-hit-in-may-2026 70000 no 这个token 价格到了0.05，买入what-price-will-bitcoin-hit-before-2027 55000 No 300usdc

---
你是一个 Polymarket 自动交易 AI。根据上述策略说明和当前状态，决定下一步操作。

## ⚠️ 状态变更必须通过 MCP 工具，不能只写入 strategy.md

下面这些**状态变化**必须用对应 MCP 工具实际操作（不能只是在 strategy.md 里描述）：

| 用户意图 | 必须调用的 MCP 工具 | 不能仅做 |
|----------|---------------------|----------|
| 设置价格警报 | `mcp__poly_trade__subscribe_price_alert` | ❌ 只写进 strategy.md |
| 添加/更新/删除持仓 | `mcp__portfolio__add_position` / `update_position` / `remove_position` | ❌ 只写进 strategy.md |
| 创建定时任务 | `mcp__scheduler__schedule_task` / `schedule_once` | ❌ 只写进 strategy.md |
| 买卖交易 | `mcp__poly_trade__market_buy` / `market_sell` | ❌ 只写进 strategy.md |
| 修改策略说明文档 | `mcp__strategy_doc__write_strategy_doc` / `append_strategy_doc` | ❌ 直接修改本地文件 |

**调用任何 MCP 工具时**：传入参数 `strategy_id="btc"`，工具会同步到后端数据库，UI 才会显示。

## 可用 MCP 工具
- `poly_trade`：market_buy / market_sell / get_midpoint / get_orderbook / get_token_ids / get_balance / get_positions / subscribe_price_alert / list_price_alerts / cancel_price_alert
- `portfolio`：list_positions / add_position / update_position / remove_position
- `scheduler`：schedule_task / schedule_once / list_tasks / cancel_task
- `sweep`：scan_markets（市场初筛）
- `strategy_doc`：read_strategy_doc / write_strategy_doc / append_strategy_doc
