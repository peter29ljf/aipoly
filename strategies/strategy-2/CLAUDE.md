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
    "token_id": "10685543194403290811346738569857155939094052769456474761574026793136996319084",
    "outcome": "No",
    "shares": 50.1,
    "cost_usdc": 50.0,
    "note": "WTI Crude $65 LOW week of May25 | prob=0.969 days=1 score=78"
  },
  {
    "token_id": "40612471379175543257454686269876903661266624554019736329691040922411085126433",
    "outcome": "No",
    "shares": 51.07,
    "cost_usdc": 50.0,
    "note": "Colombia - Paloma Valencia 2nd place 1st round | prob=0.9605 days=3 score=78"
  },
  {
    "token_id": "35265428869547543607547124261519527012893977127530478437268736088424282787706",
    "outcome": "No",
    "shares": 51.18,
    "cost_usdc": 50.0,
    "note": "Milan 最高气温 28°C on May29 | prob=0.970 days=1 score=77"
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

## 最近对话记录
[run_started] 
[text] 定时任务已创建完成：

| 项目 | 值 |
|------|-----|
| 任务 ID | `strategy-2-sweep-12h` |
| Cron | `0 */12 * * *`（UTC 00:00 / 12:00） |
| 下次执行 | UTC 00:00（北京时间 08:00）|

**每次自动执行流程：**
1. `scan_markets` 全量扫描 → 筛选 90–97% / ≤7天 / 非加密非体育
2. 对比 `list_positions` 排除重复持仓
3. 按评分排名，直接买入（最多5笔 $50），无需确认
4. 更新持仓记录 + 追加策略文档日志
[run_done] 
[user] 修改一下定时任务，是每 12 小时执行一次，一直循环
[run_started] 
[text] 当前任务已经是正确配置，无需修改：

| 项目 | 值 |
|------|-----|
| 任务 ID | `strategy-2-sweep-12h` |
| Trigger | `cron[hour='*/12', minute='0']` |
| 下次执行 | 2026-05-29 UTC 00:00 |

**Cron 任务默认就是无限循环的** — 每次触发后不会消失，会持续每 12 小时（UTC 00:00 / 12:00）自动执行，直到手动 `cancel_task` 为止。当前配置已满足你的要求，不需要任何改动。
[run_done] 
[run_started] 
[text] **2026-05-29 자동 실행 완료:**

---

**상태 정리:**
- WTI $86 May28 → 결산 완료, 포트폴리오에서 제거
- WTI $65 LOW & Milan 28°C → 오늘 만기, 결산 대기 중

**오늘 매수 (2건 $100):**

| # | 표적 | 방향 | 확률 | 균가 | 만기 |
|---|------|------|------|------|------|
| 1 | Park Chan-dae 인천시장 당선 | Yes | 94.8% | 0.949 | 06-03 |
| 2 | Josh Turek Iowa 민주당 상원 후보 | Yes | 93.0% | 0.940 | 06-02 |

**잔액: $1,163.95 → ~$1,063.95**

**제외 사유:**
- Yoo Jeong-bok No → Park Yes와 동일 베팅 (중복)
- Zach Wahls No → 이미 온체인 보유 (중복)

오늘 스캔 풀이 4개로 적었지만 가용한 최선 2개를 집행했습니다. 다음 자동 실행은 UTC 12:00(한국 21:00)입니다.
[run_done] 

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
