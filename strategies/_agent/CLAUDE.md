# aipolymarket 策略上下文

## 策略 ID（调用 MCP 工具时必须传入 strategy_id 参数）
**strategy_id = "_agent"**

## 策略说明


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
[user] 你好，简短说一句
[run_started] 
[text] 你好！准备好扫描市场、执行策略，有什么需要？
[run_done] 
[user] 你有什么mcp 工具，列表
[run_started] 
[text] 以下是可用的 MCP 工具列表：

## poly_trade（交易与行情）
- `get_balance` — 查询账户余额
- `get_positions` — 查询当前持仓
- `get_orderbook` — 查询订单簿
- `get_midpoint` — 查询中间价
- `get_token_ids` — 查询市场 token ID
- `market_buy` — 市价买入
- `market_sell` — 市价卖出
- `subscribe_price_alert` — 设置价格警报
- `list_price_alerts` — 列出价格警报
- `cancel_price_alert` — 取消价格警报

## portfolio（持仓管理）
- `add_position` — 添加持仓记录
- `list_positions` — 列出所有持仓
- `update_position` — 更新持仓信息
- `remove_position` — 删除持仓记录

## scheduler（定时任务）
- `schedule_task` — 创建定时任务（cron）
- `schedule_once` — 创建一次性定时任务
- `list_tasks` — 列出所有定时任务
- `cancel_task` — 取消定时任务

## sweep（市场扫描）
- `scan_markets` — 扫描市场，筛选高胜率标的

## strategy_doc（策略文档）
- `read_strategy_doc` — 读取策略文档
- `write_strategy_doc` — 写入策略文档
- `append_strategy_doc` — 追加策略文档内容

## Google Drive（文件管理）
- `read_file_content` / `download_file_content` — 读取文件
- `create_file` / `copy_file` — 创建/复制文件
- `search_files` / `list_recent_files` — 搜索/列出文件
- `get_file_metadata` / `get_file_permissions` — 查询文件信息
[run_done] 
[user] 卖出what-price-will-bitcoin-hit-in-may-2026 70000 一半仓位

## 用户当前消息
卖出what-price-will-bitcoin-hit-in-may-2026 70000 一半仓位

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

**调用任何 MCP 工具时**：传入参数 `strategy_id="_agent"`，工具会同步到后端数据库，UI 才会显示。

## 可用 MCP 工具
- `poly_trade`：market_buy / market_sell / get_midpoint / get_orderbook / get_token_ids / get_balance / get_positions / subscribe_price_alert / list_price_alerts / cancel_price_alert
- `portfolio`：list_positions / add_position / update_position / remove_position
- `scheduler`：schedule_task / schedule_once / list_tasks / cancel_task
- `sweep`：scan_markets（市场初筛）
- `strategy_doc`：read_strategy_doc / write_strategy_doc / append_strategy_doc
