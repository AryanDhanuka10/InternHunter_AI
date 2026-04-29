"""
Day 12 — Filter + Scoring Tests
Run:  pytest tests/test_filters.py -v
      pytest tests/ -v
"""
import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from internhunter.filters import (
    apply_filters, score_one, _stipend_to_int, _compute_score
)


# ── Fixtures ──────────────────────────────────────────────────

def _opp(**kwargs) -> dict:
    base = {
        "title":    "ML Intern",
        "stipend":  "Not mentioned",
        "location": "Not mentioned",
        "deadline": "Not mentioned",
        "source":   "other",
        "company":  "",
        "role":     "ml intern",
    }
    base.update(kwargs)
    return base


# ════════════════════════════════════════════════════════
#  _stipend_to_int
# ════════════════════════════════════════════════════════

class TestStipendToInt:

    def test_flat_inr(self):
        assert _stipend_to_int("₹20,000/month") == 20000

    def test_lacs(self):
        assert _stipend_to_int("₹110,000/month") == 110000

    def test_not_mentioned(self):
        assert _stipend_to_int("Not mentioned") == 0

    def test_empty_string(self):
        assert _stipend_to_int("") == 0

    def test_none(self):
        assert _stipend_to_int(None) == 0

    def test_small_noise_value(self):
        # ₹50/month should parse as 50, not crash
        assert _stipend_to_int("₹50/month") == 50

    def test_with_commas(self):
        assert _stipend_to_int("₹1,10,000/month") == 110000


# ════════════════════════════════════════════════════════
#  _compute_score
# ════════════════════════════════════════════════════════

class TestComputeScore:

    def test_zero_for_empty_listing(self):
        assert _compute_score(_opp(), 0) == 0

    def test_has_stipend_adds_points(self):
        score = _compute_score(_opp(stipend="₹12,000/month"), 12000)
        assert score >= 10   # at least has_stipend weight

    def test_stipend_15k_adds_more(self):
        s_low  = _compute_score(_opp(stipend="₹12,000/month"), 12000)
        s_high = _compute_score(_opp(stipend="₹15,000/month"), 15000)
        assert s_high > s_low

    def test_stipend_25k_adds_even_more(self):
        s_15 = _compute_score(_opp(stipend="₹15,000/month"), 15000)
        s_25 = _compute_score(_opp(stipend="₹25,000/month"), 25000)
        assert s_25 > s_15

    def test_preferred_location_adds_points(self, monkeypatch):
        monkeypatch.setattr("internhunter.filters.PREFERRED_LOCATIONS", ["remote"])
        s_no  = _compute_score(_opp(location="Delhi"),  0)
        s_yes = _compute_score(_opp(location="Remote"), 0)
        assert s_yes > s_no

    def test_has_deadline_adds_points(self):
        s_no  = _compute_score(_opp(deadline="Not mentioned"), 0)
        s_yes = _compute_score(_opp(deadline="31 May 2025"),   0)
        assert s_yes > s_no

    def test_known_source_adds_points(self):
        s_other    = _compute_score(_opp(source="other"),          0)
        s_known    = _compute_score(_opp(source="internshala.com"),0)
        assert s_known > s_other

    def test_has_company_adds_points(self):
        s_no  = _compute_score(_opp(company=""),       0)
        s_yes = _compute_score(_opp(company="Google"), 0)
        assert s_yes > s_no

    def test_all_conditions_stacks(self):
        """Max score listing should beat any single-condition listing."""
        max_opp = _opp(
            stipend="₹25,000/month", location="remote",
            deadline="31 May 2025", source="internshala.com", company="Razorpay"
        )
        min_opp = _opp()
        assert _compute_score(max_opp, 25000) > _compute_score(min_opp, 0)


# ════════════════════════════════════════════════════════
#  apply_filters
# ════════════════════════════════════════════════════════

class TestApplyFilters:

    def test_returns_kept_and_dropped(self):
        kept, dropped = apply_filters([_opp()])
        assert isinstance(kept, list)
        assert isinstance(dropped, list)

    def test_empty_input(self):
        kept, dropped = apply_filters([])
        assert kept == [] and dropped == []

    def test_not_mentioned_stipend_is_kept(self, monkeypatch):
        monkeypatch.setattr("internhunter.filters.MIN_STIPEND", 10000)
        kept, dropped = apply_filters([_opp(stipend="Not mentioned")])
        assert len(kept) == 1
        assert len(dropped) == 0

    def test_below_min_stipend_is_dropped(self, monkeypatch):
        monkeypatch.setattr("internhunter.filters.MIN_STIPEND", 10000)
        kept, dropped = apply_filters([_opp(stipend="₹5,000/month")])
        assert len(kept) == 0
        assert len(dropped) == 1

    def test_above_min_stipend_is_kept(self, monkeypatch):
        monkeypatch.setattr("internhunter.filters.MIN_STIPEND", 10000)
        kept, dropped = apply_filters([_opp(stipend="₹15,000/month")])
        assert len(kept) == 1
        assert len(dropped) == 0

    def test_exactly_min_stipend_is_kept(self, monkeypatch):
        monkeypatch.setattr("internhunter.filters.MIN_STIPEND", 10000)
        kept, dropped = apply_filters([_opp(stipend="₹10,000/month")])
        assert len(kept) == 1

    def test_min_stipend_zero_keeps_all(self, monkeypatch):
        monkeypatch.setattr("internhunter.filters.MIN_STIPEND", 0)
        opps = [_opp(stipend="₹1,000/month"), _opp(stipend="₹500/month")]
        kept, dropped = apply_filters(opps)
        assert len(kept) == 2
        assert len(dropped) == 0

    def test_score_added_to_kept(self):
        kept, _ = apply_filters([_opp()])
        assert "score" in kept[0]

    def test_drop_reason_added_to_dropped(self, monkeypatch):
        monkeypatch.setattr("internhunter.filters.MIN_STIPEND", 10000)
        _, dropped = apply_filters([_opp(stipend="₹3,000/month")])
        assert "drop_reason" in dropped[0]
        assert "3000" in dropped[0]["drop_reason"]

    def test_kept_sorted_by_score_descending(self, monkeypatch):
        monkeypatch.setattr("internhunter.filters.MIN_STIPEND", 0)
        opps = [
            _opp(stipend="₹10,000/month", title="Low"),
            _opp(stipend="₹25,000/month", title="High",
                 source="internshala.com", location="remote",
                 deadline="31 May 2025", company="Razorpay"),
            _opp(stipend="₹15,000/month", title="Mid"),
        ]
        kept, _ = apply_filters(opps)
        scores = [o["score"] for o in kept]
        assert scores == sorted(scores, reverse=True), "Should be sorted score DESC"

    def test_high_score_listing_first(self, monkeypatch):
        monkeypatch.setattr("internhunter.filters.MIN_STIPEND", 0)
        opps = [
            _opp(title="Low",  stipend="₹10,000/month"),
            _opp(title="High", stipend="₹30,000/month",
                 source="internshala.com", location="remote",
                 deadline="31 May 2025", company="Uber"),
        ]
        kept, _ = apply_filters(opps)
        assert kept[0]["title"] == "High"

    def test_original_fields_preserved(self):
        opp = _opp(title="Test Intern", role="backend intern")
        kept, _ = apply_filters([opp])
        assert kept[0]["title"] == "Test Intern"
        assert kept[0]["role"]  == "backend intern"

    def test_mixed_batch(self, monkeypatch):
        monkeypatch.setattr("internhunter.filters.MIN_STIPEND", 10000)
        opps = [
            _opp(stipend="₹20,000/month"),  # kept
            _opp(stipend="Not mentioned"),   # kept
            _opp(stipend="₹5,000/month"),    # dropped
            _opp(stipend="₹15,000/month"),   # kept
            _opp(stipend="₹2,000/month"),    # dropped
        ]
        kept, dropped = apply_filters(opps)
        assert len(kept)    == 3
        assert len(dropped) == 2


# ════════════════════════════════════════════════════════
#  score_one
# ════════════════════════════════════════════════════════

class TestScoreOne:

    def test_returns_int(self):
        assert isinstance(score_one(_opp()), int)

    def test_zero_for_bare_listing(self):
        assert score_one(_opp()) == 0

    def test_matches_apply_filters_score(self, monkeypatch):
        monkeypatch.setattr("internhunter.filters.MIN_STIPEND", 0)
        opp = _opp(stipend="₹20,000/month", location="remote",
                   source="internshala.com", company="Razorpay")
        kept, _ = apply_filters([opp])
        assert score_one(opp) == kept[0]["score"]


# ════════════════════════════════════════════════════════
#  database integration — score column
# ════════════════════════════════════════════════════════

class TestDatabaseScoreIntegration:

    def test_score_persisted_on_insert(self, tmp_path, monkeypatch):
        monkeypatch.setattr("internhunter.database.DB_PATH", str(tmp_path / "test.db"))
        from internhunter.database import init_db, upsert_opportunity, get_conn
        import sqlite3
        init_db()
        opp = {
            "title": "Test", "role": "ml", "company": "Co",
            "link": "https://x.com/1", "source": "internshala.com",
            "stipend": "₹20,000/month", "deadline": "31 May 2025",
            "location": "Remote", "apply_link": "https://x.com/1",
            "snippet": "test", "scraped_at": "2025-01-01", "score": 42,
        }
        upsert_opportunity(opp)
        with get_conn() as conn:
            row = conn.execute("SELECT score FROM opportunities WHERE link=?",
                               ("https://x.com/1",)).fetchone()
        assert row[0] == 42

    def test_get_top_opportunities_sorted_by_score(self, tmp_path, monkeypatch):
        monkeypatch.setattr("internhunter.database.DB_PATH", str(tmp_path / "test2.db"))
        from internhunter.database import init_db, upsert_opportunity, get_top_opportunities
        init_db()
        for i, score in enumerate([5, 80, 20], 1):
            upsert_opportunity({
                "title": f"Opp {i}", "role": "ml", "company": "",
                "link": f"https://x.com/{i}", "source": "other",
                "stipend": "Not mentioned", "deadline": "Not mentioned",
                "location": "Not mentioned", "apply_link": f"https://x.com/{i}",
                "snippet": "test", "scraped_at": "2025-01-01", "score": score,
            })
        top = get_top_opportunities(limit=3)
        assert top[0]["score"] == 80
        assert top[1]["score"] == 20
        assert top[2]["score"] == 5

    def test_update_score(self, tmp_path, monkeypatch):
        monkeypatch.setattr("internhunter.database.DB_PATH", str(tmp_path / "test3.db"))
        from internhunter.database import init_db, upsert_opportunity, update_score, get_conn
        init_db()
        upsert_opportunity({
            "title": "Test", "role": "ml", "company": "", "link": "https://y.com/1",
            "source": "other", "stipend": "Not mentioned", "deadline": "Not mentioned",
            "location": "Not mentioned", "apply_link": "https://y.com/1",
            "snippet": "t", "scraped_at": "2025-01-01", "score": 0,
        })
        with get_conn() as conn:
            opp_id = conn.execute("SELECT id FROM opportunities").fetchone()[0]
        update_score(opp_id, 99)
        with get_conn() as conn:
            row = conn.execute("SELECT score FROM opportunities WHERE id=?", (opp_id,)).fetchone()
        assert row[0] == 99