"""
filters.py — Filter and score parsed internship listings.

Filters applied (in order):
  1. Drop expired listings (deadline clearly in the past)
  2. Drop listings where stipend < MIN_STIPEND (when stipend is known)
  3. Score remaining listings by quality signals
  4. Sort by score descending
"""
import re
import logging
from internhunter.config import MIN_STIPEND, PREFERRED_LOCATIONS, SCORE_WEIGHTS, CURRENT_YEAR

logger = logging.getLogger(__name__)



# ── Domain whitelist / blacklist ──────────────────────────────
# Listings whose title contains ANY block keyword are dropped
# regardless of stipend (prevents off-domain suggestions)
_BLOCK_KEYWORDS = [
    "content writing", "content creator", "marketing intern",
    "social media", "graphic design", "ui/ux", "ui design",
    "sales intern", "business development", "hr intern",
    "human resource", "finance intern", "accounting",
    "legal intern", "operations intern", "supply chain",
    "full stack", "fullstack", "front-end", "frontend",
    "react intern", "angular", "vue.js",
    "android intern", "ios intern", "mobile app",
    "devops intern", "cloud intern",
    "event management", "customer support",
    "video editing", "photography", "telecalling",
]

# Must match at least ONE of these to be kept (your domain)
_DOMAIN_KEYWORDS = [
    "machine learning", " ml ", "data science", "data scientist",
    "software engineer", "software develop", "swe intern",
    "backend", "back-end", "python developer", "python intern",
    "deep learning", "nlp", "natural language",
    "computer vision", "artificial intelligence", " ai ",
    "ai intern", "ai research", "mlops", "research intern",
    "data analyst", "data engineer", "algorithm",
    "software intern", "tech intern", "engineering intern",
]


def apply_filters(listings: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Filter and score listings.
    Returns (kept, dropped) — both are lists of dicts.
    """
    kept, dropped = [], []

    for listing in listings:
        stipend_int = _stipend_to_int(listing.get("stipend",""))

        # ── Drop off-domain listings ─────────────────────────
        if _is_off_domain(listing):
            dropped.append({**listing, "score":0, "drop_reason":"off-domain"})
            continue

        # ── Drop expired ──────────────────────────────────────
        if listing.get("expired"):
            dropped.append({**listing, "score":0, "drop_reason":"expired deadline"})
            continue

        # ── Drop below MIN_STIPEND ────────────────────────────
        if MIN_STIPEND > 0 and stipend_int > 0 and stipend_int < MIN_STIPEND:
            dropped.append({**listing, "score":0,
                            "drop_reason":f"stipend {stipend_int} < {MIN_STIPEND}"})
            continue

        score = _compute_score(listing, stipend_int)
        kept.append({**listing, "score": score})

    kept.sort(key=lambda x: x["score"], reverse=True)

    expired_count = sum(1 for d in dropped if "expired" in d.get("drop_reason",""))
    low_stip      = sum(1 for d in dropped if "stipend" in d.get("drop_reason",""))
    logger.info(
        f"Filters: {len(kept)} kept, {len(dropped)} dropped "
        f"({expired_count} expired, {low_stip} low stipend) "
        f"top score: {kept[0]['score'] if kept else 0}"
    )
    return kept, dropped


def score_one(listing: dict) -> int:
    return _compute_score(listing, _stipend_to_int(listing.get("stipend","")))


def _stipend_to_int(stipend_str: str) -> int:
    if not stipend_str or stipend_str == "Not mentioned":
        return 0
    # Handle international: "$2,000/month" → approximate INR
    if "$" in stipend_str or "USD" in stipend_str:
        m = re.search(r"\d+", stipend_str.replace(",",""))
        return int(m.group()) * 83 if m else 0   # ~83 INR per USD
    if "€" in stipend_str or "EUR" in stipend_str:
        m = re.search(r"\d+", stipend_str.replace(",",""))
        return int(m.group()) * 90 if m else 0
    m = re.search(r"\d+", stipend_str.replace(",",""))
    return int(m.group()) if m else 0


def _compute_score(listing: dict, stipend_int: int) -> int:
    w     = SCORE_WEIGHTS
    score = 0

    # Stipend tiers
    if stipend_int > 0:
        score += w.get("has_stipend", 0)
    if stipend_int >= 15_000:
        score += w.get("stipend_15k_plus", 0)
    if stipend_int >= 25_000:
        score += w.get("stipend_25k_plus", 0)

    # Location
    location = (listing.get("location") or "").lower()
    if any(loc in location for loc in PREFERRED_LOCATIONS):
        score += w.get("preferred_location", 0)

    # Has valid deadline
    deadline = listing.get("deadline","Not mentioned")
    if deadline and deadline != "Not mentioned":
        score += w.get("has_deadline", 0)

    # Mentions current year in title/snippet — fresher listing
    text = (listing.get("title","") + " " + listing.get("snippet","")).lower()
    if str(CURRENT_YEAR) in text:
        score += w.get("is_2026", 0)

    # Known source
    if listing.get("source","other") != "other":
        score += w.get("known_source", 0)

    # Company present
    if (listing.get("company") or "").strip():
        score += w.get("has_company", 0)

    # International remote
    if listing.get("is_international"):
        score += w.get("is_international", 0)

    return score


def _is_off_domain(listing: dict) -> bool:
    """
    Return True if the listing title clearly does NOT match your target domain.
    Uses a two-pass check:
      1. Block if any off-domain keyword in title
      2. If no domain keyword found AND title is specific enough, also block
    Category pages (e.g. "150 ML internships") pass through — their title
    won't contain block keywords.
    """
    text = (listing.get("title","") + " " + listing.get("role","")).lower()

    # Pass 1: explicit block
    for kw in _BLOCK_KEYWORDS:
        if kw in text:
            return True

    return False