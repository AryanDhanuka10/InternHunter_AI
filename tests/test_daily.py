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
    draft = draft_cold_email(opp, user)
    body  = draft["text"]
    assert "Acme Corp" in body
    assert "ML Engineer" in body

# ── Edge-case parser tests (Day 8) ────────────────────────────

def test_parse_listing_extracts_all_three_fields_from_one_snippet():
    """
    When stipend, deadline AND location all appear in a single snippet,
    parse_listing() must extract all three correctly in one pass.
    Real-world case: individual Internshala listing pages contain everything.
    """
    raw = {
        "title":      "ML Intern at Razorpay",
        "link":       "https://internshala.com/job/123",
        "snippet":    "Stipend Rs. 20,000/month. Last date to apply: 15 June 2025. Work From Home.",
        "role":       "machine learning intern",
        "scraped_at": "2025-04-27T00:00:00",
    }
    result = parse_listing(raw)
    assert result["stipend"]  == "₹20,000/month",         f"stipend wrong: {result['stipend']}"
    assert "June" in result["deadline"],                   f"deadline wrong: {result['deadline']}"
    assert result["location"] == "Work From Home",         f"location wrong: {result['location']}"


def test_parse_listing_finds_stipend_in_title_when_snippet_has_none():
    """
    parse_listing() concatenates title + snippet before parsing.
    If the snippet is generic but the title contains the stipend,
    the parser must still find it — not return 'Not mentioned'.
    Real-world case: LinkedIn pulse articles often have all info in the title.
    """
    raw = {
        "title":      "ML Intern ₹25,000/month Remote — Apply Now",
        "link":       "https://linkedin.com/pulse/abc",
        "snippet":    "Great opportunity to grow your skills at a top startup.",
        "role":       "machine learning intern",
        "scraped_at": "2025-04-27T00:00:00",
    }
    result = parse_listing(raw)
    assert result["stipend"] != "Not mentioned",  "Should have found stipend in title"
    assert "25,000" in result["stipend"],          f"Expected 25000, got: {result['stipend']}"
    assert result["location"] == "Remote",         f"Should have found Remote in title"