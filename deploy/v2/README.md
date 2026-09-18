# aipoly v2 —— 无 Web UI，Telegram 为唯一控制面

## 为什么重构

v1 亏掉 $1,520 不是因为选标的错了，是因为**所有组件都以 root 跑在一起**，
代码里本来就有的分层在操作系统层面等于不存在。

具体这条链：

```
POST /api/strategies/{sid}/chat/send   ← 无任何鉴权
  → claude -p <用户文本> --allowedTools Bash,... --permission-mode acceptEdits
  → 以 root 执行
  → cat /root/.ssh/... 或 data/.env
```

**一条聊天消息 = root 任意命令。** 加上 `allow_origins=["*"]`，浏览器里任何
网站配合 SSH 隧道都能触发它，而且不需要任何凭证。

## v2 的做法

代码里的分层其实一直是对的 —— `PRIVATE_KEY` 只被 `backend/api_client.py`
和 `backend/trader.py` 读取，MCP 层和 agent 从不碰它。v2 没有重写这个分层，
只是把它**落到操作系统的权限上**：

| 组件 | 用户 | 读私钥 | shell | 说明 |
|---|---|---|---|---|
| backend | `aipoly-core` | ✅ 唯一 | ❌ | 下单执行，仅监听 127.0.0.1:8010 |
| 5 个 MCP | `aipoly-mcp` | ❌ | ❌ | 薄客户端，带 token 调 backend |
| **claude agent** | `aipoly-agent` | ❌ | ❌ | **工具白名单只有 `mcp__*`** |
| Telegram bot | `aipoly-bot` | ❌ | ❌ | 唯一控制面 |

私钥在 `/etc/aipoly/wallet.env`，`root:aipoly-core 640`。agent 另有
`InaccessiblePaths=/etc/aipoly` 兜底。`install.sh` 结尾会**实际验证**
agent 读不到、core 读得到，验证失败直接退出。

**结果：agent 被提示词注入完全劫持，也只能下单，拿不走本金。**

## 入站端口：0

Telegram 用长轮询（本机主动外连），不需要任何入站端口。
v1 必须常年开着 80/443，后面是个无鉴权的 `/api/*`；v2 连端口都没有。

公网只剩 22（SSH）。

## 与 v1 的逐项差异

| | v1 | v2 |
|---|---|---|
| 前端 | React + Caddy + 公网域名 | **删除** |
| 控制面 | Web UI（basic_auth 兜底） | Telegram 白名单 |
| `/api/*` 鉴权 | ❌ 无 | ✅ 全路由强制 token |
| CORS | `allow_origins=["*"]` | **不装该中间件** |
| chat 路由 | 自由文本 → root + Bash | **删除**，agent 只由沙箱启动器拉起 |
| agent 工具 | `Bash,Edit,Read,Write,mcp__*` | **仅 `mcp__*`** |
| 运行身份 | 全部 root | 四个独立 system 用户 |
| token 存放 | `data/.token` 644，且曾提交进公开仓库 | `/etc/aipoly/mcp.env` 640 |
| 入站端口 | 22/80/443 | **22** |

## 文件

| 文件 | 作用 |
|---|---|
| `install.sh` | 建用户、目录、凭证壳子；**自检权限隔离是否真的生效** |
| `deploy.sh` | 从旧机部署到新机（只传纯文本源码） |
| `main.py` | 替换 `backend/main.py`：去掉 CORS / 静态 / chat，加全局 token 闸门 |
| `aipoly-run-agent` | 沙箱启动器，root 所有、bot 不可写，沙箱参数写死在内 |
| `aipoly-*.service` | systemd 单元，逐个收紧 |
| `aipoly-bot.sudoers` | bot 仅能以 root 执行启动器这一个命令 |

## 部署

```bash
bash deploy/v2/deploy.sh root@<新IP>
```

然后填四个凭证文件，再：

```bash
systemctl enable --now aipoly-core aipoly-mcp@{poly_trade,portfolio,scheduler,sweep,strategy_doc} aipoly-bot
```

## 仍需人工完成（v2 不能替你做的）

1. **session key** —— v2 保证 agent 拿不到私钥，但 `aipoly-core` 拿得到。
   只有受限权限密钥能让「密钥泄露」不等于「本金归零」。这是最后一块。
2. **Telegram 两步验证** —— 否则安全模型建立在你的手机号上，SIM swap 即失控。
3. **余额告警** —— v1 最致命的不是被盗，是被盗后 3 天才发现。
   bot 应加一条定时任务：余额异常归零立刻推送。
