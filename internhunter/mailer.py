"""
mailer.py — Gmail SMTP sender + cold email drafter.

Two responsibilities:
  1. send_digest_email()  — sends the daily HTML digest to your own inbox
  2. draft_cold_email()   — returns a ready-to-send cold email string
  3. send_cold_email()    — sends a cold email to a company HR address
"""
import smtplib, logging, os
from email.mime.text       import MIMEText
from email.mime.multipart  import MIMEMultipart
from email.mime.base       import MIMEBase
from email                 import encoders
from internhunter.config   import (
    GMAIL_USER, GMAIL_APP_PASS,
    USER_NAME, USER_EMAIL, USER_COLLEGE,
    USER_BRANCH, USER_YEAR, USER_SKILLS,
    USER_GITHUB, USER_LINKEDIN, USER_RESUME_PATH,
)

logger = logging.getLogger(__name__)

# ── Cold email templates ──────────────────────────────────────

_COLD_EMAIL_SUBJECT = "Internship Application — {role} | {college}"

_COLD_EMAIL_TEXT = """\
Dear Hiring Team,

I am {name}, a {year} student of {branch} at {college}.

I came across {company} and would love to contribute as a {role} intern. \
My key skills include {skills}, and I have worked on projects that \
closely align with your domain.

I have attached my resume for your reference. I would be grateful \
for the opportunity to discuss how I can contribute to your team.

GitHub  : {github}
LinkedIn: {linkedin}

Thank you for your time.

Warm regards,
{name}
{email}
"""

_COLD_EMAIL_HTML = """\
<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;max-width:560px;margin:auto;
             color:#333;font-size:14px;line-height:1.7">
  <p>Dear Hiring Team,</p>
  <p>
    I am <strong>{name}</strong>, a {year} student of {branch} at <strong>{college}</strong>.
  </p>
  <p>
    I came across <strong>{company}</strong> and would love to contribute as a
    <strong>{role}</strong> intern. My key skills include {skills}, and I have
    worked on projects that closely align with your domain.
  </p>
  <p>I have attached my resume for your reference. I would be grateful for the
     opportunity to discuss how I can contribute to your team.</p>
  <p>
    <a href="{github}">GitHub</a> &nbsp;·&nbsp;
    <a href="{linkedin}">LinkedIn</a>
  </p>
  <p>Thank you for your time.<br><br>
     Warm regards,<br>
     <strong>{name}</strong><br>
     <a href="mailto:{email}">{email}</a>
  </p>
</body>
</html>
"""


# ── Public API ────────────────────────────────────────────────

def draft_cold_email(opportunity: dict, user: dict = None) -> dict:
    """
    Return a dict with keys: subject, text, html — ready to send or print.
    If user is None, reads from config automatically.
    """
    u = _resolve_user(user)
    fmt = dict(
        name    = u["name"],
        year    = u["year"],
        branch  = u["branch"],
        college = u["college"],
        skills  = ", ".join(u["skills"][:5]),
        github  = u["github"],
        linkedin= u["linkedin"],
        email   = u["email"],
        role    = " ".join(w if w.isupper() else w.capitalize() for w in opportunity.get("role", "Software Engineering").split()),
        company = opportunity.get("company") or opportunity.get("title", "your company"),
    )
    return {
        "subject": _COLD_EMAIL_SUBJECT.format(**fmt),
        "text":    _COLD_EMAIL_TEXT.format(**fmt),
        "html":    _COLD_EMAIL_HTML.format(**fmt),
    }


def send_digest_email(subject: str, body_html: str, to: str = None) -> bool:
    """Send the daily HTML digest to your own Gmail inbox."""
    if not _credentials_ok():
        return False

    recipient = to or GMAIL_USER
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = recipient
    msg.attach(MIMEText(body_html, "html"))

    return _send(msg, recipient, label="digest")


def send_cold_email(opportunity: dict, to_email: str,
                    user: dict = None, attach_resume: bool = True) -> bool:
    """
    Draft and send a cold email to a company HR address.
    attach_resume=True will attach the PDF at USER_RESUME_PATH if it exists.
    """
    if not _credentials_ok():
        return False

    draft = draft_cold_email(opportunity, user)
    msg   = MIMEMultipart("mixed")
    alt   = MIMEMultipart("alternative")
    alt.attach(MIMEText(draft["text"], "plain"))
    alt.attach(MIMEText(draft["html"], "html"))
    msg.attach(alt)

    msg["Subject"] = draft["subject"]
    msg["From"]    = GMAIL_USER
    msg["To"]      = to_email

    if attach_resume:
        _attach_resume(msg)

    return _send(msg, to_email, label=f"cold email → {to_email}")


# ── Private helpers ───────────────────────────────────────────

def _resolve_user(user: dict = None) -> dict:
    """Fall back to config values if no user dict provided."""
    return user or {
        "name":     USER_NAME,
        "email":    USER_EMAIL,
        "college":  USER_COLLEGE,
        "branch":   USER_BRANCH,
        "year":     USER_YEAR,
        "skills":   USER_SKILLS,
        "github":   USER_GITHUB,
        "linkedin": USER_LINKEDIN,
    }


def _credentials_ok() -> bool:
    if not GMAIL_USER or not GMAIL_APP_PASS:
        logger.warning(
            "Gmail credentials missing — set GMAIL_USER and GMAIL_APP_PASS in .env"
        )
        return False
    if len(GMAIL_APP_PASS.replace(" ", "")) < 16:
        logger.warning(
            "GMAIL_APP_PASS looks too short — must be 16 chars from Google App Passwords"
        )
        return False
    return True


def _attach_resume(msg: MIMEMultipart):
    path = USER_RESUME_PATH
    if not path or not os.path.exists(path):
        logger.info(f"Resume not found at '{path}' — sending without attachment")
        return
    with open(path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    filename = os.path.basename(path)
    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
    msg.attach(part)
    logger.info(f"Attached resume: {filename}")


def _send(msg: MIMEMultipart, to: str, label: str = "email") -> bool:
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASS)
            server.sendmail(GMAIL_USER, to, msg.as_string())
        logger.info(f"Sent {label} to {to}")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error(
            "Gmail auth failed — check GMAIL_APP_PASS in .env\n"
            "  Must be a 16-char App Password, NOT your real Gmail password\n"
            "  Get one: myaccount.google.com → Security → App Passwords"
        )
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error sending {label}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending {label}: {type(e).__name__}: {e}")
        return False