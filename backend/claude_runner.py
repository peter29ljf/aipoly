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


def _find_claude() -> str:
    # Try PATH first
    p = shutil.which("claude")
    if p:
        return p
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
        cmd = [
            _find_claude(),
            "-p", prompt,
            "--output-format", "stream-json",
            "--verbose",
            "--mcp-config", str(sid_dir / ".mcp.json"),
            "--allowedTools",
            "Bash,Edit,Read,Write,mcp__poly_trade__*,mcp__portfolio__*,mcp__scheduler__*,mcp__sweep__*,mcp__strategy_doc__*",
            "--permission-mode", "acceptEdits",
        ]

        try:
            env = os.environ.copy()
            env["AIPM_TRADE_MODE"] = "live"
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
