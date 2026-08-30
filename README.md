# aipoly

基于 Claude CLI 的 Polymarket 自动交易系统。AI 策略代理通过 MCP 工具执行真实链上交易，支持 Web UI 管理、定时自动运行、活动时间线追踪。

## ⚠️ 安全要点（部署前必读）

本项目 2026-08 发生过一次真实事故：交易钱包被第三方清空，损失约 $1,520。下面每一条都对应一个**实际存在过**的问题，部署前请逐条确认。

### 1. MCP 服务绝不能监听公网

`mcp_servers/*/server.py` 默认绑定 `127.0.0.1`。**不要改成 `0.0.0.0`。**

这些服务**没有任何认证**，而且自带 `AIPM_TOKEN`——任何能连上端口的人，都能借它们以有效凭证调用内部 API，其中包括：

- `strategy_doc.write_strategy_doc` — 改写 AI 要执行的策略文档
- `scheduler.schedule_task` — 触发 Claude 运行该策略

而 Claude 在本机以 **root** 运行、具备完整 shell 权限。也就是说，暴露这几个端口等于把一个 root shell 交给公网。

远程访问请用 SSH 隧道：

```bash
ssh -L 8101:127.0.0.1:8101 -L 8102:127.0.0.1:8102 -L 8103:127.0.0.1:8103 \
    -L 8104:127.0.0.1:8104 -L 8105:127.0.0.1:8105 root@<host>
```

### 2. 前端与后端 API 同样不能暴露公网

`/api/*` **不做任何鉴权**。前端的登录框只是客户端 UI，绕过它直接请求 API 即可。`deploy/aipoly.caddy` 已将 Caddy 绑定在 `127.0.0.1:5173`，请勿改动。访问方式：

```bash
ssh -L 5173:127.0.0.1:5173 root@<host>   # 然后打开 http://localhost:5173
```

### 3. 私钥：这台主机就是热钱包主机

本项目**运行时需要 `PRIVATE_KEY`**（py-clob-client 用它签名订单），无法“派生完 API 凭证就删掉”。因此持有它的主机必须按热钱包主机对待：

- `chmod 600 data/.env` —— 部署后立即执行
- `.gitignore` 已排除 `data/.env`，**绝不要提交**
- **使用独立的交易钱包，不要用主钱包**；只放你能承受全部损失的资金
- 定期轮换 CLOB API 凭证（`create_or_derive_api_key` 可重新生成）
- 一旦怀疑主机被入侵：该钱包和私钥**永久作废**，换新钱包，不要再向旧地址充值（攻击者的 sweeper 会持续扫走进账）

### 4. 修改默认密码

`frontend/src/AuthContext.tsx` 里的账号密码是**占位值，且本仓库公开**。部署前必须修改并重新构建前端。注意它只是客户端校验，**不能当作安全边界**——真正的边界是第 2 条的 loopback 绑定。

### 5. 启用防火墙

```bash
ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp && ufw --force enable
```

即使服务都绑定了 loopback 也要开——它是防止“某天起了个新服务忘了绑定”的兜底。

### 6. 不要把任何真实值提交进本仓库

本仓库历史中曾出现过一个 `AIPM_TOKEN`（已轮换作废）。提交前检查：

```bash
git diff --cached | grep -iE "private_key|token|secret|passphrase|password"
```

---

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

> ⚠️ **写入后立即 `chmod 600 data/.env`。** 该文件含私钥，本项目运行时需要它，无法在派生出 API 凭证后删除。请使用独立交易钱包——见上方安全要点 §3。

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

> 生产部署已改为 Caddy 提供静态构建（见 `deploy/aipoly.caddy`），不再需要 vite dev server。

如需本地开发：

```bash
# 只监听回环——不要加 --host 0.0.0.0
cd frontend && npm run dev
```

### 11. 防火墙：不要开放业务端口

**只开放 22 / 80 / 443。** 5173、8010、8101-8105 全部**不得**暴露到公网——它们没有鉴权（原因见上方安全要点）。

```bash
ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp && ufw --force enable
```

云服务商的安全组同样只放行这三个端口。

### 12. 访问与登录

通过 SSH 隧道访问（**不要**直接用 `http://服务器IP:5173`）：

```bash
ssh -L 5173:127.0.0.1:5173 root@<host>
# 然后浏览器打开 http://localhost:5173
```

默认账号定义在 `frontend/src/AuthContext.tsx`。**部署前必须修改其中的用户名和密码并重新构建前端**——本仓库是公开的，默认值人人可见。

> 该登录仅为客户端校验，不构成安全边界。真正的边界是所有服务绑定 loopback + SSH 隧道访问。

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
cd frontend && nohup npm run dev > /tmp/vite.log 2>&1 &   # 只监听回环，勿加 --host
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
