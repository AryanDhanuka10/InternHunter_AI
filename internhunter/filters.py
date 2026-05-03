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


def apply_filters(listings: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Filter and score listings.
    Returns (kept, dropped) — both are lists of dicts.
    """
    kept, dropped = [], []

    for listing in listings:
        stipend_int = _stipend_to_int(listing.get("stipend",""))

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