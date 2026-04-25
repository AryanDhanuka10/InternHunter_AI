"""SQLite storage for internship opportunities."""
import sqlite3, logging
from datetime import datetime
from internhunter.config import DB_PATH

logger = logging.getLogger(__name__)


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True) if "/" in DB_PATH else None
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS opportunities (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT,
                role        TEXT,
                company     TEXT,
                link        TEXT UNIQUE,
                source      TEXT,
                stipend     TEXT,
                deadline    TEXT,
                location    TEXT,
                apply_link  TEXT,
                snippet     TEXT,
                status      TEXT DEFAULT 'new',
                scraped_at  TEXT,
                notified    INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS applied (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                opp_id     INTEGER,
                method     TEXT,
                applied_at TEXT,
                notes      TEXT
            )
        """)
        conn.commit()
    logger.info("Database initialised")


def upsert_opportunity(opp: dict) -> bool:
    """Insert new opportunity; skip if link already exists. Returns True if inserted."""
    import os
    os.makedirs("data", exist_ok=True)
    sql = """
        INSERT OR IGNORE INTO opportunities
            (title, role, company, link, source, stipend, deadline, location, apply_link, snippet, scraped_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """
    with get_conn() as conn:
        cur = conn.execute(sql, (
            opp.get("title"), opp.get("role"), opp.get("company", ""),
            opp.get("link"), opp.get("source"), opp.get("stipend"),
            opp.get("deadline"), opp.get("location"), opp.get("apply_link"),
            opp.get("snippet"), opp.get("scraped_at")
        ))
        conn.commit()
        return cur.rowcount > 0


def get_new_opportunities(limit: int = 20) -> list[dict]:
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM opportunities WHERE status='new' AND notified=0 ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        return [dict(r) for r in cur.fetchall()]


def mark_notified(ids: list[int]):
    with get_conn() as conn:
        conn.executemany("UPDATE opportunities SET notified=1 WHERE id=?", [(i,) for i in ids])
        conn.commit()
