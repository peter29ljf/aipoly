# aipoly

基于 Claude CLI 的 Polymarket 自动交易系统。AI 策略代理通过 MCP 工具执行真实链上交易，支持 Web UI 管理、定时自动运行、活动时间线追踪。

## 架构

```
┌─────────────────────────────────────┐
│  前端 React/Vite  (port 5173/dev)   │
└────────────────┬────────────────────┘
                 │ REST API
┌────────────────▼────────────────────┐
│  后端 FastAPI        (port 8010)    │
│  APScheduler 定时器                 │
│  SQLite (alerts.db / scheduler.db)  │
└──────┬──────────────────────────────┘
       │ 启动子进程
┌──────▼──────────────────────────────┐
│  claude CLI  (-p prompt --mcp-config)│
└──────┬──────────────────────────────┘
       │ MCP SSE
┌──────▼──────────────────────────────┐
│  MCP 服务器群                        │
│  8101 poly_trade  (真实/模拟交易)    │
│  8102 portfolio   (持仓记录)         │
│  8103 scheduler   (定时任务)         │
│  8104 sweep       (市场扫描)         │
│  8105 strategy_doc (策略文档)        │
└─────────────────────────────────────┘
```

---

## 新服务器完整安装步骤

### 1. 系统依赖

```bash
apt update
apt install -y python3.12-venv nodejs npm
```

### 2. 克隆项目

```bash
git clone https://github.com/peter29ljf/aipoly.git
cd aipoly
```

### 3. Python 虚拟环境 & 依赖

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 4. 前端依赖

```bash
cd frontend && npm install && cd ..
```

### 5. 安装 Claude CLI

```bash
curl -fsSL https://claude.ai/install.sh | bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
export PATH="$HOME/.local/bin:$PATH"
claude --version   # 验证
```

### 6. 登录 Claude（必须，只需一次）

```bash
claude
# 按提示完成浏览器登录授权
# 登录成功后 Ctrl+C 退出
```

> Claude CLI 需要登录才能运行策略。授权信息保存在 `~/.claude/`，服务器重启后无需重新登录。

### 7. 配置 Polymarket 钱包凭据

```bash
mkdir -p data
cat > data/.env << 'EOF'
CLOB_API_KEY=你的API密钥
CLOB_SECRET=你的API密钥Secret
CLOB_PASS_PHRASE=你的API密钥Passphrase
PRIVATE_KEY=你的钱包私钥（不含0x前缀）
WALLET_ADDRESS=0x你的钱包地址
CLOB_HOST=https://clob.polymarket.com
EOF
```

**如何获取 Polymarket API 凭据：**
1. 登录 [polymarket.com](https://polymarket.com) 并完成 KYC
2. 钱包地址即你的 Polygon 钱包地址
3. 私钥从钱包导出（MetaMask → 账户详情 → 导出私钥）
4. API Key/Secret/Passphrase 通过私钥自动派生，可用 `py-clob-client` 生成：

```bash
.venv/bin/python3 -c "
from py_clob_client_v2 import ClobClient
client = ClobClient(
    host='https://clob.polymarket.com',
    key='你的私钥',
    chain_id=137
)
creds = client.create_or_derive_api_key()
print('CLOB_API_KEY=', creds.api_key)
print('CLOB_SECRET=', creds.api_secret)
print('CLOB_PASS_PHRASE=', creds.api_passphrase)
"
```

### 8. 修复 start.sh 路径（已在 git 中修复，首次克隆无需此步）

确认 `start.sh` 第 4 行为：
```bash
cd /root/aipoly
```

### 9. 启动所有服务

```bash
# 修改 start.sh 使其在后台运行
bash start.sh &

# 等待后端启动（约 5 秒）
sleep 5

# 验证后端
curl http://localhost:8010/health
# 应返回：{"status":"ok"}
```

### 10. 启动前端（开发模式）

```bash
# 外网访问需要 --host
nohup frontend/node_modules/.bin/vite --host 0.0.0.0 --root frontend > /tmp/vite.log 2>&1 &
```

或进入目录启动：
```bash
cd frontend && nohup npm run dev -- --host 0.0.0.0 > /tmp/vite.log 2>&1 &
```

### 11. 开放防火墙端口

在云服务商控制台（安全组/防火墙）开放以下入站 TCP 端口：

| 端口 | 用途 |
|------|------|
| 5173 | 前端 Web UI |
| 8010 | 后端 API |

### 12. 访问与登录

- **Web UI**：`http://服务器IP:5173`
- **后端 API 文档**：`http://服务器IP:8010/docs`

默认账号：

| 用户名 | 密码 | 权限 |
|--------|------|------|
| `admin` | `12340987` | 完整管理 |
| `guest` | `guest` | 只读查看 |

> 建议在 `frontend/src/AuthContext.tsx` 中修改默认密码后重新构建前端。

### 13. 启用真实交易模式

`start.sh` 会自动生成 `data/mcp.env`（唯一环境变量真源，包含 `AIPM_TRADE_MODE=live`），poly_trade MCP 启动时会 source 这个文件。**不需要也不应该手动编辑它**——每次 `bash start.sh` 都会重新生成。

验证：
```bash
# 查余额，有返回值说明凭据正确 + API 连通 + 真实交易模式已启用
curl http://localhost:8010/api/strategies/_agent/portfolio
```

---

## 日常运维

### ⚠️ 重启单个 MCP 服务器

**永远使用 `restart_mcp.sh`，不要手动拼接 `python3 -m mcp_servers.X.server` 命令。**
手动拼接容易漏传 `AIPM_TOKEN` 或 `AIPM_TRADE_MODE`，导致 API 调用静默返回 403，或交易静默退化为模拟模式。

```bash
cd /root/aipoly
bash restart_mcp.sh poly_trade      # 或 portfolio / scheduler / sweep / strategy_doc
```

该脚本会自动从 `data/mcp.env` 加载完整环境变量、杀掉旧进程、重新启动，并把日志写到 `/tmp/<name>_mcp.log`。

如果 `data/mcp.env` 中的 `AIPM_TOKEN` 为空或 `AIPM_TRADE_MODE` 不是 `sim`/`live`，MCP 服务器会**立即崩溃退出**并打印明确错误，而不是静默带着错误配置运行。

### 重启所有服务

```bash
# 停止
pkill -f "uvicorn backend.main" || true
pkill -f "mcp_servers" || true
pkill -f "vite" || true

# 启动（会自动重新生成 data/mcp.env）
cd /root/aipoly
bash start.sh &
sleep 5
cd frontend && nohup npm run dev -- --host 0.0.0.0 > /tmp/vite.log 2>&1 &
```

### 查看日志

```bash
tail -f /tmp/backend.log      # 后端日志
tail -f /tmp/vite.log         # 前端日志
tail -f /tmp/poly_trade_mcp.log  # 交易 MCP 日志
```

### 查看 AI 策略运行记录

```bash
cat strategies/_agent/logs/chat-$(date +%Y-%m-%d).jsonl | python3 -c "
import sys, json
for line in sys.stdin:
    d = json.loads(line)
    if d.get('kind') in ('run_started','run_done','text'):
        print(d['kind'], '|', str(d.get('content',''))[:100])
"
```

---

## MCP 服务器说明

| 端口 | 名称 | 工具 |
|------|------|------|
| 8101 | poly_trade | market_buy / market_sell / get_midpoint / get_balance / get_positions / get_token_ids / subscribe_price_alert |
| 8102 | portfolio | list_positions / add_position / update_position / remove_position |
| 8103 | scheduler | schedule_task / schedule_once / list_tasks / cancel_task |
| 8104 | sweep | scan_markets / list_event_categories |
| 8105 | strategy_doc | read_strategy_doc / write_strategy_doc / append_strategy_doc |

**注意**：`schedule_task` 调用时 `strategy_id` 为必填第一参数，必须传入策略 ID（如 `_agent` 或 `strategy`），否则任务不会显示在 UI 中。

---

## 环境变量说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `AIPM_TRADE_MODE` | `live` 真实交易 / `sim` 模拟 | `sim` |
| `BACKEND_PORT` | 后端监听端口 | `8010` |
| `MCP_PORT` | MCP 服务器端口（各服务器独立设置） | 见 start.sh |
| `AIPM_TOKEN` | 内部认证 token（自动生成） | — |
| `API_BASE` | MCP 服务器连接后端的地址 | `http://127.0.0.1:8010` |
