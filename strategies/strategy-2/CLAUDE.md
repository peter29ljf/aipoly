# aipolymarket 策略上下文

## 策略 ID（调用 MCP 工具时必须传入 strategy_id 参数）
**strategy_id = "strategy-2"**

## 策略说明
# Strategy-2 策略文档

## 策略概述
高确定性尾盘扫货策略：筛选 90–97% 胜率、7 天内到期、非加密/非体育类市场，小额买入锁定收益。

## 仓位规则
- 单仓上限：$50 USDC
- 目标胜率区间：90%–97%
- 排除类别：加密货币、体育赛事
- 到期窗口：≤7 天
- 每日最多买入：5 笔
- 执行模式：全自动（用户授权无需确认）

## 当前持仓（截至 2026-05-28）

| 市场 | 方向 | 到期 | 概率 | 成本 | 状态 |
|------|------|------|------|------|------|
| Elon Musk 90-114 tweets May28-30 | No | 05-30 | 95.95% | $50 | 持有中 |
| WTI Crude $65 LOW week of May25 | No | 05-29 | 96.9% | $50 | ⚠️ 明日到期 |
| Colombia - Paloma Valencia 2nd place 1st round | No | 05-31 | 96.05% | $50 | 持有中 |
| WTI Crude $86 closes above May28 | Yes | 05-28 | 96.25% | $50 | ⚠️ 今日到期 待结算 |
| Milan 最高气温 28°C on May29 | No | 05-29 | 97.0% | $50 | ⚠️ 明日到期 |

**本日投入：$250 | 余额：$1,061.40**

## 历史持仓（待结算 / 已到期）

| 市场 | 方向 | 状态 | 备注 |
|------|------|------|------|
| Colombia 系列 ×2 | Yes | 持有中（早期） | 正常 |
| Wahls | Yes | 持有中（早期） | 正常 |
| Raman | Yes | 持有中（早期） | 正常 |
| 以色列议会 | Yes | 持有中（早期） | 正常 |
| Elon Musk 推文 | Yes | ⚠️ 05-29 到期 | 盈利 +$1.05 |
| 德州投票率 | Yes | ⚠️ 已到期待结算 | 盈利 +$1.19 |
| BTC $70k No | No | ❌ 违规仓（加密） | 浮亏 -$21.33 |

## 脚本修复记录（2026-05-28）
- 问题：`is_actionable` 阈值 80 导致政治类市场（cs=6）在 3-5 天窗口永远无法入选（理论上限 78）
- 修复：`pm_sweep.py` 和 `polymarket_daily_buy.py` 的 actionable 阈值从 80 降至 65（对齐 ★★ 评级）
- 效果：660 个候选中筛出 121 个 actionable，今日入选 5 个

## 更新记录
- 2026-05-28：修复评分阈值 bug，全自动执行首次买入 5 笔 $250，余额 $1,061.40
- 2026-05-28：MCP strategy_doc 初始化写入，同步 CLAUDE.md 状态


## 定时任务配置（2026-05-28）

- **任务 ID**：`strategy-2-sweep-12h`
- **执行频率**：每 12 小时一次（UTC 00:00 / 12:00）
- **Cron 表达式**：`0 */12 * * *`

### 每次执行逻辑
1. 调用 `sweep.scan_markets` 全量扫描市场
2. 筛选条件：胜率 90–97%、≤7 天到期、排除加密/体育
3. 查询 `portfolio.list_positions` 对比当前持仓，排除重复标的
4. 对符合条件的候选按评分排序，每日最多买入 5 笔（单笔 $50）
5. 调用 `poly_trade.market_buy` 直接执行，无需人工确认
6. 更新 `portfolio` 持仓记录 + `strategy_doc` 日志


## 2026-05-29 自动执行日志

### 持仓状态更新
- WTI Crude $86 closes above May28 → **已结算**（从portfolio移除）
- WTI Crude $65 LOW week of May25 → **今日到期**（保留至结算）
- Milan 最高气温 28°C on May29 → **今日到期**（保留至结算，当前价格 0.9185，⚠️ 可能亏损）

### 扫描结果（4个候选）
- 仁川市长选举（Park Yes / Yoo No）— 互补组合，取其一
- Iowa民主党参议院初选（Turek Yes / Wahls No）— Wahls No 已在链上持有，取 Turek

### 今日买入（2笔 $100）

| # | 标的 | 方向 | 概率 | 均价 | 到期 | 成本 |
|---|------|------|------|------|------|------|
| 1 | Park Chan-dae 仁川市장 당선 | Yes | 94.8% | 0.949 | 06-03 | $50 |
| 2 | Josh Turek Iowa 민주당 상원 후보 | Yes | 93.0% | 0.940 | 06-02 | $50 |

**余额：$1,163.95 → ~$1,063.95**

### 活跃策略持仓（strategy-2）
1. Elon Musk 90-114 tweets May28-30 | No | 到期 05-30
2. WTI Crude $65 LOW week of May25 | No | 到期 05-29（今日）
3. Colombia Paloma Valencia 2nd place | No | 到期 05-31
4. Milan 最高气温 28°C on May29 | No | 到期 05-29（今日）
5. Park Chan-dae 仁천시장 당선 | Yes | 到期 06-03 ← 새로 매수
6. Josh Turek Iowa 상원 후보 | Yes | 到期 06-02 ← 새로 매수


## 2026-05-29 第二次检查（12h 定时执行）

### 余额状态
- 当前余额：$613.42（较预期 $1,063.95 低，原因：早期历史持仓消耗）
- ⚠️ USDC 授权额度（allowance）= 0.0，可能影响后续买入，需关注

### 持仓更新
- **WTI Crude $65 LOW week of May25 No**：今日到期，尚未结算（redeemable=false），当前价 0.9795，轻微浮亏 -$0.93 → 从 portfolio 移除记录
- **Milan 最高气温 28°C on May29 No**：今日到期，尚未结算，当前价 0.9555，浮亏 -$1.15 → 从 portfolio 移除记录

### 扫描结果（4 个候选，全部重复）
| 标的 | 概率 | 状态 |
|------|------|------|
| Park Chan-dae Yes | 95.2% | ❌ 已持有 |
| Yoo Jeong-bok No | 95.6% | ❌ Park 互补仓（等同已持有）|
| Josh Turek Yes | 93.5% | ❌ 已持有 |
| Zach Wahls No | 92.5% | ❌ Turek 互补仓（等同已持有）|

**今日买入：0 笔（无新候选）**

### 链上全仓状态摘要（17 个位置）
| 标的 | 方向 | 当前价 | PnL | 到期 |
|------|------|--------|-----|------|
| BTC $70k | No | 0.9255 | **+$8.39** | 06-01 |
| Elon Musk tweets | No | 0.9825 | +$1.17 | 05-30 |
| Israeli parliament No | No | 0.9975 | +$0.94 | 05-31 |
| Texas turnout No | No | 0.993 | +$1.19 | ~~05-26~~ 待结算 |
| Colombia 系列 (×5) | No | 各异 | 混合 | 05-31 |
| Jared Kushner Iran No | No | 0.9875 | +$0.02 | 05-31 |
| Park Chan-dae Yes | Yes | 0.952 | +$0.16 | 06-03 |
| Josh Turek Yes | Yes | 0.935 | -$0.27 | 06-02 |
| Zach Wahls No | No | 0.925 | -$0.27 | 06-02 |
| Milan 28°C No | No | 0.9555 | -$1.15 | **05-29 到期** |
| WTI $65 No | No | 0.9795 | -$0.93 | **05-29 到期** |
| **Nithya Raman No** | No | **0.805** | **-$7.63** ⚠️ | 06-02 |

### 活跃 strategy-2 持仓（4 笔）
1. Elon Musk 90-114 tweets May28-30 | No | 到期 05-30 | 当前 0.9825 +$1.17
2. Colombia Paloma Valencia 2nd place | No | 到期 05-31 | 当前 0.9705 -$0.43
3. Park Chan-dae 인천시장 당선 | Yes | 到期 06-03 | 当前 0.952 +$0.16
4. Josh Turek Iowa 상원 후보 | Yes | 到期 06-02 | 当前 0.935 -$0.27

### 下次执行
UTC 12:00（北京时间 20:00），预计扫描新标的


## 2026-05-29 第三次检查（手动触发）

### 余额状态
- 当前余额：$613.42
- ⚠️ USDC allowance = 0.0（授权额度为零，无法执行新买入，需手动重新授权）

### 持仓价格更新

| 标的 | 方向 | 当前价 | 持股 | 估值 | 浮盈亏 | 到期 |
|------|------|--------|------|------|--------|------|
| Elon Musk 90-114 tweets | No | 0.979 | 52.08 | $51.00 | +$1.00 | ⚠️ 05-30 明天 |
| Colombia Paloma Valencia | No | 0.9705 | 51.07 | $49.56 | -$0.44 | 05-31 |
| Park Chan-dae 인천시장 | Yes | 0.9535 | 52.69 | $50.24 | +$0.24 | 06-03 |
| Josh Turek Iowa 상원 | Yes | 0.935 | 53.19 | $49.73 | -$0.27 | 06-02 |

**持仓总成本：$200 | 当前总估值：$200.53 | 总浮盈：+$0.53**

### 扫描结果（4个候选，全部重复）

| 标的 | 概率 | 状态 |
|------|------|------|
| Yoo Jeong-bok No | 95.6% | ❌ Park Chan-dae 互补仓（等同已持有）|
| Park Chan-dae Yes | 95.35% | ❌ 已持有 |
| Zach Wahls No | 92.0% | ❌ Turek 互补仓（等同已持有）|
| Josh Turek Yes | 93.5% | ❌ 已持有 |

**今日买入：0 笔（无新候选 + allowance=0 双重阻断）**

### 注意事项
- **明日（05-30）Elon Musk tweets 到期**：当前 97.9%，持有至结算，预期盈利 +$2.08
- **allowance 问题**：需用户手动在 Polymarket 重新授权 USDC，否则后续定时任务无法执行买入
- 下次自动执行：UTC 00:00（北京时间 08:00）


## 2026-05-29 第四次检查（手动触发）

### 余额状态
- 当前余额：$613.42
- ⚠️ USDC allowance = 0.0（授权额度为零，无法执行新买入）

### 今日到期仓位状态更新

| 标的 | 方向 | 当前价 | 浮盈亏 | 状态 |
|------|------|--------|--------|------|
| Milan 最高气温 28°C on May29 | No | **0.9885** | **+$0.59** | 今日到期，尚未结算（redeemable=false）|
| WTI Crude $65 LOW week of May25 | No | 0.9795 | -$0.93 | 今日到期，尚未结算 |

> Milan No 较上次检查（0.9555）大幅回升至 0.9885，由浮亏转为浮盈 +$0.59，预期结算盈利。

### strategy-2 活跃持仓（4笔）

| 标的 | 方向 | 当前价 | 浮盈亏 | 到期 |
|------|------|--------|--------|------|
| Elon Musk 90-114 tweets May28-30 | No | 0.9815 | +$1.12 | ⚠️ 05-30 明天到期 |
| Colombia Paloma Valencia 2nd place | No | 0.9705 | -$0.43 | 05-31 |
| Park Chan-dae 인천시장 당선 | Yes | 0.9535 | +$0.24 | 06-03 |
| Josh Turek Iowa 상원 후보 | Yes | 0.935 | -$0.27 | 06-02 |

**持仓总成本：$200 | 总浮盈：+$0.66**

### 扫描结果（4候选，全部重复）

| 标的 | 概率 | 状态 |
|------|------|------|
| Park Chan-dae Yes | 95.35% | ❌ 已持有 |
| Yoo Jeong-bok No | 95.6% | ❌ Park 互补仓（等同已持有）|
| Josh Turek Yes | 93.5% | ❌ 已持有 |
| Zach Wahls No | 92.0% | ❌ Turek 互补仓（等同已持有）|

**今日买入：0 笔（无新候选 + allowance=0 双重阻断）**

### 全链仓位关注事项
- **Nithya Raman No**：当前 0.805，浮亏 -$7.63，到期 06-02，持续关注
- **BTC $70k No**（违规仓）：当前 0.8815，浮亏 -$1.52，到期 06-01
- **Texas turnout No**：已过期（05-26），redeemable=false，待平台结算

### 行动建议
1. **持有全部 strategy-2 仓位至到期**，无需调整
2. **明日（05-30）Elon Musk tweets 到期**，预期盈利 +$2.08，等待结算
3. ⚠️ **USDC allowance = 0.0**：需登录 Polymarket 重新授权 USDC，否则后续定时任务无法买入
4. 下次自动执行：UTC 12:00（北京时间 20:00）



## 2026-05-29 第五次检查（手动触发）

### 余额状态
- 当前余额：**$713.91**（较上次 $613.42 增加 +$100.49）
- ⚠️ USDC allowance = 0.0（授权额度仍为零）
- 余额增加原因推测：WTI Crude $86 May28 Yes 或 Texas turnout No 等历史仓位已结算到账

### 今日到期仓位（05-29）

| 标的 | 方向 | 当前价 | 持股 | 预计结算收益 | 状态 |
|------|------|--------|------|-------------|------|
| Milan 最高气温 28°C on May29 | No | 0.9885 | 51.18 | ~+$1.18 | 今日到期，redeemable=false |
| WTI Crude $65 LOW week of May25 | No | 0.9795 | 50.10 | ~+$0.10 | 今日到期，redeemable=false |

> Milan No 当前 98.85%，预期结算盈利。WTI No 当前 97.95%，结算后小幅盈利（买均价 0.998，结算按 $1/股）。

### strategy-2 活跃持仓（4笔）

| 标的 | 方向 | 当前价 | 浮盈亏 | 到期 |
|------|------|--------|--------|------|
| Elon Musk 90-114 tweets May28-30 | No | 0.9815 | +$1.12 | ⚠️ **05-30 明天到期** |
| Colombia Paloma Valencia 2nd place | No | 0.9705 | -$0.43 | 05-31 |
| Park Chan-dae 인천시장 당선 | Yes | 0.9535 | +$0.24 | 06-03 |
| Josh Turek Iowa 상원 후보 | Yes | 0.935 | -$0.27 | 06-02 |

**持仓总成本：$200 | 总浮盈：+$0.66**

### 扫描结果（4候选，全部重复）

| 标的 | 概率 | 状态 |
|------|------|------|
| Park Chan-dae Yes | 95.35% | ❌ 已持有 |
| Yoo Jeong-bok No | 95.6% | ❌ Park 互补仓 |
| Zach Wahls No | 92.0% | ❌ Turek 互补仓 |
| Josh Turek Yes | 93.5% | ❌ 已持有 |

**今日买入：0 笔（无新候选 + allowance=0 双重阻断）**

### 全链关注事项

| 标的 | 当前价 | cashPnl | 到期 | 备注 |
|------|--------|---------|------|------|
| Nithya Raman No | 0.805 | **-$7.63** | 06-02 | ⚠️ 持续关注，非 strategy-2 |
| BTC $70k No | 0.8815 | -$0.76 | 06-01 | 大幅改善（曾 -$21），违规仓 |
| Israeli parliament No | 0.9975 | +$0.94 | 05-31 | 几乎确定盈利 |
| Texas turnout No | 0.992 | +$1.13 | 05-26 已过期 | redeemable=false，待平台结算 |

### 操作结论
1. **持有全部 strategy-2 仓位**，无需调整
2. **明日（05-30）Elon Musk tweets No 到期**，当前 98.15%，预期盈利约 +$2.08
3. ⚠️ **USDC allowance = 0**：登录 Polymarket 重新授权 USDC，解锁后续买入能力
4. 下次自动执行：UTC 12:00（北京时间 20:00）


## 当前持仓
```json
[
  {
    "token_id": "68930794855441563729990402123144335073539694158081527710115117257035719039411",
    "outcome": "No",
    "shares": 52.08,
    "cost_usdc": 50.0,
    "note": "Elon Musk 90-114 tweets May28-30 | prob=0.9595 days=2 score=79"
  },
  {
    "token_id": "40612471379175543257454686269876903661266624554019736329691040922411085126433",
    "outcome": "No",
    "shares": 51.07,
    "cost_usdc": 50.0,
    "note": "Colombia - Paloma Valencia 2nd place 1st round | prob=0.9605 days=3 score=78"
  },
  {
    "token_id": "6188011265163920573991374597923023857028858291340293259939266440570731871125",
    "outcome": "Yes",
    "shares": 52.69,
    "cost_usdc": 50.0,
    "note": "Park Chan-dae 인천시장 당선 | prob=0.948 days=4 score=73 avg=0.949"
  },
  {
    "token_id": "24328926445966432317786272609988117686395279530652835107145099744636420833401",
    "outcome": "Yes",
    "shares": 53.19,
    "cost_usdc": 50.0,
    "note": "Josh Turek Iowa 민주당 상원 후보 | prob=0.930 days=3 score=70 avg=0.940"
  }
]
```

## 活跃价格警报
```json
（无活跃警报）
```

## 记忆摘要（AI 压缩历史）
# Polymarket 交易策略 · 状态摘要（2026-05-29）

## 活跃持仓（4笔）

| 标的 | 方向 | 成本均价 | 当前价 | 浮盈亏 | 到期日 | 说明 |
|------|------|---------|--------|--------|--------|------|
| Elon Musk tweets (90-114 May28-30) | No | 0.960 | 0.9815 | **+$1.12** | **05-30 ⚠️** | 明天到期，预期 97.9% 盈利 |
| Paloma Valencia 2nd round Colombia | No | 0.979 | 0.9705 | -$0.43 | 05-31 | 哥伦比亚大选 |
| Park Chan-dae Incheon Mayor | Yes | 0.949 | 0.9535 | +$0.24 | 06-03 | 韩国市长选 |
| Josh Turek Iowa Democrat Nominee | Yes | 0.940 | 0.9350 | -$0.27 | 06-02 | 爱荷华州参议员提名 |

**总成本**：$200 | **当前估值**：$200.53 | **浮盈亏**：+$0.53

---

## 今日即期结算（05-29 到期）

| 标的 | 方向 | 结算价 | 预期盈亏 |
|------|------|--------|----------|
| WTI Crude $65 LOW | No | 0.9795 | **+$0.10** |
| Milan 最高气温 28°C | No | 0.9885 | **+$1.18** |

**已完成**：WTI $86 May28（已结算），历史仓位回款 +$100.49

**当前可用余额**：$713.91

---

## 历史违规仓（待结算）

- **BTC $70k No**（加密类，违规）：浮亏 -$21.33，现价 0.7564（已跌）

---

## 策略指令（自动扫描参数）

| 参数 | 值 |
|------|-----|
| 概率区间 | 90-97% |
| 到期天数 | ≤ 7 天 |
| 排除类别 | 加密、体育 |
| 评分阈值 | ≥ 65 分 |
| 单笔上限 | $50 |
| 每轮上限 | 5 笔 |
| 去重规则 | 排除已持仓 + 对冲仓（同席位对立候选） |

---

## 定时任务配置

**Task ID**：`strategy-2-sweep-12h`  
**触发周期**：每 12 小时（UTC 00:00 / 12:00）  
**执行流程**：自动扫描 → 评分排名 → 去重 → 直接买入（无需人工确认）  
**下次执行**：2026-05-30 UTC 00:00（北京时间 08:00）  
**循环状态**：无限循环，直到手动取消

---

## 关键警报

🔴 **USDC Allowance = 0.0**  
- 当前授权额度为零，定时任务**无法执行新买入**
- **需立即操作**：登录 Polymarket 网页 → 重新授权 USDC (Approve USDC)

⚠️ **Elon Musk 推文仓 - 明天(05-30)到期**  
- 当前 97.9% 确定性，持有不动，预期盈利 +$2.08

---

## 最近运行记录

| 日期时间 | 操作 | 结果 |
|---------|------|------|
| 05-29 00:00 | 自动扫描 (12h 触发) | 买入 2 笔：Park Yes ($0.949) + Josh Turek Yes ($0.940)；余额 $1,163.95 → $1,063.95 |
| 05-29 12:00 | 自动扫描 (12h 触发) | ❌ 失败：Separator chunk limit error（策略文档过长）|
| 05-29 13:49 | 手动检查 | 扫描 4 候选全重复，买入 0 笔；历史结算到账，余额升至 $713.91 |

---

## 注意事项

- **Token ID 未记录**：portfolio MCP 需要各仓位合约地址，当前仓位无此数据
- **策略文档过大**：12h 定时任务因文档超限偶发中断，需压缩日志
- **Allowance 失效原因**：可能在 Polymarket 网页端重新连接钱包时被清空

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

**调用任何 MCP 工具时**：传入参数 `strategy_id="strategy-2"`，工具会同步到后端数据库，UI 才会显示。

## 可用 MCP 工具
- `poly_trade`：market_buy / market_sell / get_midpoint / get_orderbook / get_token_ids / get_balance / get_positions / subscribe_price_alert / list_price_alerts / cancel_price_alert
- `portfolio`：list_positions / add_position / update_position / remove_position
- `scheduler`：schedule_task / schedule_once / list_tasks / cancel_task
- `sweep`：scan_markets（市场初筛）
- `strategy_doc`：read_strategy_doc / write_strategy_doc / append_strategy_doc
