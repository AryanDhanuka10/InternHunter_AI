"""
scraper.py — Web scraper using Serper (Google Search API).
21 platforms tracked. Indian + international remote search.
"""
import time, random, logging, requests
from datetime import datetime, timezone
from internhunter.config import (
    SERPER_API_KEY, INTERNSHIP_ROLES, INTERNATIONAL_ROLES, MAX_RESULTS_PER_RUN
)

logger = logging.getLogger(__name__)
SERPER_URL = "https://google.serper.dev/search"

# ── All tracked sources ───────────────────────────────────────
SOURCES = [
    # Indian job boards
    "internshala.com",
    "unstop.com",
    "letsintern.com",
    "iimjobs.com",
    "naukri.com",
    "glassdoor.co.in",
    "foundit.in",           # formerly Monster India
    "shine.com",
    "freshersworld.com",
    "hirist.tech",
    "apna.co",
    "cutshort.io",
    "instahyre.com",
    # Professional/global
    "linkedin.com",
    "wellfound.com",
    "angellist.com",
    # International remote
    "indeed.com",
    "internships.com",
    "remoteok.com",
    "weworkremotely.com",
    "remote.co",
    "simplyhired.com",
    "greenhouse.io",
    "lever.co",
    "ycombinator.com",      # YC job board
]

MAX_RETRIES   = 3
RETRY_BACKOFF = [2, 5, 10]
POLITE_DELAY  = (1.5, 2.5)

# ── Indian site list for site: filter ─────────────────────────
_INDIAN_SITES = (
    "site:internshala.com OR site:unstop.com OR site:linkedin.com "
    "OR site:wellfound.com OR site:naukri.com OR site:hirist.tech "
    "OR site:iimjobs.com OR site:letsintern.com OR site:foundit.in "
    "OR site:cutshort.io OR site:instahyre.com OR site:apna.co"
)

_INTL_SITES = (
    "site:linkedin.com OR site:remoteok.com OR site:weworkremotely.com "
    "OR site:wellfound.com OR site:internships.com OR site:greenhouse.io "
    "OR site:lever.co OR site:ycombinator.com OR site:indeed.com"
)


def google_search_internships(role: str, international: bool = False) -> list[dict]:
    """Query Serper for a role. Strips API key to fix \n header bug."""
    api_key = SERPER_API_KEY.strip()
    if not api_key:
        logger.warning("SERPER_API_KEY not set — add it to .env")
        return []

    if international:
        query = f"{role} 2026 stipend OR salary apply {_INTL_SITES}"
        geo   = "us"
    else:
        query = f"{role} 2026 india stipend apply {_INDIAN_SITES}"
        geo   = "in"

    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": 10, "gl": geo, "hl": "en"}

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(SERPER_URL, json=payload, headers=headers, timeout=15)

            if resp.status_code == 429:
                wait = RETRY_BACKOFF[attempt]
                logger.warning(f"Rate limited '{role}' (attempt {attempt+1}) — waiting {wait}s")
                time.sleep(wait)
                continue

            if resp.status_code == 401:
                logger.error("Invalid SERPER_API_KEY — check .env (no spaces or newlines)")
                return []

            resp.raise_for_status()
            organic = resp.json().get("organic", [])

            if not organic:
                logger.info(f"No results for '{role}'")
                return []

            results = []
            for item in organic:
                results.append({
                    "title":            item.get("title","").strip(),
                    "link":             item.get("link","").strip(),
                    "snippet":          item.get("snippet","").strip(),
                    "source":           _detect_source(item.get("link","")),
                    "role":             role,
                    "is_international": international,
                    "scraped_at":       datetime.now(timezone.utc).isoformat(),
                })

            logger.info(f"  ✓  '{role}' → {len(results)} results")
            return results

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout '{role}' (attempt {attempt+1})")
            time.sleep(RETRY_BACKOFF[attempt])
        except requests.exceptions.ConnectionError:
            logger.error(f"No internet — '{role}'")
            return []
        except Exception as e:
            logger.error(f"Unexpected error on '{role}': {type(e).__name__}: {e}")
            return []

    logger.error(f"All {MAX_RETRIES} attempts failed for '{role}'")
    return []


def _detect_source(url: str) -> str:
    url_lower = url.lower()
    for src in SOURCES:
        if src in url_lower:
            return src
    return "other"


def scrape_all_roles() -> list[dict]:
    """Scrape all Indian + international roles, deduplicate by URL."""
    all_results, seen = [], set()
    all_roles = [(r, False) for r in INTERNSHIP_ROLES] + \
                [(r, True)  for r in INTERNATIONAL_ROLES]

    logger.info(
        f"Starting scrape — {len(INTERNSHIP_ROLES)} Indian + "
        f"{len(INTERNATIONAL_ROLES)} international roles"
    )

    for i, (role, is_intl) in enumerate(all_roles, 1):
        tag = "🌍" if is_intl else "🇮🇳"
        logger.info(f"[{i}/{len(all_roles)}] {tag} Searching: {role}")
        results = google_search_internships(role, international=is_intl)

        added = 0
        for r in results:
            if r["link"] and r["link"] not in seen:
                seen.add(r["link"])
                all_results.append(r)
                added += 1

        if added == 0 and results:
            logger.info(f"  ↳ All {len(results)} were duplicates")

        if i < len(all_roles):
            time.sleep(random.uniform(*POLITE_DELAY))

    total  = len(all_results)
    capped = min(total, MAX_RESULTS_PER_RUN)
    logger.info(f"Scrape complete — {total} unique, returning {capped}")
    return all_results[:MAX_RESULTS_PER_RUN]