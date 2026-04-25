"""Parse raw listing snippets → structured opportunity dicts using AI."""
import re, logging
from internhunter.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)


def parse_listing(raw: dict) -> dict:
    """Extract structured fields from a raw search result."""
    snippet = raw.get("snippet", "")
    title   = raw.get("title", "")

    stipend  = _extract_stipend(snippet + " " + title)
    deadline = _extract_deadline(snippet)
    location = _extract_location(snippet + " " + title)

    return {
        **raw,
        "stipend":     stipend,
        "deadline":    deadline,
        "location":    location,
        "apply_link":  raw.get("link", ""),
        "parsed":      True
    }


def _extract_stipend(text: str) -> str:
    patterns = [
        r"(?:Rs\.?|INR|₹)\s?(\d[\d,]+)\s?(?:per month|/month|pm|p\.m\.)?",
        r"(\d[\d,]+)\s?(?:per month|/month|pm)\s?(?:stipend)?",
        r"stipend[:\s]+(?:Rs\.?|INR|₹)?\s?(\d[\d,]+)"
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return f"₹{m.group(1)}/month"
    return "Not mentioned"


def _extract_deadline(text: str) -> str:
    patterns = [
        r"(?:deadline|last date|apply by|closes?)[:\s]+([A-Za-z0-9 ,]+\d{4})",
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return "Not mentioned"


def _extract_location(text: str) -> str:
    keywords = ["remote", "work from home", "wfh", "bangalore", "delhi",
                "mumbai", "hyderabad", "pune", "chennai", "kolkata", "noida", "gurugram"]
    found = [k for k in keywords if k.lower() in text.lower()]
    return ", ".join(found).title() if found else "Not mentioned"
