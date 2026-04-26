"""
Day 4 — Database Interactive Script
Loads your real 47 scraped listings into the DB and lets you query them.

Run:  python tests/test_database_interactive.py
      (No API credits used — reads from DB or re-scrapes if DB empty)
"""
import sys, os, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

from dotenv import load_dotenv; load_dotenv()

from internhunter.database import (
    init_db, upsert_many, get_new_opportunities,
    get_by_stipend, get_by_location, get_by_role, get_stats
)
from internhunter.scraper import scrape_all_roles
from internhunter.parser  import parse_all

SEP = "═" * 58


def print_table(rows: list[dict], cols: list[tuple]):
    """cols = [(field, width, label), ...]"""
    header = "  " + "  ".join(f"{label:<{w}}" for _, w, label in cols)
    print(header)
    print("  " + "─" * (sum(w for _, w, _ in cols) + 2 * len(cols)))
    for r in rows:
        line = "  " + "  ".join(str(r.get(f, "—"))[:w].ljust(w) for f, w, _ in cols)
        print(line)


def run():
    print(f"\n{SEP}")
    print("  InternHunter AI — Day 4 Database Interactive")
    print(SEP)

    # ── Step 1: Init DB ───────────────────────────────────────
    print("\n[1/5]  Initialising database...")
    init_db()
    stats = get_stats()
    print(f"       DB ready. Current total: {stats['total']} opportunities")

    # ── Step 2: Load data ─────────────────────────────────────
    print(f"\n[2/5]  Loading data into DB")
    if stats["total"] == 0:
        print("       DB is empty — running full scrape (~6 API credits)...")
        raw    = scrape_all_roles()
        parsed = parse_all(raw)
        ins, skp = upsert_many(parsed)
        print(f"       Inserted: {ins}  |  Duplicates skipped: {skp}")
    else:
        print(f"       DB already has {stats['total']} rows — skipping scrape")
        print("       (Delete data/internships.db to force a fresh scrape)")

    # ── Step 3: Stats ─────────────────────────────────────────
    print(f"\n[3/5]  Database stats")
    stats = get_stats()
    for k, v in stats.items():
        bar = "█" * min(v, 30)
        print(f"       {k:<18} {v:>3}  {bar}")

    # ── Step 4: Query examples ────────────────────────────────
    print(f"\n[4/5]  Query examples")

    print("\n  → Latest 5 new opportunities:")
    rows = get_new_opportunities(limit=5)
    print_table(rows, [
        ("title",    38, "Title"),
        ("stipend",  16, "Stipend"),
        ("location", 14, "Location"),
    ])

    print("\n  → Opportunities with stipend >= ₹15,000:")
    rows = get_by_stipend(min_amount=15000, limit=5)
    if rows:
        print_table(rows, [
            ("title",    38, "Title"),
            ("stipend",  16, "Stipend"),
            ("source",   16, "Source"),
        ])
    else:
        print("       None found (most snippets are category pages without stipend info)")

    print("\n  → Remote opportunities:")
    rows = get_by_location("remote", limit=5)
    if rows:
        print_table(rows, [("title", 40, "Title"), ("location", 20, "Location")])
    else:
        print("       None found")

    print("\n  → ML / Data Science roles:")
    rows = get_by_role("machine learning", limit=5)
    if rows:
        print_table(rows, [("title", 40, "Title"), ("role", 26, "Role")])
    else:
        print("       None found")

    # ── Step 5: CLI shell ─────────────────────────────────────
    print(f"\n[5/5]  Quick query shell  (type 'quit' to exit)")
    print("       Commands: new | stipend <amount> | location <city> | role <keyword> | stats")
    print()

    while True:
        try:
            cmd = input("  db> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break

        if cmd in ("quit", "exit", "q"):
            break
        elif cmd == "new":
            rows = get_new_opportunities(10)
            print_table(rows, [("title",38,"Title"),("stipend",16,"Stipend"),("location",14,"Location")])
        elif cmd.startswith("stipend"):
            parts = cmd.split()
            amount = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            rows = get_by_stipend(min_amount=amount, limit=10)
            print_table(rows, [("title",38,"Title"),("stipend",16,"Stipend")])
        elif cmd.startswith("location"):
            loc = cmd.split(None, 1)[1] if len(cmd.split()) > 1 else ""
            rows = get_by_location(loc, limit=10)
            print_table(rows, [("title",40,"Title"),("location",20,"Location")])
        elif cmd.startswith("role"):
            role = cmd.split(None, 1)[1] if len(cmd.split()) > 1 else ""
            rows = get_by_role(role, limit=10)
            print_table(rows, [("title",40,"Title"),("role",26,"Role")])
        elif cmd == "stats":
            stats = get_stats()
            for k, v in stats.items():
                print(f"    {k:<18} {v}")
        elif cmd:
            print("  Unknown command. Try: new | stipend 15000 | location bangalore | role ml | stats")

    print(f"\n  Day 4 done. Commit and move to Day 5 (digest.py)")
    print(f"{SEP}\n")


if __name__ == "__main__":
    run()