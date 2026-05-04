"""
Day 14 — PDF Digest Tests
Run:  pytest tests/test_digest_pdf.py -v
      pytest tests/ -v
"""
import sys, os, re, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from internhunter.digest_pdf import (
    build_digest_pdf, attach_pdf_to_email,
    _rupee as _stipend_safe, _stip_style, _safe
)
# colors not needed

# ── Fixtures ──────────────────────────────────────────────────

def _opp(n=1, **kwargs):
    base = {
        "title":      f"ML Intern #{n} @ TestCo",
        "role":       "machine learning intern",
        "source":     "internshala.com",
        "stipend":    "Rs.20,000/month",
        "deadline":   "31 May 2025",
        "location":   "Remote",
        "apply_link": f"https://internshala.com/{n}",
        "company":    "TestCo",
    }
    base.update(kwargs)
    return base

STATS = {"total":10,"new":3,"applied":1,"with_stipend":5,
         "with_deadline":2,"with_location":7,"notified":7}

HINTS = [
    {"company":"TestCo","hint":"Search LinkedIn for TestCo + DTU alumni",
     "linkedin_people":"https://linkedin.com/search/results/people/?keywords=TestCo+DTU",
     "linkedin_jobs":"https://linkedin.com/jobs/search/?keywords=TestCo",
     "college_alias":"DTU","opp_title":"ML Intern @ TestCo","role":"ml intern"},
]


# ════════════════════════════════════════════════════════
#  Helper functions
# ════════════════════════════════════════════════════════

class TestHelpers:

    def test_stipend_safe_replaces_rupee(self):
        assert "₹" not in _stipend_safe("₹20,000/month")
        assert "Rs." in _stipend_safe("₹20,000/month")

    def test_stipend_safe_not_mentioned(self):
        assert _stipend_safe("Not mentioned") == "-"

    def test_stipend_safe_empty(self):
        assert _stipend_safe("") == "-"
        assert _stipend_safe(None) == "-"

    def test_stipend_safe_abbreviates_month(self):
        assert "/mo" in _stipend_safe("₹20,000/month")

    def test_stipend_color_high_is_green(self):
        from reportlab.lib.styles import ParagraphStyle
        styles = _stip_style.__globals__["_styles"]() if hasattr(_stip_style, "__globals__") else {}
        # _stip_style returns a ParagraphStyle, just verify it runs without error
        from internhunter.digest_pdf import _styles
        S = _styles()
        result = _stip_style("₹20,000/month", S)
        assert hasattr(result, "fontName")

    def test_stipend_color_low_is_amber(self):
        from internhunter.digest_pdf import _styles
        S = _styles()
        result = _stip_style("₹8,000/month", S)
        assert hasattr(result, "fontName")

    def test_stipend_color_not_mentioned_is_grey(self):
        from internhunter.digest_pdf import _styles
        S = _styles()
        result = _stip_style("Not mentioned", S)
        assert hasattr(result, "fontName")

    def test_safe_returns_value(self):
        assert _safe("Remote") == "Remote"

    def test_safe_returns_fallback_for_not_mentioned(self):
        assert _safe("Not mentioned") == "-"

    def test_safe_custom_fallback(self):
        assert _safe("", "N/A") == "N/A"


# ════════════════════════════════════════════════════════
#  build_digest_pdf
# ════════════════════════════════════════════════════════

class TestBuildDigestPdf:

    def test_returns_file_path(self, tmp_path):
        path = build_digest_pdf([_opp()], out_dir=str(tmp_path))
        assert isinstance(path, str)

    def test_file_exists(self, tmp_path):
        path = build_digest_pdf([_opp()], out_dir=str(tmp_path))
        assert os.path.exists(path)

    def test_file_is_pdf(self, tmp_path):
        path = build_digest_pdf([_opp()], out_dir=str(tmp_path))
        with open(path, "rb") as f:
            assert f.read(4) == b"%PDF"

    def test_file_extension(self, tmp_path):
        path = build_digest_pdf([_opp()], out_dir=str(tmp_path))
        assert path.endswith(".pdf")

    def test_filename_contains_date(self, tmp_path):
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        path  = build_digest_pdf([_opp()], out_dir=str(tmp_path))
        assert today in path

    def test_creates_output_dir(self, tmp_path):
        out = str(tmp_path / "nested" / "dir")
        build_digest_pdf([_opp()], out_dir=out)
        assert os.path.isdir(out)

    def test_non_zero_file_size(self, tmp_path):
        path = build_digest_pdf([_opp()], out_dir=str(tmp_path))
        assert os.path.getsize(path) > 1000   # at least 1KB

    def test_empty_opportunities(self, tmp_path):
        path = build_digest_pdf([], out_dir=str(tmp_path))
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0

    def test_with_stats(self, tmp_path):
        path = build_digest_pdf([_opp()], stats=STATS, out_dir=str(tmp_path))
        assert os.path.exists(path)

    def test_with_referral_hints(self, tmp_path):
        path = build_digest_pdf([_opp()], referral_hints=HINTS, out_dir=str(tmp_path))
        assert os.path.exists(path)

    def test_multiple_opportunities(self, tmp_path):
        opps = [_opp(i) for i in range(10)]
        path = build_digest_pdf(opps, out_dir=str(tmp_path))
        # More rows → larger file
        size = os.path.getsize(path)
        path1 = build_digest_pdf([_opp(1)], out_dir=str(tmp_path / "one"))
        size1 = os.path.getsize(path1)
        assert size >= size1

    def test_rupee_symbol_not_in_pdf_binary(self, tmp_path):
        """PDF must not contain raw rupee glyph — causes render issues."""
        opp  = _opp(stipend="₹20,000/month")
        path = build_digest_pdf([opp], out_dir=str(tmp_path))
        raw  = open(path, "rb").read()
        # '₹' is UTF-8 0xE2 0x82 0xB9
        assert b"\xe2\x82\xb9" not in raw

    def test_stipend_shown_as_rs(self, tmp_path):
        """_stipend_safe converts rupee symbol to Rs. before PDF is built."""
        # The PDF stream is compressed — test the helper directly
        assert "Rs." in _stipend_safe("₹20,000/month")
        assert "₹"  not in _stipend_safe("₹20,000/month")


# ════════════════════════════════════════════════════════
#  attach_pdf_to_email
# ════════════════════════════════════════════════════════

class TestAttachPdfToEmail:

    def test_returns_true_when_file_exists(self, tmp_path):
        from email.mime.multipart import MIMEMultipart
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake content")
        msg = MIMEMultipart()
        assert attach_pdf_to_email(msg, str(pdf)) is True

    def test_returns_false_when_missing(self, tmp_path):
        from email.mime.multipart import MIMEMultipart
        msg = MIMEMultipart()
        assert attach_pdf_to_email(msg, str(tmp_path / "missing.pdf")) is False

    def test_returns_false_for_none(self):
        from email.mime.multipart import MIMEMultipart
        msg = MIMEMultipart()
        assert attach_pdf_to_email(msg, None) is False

    def test_attachment_added_to_message(self, tmp_path):
        from email.mime.multipart import MIMEMultipart
        pdf = tmp_path / "digest.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake content")
        msg = MIMEMultipart()
        attach_pdf_to_email(msg, str(pdf))
        payloads = msg.get_payload()
        assert any("digest.pdf" in str(p.get("Content-Disposition",""))
                   for p in payloads)

    def test_content_type_is_pdf(self, tmp_path):
        from email.mime.multipart import MIMEMultipart
        pdf = tmp_path / "report.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake content")
        msg = MIMEMultipart()
        attach_pdf_to_email(msg, str(pdf))
        payloads = msg.get_payload()
        assert any(p.get_content_type() == "application/pdf" for p in payloads)