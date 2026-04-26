"""
Day 4 — Database Tests
Run:  pytest tests/test_database.py -v
      pytest tests/ -v          (runs everything)
"""
import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from internhunter.database import (
    init_db, upsert_opportunity, upsert_many,
    get_new_opportunities, get_by_stipend, get_by_location,
    get_by_role, mark_notified, mark_applied, get_stats
)

# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Every test gets its own fresh SQLite file — no shared state."""
    monkeypatch.setattr("internhunter.database.DB_PATH", str(tmp_path / "test.db"))
    init_db()


def _opp(**kwargs) -> dict:
    """Build a minimal valid opportunity dict, override any field via kwargs."""
    base = {
        "title":      "ML Intern @ TestCo",
        "role":       "machine learning intern",
        "company":    "TestCo",
        "link":       "https://example.com/job/1",
        "source":     "internshala.com",
        "stipend":    "₹15,000/month",
        "deadline":   "31 May 2025",
        "location":   "Remote",
        "apply_link": "https://example.com/job/1",
        "snippet":    "Great ML internship",
        "scraped_at": "2025-04-26T00:00:00",
    }
    base.update(kwargs)
    return base


# ════════════════════════════════════════════════════════
#  init_db
# ════════════════════════════════════════════════════════

def test_init_db_creates_tables(tmp_path, monkeypatch):
    import sqlite3
    monkeypatch.setattr("internhunter.database.DB_PATH", str(tmp_path / "check.db"))
    init_db()
    conn = sqlite3.connect(str(tmp_path / "check.db"))
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "opportunities" in tables
    assert "applied" in tables


def test_init_db_idempotent():
    """Calling init_db() twice must not raise or corrupt the DB."""
    init_db()   # second call (fixture already called it once)


# ════════════════════════════════════════════════════════
#  upsert_opportunity
# ════════════════════════════════════════════════════════

def test_upsert_inserts_new():
    assert upsert_opportunity(_opp()) is True


def test_upsert_duplicate_returns_false():
    opp = _opp()
    upsert_opportunity(opp)
    assert upsert_opportunity(opp) is False


def test_upsert_different_links_both_inserted():
    assert upsert_opportunity(_opp(link="https://a.com/1")) is True
    assert upsert_opportunity(_opp(link="https://a.com/2")) is True


def test_upsert_missing_optional_fields():
    """company is optional — must not crash when absent."""
    opp = _opp()
    del opp["company"]
    assert upsert_opportunity(opp) is True


# ════════════════════════════════════════════════════════
#  upsert_many
# ════════════════════════════════════════════════════════

def test_upsert_many_counts():
    opps = [
        _opp(link="https://x.com/1"),
        _opp(link="https://x.com/2"),
        _opp(link="https://x.com/3"),
    ]
    inserted, skipped = upsert_many(opps)
    assert inserted == 3
    assert skipped == 0


def test_upsert_many_deduplication():
    opp = _opp(link="https://dup.com/1")
    upsert_opportunity(opp)                    # pre-insert one
    inserted, skipped = upsert_many([
        _opp(link="https://dup.com/1"),        # duplicate
        _opp(link="https://dup.com/2"),        # new
    ])
    assert inserted == 1
    assert skipped == 1


# ════════════════════════════════════════════════════════
#  get_new_opportunities
# ════════════════════════════════════════════════════════

def test_get_new_returns_inserted():
    upsert_opportunity(_opp())
    results = get_new_opportunities()
    assert len(results) == 1
    assert results[0]["title"] == "ML Intern @ TestCo"


def test_get_new_respects_limit():
    for i in range(10):
        upsert_opportunity(_opp(link=f"https://x.com/{i}"))
    assert len(get_new_opportunities(limit=3)) == 3


def test_get_new_excludes_notified():
    upsert_opportunity(_opp())
    opp_id = get_new_opportunities()[0]["id"]
    mark_notified([opp_id])
    assert len(get_new_opportunities()) == 0


def test_get_new_excludes_applied():
    upsert_opportunity(_opp())
    opp_id = get_new_opportunities()[0]["id"]
    mark_applied(opp_id, "cold_email")
    # applied ones have status='applied', not 'new'
    results = get_new_opportunities()
    assert all(r["status"] == "new" for r in results)


# ════════════════════════════════════════════════════════
#  get_by_stipend
# ════════════════════════════════════════════════════════

def test_get_by_stipend_returns_with_stipend():
    upsert_opportunity(_opp(stipend="₹20,000/month"))
    upsert_opportunity(_opp(link="https://x.com/2", stipend="Not mentioned"))
    results = get_by_stipend(min_amount=0)
    assert len(results) == 1
    assert results[0]["stipend"] == "₹20,000/month"


def test_get_by_stipend_filters_min():
    upsert_opportunity(_opp(link="https://x.com/1", stipend="₹10,000/month"))
    upsert_opportunity(_opp(link="https://x.com/2", stipend="₹25,000/month"))
    results = get_by_stipend(min_amount=15000)
    assert len(results) == 1
    assert "25,000" in results[0]["stipend"]


def test_get_by_stipend_empty_when_none_match():
    upsert_opportunity(_opp(stipend="₹5,000/month"))
    assert get_by_stipend(min_amount=50000) == []


# ════════════════════════════════════════════════════════
#  get_by_location
# ════════════════════════════════════════════════════════

def test_get_by_location_match():
    upsert_opportunity(_opp(location="Bangalore, Remote"))
    results = get_by_location("bangalore")
    assert len(results) == 1


def test_get_by_location_case_insensitive():
    upsert_opportunity(_opp(location="Mumbai"))
    assert len(get_by_location("MUMBAI")) == 1
    assert len(get_by_location("mumbai")) == 1


def test_get_by_location_no_match():
    upsert_opportunity(_opp(location="Delhi"))
    assert get_by_location("pune") == []


# ════════════════════════════════════════════════════════
#  get_by_role
# ════════════════════════════════════════════════════════

def test_get_by_role_match():
    upsert_opportunity(_opp(role="data science intern"))
    results = get_by_role("data science")
    assert len(results) == 1


def test_get_by_role_no_match():
    upsert_opportunity(_opp(role="ml intern"))
    assert get_by_role("backend") == []


# ════════════════════════════════════════════════════════
#  mark_notified
# ════════════════════════════════════════════════════════

def test_mark_notified_single():
    upsert_opportunity(_opp())
    opp_id = get_new_opportunities()[0]["id"]
    mark_notified([opp_id])
    assert get_new_opportunities() == []


def test_mark_notified_bulk():
    for i in range(5):
        upsert_opportunity(_opp(link=f"https://x.com/{i}"))
    ids = [r["id"] for r in get_new_opportunities()]
    mark_notified(ids)
    assert get_new_opportunities() == []


# ════════════════════════════════════════════════════════
#  mark_applied
# ════════════════════════════════════════════════════════

def test_mark_applied_sets_status():
    import sqlite3
    import internhunter.database as db_mod
    upsert_opportunity(_opp())
    opp_id = get_new_opportunities()[0]["id"]
    mark_applied(opp_id, "cold_email", notes="Applied via Gmail")
    conn = sqlite3.connect(db_mod._db_path())
    row = conn.execute("SELECT status FROM opportunities WHERE id=?", (opp_id,)).fetchone()
    assert row[0] == "applied"


def test_mark_applied_logs_in_applied_table():
    import sqlite3
    import internhunter.database as db_mod
    upsert_opportunity(_opp())
    opp_id = get_new_opportunities()[0]["id"]
    mark_applied(opp_id, "company_site", notes="Submitted form")
    conn = sqlite3.connect(db_mod._db_path())
    rows = conn.execute("SELECT * FROM applied WHERE opp_id=?", (opp_id,)).fetchall()
    assert len(rows) == 1
    assert rows[0][2] == "company_site"   # method column


# ════════════════════════════════════════════════════════
#  get_stats
# ════════════════════════════════════════════════════════

def test_get_stats_empty_db():
    stats = get_stats()
    assert stats["total"] == 0
    assert stats["new"] == 0


def test_get_stats_after_inserts():
    upsert_opportunity(_opp(link="https://x.com/1", stipend="₹15,000/month", location="Remote"))
    upsert_opportunity(_opp(link="https://x.com/2", stipend="Not mentioned", location="Not mentioned"))
    stats = get_stats()
    assert stats["total"]        == 2
    assert stats["new"]          == 2
    assert stats["with_stipend"] == 1
    assert stats["with_location"]== 1


def test_get_stats_applied_count():
    upsert_opportunity(_opp())
    opp_id = get_new_opportunities()[0]["id"]
    mark_applied(opp_id, "cold_email")
    stats = get_stats()
    assert stats["applied"] == 1
    assert stats["new"]     == 0