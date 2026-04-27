"""
read_logs.py — Parse and display logs/daily.log in a readable format.

Run:  python read_logs.py              # last run only
      python read_logs.py --all        # all runs in the file
      python read_logs.py --tail 20    # last N raw lines
"""
import sys, re
from datetime import datetime

LOG_PATH = "logs/daily.log"
STAGES   = ["db_init", "scrape", "parse", "store", "digest", "notify"]


def parse_runs(lines: list[str]) -> list[dict]:
    """Split log lines into individual pipeline runs."""
    runs, current = [], []
    for line in lines:
        if "pipeline started" in line:
            if current:
                runs.append(current)
            current = [line]
        elif current:
            current.append(line)
    if current:
        runs.append(current)
    return runs


def summarise_run(lines: list[str]) -> dict:
    """Extract key metrics from a single run's log lines."""
    text   = "\n".join(lines)
    result = {
        "started":    "",
        "elapsed":    "",
        "stages_ok":  [],
        "stages_fail":[],
        "scraped":    "—",
        "inserted":   "—",
        "duplicates": "—",
        "new_opps":   "—",
        "email_sent": "—",
        "errors":     [],
    }

    # Timestamp from first line
    m = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", lines[0])
    if m:
        result["started"] = m.group(1)

    for line in lines:
        # Stages
        if "└─ DONE:" in line:
            for s in ["1 · DB init","2 · Scrape","3 · Parse",
                      "4 · Store","5 · Digest","6 · Notify"]:
                if s in line:
                    m2 = re.search(r"\((.+?)\)", line)
                    result["stages_ok"].append(
                        f"{s.split('·')[1].strip()} ({m2.group(1) if m2 else '?'})"
                    )
        if "└─ FAIL:" in line:
            result["stages_fail"].append(line.strip())

        # Metrics
        m = re.search(r"Scraped (\d+) unique", line)
        if m: result["scraped"] = m.group(1)
        m = re.search(r"Inserted:\s*(\d+)\s*\|.*Duplicates.*:\s*(\d+)", line)
        if m: result["inserted"], result["duplicates"] = m.group(1), m.group(2)
        m = re.search(r"Built digest for (\d+)", line)
        if m: result["new_opps"] = m.group(1)
        if "Digest sent" in line: result["email_sent"] = "YES ✅"
        if "Email send failed" in line: result["email_sent"] = "NO ❌"
        if "Nothing to notify" in line: result["email_sent"] = "—  (nothing new)"

        # Total time
        m = re.search(r"Total time\s*:\s*([\d.]+s)", line)
        if m: result["elapsed"] = m.group(1)

        # Errors
        if "  ERROR" in line or "FAIL" in line:
            result["errors"].append(line.strip())

    return result


def print_run(run_lines: list[str], index: int, total: int):
    s = summarise_run(run_lines)
    print(f"\n{'─'*56}")
    print(f"  Run {index}/{total}  —  {s['started']}  ({s['elapsed']})")
    print(f"{'─'*56}")

    # Stage checklist
    stage_names = ["DB init", "Scrape", "Parse", "Store", "Digest", "Notify"]
    ok_names    = [x.split("(")[0].strip() for x in s["stages_ok"]]
    timing      = {x.split("(")[0].strip(): re.search(r"\((.+?)\)", x).group(1)
                   if re.search(r"\((.+?)\)", x) else "?" for x in s["stages_ok"]}

    for name in stage_names:
        if name in ok_names:
            t = timing.get(name, "")
            print(f"  ✅  {name:<12} {t}")
        elif any(name.lower() in f.lower() for f in s["stages_fail"]):
            print(f"  ❌  {name:<12} FAILED")
        else:
            print(f"  ·   {name:<12} (not reached)")

    # Metrics
    print(f"\n  Scraped   : {s['scraped']}")
    print(f"  Inserted  : {s['inserted']}  (duplicates: {s['duplicates']})")
    print(f"  New opps  : {s['new_opps']}")
    print(f"  Email     : {s['email_sent']}")

    if s["errors"]:
        print(f"\n  Errors:")
        for e in s["errors"][:5]:
            print(f"    ⚠  {e[:80]}")


def main():
    show_all  = "--all"  in sys.argv
    tail_mode = "--tail" in sys.argv

    try:
        with open(LOG_PATH, encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Log file not found: {LOG_PATH}")
        print("Run the pipeline first: python -m internhunter.scheduler")
        return

    if tail_mode:
        n = int(sys.argv[sys.argv.index("--tail") + 1]) if len(sys.argv) > sys.argv.index("--tail") + 1 else 20
        print(f"\n── Last {n} log lines ──")
        for line in lines[-n:]:
            print(line, end="")
        return

    runs = parse_runs(lines)
    if not runs:
        print("No pipeline runs found in log.")
        return

    print(f"\n{'='*56}")
    print(f"  InternHunter — Log Reader")
    print(f"  {LOG_PATH}  ({len(runs)} run(s) recorded)")
    print(f"{'='*56}")

    to_show = runs if show_all else [runs[-1]]
    for i, run in enumerate(to_show, 1 if show_all else len(runs)):
        print_run(run, i, len(runs))

    print()


if __name__ == "__main__":
    main()
