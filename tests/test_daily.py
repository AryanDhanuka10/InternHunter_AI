"""Daily smoke test — run: pytest tests/test_daily.py -v"""
import pytest
from internhunter.parser   import parse_listing, _extract_stipend, _extract_deadline
from internhunter.database import init_db, upsert_opportunity, get_new_opportunities
from internhunter.digest   import build_digest_html
from internhunter.mailer   import draft_cold_email

# ── Parser tests ─────────────────────────────────────────────
def test_extract_stipend_inr():
    assert "₹15,000" in _extract_stipend("Stipend: INR 15,000 per month")

def test_extract_stipend_symbol():
    # Parser normalises to comma-formatted output e.g. ₹20,000/month
    assert "₹20,000" in _extract_stipend("₹20000/month stipend offered")

def test_extract_deadline():
    from internhunter.parser import _extract_deadline
    result = _extract_deadline("Apply by 30 June 2025")
    assert "June" in result or "2025" in result

def test_parse_listing_keys():
    raw = {"title":"SWE Intern","link":"https://example.com","snippet":"₹15,000/month. Remote. Apply by 31 May 2025","role":"software engineering intern","scraped_at":"2025-01-01"}
    parsed = parse_listing(raw)
    assert "stipend"  in parsed
    assert "deadline" in parsed
    assert "location" in parsed

# ── Database tests ────────────────────────────────────────────
def test_db_init_and_insert(tmp_path, monkeypatch):
    monkeypatch.setattr("internhunter.database.DB_PATH", str(tmp_path / "test.db"))
    init_db()
    opp = {"title":"Test","role":"ml intern","link":"https://test.com/1",
           "source":"test","stipend":"₹10,000","deadline":"31 May","location":"Remote",
           "apply_link":"https://test.com/1","snippet":"test snippet","scraped_at":"2025-01-01"}
    assert upsert_opportunity(opp) == True
    assert upsert_opportunity(opp) == False  # duplicate

def test_get_new_opportunities(tmp_path, monkeypatch):
    monkeypatch.setattr("internhunter.database.DB_PATH", str(tmp_path / "test2.db"))
    init_db()
    opp = {"title":"Test2","role":"data intern","link":"https://test.com/2",
           "source":"test","stipend":"Not mentioned","deadline":"Not mentioned",
           "location":"Bangalore","apply_link":"https://test.com/2",
           "snippet":"data intern","scraped_at":"2025-01-01"}
    upsert_opportunity(opp)
    results = get_new_opportunities()
    assert len(results) >= 1

# ── Digest test ───────────────────────────────────────────────
def test_build_digest_html():
    opps = [{"title":"Test","role":"swe","stipend":"₹15k","deadline":"31 May","location":"Remote","apply_link":"#"}]
    html = build_digest_html(opps)
    assert "<table" in html
    assert "InternHunter" in html

# ── Mailer draft test ─────────────────────────────────────────
def test_draft_cold_email():
    opp  = {"role":"ML Engineer","company":"Acme Corp"}
    user = {"name":"Raj","year":"3rd Year","branch":"CSE","college":"DTU",
            "skills":["Python","ML"],"github":"https://github.com/raj",
            "linkedin":"https://linkedin.com/in/raj","email":"raj@example.com"}
    body = draft_cold_email(opp, user)
    assert "Raj"       in body
    assert "Acme Corp" in body
    assert "ML Engineer" in body