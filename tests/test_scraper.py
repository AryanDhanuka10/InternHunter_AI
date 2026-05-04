"""
Day 3 — Parser Tests
Run:  pytest tests/test_parser.py -v
      pytest tests/ -v          (runs everything)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from internhunter.parser import (
    _extract_stipend, _extract_deadline, _extract_location, parse_listing
)


# ════════════════════════════════════════════════════════
#  STIPEND
# ════════════════════════════════════════════════════════

class TestExtractStipend:

    # ── Your 5 real snippets ─────────────────────────────
    def test_real_cisco_lpa_range(self):
        """LPA range: Rs.3-7 LPA → lower bound converted to monthly"""
        t = "High Stipend: Most internships are subsidized by Rs.3-7 LPA"
        assert _extract_stipend(t) == "₹25,000/month"

    def test_real_internshala_no_space(self):
        """No space between label and number: Compensation20,000 inr per month"""
        t = "Compensation20,000 inr per month for 6 months."
        assert _extract_stipend(t) == "₹20,000/month"

    def test_real_uber_lacs_per_month(self):
        """Decimal Lacs/month: INR 1.1 Lacs - 1.6 Lacs per month"""
        t = "Expected Stipend: INR 1.1 Lacs - 1.6 Lacs per month ..."
        assert _extract_stipend(t) == "₹110,000/month"

    def test_real_google_no_stipend(self):
        """Category/vague snippet → Not mentioned"""
        t = "Google is hiring PhD interns in Bengaluru, Hyderabad, and Pune. 12-14 weeks of paid internship."
        assert _extract_stipend(t) == "Not mentioned"

    def test_real_linkedin_category(self):
        """Pure category page → Not mentioned"""
        t = "284 Software Engineer Intern Jobs in India (25 new) · Python Django Developer Intern"
        assert _extract_stipend(t) == "Not mentioned"

    # ── Format coverage ──────────────────────────────────
    def test_inr_flat(self):
        assert _extract_stipend("Stipend: INR 15000 per month") == "₹15,000/month"

    def test_rupee_symbol_flat(self):
        assert _extract_stipend("₹20,000/month") == "₹20,000/month"

    def test_rs_with_range(self):
        """Range: captures lower bound"""
        assert _extract_stipend("Rs. 15,000 - 20,000 /month") == "₹15,000/month"

    def test_k_notation(self):
        assert _extract_stipend("20k/month stipend offered") == "₹20,000/month"

    def test_k_notation_uppercase(self):
        assert _extract_stipend("15K per month") == "₹15,000/month"

    def test_stipend_keyword_bare(self):
        assert _extract_stipend("stipend: 12000") == "₹12,000/month"

    def test_lpa_single_value(self):
        """6 LPA → ₹50,000/month"""
        result = _extract_stipend("Package: INR 6 LPA")
        assert result == "₹50,000/month"

    def test_lacs_per_month_single(self):
        """₹ 2 Lacs per month → ₹2,00,000"""
        result = _extract_stipend("Salary: ₹2 Lacs per month")
        assert "200,000" in result or "2,00,000" in result

    def test_no_stipend_info(self):
        assert _extract_stipend("Great learning opportunity at a fast-growing startup.") == "Not mentioned"

    def test_does_not_match_year_numbers(self):
        """Year numbers like '2025' should not be treated as stipend"""
        assert _extract_stipend("Apply for summer 2025 internships today!") == "Not mentioned"


# ════════════════════════════════════════════════════════
#  DEADLINE
# ════════════════════════════════════════════════════════

class TestExtractDeadline:

    def test_last_date_to_apply(self):
        assert _extract_deadline("Last date to apply: 30 May 2025") == "30 May 2025"

    def test_last_date_of_application_with_is(self):
        """The 'is' filler between keyword and date"""
        assert _extract_deadline("Last date of application is 30th April, 2025") == "30th April, 2025"

    def test_apply_before(self):
        result = _extract_deadline("Apply before 15 June, 2025.")
        assert "June" in result and "2025" in result

    def test_apply_by_ordinal(self):
        assert _extract_deadline("Apply by 5th May 2025") == "5th May 2025"

    def test_apply_by_month_first(self):
        """Month-first format: Apply by May 15, 2025"""
        result = _extract_deadline("Apply by May 15, 2025")
        assert "May" in result and "2025" in result

    def test_deadline_keyword(self):
        assert _extract_deadline("Deadline: 25 May 2025") == "25 May 2025"

    def test_closes_on(self):
        result = _extract_deadline("Applications close: 1 July 2025")
        assert "July" in result and "2025" in result

    def test_numeric_date(self):
        assert _extract_deadline("Last Date: 20/06/2025") == "20/06/2025"

    def test_numeric_date_dash(self):
        assert _extract_deadline("Deadline: 31-05-2025") == "31-05-2025"

    def test_no_deadline(self):
        assert _extract_deadline("Apply for ML internships across India.") == "Not mentioned"

    def test_does_not_match_duration(self):
        """'6 months' should not be matched as a deadline"""
        assert _extract_deadline("Duration: 6 months. Great stipend offered.") == "Not mentioned"


# ════════════════════════════════════════════════════════
#  LOCATION
# ════════════════════════════════════════════════════════

class TestExtractLocation:

    def test_real_google_multiple_cities(self):
        """Your real snippet: Bengaluru, Hyderabad, Pune"""
        t = "Google is hiring PhD interns in Bengaluru, Hyderabad, and Pune."
        result = _extract_location(t)
        assert "Bangalore" in result   # Bengaluru → Bangalore alias
        assert "Hyderabad" in result
        assert "Pune" in result

    def test_bengaluru_alias(self):
        assert _extract_location("Office in Bengaluru") == "Bangalore"

    def test_gurgaon_alias(self):
        assert _extract_location("Role based in Gurgaon") == "Gurugram"

    def test_wfh_alias(self):
        assert _extract_location("This is a work from home internship") == "Work From Home"

    def test_wfh_abbreviation(self):
        assert _extract_location("WFH | Stipend: 15k/month") == "Work From Home"

    def test_remote(self):
        assert _extract_location("Fully remote position") == "Remote"

    def test_hybrid(self):
        assert _extract_location("Hybrid role in Delhi") in ["Hybrid, Delhi", "Delhi, Hybrid"]

    def test_multiple_cities(self):
        result = _extract_location("Offices in Mumbai and Chennai")
        assert "Mumbai" in result
        assert "Chennai" in result

    def test_no_location(self):
        assert _extract_location("Exciting opportunity for students") == "Not mentioned"

    def test_case_insensitive(self):
        assert _extract_location("BANGALORE office") == "Bangalore"


# ════════════════════════════════════════════════════════
#  parse_listing() integration
# ════════════════════════════════════════════════════════

class TestParseListing:

    def test_returns_all_keys(self):
        raw = {
            "title": "ML Intern @ Razorpay",
            "link": "https://unstop.com/job/123",
            "snippet": "Stipend Rs. 20,000/month. Work From Home. Apply by 31 May 2025.",
            "role": "machine learning intern",
            "source": "unstop.com",
            "scraped_at": "2025-01-01"
        }
        result = parse_listing(raw)
        for key in ("stipend", "deadline", "location", "apply_link", "parsed"):
            assert key in result

    def test_parsed_flag_is_true(self):
        raw = {"title": "", "link": "", "snippet": "", "role": "", "source": "", "scraped_at": ""}
        assert parse_listing(raw)["parsed"] is True

    def test_apply_link_copied_from_link(self):
        raw = {"title": "", "link": "https://example.com/job", "snippet": "", "role": "", "source": "", "scraped_at": ""}
        assert parse_listing(raw)["apply_link"] == "https://example.com/job"

    def test_full_realistic_snippet(self):
        raw = {
            "title": "Python Intern at Razorpay",
            "link": "https://internshala.com/job/456",
            "snippet": "Stipend: Rs. 25000/month. WFH. Apply by 5th May 2025.",
            "role": "software engineering intern",
            "source": "internshala.com",
            "scraped_at": "2025-04-01"
        }
        result = parse_listing(raw)
        assert result["stipend"]  == "₹25,000/month"
        assert result["location"] == "Work From Home"
        assert "May" in result["deadline"]

    def test_original_fields_preserved(self):
        """parse_listing must not drop any original scraper fields"""
        raw = {
            "title": "Test", "link": "https://x.com", "snippet": "test",
            "role": "ml intern", "source": "other", "scraped_at": "2025-01-01"
        }
        result = parse_listing(raw)
        for key in raw:
            assert key in result