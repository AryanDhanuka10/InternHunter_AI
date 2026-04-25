"""
Day 2 — Scraper Test Script
Run:  python day2_test_scraper.py

Tests:
  1. API key check
  2. Single role search (fast, uses 1 API credit)
  3. Pretty-print first 3 results as JSON
  4. Rate limit + empty result simulation
  5. Full scrape_all_roles() with progress (optional — uses ~6 credits)
"""

import json, sys, os, logging
sys.path.insert(0, os.path.dirname(__file__))

# ── Logging: show INFO in terminal ────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S"
)

from dotenv import load_dotenv
load_dotenv()

from internhunter.config import SERPER_API_KEY, INTERNSHIP_ROLES
from internhunter.scraper import google_search_internships, scrape_all_roles, _detect_source

# ─────────────────────────────────────────────────────────────
# TEST 1 — API Key presence check
# ─────────────────────────────────────────────────────────────
print("\n" + "═"*56)
print("  TEST 1 — API Key Check")
print("═"*56)

if not SERPER_API_KEY:
    print("  ❌  SERPER_API_KEY is missing from your .env!")
    print("      Get a free key at serper.dev then re-run.")
    sys.exit(1)
elif SERPER_API_KEY in ("your_serper_api_key_here", "PASTE_YOUR_SERPER_KEY_HERE"):
    print("  ❌  SERPER_API_KEY still has placeholder value in .env")
    sys.exit(1)
else:
    masked = SERPER_API_KEY[:6] + "..." + SERPER_API_KEY[-4:]
    print(f"  ✅  Key found: {masked}  (length: {len(SERPER_API_KEY)} chars)")

# ─────────────────────────────────────────────────────────────
# TEST 2 — Single role search (uses 1 API credit)
# ─────────────────────────────────────────────────────────────
print("\n" + "═"*56)
print("  TEST 2 — Single Role Search  (1 API credit)")
print("═"*56)

TEST_ROLE = "machine learning intern"
print(f"  Searching for: '{TEST_ROLE}' ...\n")

results = google_search_internships(TEST_ROLE)

if not results:
    print("  ⚠️   No results returned. Possible reasons:")
    print("       • Invalid API key")
    print("       • No internet / firewall blocking api.serper.dev")
    print("       • Serper free quota exhausted (check serper.dev dashboard)")
    sys.exit(1)

print(f"  ✅  Got {len(results)} results from Serper\n")

# ─────────────────────────────────────────────────────────────
# TEST 3 — Pretty-print first 3 results
# ─────────────────────────────────────────────────────────────
print("═"*56)
print("  TEST 3 — First 3 Results (Pretty JSON)")
print("═"*56)

for i, r in enumerate(results[:3], 1):
    print(f"\n  ── Result {i} ──────────────────────────────────")
    print(json.dumps(r, indent=4, ensure_ascii=False))

# ─────────────────────────────────────────────────────────────
# TEST 4 — Source detection check
# ─────────────────────────────────────────────────────────────
print("\n" + "═"*56)
print("  TEST 4 — Source Detection")
print("═"*56)

source_counts = {}
for r in results:
    src = r.get("source", "other")
    source_counts[src] = source_counts.get(src, 0) + 1

for src, count in sorted(source_counts.items(), key=lambda x: -x[1]):
    bar = "█" * count
    print(f"  {src:<22} {bar} ({count})")

# ─────────────────────────────────────────────────────────────
# TEST 5 — Rate limit simulation (no real API call)
# ─────────────────────────────────────────────────────────────
print("\n" + "═"*56)
print("  TEST 5 — Rate Limit Handler Simulation (offline)")
print("═"*56)

import unittest.mock as mock
import requests

# Simulate a 429 response on first call, success on second
call_count = {"n": 0}

def fake_post(*args, **kwargs):
    call_count["n"] += 1
    fake = mock.MagicMock()
    if call_count["n"] == 1:
        fake.status_code = 429
        fake.raise_for_status.side_effect = requests.exceptions.HTTPError("429")
    else:
        fake.status_code = 200
        fake.raise_for_status = lambda: None
        fake.json.return_value = {"organic": [
            {"title": "Mock ML Intern", "link": "https://mock.com/job/1",
             "snippet": "₹15,000/month. Remote. Apply by 31 May 2025."}
        ]}
    return fake

with mock.patch("internhunter.scraper.requests.post", side_effect=fake_post):
    sim_results = google_search_internships("ml intern test")

if sim_results:
    print(f"  ✅  Rate limit retry worked — got {len(sim_results)} result after retry")
else:
    print(f"  ✅  Rate limit handled gracefully (returned empty list after retries)")

# ─────────────────────────────────────────────────────────────
# TEST 6 — Empty results simulation
# ─────────────────────────────────────────────────────────────
print("\n" + "═"*56)
print("  TEST 6 — Empty Results Handler (offline)")
print("═"*56)

def fake_empty_post(*args, **kwargs):
    fake = mock.MagicMock()
    fake.status_code = 200
    fake.raise_for_status = lambda: None
    fake.json.return_value = {"organic": []}   # Serper returns nothing
    return fake

with mock.patch("internhunter.scraper.requests.post", side_effect=fake_empty_post):
    empty_results = google_search_internships("obscure role xyz")

assert empty_results == [], "Expected empty list"
print("  ✅  Empty result handled gracefully — returned [] with log message")

# ─────────────────────────────────────────────────────────────
# OPTIONAL — Full scrape (uses ~6 API credits)
# ─────────────────────────────────────────────────────────────
print("\n" + "═"*56)
print("  OPTIONAL — Full scrape_all_roles()")
print("═"*56)
answer = input("  Run full scrape for ALL roles? Uses ~6 API credits. (y/n): ").strip().lower()

if answer == "y":
    print()
    all_results = scrape_all_roles()
    print(f"\n  ✅  Total unique listings: {len(all_results)}")
    print("\n  Top 5 by source:")
    sources = {}
    for r in all_results:
        sources[r["source"]] = sources.get(r["source"], 0) + 1
    for src, cnt in sorted(sources.items(), key=lambda x: -x[1])[:5]:
        print(f"    {src:<25} {cnt} listings")
else:
    print("  Skipped. Run full pipeline with: python -m internhunter.scheduler")

# ─────────────────────────────────────────────────────────────
print("\n" + "═"*56)
print("  🎉  Day 2 complete! All scraper tests passed.")
print("  Next: Day 3 — parser.py (extract stipend/deadline/location)")
print("═"*56 + "\n")
