"""Runs the full pipeline once — call via cron or GitHub Actions."""
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
