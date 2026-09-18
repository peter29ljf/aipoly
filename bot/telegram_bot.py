"""aipoly 的唯一控制面：Telegram 长轮询机器人。

为什么是长轮询而不是 webhook：长轮询由本机主动向外连接，**不需要监听任何
入站端口**。旧版的 Web UI 必须常年开着一个公网端口，而那个端口后面是一个
无鉴权的 /api/*；这里没有端口可开，也就没有那条路。

鉴权只认 message.from.id（发送者），不认 chat.id——chat.id 在群组里可被
拉入陌生人，from.id 是 Telegram 服务端认证过的发送者身份，不可伪造。

自由文本会转给 agent。这在旧架构下等同于 RCE（agent 带 Bash 且以 root 跑），
在新架构下是安全的：agent 以 aipoly-agent 运行、无 Bash/Write 工具、
读不到 /etc/aipoly/wallet.env。它能下单，但拿不走本金。
"""

import html
import logging
import os
import subprocess
import time

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aipoly.bot")

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
if not TOKEN:
    raise SystemExit("TELEGRAM_BOT_TOKEN 未设置（应在 /etc/aipoly/telegram.env）")

# 逗号分隔的数字 user id。空 = 谁都不放行，这是刻意的失败方向：
# 配错的后果是自己用不了，而不是所有人都能用。
ADMINS = {
    int(x) for x in os.environ.get("TELEGRAM_ADMIN_IDS", "").replace(" ", "").split(",") if x
}
if not ADMINS:
    logger.warning("TELEGRAM_ADMIN_IDS 为空 —— 所有消息都会被拒绝")

API = f"https://api.telegram.org/bot{TOKEN}"
BACKEND = os.environ.get("API_BASE", "http://127.0.0.1:8010")
AIPM_TOKEN = os.environ.get("AIPM_TOKEN", "")
DEFAULT_SID = os.environ.get("AIPOLY_SID", "sweep")
AGENT_LAUNCHER = "/usr/local/sbin/aipoly-run-agent"

POLL_TIMEOUT = 50          # getUpdates 的 long-poll 秒数
MIN_INTERVAL = 2.0         # 每用户最小消息间隔，防手抖刷屏
_last_seen: dict[int, float] = {}


def _backend(method: str, path: str, **kw) -> dict:
    headers = {"x-aipm-token": AIPM_TOKEN} if AIPM_TOKEN else {}
    r = httpx.request(method, f"{BACKEND}{path}", headers=headers, timeout=20.0, **kw)
    r.raise_for_status()
    return r.json()


def send(chat_id: int, text: str) -> None:
    """发消息。Telegram 单条上限 4096 字符，超出就切段。"""
    for i in range(0, len(text), 3900):
        chunk = text[i : i + 3900]
        try:
            httpx.post(
                f"{API}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": chunk,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=20.0,
            )
        except Exception:
            logger.exception("sendMessage 失败")


# --------------------------------------------------------------------------
# 命令
# --------------------------------------------------------------------------

HELP = """<b>aipoly 控制台</b>

<b>只读</b>
/status — 余额、持仓数、定时任务状态
/positions — 当前持仓明细
/pnl — 已结算盈亏汇总

<b>控制</b>
/pause — 暂停每日自动扫描
/resume — 恢复自动扫描
/stop — 紧急停止：取消全部定时任务

<b>策略</b>
直接发文字即可和 AI 讨论策略、调整规则。
AI 能下单和改策略文档，但<b>读不到私钥</b>。

/help — 这份说明"""


def cmd_status(chat_id: int) -> None:
    try:
        bal = _backend("GET", "/_internal/balance").get("balance", "?")
        pos = _backend("GET", f"/api/strategies/{DEFAULT_SID}/positions")
        tasks = _backend("GET", f"/api/strategies/{DEFAULT_SID}/schedules")
        send(
            chat_id,
            f"<b>状态</b>\n"
            f"余额：<code>${bal}</code>\n"
            f"持仓：{len(pos) if isinstance(pos, list) else '?'} 笔\n"
            f"定时任务：{len(tasks) if isinstance(tasks, list) else '?'} 个",
        )
    except Exception as e:
        send(chat_id, f"⚠️ 读取失败：<code>{html.escape(str(e))}</code>")


def cmd_positions(chat_id: int) -> None:
    try:
        pos = _backend("GET", f"/api/strategies/{DEFAULT_SID}/positions")
        if not pos:
            send(chat_id, "当前无持仓。")
            return
        lines = ["<b>持仓</b>"]
        for p in pos:
            lines.append(
                f"• {html.escape(str(p.get('note', p.get('token_id', ''))[:60]))}\n"
                f"  {p.get('outcome')} {p.get('shares')} 份 / 成本 ${p.get('cost_usdc')}"
            )
        send(chat_id, "\n".join(lines))
    except Exception as e:
        send(chat_id, f"⚠️ 读取失败：<code>{html.escape(str(e))}</code>")


def run_agent(chat_id: int, prompt: str) -> None:
    """把自由文本交给沙箱里的 agent。

    经 sudo 调用一个 root 拥有、bot 不可写的启动器，沙箱参数全部固定在那里，
    bot 只能传 prompt。这样即使 bot 进程被攻破，也无法放宽自己的约束。
    """
    send(chat_id, "🤔 正在思考…")
    try:
        r = subprocess.run(
            ["sudo", "-n", AGENT_LAUNCHER, str(chat_id)],
            input=prompt,
            text=True,
            capture_output=True,
            timeout=600,
        )
        out = (r.stdout or "").strip() or (r.stderr or "").strip() or "（无输出）"
        send(chat_id, html.escape(out[:3800]))
    except subprocess.TimeoutExpired:
        send(chat_id, "⏱ agent 超时（10 分钟），已终止。")
    except Exception as e:
        send(chat_id, f"⚠️ agent 启动失败：<code>{html.escape(str(e))}</code>")


def handle(msg: dict) -> None:
    user = (msg.get("from") or {}).get("id")
    chat_id = (msg.get("chat") or {}).get("id")
    text = (msg.get("text") or "").strip()
    if not user or not chat_id or not text:
        return

    # 鉴权：只认发送者 id
    if user not in ADMINS:
        logger.warning("拒绝未授权用户 %s: %.50s", user, text)
        return  # 静默丢弃，不回复——不给探测者任何反馈

    now = time.monotonic()
    if now - _last_seen.get(user, 0.0) < MIN_INTERVAL:
        return
    _last_seen[user] = now

    cmd = text.split()[0].lower().split("@")[0]
    if cmd in ("/start", "/help"):
        send(chat_id, HELP)
    elif cmd == "/status":
        cmd_status(chat_id)
    elif cmd == "/positions":
        cmd_positions(chat_id)
    elif cmd in ("/pause", "/resume", "/stop"):
        run_agent(chat_id, {
            "/pause": "暂停每日自动扫描任务，确认后报告结果。",
            "/resume": "恢复每日自动扫描任务，确认后报告结果。",
            "/stop": "紧急停止：取消全部定时任务，不要下任何新单，报告取消了哪些。",
        }[cmd])
    elif cmd.startswith("/"):
        send(chat_id, f"未知命令 {html.escape(cmd)}。/help 查看可用命令。")
    else:
        run_agent(chat_id, text)


def main() -> None:
    logger.info("bot 启动，授权用户 %d 个，后端 %s", len(ADMINS), BACKEND)
    offset = 0
    while True:
        try:
            r = httpx.get(
                f"{API}/getUpdates",
                params={"offset": offset, "timeout": POLL_TIMEOUT},
                timeout=POLL_TIMEOUT + 15,
            )
            for upd in r.json().get("result", []):
                offset = upd["update_id"] + 1
                if "message" in upd:
                    handle(upd["message"])
        except httpx.TimeoutException:
            continue          # 长轮询正常超时
        except Exception:
            logger.exception("轮询出错，5 秒后重试")
            time.sleep(5)


if __name__ == "__main__":
    main()
