"""SQLite storage for internship opportunities."""
import os, sqlite3, logging
from internhunter.config import DB_PATH

logger = logging.getLogger(__name__)


def _db_path() -> str:
    """Read DB_PATH at call-time so pytest monkeypatch always works."""
    import internhunter.database as _self
    return _self.DB_PATH


def get_conn():
    return sqlite3.connect(_db_path())


def init_db():
    path = _db_path()
    if "/" in path:
        os.makedirs(os.path.dirname(path), exist_ok=True)
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
                notified    INTEGER DEFAULT 0,
                score       INTEGER DEFAULT 0,
                duration    TEXT,
                expired     INTEGER DEFAULT 0,
                is_international INTEGER DEFAULT 0
            )
        """)
        # Migration: add score column to existing DBs (safe — no-op if already exists)
        existing = [r[1] for r in conn.execute("PRAGMA table_info(opportunities)").fetchall()]
        if "score" not in existing:
            conn.execute("ALTER TABLE opportunities ADD COLUMN score INTEGER DEFAULT 0")
            logger.info("Migration: added score column")
        if "duration" not in existing:
            conn.execute("ALTER TABLE opportunities ADD COLUMN duration TEXT")
        if "expired" not in existing:
            conn.execute("ALTER TABLE opportunities ADD COLUMN expired INTEGER DEFAULT 0")
        if "is_international" not in existing:
            conn.execute("ALTER TABLE opportunities ADD COLUMN is_international INTEGER DEFAULT 0")
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
    logger.info("Database initialised at %s", path)


def upsert_opportunity(opp: dict) -> bool:
    """Insert new opportunity; skip if link already exists. Returns True if inserted."""
    sql = """
        INSERT OR IGNORE INTO opportunities
            (title, role, company, link, source, stipend, deadline, location,
             apply_link, snippet, scraped_at, score, duration, expired, is_international)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """
    with get_conn() as conn:
        cur = conn.execute(sql, (
            opp.get("title"),       opp.get("role"),      opp.get("company", ""),
            opp.get("link"),        opp.get("source"),    opp.get("stipend"),
            opp.get("deadline"),    opp.get("location"),  opp.get("apply_link"),
            opp.get("snippet"),     opp.get("scraped_at"),opp.get("score", 0),
            opp.get("duration"),    1 if opp.get("expired") else 0,
            1 if opp.get("is_international") else 0,
        ))
        conn.commit()
        return cur.rowcount > 0


def upsert_many(opps: list[dict]) -> tuple[int, int]:
    """Bulk insert. Returns (inserted, skipped) counts."""
    inserted = skipped = 0
    for opp in opps:
        if upsert_opportunity(opp):
            inserted += 1
        else:
            skipped += 1
    logger.info(f"upsert_many: {inserted} new, {skipped} duplicates skipped")
    return inserted, skipped


def get_new_opportunities(limit: int = 20) -> list[dict]:
    """Return unnotified new opportunities, newest first."""
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM opportunities WHERE status='new' AND notified=0 "
            "ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        return [dict(r) for r in cur.fetchall()]


def get_by_stipend(min_amount: int = 0, limit: int = 20) -> list[dict]:
    """Return opportunities where parsed stipend >= min_amount (INR/month)."""
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM opportunities WHERE stipend != 'Not mentioned' "
            "ORDER BY id DESC LIMIT ?",
            (limit * 3,)
        )
        rows = [dict(r) for r in cur.fetchall()]

    if min_amount <= 0:
        return rows[:limit]

    def to_int(stipend_str: str) -> int:
        import re
        m = re.search(r"\d+", stipend_str.replace(",", ""))
        return int(m.group()) if m else 0

    return [r for r in rows if to_int(r["stipend"]) >= min_amount][:limit]


def get_by_location(location: str, limit: int = 20) -> list[dict]:
    """Return opportunities matching a location keyword (case-insensitive)."""
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM opportunities WHERE LOWER(location) LIKE ? "
            "ORDER BY id DESC LIMIT ?",
            (f"%{location.lower()}%", limit)
        )
        return [dict(r) for r in cur.fetchall()]


def get_by_role(role: str, limit: int = 20) -> list[dict]:
    """Return opportunities matching a role keyword (case-insensitive)."""
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM opportunities WHERE LOWER(role) LIKE ? "
            "ORDER BY id DESC LIMIT ?",
            (f"%{role.lower()}%", limit)
        )
        return [dict(r) for r in cur.fetchall()]


def mark_notified(ids: list[int]):
    with get_conn() as conn:
        conn.executemany(
            "UPDATE opportunities SET notified=1 WHERE id=?",
            [(i,) for i in ids]
        )
        conn.commit()


def mark_applied(opp_id: int, method: str, notes: str = ""):
    """Log that you applied to an opportunity."""
    from datetime import datetime, timezone
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO applied (opp_id, method, applied_at, notes) VALUES (?,?,?,?)",
            (opp_id, method, datetime.now(timezone.utc).isoformat(), notes)
        )
        conn.execute(
            "UPDATE opportunities SET status='applied' WHERE id=?",
            (opp_id,)
        )
        conn.commit()
    logger.info(f"Marked opp {opp_id} as applied via {method}")


def get_stats() -> dict:
    """Return a summary dict — used in digest and dashboard."""
    with get_conn() as conn:
        def scalar(sql, *args):
            return conn.execute(sql, args).fetchone()[0] or 0
        return {
            "total":         scalar("SELECT COUNT(*) FROM opportunities"),
            "new":           scalar("SELECT COUNT(*) FROM opportunities WHERE status='new'"),
            "applied":       scalar("SELECT COUNT(*) FROM opportunities WHERE status='applied'"),
            "with_stipend":  scalar("SELECT COUNT(*) FROM opportunities WHERE stipend != 'Not mentioned'"),
            "with_deadline": scalar("SELECT COUNT(*) FROM opportunities WHERE deadline != 'Not mentioned'"),
            "with_location": scalar("SELECT COUNT(*) FROM opportunities WHERE location != 'Not mentioned'"),
            "notified":      scalar("SELECT COUNT(*) FROM opportunities WHERE notified=1"),
        }


def get_top_opportunities(limit: int = 20, min_score: int = 0) -> list[dict]:
    """
    Return opportunities sorted by score DESC, then id DESC.
    Best listings (high stipend + preferred location + known source) surface first.
    Pass min_score to filter out low-quality listings entirely.
    """
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM opportunities "
            "WHERE score >= ? "
            "ORDER BY score DESC, id DESC LIMIT ?",
            (min_score, limit)
        )
        return [dict(r) for r in cur.fetchall()]


def update_score(opp_id: int, score: int):
    """Update the score for a single opportunity (used for re-scoring existing rows)."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE opportunities SET score=? WHERE id=?",
            (score, opp_id)
        )
        conn.commit()


def unmark_applied(opp_id: int):
    """Revert an opportunity from applied back to new status."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE opportunities SET status=? WHERE id=?",
            ('new', opp_id)
        )
        # Also remove from applied log
        conn.execute("DELETE FROM applied WHERE opp_id=?", (opp_id,))
        conn.commit()
    logger.info(f"Unmarked opp {opp_id} — status reset to new")


def rescore_all() -> int:
    """
    Re-compute and save scores for every row in the DB.
    Useful after changing SCORE_WEIGHTS in config.
    Returns the number of rows updated.
    """
    from internhunter.filters import score_one
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = [dict(r) for r in conn.execute("SELECT * FROM opportunities").fetchall()]

    updated = 0
    for row in rows:
        new_score = score_one(row)
        if new_score != (row.get("score") or 0):
            update_score(row["id"], new_score)
            updated += 1

    logger.info(f"rescore_all: updated {updated}/{len(rows)} rows")
    return updated


def get_opportunities_filtered(
    role: str = "",
    location: str = "",
    min_stipend: int = 0,
    show_expired: bool = False,
    international_only: bool = False,
    limit: int = 50,
) -> list[dict]:
    """
    Proper SQL-side filtering — role/location/stipend are matched IN the DB,
    not passed as search terms to LinkedIn.

    This is what the dashboard filter should use, not get_by_role/get_by_location
    which only do partial text matches on stored data.
    """
    conditions = ["1=1"]
    params     = []

    if not show_expired:
        conditions.append("(expired = 0 OR expired IS NULL)")

    if role:
        conditions.append("LOWER(role) LIKE ?")
        params.append(f"%{role.lower()}%")

    if location:
        conditions.append("LOWER(location) LIKE ?")
        params.append(f"%{location.lower()}%")

    if international_only:
        conditions.append("is_international = 1")

    where = " AND ".join(conditions)
    sql   = f"SELECT * FROM opportunities WHERE {where} ORDER BY score DESC, id DESC LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]

    # Stipend filter in Python (stipend is a string like "₹15,000/month")
    if min_stipend > 0:
        import re
        def to_int(s):
            if not s or s == "Not mentioned": return 0
            m = re.search(r"\d+", s.replace(",",""))
            return int(m.group()) if m else 0
        rows = [r for r in rows if to_int(r.get("stipend","")) >= min_stipend
                or r.get("stipend","") == "Not mentioned"]

    return rows