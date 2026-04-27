"""
Day 5 — Digest Tests
Run:  pytest tests/test_digest.py -v
      pytest tests/ -v
"""
import sys, os, re, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from internhunter.digest import (
    build_digest_html, build_digest_text, save_digest,
    _source_badge, _stipend_style, _safe
)


# ── Fixtures ──────────────────────────────────────────────────

def _opp(**kwargs) -> dict:
    base = {
        "title":      "ML Intern @ Razorpay",
        "role":       "machine learning intern",
        "source":     "internshala.com",
        "stipend":    "₹20,000/month",
        "deadline":   "31 May 2025",
        "location":   "Remote",
        "apply_link": "https://internshala.com/job/1",
        "link":       "https://internshala.com/job/1",
    }
    base.update(kwargs)
    return base


SAMPLE_OPPS = [
    _opp(title="ML Intern @ Razorpay",    stipend="₹20,000/month",  location="Remote"),
    _opp(title="SWE Intern @ Zepto",      stipend="₹15,000/month",  location="Bangalore",
         source="unstop.com", apply_link="https://unstop.com/job/2"),
    _opp(title="Data Intern @ Swiggy",    stipend="Not mentioned",  location="Not mentioned",
         source="linkedin.com/jobs", apply_link="https://linkedin.com/job/3"),
    _opp(title="Backend Intern @ Meesho", stipend="₹10,000/month",  location="Hyderabad",
         source="wellfound.com", apply_link="https://wellfound.com/job/4"),
]


# ════════════════════════════════════════════════════════
#  Helper functions
# ════════════════════════════════════════════════════════

class TestHelpers:

    def test_safe_returns_value_when_present(self):
        assert _safe("Remote") == "Remote"

    def test_safe_returns_fallback_for_not_mentioned(self):
        assert _safe("Not mentioned") == "—"

    def test_safe_returns_fallback_for_empty(self):
        assert _safe("") == "—"
        assert _safe(None) == "—"

    def test_safe_custom_fallback(self):
        assert _safe("Not mentioned", "N/A") == "N/A"

    def test_stipend_style_high_green(self):
        style = _stipend_style("₹20,000/month")
        assert "1a7f37" in style   # green
        assert "bold" in style

    def test_stipend_style_low_amber(self):
        style = _stipend_style("₹10,000/month")
        assert "b76e00" in style   # amber

    def test_stipend_style_not_mentioned_grey(self):
        style = _stipend_style("Not mentioned")
        assert "aaa" in style

    def test_source_badge_internshala(self):
        badge = _source_badge("internshala.com")
        assert "0d6efd" in badge   # blue
        assert "Internshala" in badge

    def test_source_badge_linkedin(self):
        badge = _source_badge("linkedin.com/jobs")
        assert "0a66c2" in badge
        assert "Linkedin" in badge

    def test_source_badge_unknown(self):
        badge = _source_badge("someweirdsite.io")
        assert "6c757d" in badge   # grey fallback


# ════════════════════════════════════════════════════════
#  build_digest_html
# ════════════════════════════════════════════════════════

class TestBuildDigestHtml:

    def test_returns_string(self):
        assert isinstance(build_digest_html(SAMPLE_OPPS), str)

    def test_contains_doctype(self):
        html = build_digest_html(SAMPLE_OPPS)
        assert "<!DOCTYPE html>" in html

    def test_contains_all_titles(self):
        html = build_digest_html(SAMPLE_OPPS)
        for opp in SAMPLE_OPPS:
            assert opp["title"] in html

    def test_contains_apply_links(self):
        html = build_digest_html(SAMPLE_OPPS)
        assert "https://internshala.com/job/1" in html
        assert "https://unstop.com/job/2"      in html

    def test_high_stipend_shows_green(self):
        html = build_digest_html([_opp(stipend="₹20,000/month")])
        assert "1a7f37" in html

    def test_low_stipend_shows_amber(self):
        html = build_digest_html([_opp(stipend="₹8,000/month")])
        assert "b76e00" in html

    def test_not_mentioned_shows_dash(self):
        html = build_digest_html([_opp(stipend="Not mentioned")])
        # Should show — not the raw "Not mentioned" string in the cell
        assert "—" in html

    def test_contains_source_badges(self):
        html = build_digest_html(SAMPLE_OPPS)
        assert "Internshala" in html
        assert "Unstop"      in html
        assert "Linkedin"    in html

    def test_empty_list_shows_fallback_message(self):
        html = build_digest_html([])
        assert "No new opportunities" in html

    def test_count_in_header(self):
        html = build_digest_html(SAMPLE_OPPS)
        assert f"{len(SAMPLE_OPPS)}" in html

    def test_with_stats_bar(self):
        stats = {"total": 47, "new": 10, "applied": 3, "with_stipend": 8}
        html  = build_digest_html(SAMPLE_OPPS, stats=stats)
        assert "47" in html
        assert "With Stipend" in html

    def test_without_stats_no_stats_bar(self):
        html = build_digest_html(SAMPLE_OPPS, stats=None)
        assert "With Stipend" not in html

    def test_footer_present(self):
        html = build_digest_html(SAMPLE_OPPS)
        assert "InternHunter Bot" in html

    def test_single_opportunity(self):
        html = build_digest_html([_opp()])
        assert '<b>1</b> new opportunity' in html   # singular

    def test_multiple_opportunities(self):
        html = build_digest_html(SAMPLE_OPPS)
        assert "opportunities" in html       # plural


# ════════════════════════════════════════════════════════
#  build_digest_text
# ════════════════════════════════════════════════════════

class TestBuildDigestText:

    def test_returns_string(self):
        assert isinstance(build_digest_text(SAMPLE_OPPS), str)

    def test_contains_header(self):
        text = build_digest_text(SAMPLE_OPPS)
        assert "InternHunter Daily Digest" in text

    def test_contains_all_titles(self):
        text = build_digest_text(SAMPLE_OPPS)
        for opp in SAMPLE_OPPS:
            assert opp["title"] in text

    def test_contains_stipend_and_location(self):
        text = build_digest_text([_opp(stipend="₹20,000/month", location="Remote")])
        assert "₹20,000/month" in text
        assert "Remote" in text

    def test_not_mentioned_shows_dash(self):
        text = build_digest_text([_opp(stipend="Not mentioned")])
        assert "—" in text

    def test_empty_list_message(self):
        text = build_digest_text([])
        assert "No new opportunities" in text

    def test_numbered_entries(self):
        text = build_digest_text(SAMPLE_OPPS)
        assert "[1]" in text
        assert f"[{len(SAMPLE_OPPS)}]" in text

    def test_apply_links_present(self):
        text = build_digest_text(SAMPLE_OPPS)
        assert "https://internshala.com/job/1" in text


# ════════════════════════════════════════════════════════
#  save_digest
# ════════════════════════════════════════════════════════

class TestSaveDigest:

    def test_creates_html_and_text_files(self, tmp_path):
        html = build_digest_html(SAMPLE_OPPS)
        text = build_digest_text(SAMPLE_OPPS)
        html_path, text_path = save_digest(html, text, out_dir=str(tmp_path))
        assert os.path.exists(html_path)
        assert os.path.exists(text_path)

    def test_html_file_has_correct_extension(self, tmp_path):
        html_path, _ = save_digest("html", "text", out_dir=str(tmp_path))
        assert html_path.endswith(".html")

    def test_text_file_has_correct_extension(self, tmp_path):
        _, text_path = save_digest("html", "text", out_dir=str(tmp_path))
        assert text_path.endswith(".txt")

    def test_file_content_matches(self, tmp_path):
        html = build_digest_html(SAMPLE_OPPS)
        text = build_digest_text(SAMPLE_OPPS)
        html_path, text_path = save_digest(html, text, out_dir=str(tmp_path))
        assert open(html_path).read() == html
        assert open(text_path).read() == text

    def test_creates_output_dir_if_missing(self, tmp_path):
        out = str(tmp_path / "nested" / "digest")
        save_digest("html", "text", out_dir=out)
        assert os.path.isdir(out)

    def test_filename_contains_date(self, tmp_path):
        from datetime import datetime
        html_path, _ = save_digest("html", "text", out_dir=str(tmp_path))
        today = datetime.now().strftime("%Y-%m-%d")
        assert today in html_path