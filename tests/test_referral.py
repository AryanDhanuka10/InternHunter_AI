"""
Day 13 — Referral Tests
Run:  pytest tests/test_referral.py -v
      pytest tests/ -v
"""
import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from internhunter.referral import (
    build_referral_hints, referral_section_html, referral_section_text,
    _extract_company, _college_aliases, _linkedin_people_url, _linkedin_jobs_url
)


# ── Fixtures ──────────────────────────────────────────────────

def _opp(title="ML Intern @ TestCo", company="TestCo", role="ml intern", source="internshala.com"):
    return {"title": title, "company": company, "role": role, "source": source}


# ════════════════════════════════════════════════════════
#  _college_aliases
# ════════════════════════════════════════════════════════

class TestCollegeAliases:

    def test_dtu_extracted(self):
        aliases = _college_aliases("Delhi Technological University")
        assert "DTU" in aliases

    def test_iit_extracted(self):
        aliases = _college_aliases("Indian Institute of Technology")
        assert "IIT" in aliases[0] or "IIT" in aliases

    def test_full_name_always_included(self):
        name = "Delhi Technological University"
        assert name in _college_aliases(name)

    def test_short_name_returns_itself(self):
        aliases = _college_aliases("DTU")
        assert "DTU" in aliases

    def test_returns_list(self):
        assert isinstance(_college_aliases("Any College"), list)

    def test_acronym_is_first(self):
        aliases = _college_aliases("Delhi Technological University")
        assert aliases[0] == "DTU"


# ════════════════════════════════════════════════════════
#  _extract_company
# ════════════════════════════════════════════════════════

class TestExtractCompany:

    def test_uses_company_field_when_present(self):
        assert _extract_company(_opp(company="Razorpay")) == "Razorpay"

    def test_at_pattern(self):
        opp = _opp(title="ML Intern @ Razorpay", company="")
        assert _extract_company(opp) == "Razorpay"

    def test_at_pattern_with_spaces(self):
        opp = _opp(title="SWE Intern @ Tata Consultancy", company="")
        assert "Tata" in _extract_company(opp)

    def test_at_pattern_lowercase(self):
        opp = _opp(title="ML Intern at Meesho", company="")
        assert _extract_company(opp) == "Meesho"

    def test_linkedin_pulse_format(self):
        """Real format: 'Company name: Uber Role: SWE Intern'"""
        opp = _opp(title="Company name: Uber Role: Software Engineering Intern", company="")
        assert _extract_company(opp) == "Uber"

    def test_linkedin_pulse_upstox(self):
        opp = _opp(title="Company name: Upstox Role: SDE Intern Batch Eligible: 2026", company="")
        assert _extract_company(opp) == "Upstox"

    def test_all_caps_offers_format(self):
        """Real format: 'GOOGLE OFFERS SUMMER INTERNSHIP'"""
        opp = _opp(title="GOOGLE OFFERS SUMMER INTERNSHIP FOR SOFTWARE", company="")
        assert _extract_company(opp) == "Google"

    def test_all_caps_hiring_format(self):
        opp = _opp(title="AMAZON HIRING SOFTWARE INTERNS 2026", company="")
        assert _extract_company(opp) == "Amazon"

    def test_empty_when_no_pattern_matches(self):
        opp = _opp(title="7238 Internships in India 2026", company="")
        assert _extract_company(opp) == ""

    def test_category_page_returns_empty(self):
        opp = _opp(title="212 Software Development Internships - Internshala", company="")
        assert _extract_company(opp) == ""


# ════════════════════════════════════════════════════════
#  _linkedin_people_url
# ════════════════════════════════════════════════════════

class TestLinkedInPeopleUrl:

    def test_returns_linkedin_url(self):
        url = _linkedin_people_url("Razorpay", "DTU")
        assert "linkedin.com" in url

    def test_company_in_url(self):
        url = _linkedin_people_url("Razorpay", "DTU")
        assert "Razorpay" in url

    def test_college_alias_in_url(self):
        url = _linkedin_people_url("Razorpay", "DTU")
        assert "DTU" in url

    def test_people_search_endpoint(self):
        url = _linkedin_people_url("Uber", "IIT")
        assert "search/results/people" in url

    def test_spaces_encoded(self):
        url = _linkedin_people_url("Tata Consultancy", "DTU")
        assert " " not in url   # spaces must be URL-encoded

    def test_jobs_url_contains_company(self):
        url = _linkedin_jobs_url("Google", "ml intern")
        assert "Google" in url
        assert "linkedin.com/jobs" in url


# ════════════════════════════════════════════════════════
#  build_referral_hints
# ════════════════════════════════════════════════════════

class TestBuildReferralHints:

    def test_returns_list(self):
        assert isinstance(build_referral_hints([_opp()]), list)

    def test_empty_input_returns_empty(self):
        assert build_referral_hints([]) == []

    def test_one_hint_per_company(self):
        opps = [_opp(company="Razorpay"), _opp(company="Razorpay")]
        hints = build_referral_hints(opps)
        assert len(hints) == 1

    def test_deduplication_case_insensitive(self):
        opps = [_opp(company="uber"), _opp(company="Uber"), _opp(company="UBER")]
        hints = build_referral_hints(opps)
        assert len(hints) == 1

    def test_hint_contains_company(self):
        hints = build_referral_hints([_opp(company="Razorpay")])
        assert "Razorpay" in hints[0]["hint"]

    def test_hint_contains_college_alias(self):
        # alias is whatever _college_aliases() derives from USER_COLLEGE in .env
        hints = build_referral_hints([_opp(company="Uber")])
        alias = hints[0]["college_alias"]
        assert alias in hints[0]["hint"]

    def test_linkedin_people_url_present(self):
        hints = build_referral_hints([_opp(company="Meesho")])
        assert "linkedin_people" in hints[0]
        assert "linkedin.com" in hints[0]["linkedin_people"]

    def test_linkedin_jobs_url_present(self):
        hints = build_referral_hints([_opp(company="Meesho")])
        assert "linkedin_jobs" in hints[0]
        assert "linkedin.com" in hints[0]["linkedin_jobs"]

    def test_hint_dict_has_required_keys(self):
        hints = build_referral_hints([_opp(company="TestCo")])
        for key in ("company","role","hint","linkedin_people","linkedin_jobs","college_alias","opp_title"):
            assert key in hints[0], f"Missing key: {key}"

    def test_category_page_skipped(self):
        opps = [
            _opp(title="212 Software Internships - Internshala", company=""),
            _opp(title="ML Intern @ Razorpay", company="Razorpay"),
        ]
        hints = build_referral_hints(opps)
        companies = [h["company"] for h in hints]
        assert "Razorpay" in companies
        # The category page should not produce a hint
        assert not any("212" in c or "Internshala" in c for c in companies)

    def test_all_real_formats_extracted(self):
        """All 4 title formats from your real DB should produce hints."""
        opps = [
            {"title": "GOOGLE OFFERS SUMMER INTERNSHIP", "company": "", "role": "swe", "source": "other"},
            {"title": "Company name: Uber Role: SWE Intern - LinkedIn", "company": "", "role": "swe", "source": "linkedin.com/jobs"},
            {"title": "ML Intern @ Razorpay", "company": "Razorpay", "role": "ml", "source": "internshala.com"},
            {"title": "Backend Intern at Meesho", "company": "", "role": "backend", "source": "other"},
        ]
        hints = build_referral_hints(opps)
        companies = [h["company"] for h in hints]
        assert "Google"   in companies
        assert "Uber"     in companies
        assert "Razorpay" in companies
        assert "Meesho"   in companies


# ════════════════════════════════════════════════════════
#  referral_section_html
# ════════════════════════════════════════════════════════

class TestReferralSectionHtml:

    def test_empty_input_returns_empty_string(self):
        assert referral_section_html([]) == ""

    def test_returns_html_string(self):
        hints = build_referral_hints([_opp(company="Razorpay")])
        html  = referral_section_html(hints)
        assert "<table" in html

    def test_contains_company_name(self):
        hints = build_referral_hints([_opp(company="Razorpay")])
        html  = referral_section_html(hints)
        assert "Razorpay" in html

    def test_contains_find_alumni_link(self):
        hints = build_referral_hints([_opp(company="Uber")])
        html  = referral_section_html(hints)
        assert "Find Alumni" in html

    def test_linkedin_url_in_html(self):
        hints = build_referral_hints([_opp(company="Meesho")])
        html  = referral_section_html(hints)
        assert "linkedin.com" in html

    def test_hint_count_in_header(self):
        opps  = [_opp(company="A"), _opp(company="B"), _opp(company="C")]
        hints = build_referral_hints(opps)
        html  = referral_section_html(hints)
        assert "3 Companies" in html


# ════════════════════════════════════════════════════════
#  referral_section_text
# ════════════════════════════════════════════════════════

class TestReferralSectionText:

    def test_empty_input_returns_empty_string(self):
        assert referral_section_text([]) == ""

    def test_contains_referral_finder_header(self):
        hints = build_referral_hints([_opp(company="Razorpay")])
        text  = referral_section_text(hints)
        assert "REFERRAL FINDER" in text

    def test_contains_company(self):
        hints = build_referral_hints([_opp(company="Uber")])
        text  = referral_section_text(hints)
        assert "Uber" in text

    def test_contains_alumni_url(self):
        hints = build_referral_hints([_opp(company="Meesho")])
        text  = referral_section_text(hints)
        assert "linkedin.com" in text

    def test_numbered_entries(self):
        opps  = [_opp(company="A"), _opp(company="B")]
        hints = build_referral_hints(opps)
        text  = referral_section_text(hints)
        assert "[1]" in text
        assert "[2]" in text

    def test_contains_hint_text(self):
        hints = build_referral_hints([_opp(company="Google")])
        text  = referral_section_text(hints)
        assert "Search LinkedIn" in text