"""AI 记忆压缩器：每次策略运行完毕后，用 Claude CLI 压缩聊天历史，保存关键决策信息。"""

import asyncio
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

STRATEGIES_DIR = Path(__file__).resolve().parent.parent / "strategies"


def _read_all_events(sid: str) -> list[dict]:
    """读取策略所有日志文件的事件。"""
    log_dir = STRATEGIES_DIR / sid / "logs"
    if not log_dir.exists():
        return []
    events = []
    for f in sorted(log_dir.glob("chat-*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except Exception:
                    pass
    return events


def _read_current_memory(sid: str) -> str:
    """读取当前压缩记忆（如果存在）。"""
    p = STRATEGIES_DIR / sid / "memory.md"
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    return ""


def _save_memory(sid: str, content: str):
    p = STRATEGIES_DIR / sid / "memory.md"
    p.write_text(content, encoding="utf-8")


def _build_prompt(sid: str, events: list[dict], current_memory: str) -> str:
    """构建压缩 prompt。"""
    # 只取最近 50 条事件
    recent = events[-50:]

    lines = []
    for e in recent:
        kind = e.get("kind", "raw")
        ts = e.get("ts", "")[:16]
        if kind in ("run_started", "run_done"):
            trigger = e.get("trigger", "")
            lines.append(f"[{ts}] {kind} trigger={trigger}")
        elif kind == "run_error":
            lines.append(f"[{ts}][ERROR] {e.get('error', '')}")
        elif kind == "text":
            content = (e.get("content") or e.get("text") or "")[:600]
            lines.append(f"[{ts}][AI] {content}")
        elif kind == "user":
            content = (e.get("content") or e.get("text") or "")[:200]
            lines.append(f"[{ts}][User] {content}")

    raw_log = "\n".join(lines)
    prev_section = f"## 上次压缩记忆\n{current_memory}\n\n" if current_memory else ""

    return (
        f"你是 Polymarket 交易策略的记忆管理器。请将以下对话压缩成结构化摘要。\n\n"
        f"{prev_section}"
        f"## 最新对话\n{raw_log}\n\n"
        f"---\n"
        f"请输出 Markdown 格式摘要（中文，800字以内），包含：\n"
        f"1. **活跃持仓** — 标的名、方向、token_id、金额、概率、到期日\n"
        f"2. **已结算/平仓** — 盈亏结果\n"
        f"3. **策略指令** — 用户设定的规则、参数\n"
        f"4. **定时任务/警报** — 已配置的自动触发\n"
        f"5. **最近操作摘要** — 最近1-2次运行做了什么\n\n"
        f"要求：保留所有 token_id 和关键数字，忽略分析过程。"
    )


async def compress_memory(sid: str):
    """用 Claude CLI 异步压缩记忆，run_done 后调用。"""
    from backend.claude_runner import _find_claude

    try:
        claude_bin = _find_claude()
    except FileNotFoundError:
        logger.warning("[memory_compressor] claude CLI not found, skipping")
        return

    try:
        events = _read_all_events(sid)
        if len(events) < 5:
            return  # 事件太少，不压缩

        current_memory = _read_current_memory(sid)
        prompt = _build_prompt(sid, events, current_memory)

        proc = await asyncio.create_subprocess_exec(
            claude_bin,
            "-p", prompt,
            "--output-format", "text",
            "--model", "claude-haiku-4-5",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )

        # 最多等 60 秒
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
        except asyncio.TimeoutError:
            proc.kill()
            logger.warning("[memory_compressor] Timeout for %s", sid)
            return

        if proc.returncode == 0:
            compressed = stdout.decode("utf-8", errors="replace").strip()
            if compressed:
                _save_memory(sid, compressed)
                logger.info("[memory_compressor] ✓ Compressed memory for %s (%d chars)", sid, len(compressed))
        else:
            logger.warning("[memory_compressor] claude exited %d for %s", proc.returncode, sid)

    except Exception as e:
        logger.warning("[memory_compressor] Failed for %s: %s", sid, e)


def read_memory(sid: str) -> str:
    """读取压缩记忆，供 CLAUDE.md 重建使用。"""
    return _read_current_memory(sid)
