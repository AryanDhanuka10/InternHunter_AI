"""Central config — all env vars and constants live here."""
import os
from dotenv import load_dotenv

load_dotenv()

# ── User Profile ──────────────────────────────────────────────
USER_NAME        = os.getenv("USER_NAME", "Your Name")
USER_EMAIL       = os.getenv("USER_EMAIL", "you@example.com")
USER_COLLEGE     = os.getenv("USER_COLLEGE", "IIT/NIT/DTU etc.")
USER_BRANCH      = os.getenv("USER_BRANCH", "Computer Science")
USER_YEAR        = os.getenv("USER_YEAR", "3rd Year B.Tech")
USER_SKILLS      = os.getenv("USER_SKILLS", "Python, ML, React").split(",")
USER_GITHUB      = os.getenv("USER_GITHUB", "https://github.com/yourhandle")
USER_LINKEDIN    = os.getenv("USER_LINKEDIN", "https://linkedin.com/in/yourhandle")
USER_RESUME_PATH = os.getenv("USER_RESUME_PATH", "assets/resume.pdf")

# ── Search Settings ───────────────────────────────────────────
INTERNSHIP_ROLES = [
    "software engineering intern",
    "machine learning intern",
    "data science intern",
    "backend intern",
    "AI intern"
]
PREFERRED_LOCATIONS = ["remote", "Greater Noida", "Noida", "Delhi", "Bangalore", "Mumbai", "Hyderabad"]
MIN_STIPEND        = 10000          # INR per month (0 = no filter)
MAX_RESULTS_PER_RUN = 50

# ── API Keys ──────────────────────────────────────────────────
SERPER_API_KEY   = os.getenv("SERPER_API_KEY", "")   # google search
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY", "")   # email drafting
GMAIL_USER       = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASS   = os.getenv("GMAIL_APP_PASS", "")   # Gmail App Password

# ── Paths ─────────────────────────────────────────────────────
DB_PATH          = "data/internships.db"
LOG_PATH         = "logs/daily.log"
DIGEST_PATH      = "data/digest"
