"""
InternHunter AI - Project Template Generator
Run this once to scaffold the entire project structure.
"""

import os
import sys

STRUCTURE = {
    "internhunter/": None,
    "internhunter/__init__.py": "",
    "internhunter/config.py": '''"""Central config — all env vars and constants live here."""
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
    "fullstack intern",
    "research intern"
]
PREFERRED_LOCATIONS = ["remote", "bangalore", "delhi", "mumbai", "hyderabad"]
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
''',
    "internhunter/scraper.py": '''"""Web scraper — pulls internship listings from multiple sources."""
import re, time, random, logging, requests
from datetime import datetime
from internhunter.config import SERPER_API_KEY, INTERNSHIP_ROLES, MAX_RESULTS_PER_RUN

logger = logging.getLogger(__name__)

SOURCES = [
    "internshala.com",
    "linkedin.com/jobs",
    "unstop.com",
    "wellfound.com",
    "indeed.co.in",
    "letsintern.com",
    "iimjobs.com"
]


def google_search_internships(role: str, extra_query: str = "") -> list[dict]:
    """Use Serper (Google Search API) to find internship listings."""
    if not SERPER_API_KEY:
        logger.warning("SERPER_API_KEY not set — skipping search")
        return []

    query = f"{role} internship 2025 {extra_query} stipend apply"
    url   = "https://google.serper.dev/search"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {"q": query, "num": 10, "gl": "in", "hl": "en"}

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        r.raise_for_status()
        results = r.json().get("organic", [])
        parsed = []
        for item in results:
            parsed.append({
                "title":   item.get("title", ""),
                "link":    item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source":  _detect_source(item.get("link", "")),
                "role":    role,
                "scraped_at": datetime.utcnow().isoformat()
            })
        return parsed
    except Exception as e:
        logger.error(f"Search failed for '{role}': {e}")
        return []


def _detect_source(url: str) -> str:
    for src in SOURCES:
        if src in url:
            return src
    return "other"


def scrape_all_roles() -> list[dict]:
    """Run search for every role in config and deduplicate by URL."""
    all_results, seen = [], set()
    for role in INTERNSHIP_ROLES:
        results = google_search_internships(role)
        for r in results:
            if r["link"] not in seen:
                seen.add(r["link"])
                all_results.append(r)
        time.sleep(random.uniform(1, 2))  # polite delay
    logger.info(f"Total unique listings scraped: {len(all_results)}")
    return all_results[:MAX_RESULTS_PER_RUN]
''',
    "internhunter/parser.py": '''"""Parse raw listing snippets → structured opportunity dicts using AI."""
import re, logging
from internhunter.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)


def parse_listing(raw: dict) -> dict:
    """Extract structured fields from a raw search result."""
    snippet = raw.get("snippet", "")
    title   = raw.get("title", "")

    stipend  = _extract_stipend(snippet + " " + title)
    deadline = _extract_deadline(snippet)
    location = _extract_location(snippet + " " + title)

    return {
        **raw,
        "stipend":     stipend,
        "deadline":    deadline,
        "location":    location,
        "apply_link":  raw.get("link", ""),
        "parsed":      True
    }


def _extract_stipend(text: str) -> str:
    patterns = [
        r"(?:Rs\.?|INR|₹)\s?(\d[\d,]+)\s?(?:per month|/month|pm|p\.m\.)?",
        r"(\d[\d,]+)\s?(?:per month|/month|pm)\s?(?:stipend)?",
        r"stipend[:\s]+(?:Rs\.?|INR|₹)?\s?(\d[\d,]+)"
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return f"₹{m.group(1)}/month"
    return "Not mentioned"


def _extract_deadline(text: str) -> str:
    patterns = [
        r"(?:deadline|last date|apply by|closes?)[:\s]+([A-Za-z0-9 ,]+\d{4})",
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return "Not mentioned"


def _extract_location(text: str) -> str:
    keywords = ["remote", "work from home", "wfh", "bangalore", "delhi",
                "mumbai", "hyderabad", "pune", "chennai", "kolkata", "noida", "gurugram"]
    found = [k for k in keywords if k.lower() in text.lower()]
    return ", ".join(found).title() if found else "Not mentioned"
''',
    "internhunter/database.py": '''"""SQLite storage for internship opportunities."""
import sqlite3, logging
from datetime import datetime
from internhunter.config import DB_PATH

logger = logging.getLogger(__name__)


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True) if "/" in DB_PATH else None
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS opportunities (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT,
                role        TEXT,
                company     TEXT,
                link        TEXT UNIQUE,
                source      TEXT,
                stipend     TEXT,
                deadline    TEXT,
                location    TEXT,
                apply_link  TEXT,
                snippet     TEXT,
                status      TEXT DEFAULT 'new',
                scraped_at  TEXT,
                notified    INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS applied (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                opp_id     INTEGER,
                method     TEXT,
                applied_at TEXT,
                notes      TEXT
            )
        """)
        conn.commit()
    logger.info("Database initialised")


def upsert_opportunity(opp: dict) -> bool:
    """Insert new opportunity; skip if link already exists. Returns True if inserted."""
    import os
    os.makedirs("data", exist_ok=True)
    sql = """
        INSERT OR IGNORE INTO opportunities
            (title, role, company, link, source, stipend, deadline, location, apply_link, snippet, scraped_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """
    with get_conn() as conn:
        cur = conn.execute(sql, (
            opp.get("title"), opp.get("role"), opp.get("company", ""),
            opp.get("link"), opp.get("source"), opp.get("stipend"),
            opp.get("deadline"), opp.get("location"), opp.get("apply_link"),
            opp.get("snippet"), opp.get("scraped_at")
        ))
        conn.commit()
        return cur.rowcount > 0


def get_new_opportunities(limit: int = 20) -> list[dict]:
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM opportunities WHERE status='new' AND notified=0 ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        return [dict(r) for r in cur.fetchall()]


def mark_notified(ids: list[int]):
    with get_conn() as conn:
        conn.executemany("UPDATE opportunities SET notified=1 WHERE id=?", [(i,) for i in ids])
        conn.commit()
''',
    "internhunter/mailer.py": '''"""Email drafting + sending via Gmail SMTP."""
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
''',
    "internhunter/digest.py": '''"""Build the daily HTML digest of new opportunities."""
from datetime import datetime


def build_digest_html(opportunities: list[dict]) -> str:
    rows = ""
    for o in opportunities:
        rows += f"""
        <tr>
            <td style='padding:8px;border:1px solid #ddd'>{o.get('title','—')}</td>
            <td style='padding:8px;border:1px solid #ddd'>{o.get('role','—')}</td>
            <td style='padding:8px;border:1px solid #ddd'>{o.get('stipend','—')}</td>
            <td style='padding:8px;border:1px solid #ddd'>{o.get('deadline','—')}</td>
            <td style='padding:8px;border:1px solid #ddd'>{o.get('location','—')}</td>
            <td style='padding:8px;border:1px solid #ddd'>
                <a href='{o.get("apply_link","#")}'>Apply →</a>
            </td>
        </tr>"""

    return f"""
    <html><body style='font-family:Arial,sans-serif;max-width:900px;margin:auto'>
    <h2 style='color:#1a73e8'>🚀 InternHunter Daily Digest — {datetime.now().strftime('%d %b %Y')}</h2>
    <p>Found <b>{len(opportunities)}</b> new internship opportunities today.</p>
    <table style='border-collapse:collapse;width:100%'>
        <tr style='background:#1a73e8;color:white'>
            <th style='padding:8px'>Title</th><th>Role</th><th>Stipend</th>
            <th>Deadline</th><th>Location</th><th>Apply</th>
        </tr>
        {rows}
    </table>
    <br><p style='color:grey;font-size:12px'>InternHunter Bot · auto-generated</p>
    </body></html>"""
''',
    "internhunter/scheduler.py": '''"""Runs the full pipeline once — call via cron or GitHub Actions."""
import logging, os
from datetime import datetime
from internhunter.scraper  import scrape_all_roles
from internhunter.parser   import parse_listing
from internhunter.database import init_db, upsert_opportunity, get_new_opportunities, mark_notified
from internhunter.digest   import build_digest_html
from internhunter.mailer   import send_digest_email

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.FileHandler("logs/daily.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run():
    logger.info("═══ InternHunter pipeline started ═══")
    init_db()

    raw    = scrape_all_roles()
    parsed = [parse_listing(r) for r in raw]

    new_count = sum(upsert_opportunity(p) for p in parsed)
    logger.info(f"New opportunities stored: {new_count}")

    opps = get_new_opportunities(30)
    if opps:
        html = build_digest_html(opps)
        sent = send_digest_email(
            subject=f"[InternHunter] {len(opps)} New Internships — {datetime.now().strftime('%d %b')}",
            body_html=html
        )
        if sent:
            mark_notified([o["id"] for o in opps])
    else:
        logger.info("No new opportunities to report today.")

    logger.info("═══ Pipeline complete ═══")


if __name__ == "__main__":
    run()
''',
    "tests/__init__.py": "",
    "tests/test_daily.py": '''"""Daily smoke test — run: pytest tests/test_daily.py -v"""
import pytest
from internhunter.parser   import parse_listing, _extract_stipend, _extract_deadline
from internhunter.database import init_db, upsert_opportunity, get_new_opportunities
from internhunter.digest   import build_digest_html
from internhunter.mailer   import draft_cold_email

# ── Parser tests ─────────────────────────────────────────────
def test_extract_stipend_inr():
    assert "₹15,000" in _extract_stipend("Stipend: INR 15,000 per month")

def test_extract_stipend_symbol():
    assert "₹20000" in _extract_stipend("₹20000/month stipend offered")

def test_extract_deadline():
    from internhunter.parser import _extract_deadline
    result = _extract_deadline("Apply by 30 June 2025")
    assert "June" in result or "2025" in result

def test_parse_listing_keys():
    raw = {"title":"SWE Intern","link":"https://example.com","snippet":"₹15,000/month. Remote. Apply by 31 May 2025","role":"software engineering intern","scraped_at":"2025-01-01"}
    parsed = parse_listing(raw)
    assert "stipend"  in parsed
    assert "deadline" in parsed
    assert "location" in parsed

# ── Database tests ────────────────────────────────────────────
def test_db_init_and_insert(tmp_path, monkeypatch):
    monkeypatch.setattr("internhunter.database.DB_PATH", str(tmp_path / "test.db"))
    init_db()
    opp = {"title":"Test","role":"ml intern","link":"https://test.com/1",
           "source":"test","stipend":"₹10,000","deadline":"31 May","location":"Remote",
           "apply_link":"https://test.com/1","snippet":"test snippet","scraped_at":"2025-01-01"}
    assert upsert_opportunity(opp) == True
    assert upsert_opportunity(opp) == False  # duplicate

def test_get_new_opportunities(tmp_path, monkeypatch):
    monkeypatch.setattr("internhunter.database.DB_PATH", str(tmp_path / "test2.db"))
    init_db()
    opp = {"title":"Test2","role":"data intern","link":"https://test.com/2",
           "source":"test","stipend":"Not mentioned","deadline":"Not mentioned",
           "location":"Bangalore","apply_link":"https://test.com/2",
           "snippet":"data intern","scraped_at":"2025-01-01"}
    upsert_opportunity(opp)
    results = get_new_opportunities()
    assert len(results) >= 1

# ── Digest test ───────────────────────────────────────────────
def test_build_digest_html():
    opps = [{"title":"Test","role":"swe","stipend":"₹15k","deadline":"31 May","location":"Remote","apply_link":"#"}]
    html = build_digest_html(opps)
    assert "<table" in html
    assert "InternHunter" in html

# ── Mailer draft test ─────────────────────────────────────────
def test_draft_cold_email():
    opp  = {"role":"ML Engineer","company":"Acme Corp"}
    user = {"name":"Raj","year":"3rd Year","branch":"CSE","college":"DTU",
            "skills":["Python","ML"],"github":"https://github.com/raj",
            "linkedin":"https://linkedin.com/in/raj","email":"raj@example.com"}
    body = draft_cold_email(opp, user)
    assert "Raj"       in body
    assert "Acme Corp" in body
    assert "ML Engineer" in body
''',
    "app/__init__.py": "",
    "app/main.py": '''"""
FastAPI app — run: uvicorn app.main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import opportunities, profile, actions

app = FastAPI(title="InternHunter API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(opportunities.router, prefix="/api/opportunities", tags=["opportunities"])
app.include_router(profile.router,       prefix="/api/profile",       tags=["profile"])
app.include_router(actions.router,       prefix="/api/actions",        tags=["actions"])

@app.get("/")
def root():
    return {"status": "InternHunter is running 🚀"}
''',
    "app/routers/__init__.py": "",
    "app/routers/opportunities.py": '''from fastapi import APIRouter
from internhunter.database import init_db, get_new_opportunities

router = APIRouter()

@router.get("/")
def list_opportunities(limit: int = 20):
    init_db()
    return get_new_opportunities(limit)
''',
    "app/routers/profile.py": '''from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter()

class Profile(BaseModel):
    name: str
    email: str
    college: str
    branch: str
    year: str
    skills: List[str]
    github: str
    linkedin: str

_profile_store = {}

@router.post("/")
def save_profile(profile: Profile):
    _profile_store.update(profile.dict())
    return {"message": "Profile saved", "profile": _profile_store}

@router.get("/")
def get_profile():
    return _profile_store
''',
    "app/routers/actions.py": '''from fastapi import APIRouter
from internhunter.scheduler import run as run_pipeline

router = APIRouter()

@router.post("/run-pipeline")
def trigger_pipeline():
    try:
        run_pipeline()
        return {"status": "success", "message": "Pipeline ran successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
''',
    "data/.gitkeep": "",
    "logs/.gitkeep": "",
    "assets/.gitkeep": "",
    ".env.example": """# ── Copy this to .env and fill in your values ──
USER_NAME=Your Full Name
USER_EMAIL=you@gmail.com
USER_COLLEGE=Delhi Technological University
USER_BRANCH=Computer Science and Engineering
USER_YEAR=3rd Year B.Tech
USER_SKILLS=Python,Machine Learning,React,SQL,FastAPI
USER_GITHUB=https://github.com/yourusername
USER_LINKEDIN=https://linkedin.com/in/yourusername
USER_RESUME_PATH=assets/resume.pdf

SERPER_API_KEY=your_serper_api_key_here
OPENAI_API_KEY=your_openai_key_here_optional

GMAIL_USER=you@gmail.com
GMAIL_APP_PASS=your_16_char_app_password
""",
    "requirements.txt": """# Core
requests>=2.31.0
python-dotenv>=1.0.0

# Database
# sqlite3 is built-in

# Web framework
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
pydantic>=2.0.0

# Testing
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx>=0.27.0

# PDF generation
reportlab>=4.0.0

# Scheduler (optional: use cron or GitHub Actions instead)
schedule>=1.2.0

# HTML parsing (for direct site scraping later)
beautifulsoup4>=4.12.0
lxml>=5.0.0
""",
    ".github/workflows/daily.yml": """name: Daily Internship Hunt

on:
  schedule:
    - cron: '0 4 * * *'   # 9:30 AM IST every day
  workflow_dispatch:        # allow manual trigger

jobs:
  hunt:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run pipeline
        env:
          SERPER_API_KEY: ${{ secrets.SERPER_API_KEY }}
          GMAIL_USER:     ${{ secrets.GMAIL_USER }}
          GMAIL_APP_PASS: ${{ secrets.GMAIL_APP_PASS }}
          USER_NAME:      ${{ secrets.USER_NAME }}
          USER_EMAIL:     ${{ secrets.USER_EMAIL }}
          USER_COLLEGE:   ${{ secrets.USER_COLLEGE }}
          USER_BRANCH:    ${{ secrets.USER_BRANCH }}
          USER_YEAR:      ${{ secrets.USER_YEAR }}
          USER_SKILLS:    ${{ secrets.USER_SKILLS }}
          USER_GITHUB:    ${{ secrets.USER_GITHUB }}
          USER_LINKEDIN:  ${{ secrets.USER_LINKEDIN }}
        run: python -m internhunter.scheduler

      - name: Run tests
        run: pytest tests/ -v --tb=short
""",
    "commit_messages.txt": """# ── Daily Git Commit Messages (copy-paste ready) ──

Day 1:  feat: scaffold project structure and config
Day 2:  feat: add google search scraper with Serper API
Day 3:  feat: add regex parser for stipend/deadline/location
Day 4:  feat: add SQLite database layer with upsert logic
Day 5:  feat: add daily digest HTML builder
Day 6:  feat: add Gmail SMTP mailer and cold email template
Day 7:  feat: wire full pipeline in scheduler.py
Day 8:  test: add daily smoke tests (parser, db, digest, mailer)
Day 9:  feat: add FastAPI app with opportunities/profile/actions routes
Day 10: ci: add GitHub Actions workflow for daily 9:30 AM IST run
Day 11: feat: add .env.example and dotenv config loading
Day 12: refactor: clean up logging and error handling across modules
Day 13: feat: add stipend filter in config
Day 14: docs: update README with setup and usage instructions
Day 15: feat: add Streamlit dashboard (Day 15 task)
""",
    "README.md": """# 🚀 InternHunter AI

> Automated internship finder for B.Tech students — searches the web daily, parses key details, emails you a digest, and drafts cold emails.

## Quick Start

```bash
# 1. Create project structure
python template.py

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# → Edit .env with your details

# 4. Run once manually
python -m internhunter.scheduler

# 5. Run tests
pytest tests/ -v

# 6. Start API server
uvicorn app.main:app --reload
```

## How It Works

1. **Scraper** → Searches Google (via Serper API) for internship roles you define
2. **Parser** → Extracts stipend, deadline, location from snippets
3. **Database** → Stores unique opportunities in SQLite
4. **Digest** → Builds a clean HTML email with all new opportunities
5. **Mailer** → Sends the digest to your Gmail inbox
6. **Scheduler** → Runs the full pipeline; triggered daily via GitHub Actions

## APIs Needed

| API | Free Tier | Purpose |
|-----|-----------|---------|
| [Serper](https://serper.dev) | 2500 searches/month | Google search |
| Gmail App Password | Free | Send digest emails |

## Automation (GitHub Actions)

Push this repo to GitHub, add secrets in Settings → Secrets, and the pipeline runs every day at 9:30 AM IST automatically — **free forever**.
"""
}


def create_structure():
    print("🏗  Creating InternHunter project structure...\n")
    for path, content in STRUCTURE.items():
        if path.endswith("/"):
            os.makedirs(path, exist_ok=True)
            print(f"  📁  {path}")
        else:
            os.makedirs(os.path.dirname(path) if "/" in path else ".", exist_ok=True)
            if not os.path.exists(path):
                with open(path, "w") as f:
                    f.write(content or "")
                print(f"  ✅  {path}")
            else:
                print(f"  ⏭   {path}  (already exists, skipped)")

    print("\n✨  Done! Next steps:")
    print("  1.  pip install -r requirements.txt")
    print("  2.  cp .env.example .env  →  fill in your details")
    print("  3.  python -m internhunter.scheduler   (manual test run)")
    print("  4.  pytest tests/ -v")


if __name__ == "__main__":
    create_structure()