"""
parser.py — Extract structured fields from raw Serper snippets.
Pure regex, no external API, runs fully offline.

Handles:
  - ₹/Rs./INR flat amounts       e.g. Rs. 15,000/month
  - Ranges                        e.g. Rs. 15,000 - 20,000/month
  - k-notation                    e.g. 15k/month
  - Lacs per month                e.g. INR 1.1 Lacs per month  → ₹1,10,000/month
  - LPA (annual)                  e.g. Rs. 3-7 LPA             → ₹25,000/month
  - No-space labels               e.g. Compensation20,000 inr per month
  - All major deadline wordings   e.g. last date / apply by / apply before / closes
  - City aliases                  e.g. Bengaluru → Bangalore, Gurgaon → Gurugram
"""
import re
import logging

logger = logging.getLogger(__name__)

# ── Month name fragment used across deadline patterns ─────────
_M = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?"
    r"|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?"
    r"|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)

# ── Stipend patterns — ordered most-specific → least-specific ─
#    Every pattern must have exactly ONE capture group: the numeric value.
_STIPEND_PATTERNS = [re.compile(p, re.IGNORECASE) for p in [

    # 1. Lacs per month  →  "INR 1.1 Lacs per month", "₹ 1.6 Lacs/month"
    #    Captured: the decimal number (e.g. "1.1"). Conversion: ×1,00,000
    r"(?:Rs\.?|INR|₹)\s*([\d]+(?:\.\d+)?)\s*Lac(?:s|hs?)?\s*(?:[-\u2013]\s*[\d.]+\s*Lac(?:s|hs?)?\s*)?(?:per\s*month|/\s*month|p\.?m\.?)",

    # 2. LPA (annual)  →  "Rs. 3-7 LPA", "INR 5 LPA"
    #    Captured: lower bound. Conversion: ×1,00,000 ÷ 12
    r"(?:Rs\.?|INR|₹)\s*([\d.]+)\s*(?:[-–]\s*[\d.]+\s*)?(?:LPA|L\.P\.A\.?)",

    # 3. Range with currency symbol  →  "Rs. 15,000 - 20,000/month"
    #    Captured: lower bound only (conservative estimate)
    r"(?:Rs\.?|INR|₹)\s*([\d,]+)\s*[-–]\s*[\d,]+\s*(?:per\s*month|/\s*month|p\.?m\.?)?",

    # 4. Flat with currency symbol  →  "₹20,000/month", "Rs. 15000 per month"
    r"(?:Rs\.?|INR|₹)\s*([\d,]+)(?!\s*[\d.]*\s*Lac)\s*(?:per\s*month|/\s*month|p\.?m\.?)?",

    # 5. Compensation/Stipend label + number + INR/inr  →  "Compensation20,000 inr per month"
    r"(?:compensation|stipend|salary)[^\d]*([\d,]{4,})\s*(?:inr|rs\.?|₹)?\s*(?:per\s*month|/\s*month|p\.?m\.?)?",

    # 6. Bare number + per month (no currency symbol)  →  "20,000 per month"
    r"(?<!\d)([\d,]{4,})\s*(?:per\s*month|/\s*month|p\.?m\.?)",

    # 7. k-notation  →  "15k/month", "20K per month"
    r"(?<!\d)([\d]+[kK])\s*(?:per\s*month|/\s*month|p\.?m\.?)",

    # 8. Stipend keyword + bare number  →  "stipend: 15000"
    r"stipend[:\s]+(?:Rs\.?|INR|₹)?\s*([\d,]{4,})",
]]

# ── Deadline patterns — ordered specific → generic ────────────
_DEADLINE_PATTERNS = [re.compile(p, re.IGNORECASE) for p in [
    # "Last date to apply: 30 May 2025"
    # "Last date of application is 30th April, 2025"
    # "Last date: 20 June 2025"
    rf"last\s*date\b[^,\n]{{0,40}}?(\d{{1,2}}(?:st|nd|rd|th)?\s+{_M}[,\s]*\d{{4}})",

    # "Apply before 15 June, 2025"
    rf"apply\s*before[:\s]+(\d{{1,2}}(?:st|nd|rd|th)?\s+{_M}[,\s]*\d{{4}})",

    # "Apply by 5th May 2025" / "Apply by May 5, 2025"
    rf"apply\s*by[:\s]+(\d{{1,2}}(?:st|nd|rd|th)?\s+{_M}[,\s]*\d{{4}}|{_M}\s+\d{{1,2}}[,\s]*\d{{4}})",

    # "Deadline: 25 May 2025" / "Deadline 25 May 2025"
    rf"deadline[:\s]+(\d{{1,2}}(?:st|nd|rd|th)?\s+{_M}[,\s]*\d{{4}})",

    # "closes on June 30, 2025" / "Applications close: 1 July 2025"
    rf"closes?(?:\s*on)?[:\s]+(?:\w+\s+)?(\d{{1,2}}(?:st|nd|rd|th)?\s+{_M}[,\s]*\d{{4}}|{_M}\s+\d{{1,2}}[,\s]*\d{{4}})",

    # Numeric fallback: DD/MM/YYYY or DD-MM-YYYY
    r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
]]

# ── Location keywords — checked in order, first match wins ────
_LOCATION_KEYWORDS = [
    "work from home", "wfh",
    "remote", "hybrid",
    "pan india",
    "bangalore", "bengaluru",
    "delhi", "new delhi",
    "mumbai",
    "hyderabad",
    "pune",
    "chennai",
    "kolkata",
    "noida",
    "gurugram", "gurgaon",
    "ahmedabad",
    "jaipur",
    "kochi",
    "indore",
]

_LOCATION_CANONICAL = {
    "wfh":            "Work From Home",
    "work from home": "Work From Home",
    "bengaluru":      "Bangalore",
    "new delhi":      "Delhi",
    "gurgaon":        "Gurugram",
}


# ── Public API ────────────────────────────────────────────────

def parse_listing(raw: dict) -> dict:
    """
    Enrich a raw scraper dict with parsed stipend / deadline / location.
    Safe — never raises, always returns a complete dict.
    """
    text = (raw.get("snippet", "") + " " + raw.get("title", "")).strip()
    return {
        **raw,
        "stipend":    _extract_stipend(text),
        "deadline":   _extract_deadline(text),
        "location":   _extract_location(text),
        "apply_link": raw.get("link", ""),
        "parsed":     True,
    }


def parse_all(listings: list[dict]) -> list[dict]:
    """Parse a batch and log a hit-rate summary."""
    results = [parse_listing(r) for r in listings]
    total   = len(results)
    s = sum(1 for r in results if r["stipend"]  != "Not mentioned")
    d = sum(1 for r in results if r["deadline"] != "Not mentioned")
    l = sum(1 for r in results if r["location"] != "Not mentioned")
    logger.info(
        f"Parsed {total} listings — "
        f"stipend {s}/{total} · deadline {d}/{total} · location {l}/{total}"
    )
    return results


# ── Private helpers ───────────────────────────────────────────

def _extract_stipend(text: str) -> str:
    for i, pattern in enumerate(_STIPEND_PATTERNS):
        m = pattern.search(text)
        if not m:
            continue
        raw_val = m.group(1).replace(",", "").strip()

        try:
            # Pattern 1 — Lacs/month: multiply by 1,00,000
            if i == 0:
                monthly = float(raw_val) * 100_000
                return f"₹{monthly:,.0f}/month"

            # Pattern 2 — LPA (annual): divide by 12
            if i == 1:
                monthly = float(raw_val) * 100_000 / 12
                return f"₹{monthly:,.0f}/month"

            # Pattern 7 — k notation: "15k" → 15,000
            if raw_val.lower().endswith("k"):
                return f"₹{int(raw_val[:-1]) * 1000:,}/month"

            # All others — plain integer
            return f"₹{int(raw_val):,}/month"

        except (ValueError, AttributeError):
            continue   # malformed number — try next pattern

    return "Not mentioned"


def _extract_deadline(text: str) -> str:
    for pattern in _DEADLINE_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(1).strip().rstrip(",").strip()
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