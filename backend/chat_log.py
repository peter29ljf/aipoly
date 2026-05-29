"""JSONL 聊天日志：每策略每天一个文件，追加写入。"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

STRATEGIES_DIR = Path(__file__).resolve().parent.parent / "strategies"


def _log_path(sid: str) -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_dir = STRATEGIES_DIR / sid / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"chat-{today}.jsonl"


def append(sid: str, event: dict):
    path = _log_path(sid)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def read_recent(sid: str, n: int = 20) -> list[dict]:
    """读取最近 n 条日志（跨文件）。"""
    log_dir = STRATEGIES_DIR / sid / "logs"
    if not log_dir.exists():
        return []
    files = sorted(log_dir.glob("chat-*.jsonl"), reverse=True)
    lines = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            lines = fh.readlines() + lines
        if len(lines) >= n:
            break
    events = []
    for line in lines:
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except Exception:
                pass
    return events[-n:]
