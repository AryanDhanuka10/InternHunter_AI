"""
scheduler.py — Full pipeline orchestrator.

Stages (in order):
  1. DB init
  2. Scrape     — Serper API search across all roles
  3. Parse      — extract stipend / deadline / location
  4. Store      — upsert into SQLite, count new vs duplicates
  5. Digest     — build HTML + plain-text email
  6. Notify     — send digest via Gmail, mark notified
  7. Summary    — print + log final stats for the run

Run manually:   python -m internhunter.scheduler
GitHub Actions: triggered by .github/workflows/daily.yml
"""
import logging, os, time, traceback
from datetime import datetime, timezone
from internhunter.scraper  import scrape_all_roles
from internhunter.parser   import parse_all
from internhunter.filters  import apply_filters
from internhunter.database import (
    init_db, upsert_many, get_new_opportunities,
    mark_notified, get_stats
)
from internhunter.digest   import build_digest_html, build_digest_text, save_digest
from internhunter.digest_pdf import build_digest_pdf, attach_pdf_to_email
from internhunter.referral   import build_referral_hints
from internhunter.mailer   import send_digest_email

# ── Logging setup — writes to BOTH terminal and logs/daily.log ─
os.makedirs("logs", exist_ok=True)
_log_path = os.path.join("logs", "daily.log")

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S",
    handlers= [
        logging.FileHandler(_log_path, encoding="utf-8"),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


# ── Stage runner ──────────────────────────────────────────────

def _stage(name: str):
    """Context manager — logs stage start/end/duration and catches errors."""
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        logger.info(f"┌─ STAGE: {name}")
        t0 = time.perf_counter()
        try:
            yield
            elapsed = time.perf_counter() - t0
            logger.info(f"└─ DONE:  {name}  ({elapsed:.1f}s)")
        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error(f"└─ FAIL:  {name}  ({elapsed:.1f}s) — {type(e).__name__}: {e}")
            logger.debug(traceback.format_exc())
            raise   # re-raise so run() can decide to abort or continue

    return _ctx()


# ── Main pipeline ─────────────────────────────────────────────

def run() -> dict:
    """
    Execute all 7 stages. Returns a summary dict.
    Stages 2-6 are individually try/except'd — a failure in one
    stage logs the error but allows subsequent stages to still run.
    """
    run_start = time.perf_counter()
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    logger.info("=" * 56)
    logger.info("  InternHunter pipeline started")
    logger.info(f"  {started_at}")
    logger.info("=" * 56)

    summary = {
        "started_at":  started_at,
        "scraped":     0,
        "parsed":      0,
        "inserted":    0,
        "filtered":    0,
        "dropped":     0,
        "duplicates":  0,
        "new_opps":    0,
        "email_sent":  False,
        "pdf_path":    "",
        "stages_ok":   [],
        "stages_fail": [],
        "elapsed_s":   0,
    }

    # ── Stage 1: DB init (must succeed — abort if not) ────────
    with _stage("1 · DB init"):
        init_db()
    summary["stages_ok"].append("db_init")

    # ── Stage 2: Scrape ───────────────────────────────────────
    raw = []
    try:
        with _stage("2 · Scrape"):
            raw = scrape_all_roles()
            summary["scraped"] = len(raw)
            logger.info(f"  Scraped {len(raw)} unique listings")
        summary["stages_ok"].append("scrape")
    except Exception:
        summary["stages_fail"].append("scrape")

    # ── Stage 3: Parse ────────────────────────────────────────
    parsed = []
    try:
        with _stage("3 · Parse"):
            parsed = parse_all(raw)
            summary["parsed"] = len(parsed)
            with_stipend  = sum(1 for p in parsed if p["stipend"]  != "Not mentioned")
            with_location = sum(1 for p in parsed if p["location"] != "Not mentioned")
            logger.info(
                f"  Parsed {len(parsed)} listings — "
                f"stipend: {with_stipend}  location: {with_location}"
            )
        summary["stages_ok"].append("parse")
    except Exception:
        summary["stages_fail"].append("parse")

    # ── Stage 3.5: Filter + Score ────────────────────────────
    filtered = parsed   # default: keep all if filter stage fails
    try:
        with _stage("3.5 · Filter + Score"):
            filtered, dropped = apply_filters(parsed)
            summary["filtered"] = len(filtered)
            summary["dropped"]  = len(dropped)
            logger.info(
                f"  Kept {len(filtered)}, dropped {len(dropped)} "                f"(stipend below threshold or noise)"            )
        summary["stages_ok"].append("filter")
    except Exception:
        summary["stages_fail"].append("filter")

    # ── Stage 4: Store ────────────────────────────────────────
    try:
        with _stage("4 · Store"):
            inserted, skipped = upsert_many(filtered)
            summary["inserted"]   = inserted
            summary["duplicates"] = skipped
            logger.info(f"  Inserted: {inserted}  |  Duplicates skipped: {skipped}")
        summary["stages_ok"].append("store")
    except Exception:
        summary["stages_fail"].append("store")

    # ── Stage 5: Digest ───────────────────────────────────────
    opps      = []
    html_body = ""
    try:
        with _stage("5 · Digest"):
            opps = get_new_opportunities(limit=30)
            summary["new_opps"] = len(opps)
            if opps:
                stats         = get_stats()
                ref_hints     = build_referral_hints(opps)
                html_body     = build_digest_html(opps, stats=stats, show_referrals=True)
                text_body     = build_digest_text(opps, show_referrals=True)
                hp, tp        = save_digest(html_body, text_body)
                pdf_path      = build_digest_pdf(opps, stats=stats, referral_hints=ref_hints)
                summary["pdf_path"] = pdf_path
                logger.info(f"  Built digest for {len(opps)} opportunities")
                logger.info(f"  Saved HTML → {hp}")
                logger.info(f"  Saved PDF  → {pdf_path}")
            else:
                logger.info("  No new opportunities — digest skipped")
        summary["stages_ok"].append("digest")
    except Exception:
        summary["stages_fail"].append("digest")

    # ── Stage 6: Notify ───────────────────────────────────────
    try:
        with _stage("6 · Notify"):
            if opps and html_body:
                date_str = datetime.now().strftime("%d %b")
                sent = send_digest_email(
                    subject   = f"[InternHunter] {len(opps)} New Internships — {date_str}",
                    body_html = html_body,
                    pdf_path  = summary.get("pdf_path", ""),
                )
                summary["email_sent"] = sent
                if sent:
                    mark_notified([o["id"] for o in opps])
                    logger.info(f"  Digest sent and {len(opps)} opportunities marked notified")
                else:
                    logger.warning("  Email send failed — check GMAIL_USER / GMAIL_APP_PASS in .env")
            else:
                logger.info("  Nothing to notify")
        summary["stages_ok"].append("notify")
    except Exception:
        summary["stages_fail"].append("notify")

    # ── Stage 7: Summary ──────────────────────────────────────
    elapsed = time.perf_counter() - run_start
    summary["elapsed_s"] = round(elapsed, 1)

    logger.info("=" * 56)
    logger.info("  PIPELINE SUMMARY")
    logger.info("=" * 56)
    logger.info(f"  Scraped     : {summary['scraped']}")
    logger.info(f"  Parsed      : {summary['parsed']}")
    logger.info(f"  Filtered    : {summary['filtered']}  (dropped: {summary['dropped']})")
    logger.info(f"  Inserted    : {summary['inserted']}  (duplicates: {summary['duplicates']})")
    logger.info(f"  New in inbox: {summary['new_opps']}")
    logger.info(f"  Email sent  : {'YES' if summary['email_sent'] else 'NO'}")
    logger.info(f"  Stages OK   : {', '.join(summary['stages_ok'])}")
    if summary["stages_fail"]:
        logger.error(f"  Stages FAIL : {', '.join(summary['stages_fail'])}")
    logger.info(f"  Total time  : {elapsed:.1f}s")
    logger.info("=" * 56)

    return summary


# ── Entry point ───────────────────────────────────────────────

if __name__ == "__main__":
    result = run()
    if result["stages_fail"]:
        raise SystemExit(1)   # non-zero exit for GitHub Actions to catch