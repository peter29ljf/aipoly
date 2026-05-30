"""价格警报 SQLite 持久化。"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "alerts.db"


def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sid TEXT NOT NULL,
                token_id TEXT NOT NULL,
                target REAL NOT NULL,
                direction TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                note TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                fired_at TEXT,
                fired_price REAL
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status_token ON alerts(status, token_id)")


def create_alert(sid: str, token_id: str, target: float, direction: str, note: str = "") -> dict:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO alerts (sid, token_id, target, direction, note, created_at) VALUES (?,?,?,?,?,?)",
            (sid, token_id, target, direction, note, now),
        )
        new_id = cur.lastrowid
        c.commit()
        row = c.execute("SELECT * FROM alerts WHERE id=?", (new_id,)).fetchone()
        return dict(row) if row else {"id": new_id, "sid": sid, "token_id": token_id, "target": target, "direction": direction, "status": "active"}


def get_alert(alert_id: int) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM alerts WHERE id=?", (alert_id,)).fetchone()
        return dict(row) if row else None


def get_active_alerts(sid: str) -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM alerts WHERE sid=? AND status='active'", (sid,)).fetchall()
        return [dict(r) for r in rows]


def get_all_active_alerts() -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM alerts WHERE status='active'").fetchall()
        return [dict(r) for r in rows]


def mark_fired(alert_id: int, fired_price: float):
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        c.execute(
            "UPDATE alerts SET status='fired', fired_at=?, fired_price=? WHERE id=?",
            (now, fired_price, alert_id),
        )


def cancel_alert(alert_id: int) -> bool:
    with _conn() as c:
        cur = c.execute("UPDATE alerts SET status='cancelled' WHERE id=? AND status='active'", (alert_id,))
        return cur.rowcount > 0


def cancel_all_for_strategy(sid: str) -> int:
    """取消某策略的所有活跃警报，返回取消数量。策略删除时调用。"""
    with _conn() as c:
        cur = c.execute(
            "UPDATE alerts SET status='cancelled' WHERE sid=? AND status='active'", (sid,)
        )
        n = cur.rowcount
        if n:
            import logging
            logging.getLogger(__name__).info("Cancelled %d orphaned alerts for strategy=%s", n, sid)
        return n


def list_alerts(sid: str) -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM alerts WHERE sid=? ORDER BY created_at DESC", (sid,)).fetchall()
        return [dict(r) for r in rows]
