"""strategy.md 读写：strategies/{sid}/strategy.md"""

from pathlib import Path

STRATEGIES_DIR = Path(__file__).resolve().parent.parent / "strategies"


def _path(sid: str) -> Path:
    return STRATEGIES_DIR / sid / "strategy.md"


def read(sid: str) -> str:
    p = _path(sid)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def write(sid: str, content: str):
    p = _path(sid)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def append(sid: str, content: str):
    p = _path(sid)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write("\n" + content)
