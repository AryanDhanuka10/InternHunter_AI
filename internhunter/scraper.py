"""Web scraper — pulls internship listings from multiple sources."""
import time, random, logging, requests
from datetime import datetime
from internhunter.config import SERPER_API_KEY, INTERNSHIP_ROLES, MAX_RESULTS_PER_RUN

logger = logging.getLogger(__name__)

SERPER_URL = "https://google.serper.dev/search"

SOURCES = [
    "internshala.com",
    "linkedin.com/jobs",
    "unstop.com",
    "wellfound.com",
    "indeed.co.in",
    "letsintern.com",
    "iimjobs.com",
    "naukri.com",
    "glassdoor.co.in",
]

# ── Retry / rate-limit settings ───────────────────────────────
MAX_RETRIES   = 3          # retries per role on 429 / network error
RETRY_BACKOFF = [2, 5, 10] # seconds to wait before each retry
POLITE_DELAY  = (1.5, 3.0) # random sleep range between roles (seconds)


def google_search_internships(role: str, extra_query: str = "") -> list[dict]:
    """
    Query Serper (Google Search API) for a given role.
    Handles:
      - Missing API key         → warns and returns []
      - HTTP 429 rate limit     → retries with exponential backoff
      - Empty organic results   → logs and returns []
      - Network / timeout error → logs and returns []
    """
    if not SERPER_API_KEY:
        logger.warning("SERPER_API_KEY not set — add it to your .env and rerun")
        return []

    query   = f"{role} internship 2026 india {extra_query} stipend apply site:internshala.com OR site:linkedin.com OR site:unstop.com OR site:wellfound.com"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {"q": query, "num": 10, "gl": "in", "hl": "en"}

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(SERPER_URL, json=payload, headers=headers, timeout=15)

            # ── Rate limit hit ─────────────────────────────────
            if resp.status_code == 429:
                wait = RETRY_BACKOFF[attempt]
                logger.warning(f"Rate limited on '{role}' (attempt {attempt+1}/{MAX_RETRIES}) — waiting {wait}s")
                time.sleep(wait)
                continue

            # ── Auth error ─────────────────────────────────────
            if resp.status_code == 401:
                logger.error("Invalid SERPER_API_KEY — check your .env file")
                return []

            # ── Other HTTP errors ──────────────────────────────
            resp.raise_for_status()

            organic = resp.json().get("organic", [])

            if not organic:
                logger.info(f"No results returned for '{role}' — Serper query may need tuning")
                return []

            results = []
            for item in organic:
                results.append({
                    "title":      item.get("title", "").strip(),
                    "link":       item.get("link", "").strip(),
                    "snippet":    item.get("snippet", "").strip(),
                    "source":     _detect_source(item.get("link", "")),
                    "role":       role,
                    "scraped_at": datetime.utcnow().isoformat(),
                })

            logger.info(f"  ✓  '{role}' → {len(results)} results")
            return results

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on '{role}' (attempt {attempt+1}/{MAX_RETRIES})")
            time.sleep(RETRY_BACKOFF[attempt])

        except requests.exceptions.ConnectionError:
            logger.error(f"No internet connection while fetching '{role}'")
            return []

        except Exception as e:
            logger.error(f"Unexpected error on '{role}': {type(e).__name__}: {e}")
            return []

    logger.error(f"All {MAX_RETRIES} attempts failed for '{role}' — skipping")
    return []


def _detect_source(url: str) -> str:
    for src in SOURCES:
        if src in url:
            return src
    return "other"


def scrape_all_roles() -> list[dict]:
    """
    Run search for every role in config, deduplicate by URL.
    Returns up to MAX_RESULTS_PER_RUN unique listings.
    """
    all_results, seen = [], set()

    logger.info(f"Starting scrape for {len(INTERNSHIP_ROLES)} roles...")

    for i, role in enumerate(INTERNSHIP_ROLES, 1):
        logger.info(f"[{i}/{len(INTERNSHIP_ROLES)}] Searching: {role}")
        results = google_search_internships(role)

        added = 0
        for r in results:
            if r["link"] and r["link"] not in seen:
                seen.add(r["link"])
                all_results.append(r)
                added += 1

        if added == 0 and results:
            logger.info(f"  ↳ All {len(results)} results were duplicates — skipped")

        # Polite delay between roles (skip after last one)
        if i < len(INTERNSHIP_ROLES):
            delay = random.uniform(*POLITE_DELAY)
            logger.debug(f"  Sleeping {delay:.1f}s before next role...")
            time.sleep(delay)

    total = len(all_results)
    capped = min(total, MAX_RESULTS_PER_RUN)
    logger.info(f"Scrape complete — {total} unique listings found, returning {capped}")
    return all_results[:MAX_RESULTS_PER_RUN]