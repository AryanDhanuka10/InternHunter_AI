"""
filters.py — Filter and score parsed internship listings.

Pipeline position: called AFTER parse_all(), BEFORE upsert_many().

  raw = scrape_all_roles()
  parsed = parse_all(raw)
  filtered, dropped = apply_filters(parsed)   ← HERE
  upsert_many(filtered)

Two responsibilities:
  1. FILTER  — drop listings whose stipend is below MIN_STIPEND
  2. SCORE   — assign an integer score to each listing based on SCORE_WEIGHTS
               so the best listings always surface at the top
"""
import re
import logging
from internhunter.config import (
    MIN_STIPEND, PREFERRED_LOCATIONS, SCORE_WEIGHTS
)

logger = logging.getLogger(__name__)

# ── Public API ────────────────────────────────────────────────

def apply_filters(listings: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Filter and score a list of parsed listings.

    Returns:
        (kept, dropped)
        kept    — list with 'score' key added, sorted score DESC
        dropped — list of listings that failed the stipend filter
    """
    kept, dropped = [], []

    for listing in listings:
        stipend_int = _stipend_to_int(listing.get("stipend", ""))

        # ── Filter: drop if below MIN_STIPEND ────────────────
        # Only drop when stipend is actually parsed AND below threshold.
        # "Not mentioned" is kept — we can't rule it out.
        if MIN_STIPEND > 0 and stipend_int > 0 and stipend_int < MIN_STIPEND:
            dropped.append({**listing, "score": 0, "drop_reason": f"stipend {stipend_int} < {MIN_STIPEND}"})
            continue

        # ── Score ─────────────────────────────────────────────
        score = _compute_score(listing, stipend_int)
        kept.append({**listing, "score": score})

    # Sort by score descending — best listings first
    kept.sort(key=lambda x: x["score"], reverse=True)

    logger.info(
        f"Filters: {len(kept)} kept, {len(dropped)} dropped "
        f"(stipend < ₹{MIN_STIPEND:,})  "
        f"top score: {kept[0]['score'] if kept else 0}"
    )
    if dropped:
        logger.info(f"  Dropped: {[d['title'][:40] for d in dropped[:3]]}")

    return kept, dropped


def score_one(listing: dict) -> int:
    """Score a single listing — useful for re-scoring existing DB rows."""
    return _compute_score(listing, _stipend_to_int(listing.get("stipend", "")))


# ── Private helpers ───────────────────────────────────────────

def _stipend_to_int(stipend_str: str) -> int:
    """
    Convert '₹20,000/month' → 20000.
    Returns 0 for 'Not mentioned' or unparseable strings.
    """
    if not stipend_str or stipend_str == "Not mentioned":
        return 0
    m = re.search(r"\d+", stipend_str.replace(",", ""))
    return int(m.group()) if m else 0


def _compute_score(listing: dict, stipend_int: int) -> int:
    """
    Add up SCORE_WEIGHTS for every condition that matches.
    Pure function — no side effects.
    """
    w     = SCORE_WEIGHTS
    score = 0

    # Stipend tiers
    if stipend_int > 0:
        score += w.get("has_stipend", 0)
    if stipend_int >= 15_000:
        score += w.get("stipend_15k_plus", 0)
    if stipend_int >= 25_000:
        score += w.get("stipend_25k_plus", 0)

    # Location match
    location = (listing.get("location") or "").lower()
    if any(loc in location for loc in PREFERRED_LOCATIONS):
        score += w.get("preferred_location", 0)

    # Has deadline — signals individual listing not category page
    deadline = listing.get("deadline", "Not mentioned")
    if deadline and deadline != "Not mentioned":
        score += w.get("has_deadline", 0)

    # Known source — internshala/unstop/wellfound have structured data
    source = listing.get("source", "other")
    if source != "other":
        score += w.get("known_source", 0)

    # Company extracted
    company = (listing.get("company") or "").strip()
    if company:
        score += w.get("has_company", 0)

    return score