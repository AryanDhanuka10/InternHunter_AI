"""
Day 6 — Mailer Tests
Run:  pytest tests/test_mailer.py -v
      pytest tests/ -v
"""
import sys, os, smtplib
import unittest.mock as mock
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from internhunter.mailer import (
    draft_cold_email, send_digest_email, send_cold_email,
    _credentials_ok, _resolve_user
)

FAKE_USER = {
    "name": "Aryan Dhanuka", "email": "aryan@example.com",
    "college": "DTU", "branch": "CSE", "year": "3rd Year B.Tech",
    "skills": ["Python", "ML", "React", "SQL", "FastAPI"],
    "github": "https://github.com/aryan", "linkedin": "https://linkedin.com/in/aryan",
}
FAKE_OPP = {
    "role": "machine learning intern", "company": "Google DeepMind",
    "title": "ML Research Intern @ Google", "link": "https://careers.google.com/1",
}


# ════════════════════════════════════════════════════════
#  draft_cold_email
# ════════════════════════════════════════════════════════

class TestDraftColdEmail:

    def test_returns_dict_with_required_keys(self):
        draft = draft_cold_email(FAKE_OPP, FAKE_USER)
        assert "subject" in draft
        assert "text"    in draft
        assert "html"    in draft

    def test_subject_contains_role_and_college(self):
        draft = draft_cold_email(FAKE_OPP, FAKE_USER)
        assert "Machine Learning Intern" in draft["subject"]
        assert "DTU" in draft["subject"]

    def test_text_contains_user_name(self):
        draft = draft_cold_email(FAKE_OPP, FAKE_USER)
        assert "Aryan Dhanuka" in draft["text"]

    def test_text_contains_company(self):
        draft = draft_cold_email(FAKE_OPP, FAKE_USER)
        assert "Google DeepMind" in draft["text"]

    def test_text_contains_skills(self):
        draft = draft_cold_email(FAKE_OPP, FAKE_USER)
        assert "Python" in draft["text"]
        assert "ML" in draft["text"]

    def test_text_contains_github_and_linkedin(self):
        draft = draft_cold_email(FAKE_OPP, FAKE_USER)
        assert "https://github.com/aryan"        in draft["text"]
        assert "https://linkedin.com/in/aryan"   in draft["text"]

    def test_html_is_valid_html(self):
        draft = draft_cold_email(FAKE_OPP, FAKE_USER)
        assert "<html>" in draft["html"]
        assert "</html>" in draft["html"]
        assert "Aryan Dhanuka" in draft["html"]

    def test_html_contains_links(self):
        draft = draft_cold_email(FAKE_OPP, FAKE_USER)
        assert 'href="https://github.com/aryan"'      in draft["html"]
        assert 'href="https://linkedin.com/in/aryan"' in draft["html"]

    def test_uses_config_when_no_user_passed(self, monkeypatch):
        monkeypatch.setattr("internhunter.mailer.USER_NAME",    "Config User")
        monkeypatch.setattr("internhunter.mailer.USER_COLLEGE", "IIT Delhi")
        draft = draft_cold_email(FAKE_OPP)   # no user= argument
        assert "Config User" in draft["text"]
        assert "IIT Delhi"   in draft["subject"]

    def test_max_5_skills_in_email(self):
        user = {**FAKE_USER, "skills": ["Golang","Rust","Kotlin","Swift","Scala","COBOL","Fortran"]}
        draft = draft_cold_email(FAKE_OPP, user)
        assert "COBOL" not in draft["text"]
        assert "Fortran" not in draft["text"]

    def test_fallback_when_company_missing(self):
        opp = {"role": "backend intern"}   # no company key
        draft = draft_cold_email(opp, FAKE_USER)
        assert "Backend Intern" in draft["subject"]
        # should not crash and should put something in place of company
        assert draft["text"]

    def test_role_is_title_cased(self):
        draft = draft_cold_email(FAKE_OPP, FAKE_USER)
        assert "Machine Learning Intern" in draft["subject"]  # not lowercase


# ════════════════════════════════════════════════════════
#  _credentials_ok
# ════════════════════════════════════════════════════════

class TestCredentialsOk:

    def test_missing_gmail_user_returns_false(self, monkeypatch):
        monkeypatch.setattr("internhunter.mailer.GMAIL_USER",     "")
        monkeypatch.setattr("internhunter.mailer.GMAIL_APP_PASS", "abcdabcdabcdabcd")
        assert _credentials_ok() is False

    def test_missing_app_pass_returns_false(self, monkeypatch):
        monkeypatch.setattr("internhunter.mailer.GMAIL_USER",     "user@gmail.com")
        monkeypatch.setattr("internhunter.mailer.GMAIL_APP_PASS", "")
        assert _credentials_ok() is False

    def test_short_app_pass_returns_false(self, monkeypatch):
        monkeypatch.setattr("internhunter.mailer.GMAIL_USER",     "user@gmail.com")
        monkeypatch.setattr("internhunter.mailer.GMAIL_APP_PASS", "tooshort")
        assert _credentials_ok() is False

    def test_valid_credentials_returns_true(self, monkeypatch):
        monkeypatch.setattr("internhunter.mailer.GMAIL_USER",     "user@gmail.com")
        monkeypatch.setattr("internhunter.mailer.GMAIL_APP_PASS", "abcdabcdabcdabcd")
        assert _credentials_ok() is True


# ════════════════════════════════════════════════════════
#  send_digest_email  (mocked SMTP)
# ════════════════════════════════════════════════════════

@pytest.fixture
def valid_creds(monkeypatch):
    monkeypatch.setattr("internhunter.mailer.GMAIL_USER",     "aryan@gmail.com")
    monkeypatch.setattr("internhunter.mailer.GMAIL_APP_PASS", "abcdabcdabcdabcd")


class TestSendDigestEmail:

    def test_returns_true_on_success(self, valid_creds):
        with mock.patch("internhunter.mailer.smtplib.SMTP_SSL") as mock_smtp:
            mock_smtp.return_value.__enter__ = mock.Mock(return_value=mock.MagicMock())
            mock_smtp.return_value.__exit__  = mock.Mock(return_value=False)
            result = send_digest_email("Test Subject", "<h1>Test</h1>")
        assert result is True

    def test_returns_false_when_no_credentials(self, monkeypatch):
        monkeypatch.setattr("internhunter.mailer.GMAIL_USER",     "")
        monkeypatch.setattr("internhunter.mailer.GMAIL_APP_PASS", "")
        assert send_digest_email("Subject", "<h1>body</h1>") is False

    def test_returns_false_on_auth_error(self, valid_creds):
        with mock.patch("internhunter.mailer.smtplib.SMTP_SSL") as mock_smtp:
            instance = mock_smtp.return_value.__enter__.return_value
            instance.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Bad credentials")
            result = send_digest_email("Subject", "<h1>body</h1>")
        assert result is False

    def test_returns_false_on_smtp_error(self, valid_creds):
        with mock.patch("internhunter.mailer.smtplib.SMTP_SSL") as mock_smtp:
            instance = mock_smtp.return_value.__enter__.return_value
            instance.sendmail.side_effect = smtplib.SMTPException("Connection refused")
            result = send_digest_email("Subject", "<h1>body</h1>")
        assert result is False

    def test_sends_to_custom_recipient(self, valid_creds):
        sent_to = {}
        def fake_sendmail(from_addr, to_addr, msg):
            sent_to["to"] = to_addr
        with mock.patch("internhunter.mailer.smtplib.SMTP_SSL") as mock_smtp:
            instance = mock_smtp.return_value.__enter__.return_value
            instance.sendmail.side_effect = fake_sendmail
            send_digest_email("Subj", "<h1>body</h1>", to="other@gmail.com")
        assert sent_to.get("to") == "other@gmail.com"


# ════════════════════════════════════════════════════════
#  send_cold_email  (mocked SMTP)
# ════════════════════════════════════════════════════════

class TestSendColdEmail:

    def test_returns_true_on_success(self, valid_creds):
        with mock.patch("internhunter.mailer.smtplib.SMTP_SSL") as mock_smtp:
            mock_smtp.return_value.__enter__ = mock.Mock(return_value=mock.MagicMock())
            mock_smtp.return_value.__exit__  = mock.Mock(return_value=False)
            result = send_cold_email(FAKE_OPP, "hr@company.com",
                                     user=FAKE_USER, attach_resume=False)
        assert result is True

    def test_no_credentials_returns_false(self, monkeypatch):
        monkeypatch.setattr("internhunter.mailer.GMAIL_USER",     "")
        monkeypatch.setattr("internhunter.mailer.GMAIL_APP_PASS", "")
        assert send_cold_email(FAKE_OPP, "hr@co.com",
                               user=FAKE_USER, attach_resume=False) is False

    def test_skips_resume_when_flag_false(self, valid_creds):
        attach_called = {"n": 0}
        original = __import__("internhunter.mailer", fromlist=["_attach_resume"])
        with mock.patch("internhunter.mailer._attach_resume",
                        side_effect=lambda m: attach_called.__setitem__("n", 1)):
            with mock.patch("internhunter.mailer.smtplib.SMTP_SSL") as mock_smtp:
                mock_smtp.return_value.__enter__ = mock.Mock(return_value=mock.MagicMock())
                mock_smtp.return_value.__exit__  = mock.Mock(return_value=False)
                send_cold_email(FAKE_OPP, "hr@co.com",
                                user=FAKE_USER, attach_resume=False)
        assert attach_called["n"] == 0
