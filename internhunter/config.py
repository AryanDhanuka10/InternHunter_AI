"""Central config — all env vars and constants live here."""
import os
from dotenv import load_dotenv

load_dotenv()

def _env(key, default=""):
    """Strip trailing whitespace/newlines — fixes the \n header bug."""
    return os.getenv(key, default).strip()

# ── User Profile ──────────────────────────────────────────────
USER_NAME        = _env("USER_NAME", "Your Name")
USER_EMAIL       = _env("USER_EMAIL", "you@example.com")
USER_COLLEGE     = _env("USER_COLLEGE", "IIT/NIT/DTU etc.")
USER_BRANCH      = _env("USER_BRANCH", "Computer Science")
USER_YEAR        = _env("USER_YEAR", "3rd Year B.Tech")
USER_SKILLS      = [s.strip() for s in _env("USER_SKILLS", "Python,ML,React").split(",")]
USER_GITHUB      = _env("USER_GITHUB", "https://github.com/yourhandle")
USER_LINKEDIN    = _env("USER_LINKEDIN", "https://linkedin.com/in/yourhandle")
USER_RESUME_PATH = _env("USER_RESUME_PATH", "assets/resume.pdf")

# ── Target Roles (your domain only) ──────────────────────────
INTERNSHIP_ROLES = [
    "machine learning intern",
    "data science intern",
    "software engineering intern",
    "backend developer intern",
    "AI research intern",
    "python developer intern",
    "deep learning intern",
    "NLP intern",
    "computer vision intern",
    "MLOps intern",
]

INTERNATIONAL_ROLES = [
    "remote machine learning intern",
    "remote data science intern",
    "remote AI research intern",
    "remote python developer intern",
]

PREFERRED_LOCATIONS = [
    "remote", "work from home", "wfh",
    "bangalore", "delhi", "mumbai",
    "hyderabad", "noida", "gurugram",
]

MIN_STIPEND         = 10000
MAX_RESULTS_PER_RUN = 100

# ── Scoring weights ───────────────────────────────────────────
SCORE_WEIGHTS = {
    "has_stipend":        10,
    "stipend_15k_plus":   15,
    "stipend_25k_plus":   20,
    "preferred_location": 15,
    "has_deadline":       10,
    "is_2026":            20,
    "known_source":        5,
    "has_company":         5,
    "is_international":   10,
}

CURRENT_YEAR = 2026

# ── API Keys ──────────────────────────────────────────────────
SERPER_API_KEY = _env("SERPER_API_KEY")
OPENAI_API_KEY = _env("OPENAI_API_KEY")
GMAIL_USER     = _env("GMAIL_USER")
GMAIL_APP_PASS = _env("GMAIL_APP_PASS")

# ── Paths ─────────────────────────────────────────────────────
DB_PATH     = "data/internships.db"
LOG_PATH    = "logs/daily.log"
DIGEST_PATH = "data/digest"