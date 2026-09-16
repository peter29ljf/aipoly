"""Claude 子进程执行器：以 claude CLI 运行策略，流式读取 JSON 事件。"""

import asyncio
import glob
import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from backend.strategy_lock import strategy_lock, is_locked
from backend.event_bus import event_bus
from backend import chat_log, strategies as strat_module

logger = logging.getLogger(__name__)

STRATEGIES_DIR = Path(__file__).resolve().parent.parent / "strategies"
AUTH_ENV_FILE = Path(__file__).resolve().parent.parent / "data" / "claude_auth.env"

# 任一变量存在即可完成鉴权；OAuth 长期令牌是首选，因为它不随会话过期，
# 而 ~/.claude/.credentials.json 里的会话凭证过期后后台进程无法走浏览器刷新。
_AUTH_VARS = ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")


def _find_claude() -> str:
    # Try PATH first
    p = shutil.which("claude")
    if p:
        return p
    # Known fixed install locations (PATH may not be inherited depending on
    # how this process was launched: nohup, pm2, cron, systemd, ...)
    fixed_paths = [
        os.path.expanduser("~/.local/bin/claude"),
        "/root/.local/bin/claude",
        "/usr/local/bin/claude",
    ]
    for fp in fixed_paths:
        if os.path.isfile(fp) and os.access(fp, os.X_OK):
            return fp
    # Cursor extension (common on this server)
    patterns = [
        "/root/.cursor-server/extensions/anthropic.claude-code-*/resources/native-binary/claude",
        "/home/*/.cursor-server/extensions/anthropic.claude-code-*/resources/native-binary/claude",
        "/root/.vscode-server/extensions/anthropic.claude-code-*/resources/native-binary/claude",
    ]
    for pat in patterns:
        matches = glob.glob(pat)
        if matches:
            return sorted(matches)[-1]  # pick latest version
    raise FileNotFoundError("claude CLI not found. Install Claude Code or add it to PATH.")


def _apply_claude_auth(env: dict) -> None:
    """确保子进程带有可用的 Claude 授权，缺失时抛出可读的中文错误。

    start.sh 会 source data/claude_auth.env，但 cron / systemd / 手工拉起后端时
    未必经过它，所以这里兜底再读一次文件。
    """
    if any(env.get(v) for v in _AUTH_VARS):
        return

    hint = (
        "缺少 Claude 授权：请运行 `claude setup-token` 生成长期令牌，并写入 "
        f"{AUTH_ENV_FILE}（格式 CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat...，权限 600）。"
    )
    if not AUTH_ENV_FILE.is_file():
        raise RuntimeError(hint)

    for line in AUTH_ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if key in _AUTH_VARS:
            env[key] = val.strip().strip('"').strip("'")

    if not any(env.get(v) for v in _AUTH_VARS):
        raise RuntimeError(hint)


_TRIGGER_PROMPTS = {
    "manual": "请检查当前市场状态，根据策略文档执行下一步操作。",
    "alert":  "价格警报已触发，请查看当前持仓和市场状态，决定是否需要调整仓位。",
    "cron":   "定时任务触发，请按策略文档执行例行市场扫描和操作。",
    "chat":   "",  # replaced by user_message
}


def _translate_event(raw: dict) -> dict | None:
    """把 Claude stream-json 格式转换为我们自己的 kind-based 格式。

    只从 type=result 提取最终文本（避免与 type=assistant 重复）。
    tool_use 事件忽略（不显示，用户无需看到工具调用细节）。
    """
    t = raw.get("type", "")

    # Final result — Claude 的完整回复
    if t == "result":
        result = raw.get("result", "")
        if result and not raw.get("is_error"):
            return {"kind": "text", "content": result}
        if raw.get("is_error"):
            return {"kind": "run_error", "error": raw.get("result", "Claude error")}
        return None

    # Skip everything else: system/init, assistant (intermediate), rate_limit, user, post_turn_summary
    return None


async def run_claude(sid: str, trigger: str = "manual", extra: dict | None = None) -> bool:
    """在独占锁下运行 Claude CLI。返回 True 表示成功启动（不等待完成）。"""
    if is_locked(sid):
        logger.warning("Strategy %s already running, skip", sid)
        return False

    strat_module.rebuild_claude_md(sid, user_message=(extra or {}).get("user_message", ""))

    asyncio.create_task(_run(sid, trigger, extra or {}))
    return True


async def _run(sid: str, trigger: str, extra: dict):
    async with strategy_lock(sid):
        now = datetime.now(timezone.utc).isoformat()
        started = {"kind": "run_started", "trigger": trigger, "extra": extra, "ts": now}
        await event_bus.publish(sid, started)
        chat_log.append(sid, started)

        # Determine prompt: user message takes priority, then trigger default
        prompt = extra.get("user_message") or _TRIGGER_PROMPTS.get(trigger, "请执行下一步操作。")

        sid_dir = STRATEGIES_DIR / sid

        try:
            cmd = [
                _find_claude(),
                "-p", prompt,
                "--model", "opus",  # 策略决策统一用 Opus，不随 CLI 默认值漂移
                "--output-format", "stream-json",
                "--verbose",
                "--mcp-config", str(sid_dir / ".mcp.json"),
                "--allowedTools",
                "Bash,Edit,Read,Write,mcp__poly_trade__*,mcp__portfolio__*,mcp__scheduler__*,mcp__sweep__*,mcp__strategy_doc__*",
                "--permission-mode", "acceptEdits",
            ]

            env = os.environ.copy()
            env["AIPM_TRADE_MODE"] = "live"
            _apply_claude_auth(env)
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(sid_dir),
                env=env,
                limit=10 * 1024 * 1024,  # 10MB — 防止长 JSON 行触发 LimitOverrunError
            )

            async def read_stdout():
                async for raw in proc.stdout:
                    line = raw.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    try:
                        raw_event = json.loads(line)
                    except Exception:
                        raw_event = {"type": "raw", "text": line}

                    event = _translate_event(raw_event)
                    if event is None:
                        continue  # skip noise (system/init/rate_limit)
                    event.setdefault("ts", datetime.now(timezone.utc).isoformat())
                    await event_bus.publish(sid, event)
                    chat_log.append(sid, event)

            async def read_stderr():
                async for raw in proc.stderr:
                    line = raw.decode("utf-8", errors="replace").strip()
                    if line:
                        logger.warning("[claude %s stderr] %s", sid, line)

            await asyncio.gather(read_stdout(), read_stderr())
            await proc.wait()

            done = {"kind": "run_done", "exit_code": proc.returncode, "ts": datetime.now(timezone.utc).isoformat()}
            await event_bus.publish(sid, done)
            chat_log.append(sid, done)

            # 异步压缩记忆（不阻塞主流程）
            from backend.memory_compressor import compress_memory
            asyncio.create_task(compress_memory(sid))

        except Exception as e:
            err = {"kind": "run_error", "error": str(e), "ts": datetime.now(timezone.utc).isoformat()}
            await event_bus.publish(sid, err)
            chat_log.append(sid, err)
            logger.exception("Claude run failed for %s", sid)
