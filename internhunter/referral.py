"""
referral.py — Generate LinkedIn referral search hints for each company.

For every unique company in the digest, produces:
  - A plain-English hint  ("Search LinkedIn for Razorpay + DTU alumni")
  - A pre-filled LinkedIn people-search URL (one click, opens in browser)
  - A pre-filled LinkedIn jobs URL for the same company

Called by digest.py:
    hints = build_referral_hints(opportunities)
    html  = referral_section_html(hints)
    text  = referral_section_text(hints)
"""
import re
import urllib.parse
import logging
from internhunter.config import USER_COLLEGE

logger = logging.getLogger(__name__)

# Short college aliases to include in the search
# e.g. "Delhi Technological University" → ["DTU", "Delhi Technological University"]
def _college_aliases(college: str) -> list[str]:
    """
    Return a list of search terms for the college.
    Tries to detect common acronyms automatically.
    """
    college = college.strip()
    aliases = [college]

    # Extract acronym from words longer than 2 chars (skips 'of', 'and', 'the')
    words   = [w for w in college.split() if len(w) > 2]
    acronym = "".join(w[0].upper() for w in words)
    if len(acronym) >= 2 and acronym != college:
        aliases.insert(0, acronym)   # put acronym first — more searchable

    return aliases


def _extract_company(opp: dict) -> str:
    """
    Pull company name from an opportunity dict.
    Handles 4 real-world title formats seen in Serper results.
    """
    company = (opp.get("company") or "").strip()
    if company:
        return company

    title = opp.get("title", "")

    # Format 1: LinkedIn pulse — "Company name: Uber Role: SWE Intern"
    m = re.search(r"Company name:\s*([A-Za-z0-9][A-Za-z0-9 &._\-]+?)\s+Role:", title)
    if m:
        return m.group(1).strip()

    # Format 2: "ML Intern @ Razorpay"
    m = re.search(r"@\s*([A-Za-z0-9][A-Za-z0-9 &._\-]+)", title)
    if m:
        return m.group(1).strip()

    # Format 3: "ML Intern at Meesho"
    m = re.search(r"\bat\s+([A-Z][A-Za-z0-9 &._\-]+)", title)
    if m:
        return m.group(1).strip()

    # Format 4: "GOOGLE OFFERS SUMMER INTERNSHIP" — all-caps headline
    m = re.search(r"^([A-Z]{2,}(?:\s+[A-Z]{2,})*)\s+(?:OFFERS|HIRING|IS HIRING)", title)
    if m:
        return m.group(1).title()

    return ""


def _linkedin_people_url(company: str, college_alias: str) -> str:
    """
    Build a LinkedIn people-search URL pre-filled with company + college.
    Opens linkedin.com/search/results/people with keyword filters.
    """
    keywords = f"{company} {college_alias}"
    params   = urllib.parse.urlencode({
        "keywords":  keywords,
        "origin":    "GLOBAL_SEARCH_HEADER",
        "sid":       "referral",
    })
    return f"https://www.linkedin.com/search/results/people/?{params}"


def _linkedin_jobs_url(company: str, role: str = "") -> str:
    """LinkedIn job search pre-filtered for company + role."""
    query  = f"{company} {role}".strip() if role else company
    params = urllib.parse.urlencode({"keywords": query, "f_C": ""})
    return f"https://www.linkedin.com/jobs/search/?{params}"


# ── Public API ────────────────────────────────────────────────

def build_referral_hints(opportunities: list[dict]) -> list[dict]:
    """
    Build a deduplicated list of referral hint dicts, one per unique company.

    Each dict has:
        company         str   — cleaned company name
        role            str   — internship role
        hint            str   — plain-English suggestion
        linkedin_people str   — URL to search for alumni at that company
        linkedin_jobs   str   — URL to browse company's jobs on LinkedIn
        college_alias   str   — the alias used (e.g. "DTU")
        opp_title       str   — original opportunity title (for context)
    """
    aliases = _college_aliases(USER_COLLEGE)
    primary_alias = aliases[0]   # e.g. "DTU"

    seen, hints = set(), []

    for opp in opportunities:
        company = _extract_company(opp)
        if not company or company.lower() in seen:
            continue
        # Skip obvious non-companies (category page titles)
        if any(skip in company.lower() for skip in [
            "internship", "job", "india", "intern", "latest", "top", "best"
        ]):
            continue

        seen.add(company.lower())
        role = opp.get("role", "intern")

        hints.append({
            "company":          company,
            "role":             role,
            "hint":             (
                f"Search LinkedIn for '{company} {primary_alias} alumni' "
                f"→ connect and ask for a referral for the {role} role"
            ),
            "linkedin_people":  _linkedin_people_url(company, primary_alias),
            "linkedin_jobs":    _linkedin_jobs_url(company, role),
            "college_alias":    primary_alias,
            "opp_title":        opp.get("title", ""),
        })

    logger.info(f"Built {len(hints)} referral hints for {len(seen)} unique companies")
    return hints


def referral_section_html(hints: list[dict]) -> str:
    """Render referral hints as an HTML block for the digest email."""
    if not hints:
        return ""

    rows = ""
    for h in hints:
        company   = h["company"]
        alias     = h["college_alias"]
        people_url = h["linkedin_people"]
        jobs_url   = h["linkedin_jobs"]

        rows += f"""
        <tr>
          <td style='padding:10px 12px;border-bottom:1px solid #eee;
                     font-size:13px;font-weight:bold;color:#1a1a1a'>
            {company}
          </td>
          <td style='padding:10px 12px;border-bottom:1px solid #eee;font-size:12px;color:#555'>
            Search LinkedIn for <b>{company} + {alias} alumni</b>
            and send a connection request mentioning the internship.
          </td>
          <td style='padding:10px 12px;border-bottom:1px solid #eee;text-align:center'>
            <a href='{people_url}'
               style='background:#0a66c2;color:white;padding:4px 12px;
                      border-radius:4px;text-decoration:none;font-size:12px;
                      font-weight:bold;margin-right:4px'>
              👥 Find Alumni
            </a>
            <a href='{jobs_url}'
               style='background:#f1f3f4;color:#333;padding:4px 12px;
                      border-radius:4px;text-decoration:none;font-size:12px;
                      border:1px solid #ddd'>
              💼 Jobs
            </a>
          </td>
        </tr>"""

    return f"""
    <div style='padding:20px 28px 0'>
      <h3 style='font-size:14px;color:#444;margin:0 0 12px;
                 text-transform:uppercase;letter-spacing:0.5px'>
        🤝 Referral Finder — {len(hints)} Companies
      </h3>
      <p style='font-size:12px;color:#888;margin:0 0 12px'>
        A referral from a {hints[0]['college_alias'] if hints else ''} alum dramatically
        increases your chances. One message, one click.
      </p>
      <table style='width:100%;border-collapse:collapse'>
        <thead>
          <tr style='background:#f1f3f4;font-size:11px;color:#666;text-transform:uppercase'>
            <th style='padding:8px 12px;text-align:left'>Company</th>
            <th style='padding:8px 12px;text-align:left'>Hint</th>
            <th style='padding:8px 12px;text-align:center'>Action</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>"""


def referral_section_text(hints: list[dict]) -> str:
    """Render referral hints as plain text for the fallback digest."""
    if not hints:
        return ""

    lines = [
        "",
        "=" * 60,
        "  REFERRAL FINDER",
        "=" * 60,
    ]
    for i, h in enumerate(hints, 1):
        lines += [
            "",
            f"  [{i}] {h['company']}",
            f"      Hint:    {h['hint']}",
            f"      Alumni:  {h['linkedin_people']}",
            f"      Jobs:    {h['linkedin_jobs']}",
        ]
    return "\n".join(lines)