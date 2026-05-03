"""
parser.py — Extract structured fields from raw Serper snippets.
Pure regex, no external API, runs fully offline.

Key improvements:
  - Year validation — rejects deadlines from past years
  - Duration extraction — "2 months", "6 weeks" etc.
  - Expired listing detection
  - Stipend from structured snippets (Duration: | Stipend: pattern)
  - International salary handling (USD/EUR)
"""
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

CURRENT_YEAR = datetime.now().year  # 2026

# ── Month names ───────────────────────────────────────────────
_M = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?"
    r"|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?"
    r"|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)

# ── Stipend patterns ──────────────────────────────────────────
_STIPEND_PATTERNS = [re.compile(p, re.IGNORECASE) for p in [
    # Lacs/month: "INR 1.1 Lacs per month"
    r"(?:Rs\.?|INR|₹)\s*([\d]+(?:\.\d+)?)\s*Lac(?:s|hs?)?\s*(?:[-–]\s*[\d.]+\s*Lac(?:s|hs?)?\s*)?(?:per\s*month|/\s*month|p\.?m\.?)",
    # LPA annual: "Rs. 3-7 LPA"
    r"(?:Rs\.?|INR|₹)\s*([\d.]+)\s*(?:[-–]\s*[\d.]+\s*)?(?:LPA|L\.P\.A\.?)",
    # Range: "Rs. 15,000 - 20,000/month"
    r"(?:Rs\.?|INR|₹)\s*([\d,]+)\s*[-–]\s*[\d,]+\s*(?:per\s*month|/\s*month|p\.?m\.?)?",
    # Flat: "₹20,000/month"
    r"(?:Rs\.?|INR|₹)\s*([\d,]+)(?!\s*[\d.]*\s*Lac)\s*(?:per\s*month|/\s*month|p\.?m\.?)?",
    # Label+number: "Compensation20,000 inr per month" / "Stipend: 15000"
    r"(?:compensation|stipend|salary)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]{4,})\s*(?:inr|rs\.?|₹)?\s*(?:per\s*month|/\s*month|p\.?m\.?)?",
    # Bare number + per month
    r"(?<!\d)([\d,]{4,})\s*(?:per\s*month|/\s*month|p\.?m\.?)",
    # k-notation: "15k/month"
    r"(?<!\d)([\d]+[kK])\s*(?:per\s*month|/\s*month|p\.?m\.?)",
    # Structured snippet "Stipend | Rs. 15,000"
    r"[Ss]tipend\s*\|\s*(?:Rs\.?|INR|₹)\s*([\d,]+)",
    # USD/EUR for international: "$2000/month", "€1500 per month"
    r"(?:\$|USD|€|EUR)\s*([\d,]+)\s*(?:per\s*month|/\s*month|/mo)?",
]]

# ── Duration patterns ─────────────────────────────────────────
_DURATION_PATTERNS = [re.compile(p, re.IGNORECASE) for p in [
    r"(\d+)\s*(?:-\s*\d+\s*)?months?\s*(?:internship|duration|program)?",
    r"(\d+)\s*weeks?\s*(?:internship|program)?",
    r"duration[:\s]+(\d+\s*(?:months?|weeks?))",
]]

# ── Deadline patterns ─────────────────────────────────────────
_DEADLINE_PATTERNS = [re.compile(p, re.IGNORECASE) for p in [
    rf"last\s*date\b[^,\n]{{0,40}}?(\d{{1,2}}(?:st|nd|rd|th)?\s+{_M}[,\s]*\d{{4}})",
    rf"apply\s*before[:\s]+(\d{{1,2}}(?:st|nd|rd|th)?\s+{_M}[,\s]*\d{{4}})",
    rf"apply\s*by[:\s]+(\d{{1,2}}(?:st|nd|rd|th)?\s+{_M}[,\s]*\d{{4}}|{_M}\s+\d{{1,2}}[,\s]*\d{{4}})",
    rf"deadline[:\s]+(\d{{1,2}}(?:st|nd|rd|th)?\s+{_M}[,\s]*\d{{4}})",
    rf"closes?(?:\s*on)?[:\s]+(?:\w+\s+)?(\d{{1,2}}(?:st|nd|rd|th)?\s+{_M}[,\s]*\d{{4}}|{_M}\s+\d{{1,2}}[,\s]*\d{{4}})",
    r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
]]

# ── Location keywords ─────────────────────────────────────────
_LOCATION_KEYWORDS = [
    "work from home", "wfh", "remote", "hybrid", "pan india",
    "worldwide", "global", "international",
    "bangalore", "bengaluru", "delhi", "new delhi", "mumbai",
    "hyderabad", "pune", "chennai", "kolkata", "noida",
    "gurugram", "gurgaon", "ahmedabad", "jaipur", "kochi", "indore",
    # International cities
    "san francisco", "new york", "london", "singapore", "dubai",
    "berlin", "amsterdam", "toronto", "sydney",
]

_LOCATION_CANONICAL = {
    "wfh": "Work From Home", "work from home": "Work From Home",
    "bengaluru": "Bangalore", "new delhi": "Delhi", "gurgaon": "Gurugram",
    "worldwide": "Remote (Global)", "global": "Remote (Global)",
    "international": "Remote (Global)",
    "san francisco": "San Francisco, USA",
    "new york": "New York, USA",
    "london": "London, UK",
    "singapore": "Singapore",
    "dubai": "Dubai, UAE",
}

# Month → number for expiry check
_MONTH_NUM = {
    "jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
    "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12,
}


# ── Public API ────────────────────────────────────────────────

def parse_listing(raw: dict) -> dict:
    """Parse a raw scraper dict into structured fields."""
    text     = (raw.get("snippet","") + " " + raw.get("title","")).strip()
    deadline = _extract_deadline(text)
    expired  = _is_expired(deadline)

    return {
        **raw,
        "stipend":    _extract_stipend(text),
        "deadline":   deadline,
        "location":   _extract_location(text),
        "duration":   _extract_duration(text),
        "expired":    expired,
        "apply_link": raw.get("link",""),
        "parsed":     True,
    }


def parse_all(listings: list[dict]) -> list[dict]:
    """Parse batch and log hit-rate summary."""
    results  = [parse_listing(r) for r in listings]
    total    = len(results)
    expired  = sum(1 for r in results if r.get("expired"))
    s = sum(1 for r in results if r["stipend"]  != "Not mentioned")
    d = sum(1 for r in results if r["deadline"] != "Not mentioned")
    l = sum(1 for r in results if r["location"] != "Not mentioned")
    logger.info(
        f"Parsed {total} listings — stipend:{s}/{total} deadline:{d}/{total} "
        f"location:{l}/{total} expired:{expired}"
    )
    return results


# ── Private helpers ───────────────────────────────────────────

def _extract_stipend(text: str) -> str:
    for i, pattern in enumerate(_STIPEND_PATTERNS):
        m = pattern.search(text)
        if not m:
            continue
        raw_val = m.group(1).replace(",","").strip()
        try:
            if i == 0:   # Lacs/month
                return f"₹{float(raw_val)*100_000:,.0f}/month"
            if i == 1:   # LPA → monthly
                return f"₹{float(raw_val)*100_000/12:,.0f}/month"
            if raw_val.lower().endswith("k"):
                return f"₹{int(raw_val[:-1])*1000:,}/month"
            if i == 8:   # USD/EUR international
                # Return as-is with currency symbol detected from text
                sym = "$" if "$" in text or "USD" in text.upper() else "€"
                return f"{sym}{int(raw_val):,}/month"
            return f"₹{int(raw_val):,}/month"
        except (ValueError, AttributeError):
            continue
    return "Not mentioned"


def _extract_deadline(text: str) -> str:
    for pattern in _DEADLINE_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(1).strip().rstrip(",").strip()
    return "Not mentioned"


def _extract_duration(text: str) -> str:
    """Extract internship duration e.g. '3 months', '6 weeks'."""
    for pattern in _DURATION_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(1).strip() if len(m.group(1)) > 2 else f"{m.group(1)} months"
    return "Not mentioned"


def _extract_location(text: str) -> str:
    text_lower = text.lower()
    found, seen = [], set()
    for kw in _LOCATION_KEYWORDS:
        if kw in text_lower:
            canonical = _LOCATION_CANONICAL.get(kw, kw.title())
            if canonical not in seen:
                seen.add(canonical)
                found.append(canonical)
    return ", ".join(found) if found else "Not mentioned"


def _is_expired(deadline_str: str) -> bool:
    """
    Return True if the deadline is definitely in the past.
    Listings with 'Not mentioned' are kept (can't rule out).
    """
    if not deadline_str or deadline_str == "Not mentioned":
        return False
    try:
        # Try to extract year from deadline string
        year_m = re.search(r"\b(20\d{2})\b", deadline_str)
        if not year_m:
            return False
        year = int(year_m.group(1))
        if year < CURRENT_YEAR:
            return True
        if year > CURRENT_YEAR:
            return False
        # Same year — check month
        month_m = re.search(
            r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)",
            deadline_str.lower()
        )
        if month_m:
            month_num = _MONTH_NUM.get(month_m.group(1)[:3], 0)
            current_month = datetime.now().month
            return month_num < current_month
    except Exception:
        pass
    return False