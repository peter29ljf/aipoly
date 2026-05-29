"""持仓 JSON 读写：strategies/{sid}/portfolio.json"""

import json
from pathlib import Path

STRATEGIES_DIR = Path(__file__).resolve().parent.parent / "strategies"


def _path(sid: str) -> Path:
    return STRATEGIES_DIR / sid / "portfolio.json"


def load(sid: str) -> dict:
    p = _path(sid)
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {"positions": []}


def save(sid: str, data: dict):
    p = _path(sid)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_positions(sid: str) -> list[dict]:
    return load(sid).get("positions", [])


def add_position(sid: str, token_id: str, outcome: str, shares: float, cost_usdc: float, note: str = "") -> dict:
    data = load(sid)
    pos = {
        "token_id": token_id,
        "outcome": outcome,
        "shares": shares,
        "cost_usdc": cost_usdc,
        "note": note,
    }
    data["positions"].append(pos)
    save(sid, data)
    return pos


def update_position(sid: str, token_id: str, **kwargs) -> dict | None:
    data = load(sid)
    for pos in data["positions"]:
        if pos["token_id"] == token_id:
            pos.update(kwargs)
            save(sid, data)
            return pos
    return None


def remove_position(sid: str, token_id: str) -> bool:
    data = load(sid)
    before = len(data["positions"])
    data["positions"] = [p for p in data["positions"] if p["token_id"] != token_id]
    if len(data["positions"]) < before:
        save(sid, data)
        return True
    return False
