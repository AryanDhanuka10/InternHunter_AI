"""
Day 6 — Mailer Interactive Script
Tests cold email drafting (offline) and optionally sends a real digest email.

Run:  python tests/test_mailer_interactive.py
"""
import sys, os, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

from dotenv import load_dotenv; load_dotenv()
from internhunter.mailer  import draft_cold_email, send_digest_email, _credentials_ok
from internhunter.digest  import build_digest_html, build_digest_text
from internhunter.config  import GMAIL_USER

SEP = "═" * 58

FAKE_OPP = {
    "role":    "machine learning intern",
    "company": "Google DeepMind",
    "title":   "ML Research Intern @ Google DeepMind",
    "link":    "https://careers.google.com/jobs/1",
}

def run():
    print(f"\n{SEP}")
    print("  InternHunter — Day 6 Mailer Interactive")
    print(SEP)

    # ── Step 1: credentials check ──────────────────────────
    print("\n[1/4]  Credentials check")
    if _credentials_ok():
        print(f"  ✅  Gmail ready: {GMAIL_USER}")
    else:
        print("  ❌  Gmail not configured. Add to .env:")
        print("      GMAIL_USER=you@gmail.com")
        print("      GMAIL_APP_PASS=your_16_char_app_password")
        print("\n  Continuing with offline tests only...\n")

    # ── Step 2: draft cold email (offline) ─────────────────
    print("\n[2/4]  Cold email draft (offline, no API used)")
    draft = draft_cold_email(FAKE_OPP)   # reads from config/.env
    print("\n  ── Subject ──────────────────────────────────────")
    print(f"  {draft['subject']}")
    print("\n  ── Body (plain text) ────────────────────────────")
    print("\n".join(f"  {line}" for line in draft["text"].splitlines()))
    print("\n  ✅  draft_cold_email() works")

    # ── Step 3: save cold email to file ───────────────────
    os.makedirs("data/digest", exist_ok=True)
    with open("data/digest/cold_email_sample.txt", "w") as f:
        f.write(f"Subject: {draft['subject']}\n\n{draft['text']}")
    with open("data/digest/cold_email_sample.html", "w") as f:
        f.write(draft["html"])
    print("\n  Saved drafts:")
    print("  → data/digest/cold_email_sample.txt")
    print("  → data/digest/cold_email_sample.html")

    # ── Step 4: send real digest (optional) ───────────────
    print(f"\n[4/4]  Send real digest email to yourself")
    if not _credentials_ok():
        print("  Skipped — fix credentials first")
    else:
        ans = input(f"  Send test digest to {GMAIL_USER}? (y/n): ").strip().lower()
        if ans == "y":
            fake_opps = [
                {"title":"ML Intern @ Razorpay","source":"internshala.com",
                 "stipend":"₹20,000/month","deadline":"31 May 2025",
                 "location":"Remote","apply_link":"https://internshala.com/1",
                 "link":"#","role":"ml intern","scraped_at":""},
                {"title":"SWE Intern @ Zepto","source":"unstop.com",
                 "stipend":"₹15,000/month","deadline":"15 June 2025",
                 "location":"Bangalore","apply_link":"https://unstop.com/2",
                 "link":"#","role":"swe intern","scraped_at":""},
                {"title":"Data Science Intern @ Swiggy","source":"linkedin.com/jobs",
                 "stipend":"Not mentioned","deadline":"Not mentioned",
                 "location":"Hyderabad","apply_link":"https://linkedin.com/3",
                 "link":"#","role":"data science intern","scraped_at":""},
            ]
            stats = {"total":47,"new":3,"applied":0,"with_stipend":2,
                     "with_deadline":2,"with_location":3,"notified":0}
            html = build_digest_html(fake_opps, stats=stats)
            sent = send_digest_email(
                subject="[InternHunter] Test Digest — Day 6",
                body_html=html
            )
            if sent:
                print(f"  ✅  Email sent! Check your inbox: {GMAIL_USER}")
                print("      (Check Spam if not in inbox — first send often lands there)")
            else:
                print("  ❌  Send failed — check logs above for the exact error")
        else:
            print("  Skipped")

    print(f"\n  Day 6 done. Run: pytest tests/test_mailer.py -v")
    print(f"{SEP}\n")

if __name__ == "__main__":
    run()
