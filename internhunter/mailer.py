"""Email drafting + sending via Gmail SMTP."""
import smtplib, logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from internhunter.config import GMAIL_USER, GMAIL_APP_PASS, USER_NAME, USER_EMAIL

logger = logging.getLogger(__name__)


COLD_MAIL_TEMPLATE = """Subject: Internship Application — {role} | {college}

Dear Hiring Team,

I am {name}, a {year} student of {branch} at {college}. I came across {company} and would love to contribute as a {role} intern.

My key skills include {skills}. I have worked on projects that align closely with your domain, and I believe I can add immediate value to your team.

I have attached my resume for your reference. I would be grateful for the opportunity to discuss how I can contribute.

GitHub: {github}
LinkedIn: {linkedin}

Thank you for your time.

Warm regards,
{name}
{email}
"""


def draft_cold_email(opportunity: dict, user: dict) -> str:
    return COLD_MAIL_TEMPLATE.format(
        role     = opportunity.get("role", "Software Engineering"),
        company  = opportunity.get("company", "your company"),
        name     = user["name"],
        year     = user["year"],
        branch   = user["branch"],
        college  = user["college"],
        skills   = ", ".join(user["skills"][:5]),
        github   = user["github"],
        linkedin = user["linkedin"],
        email    = user["email"]
    )


def send_digest_email(subject: str, body_html: str, to: str = None):
    """Send the daily digest to the user's own inbox."""
    if not GMAIL_USER or not GMAIL_APP_PASS:
        logger.warning("Gmail credentials not set — skipping email")
        return False

    to = to or GMAIL_USER
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = to
    msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASS)
            server.sendmail(GMAIL_USER, to, msg.as_string())
        logger.info(f"Digest sent to {to}")
        return True
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False
