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
USER_SKILLS      = os.getenv("USER_SKILLS", "Python,ML,React").split(",")
USER_GITHUB      = os.getenv("USER_GITHUB", "https://github.com/yourhandle")
USER_LINKEDIN    = os.getenv("USER_LINKEDIN", "https://linkedin.com/in/yourhandle")
USER_RESUME_PATH = os.getenv("USER_RESUME_PATH", "assets/resume.pdf")

# ── Search Settings ───────────────────────────────────────────
INTERNSHIP_ROLES = [
    "software engineering intern",
    "machine learning intern",
    "data science intern",
    "backend intern",
    "fullstack intern",
    "research intern",
]
PREFERRED_LOCATIONS = ["remote", "bangalore", "delhi", "mumbai", "hyderabad"]
MIN_STIPEND         = 10000   # INR/month — listings below this are dropped (0 = keep all)
MAX_RESULTS_PER_RUN = 50

# ── Scoring weights ───────────────────────────────────────────
# Score = sum of weights for each condition that matches.
# Higher score → listing appears first in digest and dashboard.
SCORE_WEIGHTS = {
    "has_stipend":        12,   # any stipend info extracted
    "stipend_15k_plus":   15,   # stipend >= ₹15,000/month
    "stipend_25k_plus":   20,   # stipend >= ₹25,000/month (stacks with above)
    "preferred_location": 20,   # matches any location in PREFERRED_LOCATIONS
    "has_deadline":       10,   # deadline extracted (means it's an individual listing)
    "known_source":       5,    # internshala / unstop / wellfound (not 'other')
    "has_company":        5,    # company field is non-empty
}

# ── API Keys ──────────────────────────────────────────────────
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
GMAIL_USER     = os.getenv("GMAIL_USER", "").strip()
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "").strip()

# ── Paths ─────────────────────────────────────────────────────
DB_PATH     = "data/internships.db"
LOG_PATH    = "logs/daily.log"
DIGEST_PATH = "data/digest"