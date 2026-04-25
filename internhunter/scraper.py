"""Web scraper — pulls internship listings from multiple sources."""
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
