"""活动时间线：把 chat JSONL 聚合成每次 CLI 运行的摘要。"""

import glob
import json
import re
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/api/strategies/{sid}/activity", tags=["activity"])

STRATEGIES_DIR = Path(__file__).resolve().parents[2] / "strategies"

TRIGGER_LABELS = {
    "manual": "手动触发",
    "chat":   "对话触发",
    "schedule": "定时触发",
    "cron":   "定时触发",
    "alert":  "警报触发",
}


def _strip_markdown(text: str) -> str:
    """简单去除 markdown，保留纯文字摘要。"""
    text = re.sub(r'\|[^\n]*', '', text)          # 表格行
    text = re.sub(r'#{1,6}\s*', '', text)          # 标题
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)  # 粗/斜体
    text = re.sub(r'`[^`]*`', '', text)            # 行内代码
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # 链接
    text = re.sub(r'\n{2,}', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _summarize(text: str, max_len: int = 80) -> str:
    clean = _strip_markdown(text)
    # 取第一句有意义的内容
    for line in clean.split('。'):
        line = line.strip()
        if len(line) > 10:
            return line[:max_len] + ('…' if len(line) > max_len else '')
    return clean[:max_len] + ('…' if len(clean) > max_len else '')


def load_activity(sid: str, limit: int = 30) -> list[dict]:
    log_dir = STRATEGIES_DIR / sid / "logs"
    if not log_dir.exists():
        return []

    files = sorted(glob.glob(str(log_dir / "chat-*.jsonl")), reverse=True)

    runs: list[dict] = []
    current: dict | None = None

    # 从最新文件往前读，收集足够的 runs
    all_lines: list[str] = []
    for f in files:
        try:
            lines = Path(f).read_text(encoding="utf-8").splitlines()
            all_lines = lines + all_lines
        except Exception:
            pass

    for raw in all_lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            ev = json.loads(raw)
        except Exception:
            continue

        kind = ev.get("kind", "")
        ts = ev.get("ts", "")

        if kind == "run_started":
            trigger = ev.get("trigger", "manual")
            user_msg = (ev.get("extra") or {}).get("user_message", "")
            current = {
                "ts": ts,
                "trigger": trigger,
                "trigger_label": TRIGGER_LABELS.get(trigger, trigger),
                "user_message": user_msg[:60] if user_msg else None,
                "summary": None,
                "status": "running",
                "exit_code": None,
                "duration_s": None,
                "_start_ts": ts,
                "_texts": [],
            }

        elif kind == "text" and current is not None:
            current["_texts"].append(ev.get("content", ""))

        elif kind == "run_done" and current is not None:
            current["exit_code"] = ev.get("exit_code")
            current["status"] = "ok" if ev.get("exit_code") == 0 else "error"
            # 计算耗时
            try:
                from datetime import datetime, timezone
                t0 = datetime.fromisoformat(current["_start_ts"])
                t1 = datetime.fromisoformat(ts)
                current["duration_s"] = int((t1 - t0).total_seconds())
            except Exception:
                pass
            # 摘要取所有 text 合并后首句
            full_text = " ".join(current["_texts"])
            current["summary"] = _summarize(full_text) if full_text else None
            # 清理内部字段
            del current["_texts"], current["_start_ts"]
            runs.append(current)
            current = None

        elif kind == "run_error" and current is not None:
            current["status"] = "error"
            current["summary"] = ev.get("error", "运行出错")[:80]
            del current["_texts"], current["_start_ts"]
            runs.append(current)
            current = None

    # 时间倒序，最新在前
    runs.reverse()
    return runs[:limit]


@router.get("")
def get_activity(sid: str, limit: int = 30):
    return load_activity(sid, limit)
