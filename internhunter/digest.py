"""
digest.py — Build the daily HTML + plain-text digest of new opportunities.

Produces two outputs:
  build_digest_html()  → rich HTML email (rendered in Gmail / any mail client)
  build_digest_text()  → plain-text fallback (readable in terminal too)

Both functions accept the same list[dict] from get_new_opportunities().
"""
from datetime import datetime
from internhunter.referral import build_referral_hints, referral_section_html, referral_section_text


# ── Helpers ───────────────────────────────────────────────────

def _source_badge(source: str) -> str:
    colours = {
        "internshala.com":  "#0d6efd",
        "linkedin.com/jobs":"#0a66c2",
        "unstop.com":       "#6f42c1",
        "wellfound.com":    "#e67e22",
        "naukri.com":       "#c0392b",
        "glassdoor.co.in":  "#27ae60",
        "other":            "#6c757d",
    }
    colour = colours.get(source, colours["other"])
    label  = source.replace(".com", "").replace(".co.in", "").replace("/jobs", "").title()
    return (
        f"<span style='background:{colour};color:white;padding:2px 7px;"
        f"border-radius:10px;font-size:11px;font-weight:bold'>{label}</span>"
    )


def _stipend_style(stipend: str) -> str:
    """Green if >= 15k, amber if < 15k, grey if Not mentioned."""
    if stipend == "Not mentioned":
        return "color:#aaa"
    try:
        import re
        amount = int(re.sub(r"[^\d]", "", stipend.split("/")[0]))
        if amount >= 15000:
            return "color:#1a7f37;font-weight:bold"
        return "color:#b76e00;font-weight:bold"
    except Exception:
        return ""


def _safe(value: str, fallback: str = "—") -> str:
    v = (value or "").strip()
    return v if v and v != "Not mentioned" else fallback


# ── HTML digest ───────────────────────────────────────────────

def build_digest_html(opportunities: list[dict], stats: dict = None, show_referrals: bool = True) -> str:
    """
    Build a full HTML email digest.
    Pass stats=get_stats() to include a summary header bar.
    """
    date_str = datetime.now().strftime("%A, %d %b %Y")
    count    = len(opportunities)

    # ── Stats bar ─────────────────────────────────────────────
    stats_html = ""
    if stats:
        stats_html = f"""
        <table style='width:100%;margin-bottom:20px;background:#f8f9fa;
                      border-radius:8px;padding:12px 0'>
          <tr style='text-align:center'>
            <td><b style='font-size:22px;color:#1a73e8'>{stats.get('total',0)}</b>
                <br><span style='font-size:11px;color:#666'>Total</span></td>
            <td><b style='font-size:22px;color:#1a7f37'>{stats.get('new',0)}</b>
                <br><span style='font-size:11px;color:#666'>New</span></td>
            <td><b style='font-size:22px;color:#b76e00'>{stats.get('applied',0)}</b>
                <br><span style='font-size:11px;color:#666'>Applied</span></td>
            <td><b style='font-size:22px;color:#6f42c1'>{stats.get('with_stipend',0)}</b>
                <br><span style='font-size:11px;color:#666'>With Stipend</span></td>
          </tr>
        </table>"""

    # ── Opportunity rows ──────────────────────────────────────
    rows_html = ""
    for i, o in enumerate(opportunities):
        bg       = "#ffffff" if i % 2 == 0 else "#f8f9fa"
        stipend  = _safe(o.get("stipend"))
        deadline = _safe(o.get("deadline"))
        location = _safe(o.get("location"))
        title    = _safe(o.get("title"), "Untitled")
        link     = o.get("apply_link") or o.get("link") or "#"
        source   = o.get("source", "other")

        rows_html += f"""
        <tr style='background:{bg}'>
          <td style='padding:10px 12px;border-bottom:1px solid #eee;max-width:280px'>
            <a href='{link}' style='color:#1a73e8;text-decoration:none;font-weight:bold;
               font-size:13px'>{title}</a><br>
            <span style='font-size:11px;margin-top:3px;display:inline-block'>
              {_source_badge(source)}
            </span>
          </td>
          <td style='padding:10px 12px;border-bottom:1px solid #eee;
                     font-size:13px;{_stipend_style(stipend)}'>{stipend}</td>
          <td style='padding:10px 12px;border-bottom:1px solid #eee;
                     font-size:13px;color:#555'>{deadline}</td>
          <td style='padding:10px 12px;border-bottom:1px solid #eee;
                     font-size:13px;color:#555'>{location}</td>
          <td style='padding:10px 12px;border-bottom:1px solid #eee;text-align:center'>
            <a href='{link}' style='background:#1a73e8;color:white;padding:5px 14px;
               border-radius:4px;text-decoration:none;font-size:12px;
               font-weight:bold'>Apply →</a>
          </td>
        </tr>"""

    # ── No results fallback ───────────────────────────────────
    if not rows_html:
        rows_html = """
        <tr><td colspan='5' style='text-align:center;padding:30px;color:#888'>
          No new opportunities found today. Check back tomorrow!
        </td></tr>"""

    # ── Referral section ──────────────────────────────────
    referral_html = referral_section_html(build_referral_hints(opportunities)) if show_referrals else ""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset='utf-8'></head>
<body style='margin:0;padding:20px;font-family:Arial,sans-serif;
             background:#f0f4f8;color:#333'>
  <div style='max-width:860px;margin:auto;background:white;
              border-radius:10px;overflow:hidden;
              box-shadow:0 2px 8px rgba(0,0,0,0.1)'>

    <!-- Header -->
    <div style='background:linear-gradient(135deg,#1a73e8,#0d47a1);
                padding:24px 28px;color:white'>
      <h1 style='margin:0;font-size:22px'>🚀 InternHunter Daily Digest</h1>
      <p style='margin:4px 0 0;opacity:0.85;font-size:14px'>{date_str}
         &nbsp;·&nbsp; <b>{count}</b> new opportunit{'y' if count==1 else 'ies'}</p>
    </div>

    <div style='padding:20px 28px'>
      {stats_html}

      <!-- Table -->
      <table style='width:100%;border-collapse:collapse'>
        <thead>
          <tr style='background:#f1f3f4;color:#444;font-size:12px;
                     text-transform:uppercase;letter-spacing:0.5px'>
            <th style='padding:10px 12px;text-align:left'>Opportunity</th>
            <th style='padding:10px 12px;text-align:left'>Stipend</th>
            <th style='padding:10px 12px;text-align:left'>Deadline</th>
            <th style='padding:10px 12px;text-align:left'>Location</th>
            <th style='padding:10px 12px;text-align:center'>Action</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </div>

    <!-- Referral hints -->
    {referral_html}

    <!-- Footer -->
    <div style='padding:14px 28px;background:#f8f9fa;
                border-top:1px solid #eee;font-size:11px;color:#999'>
      InternHunter Bot &nbsp;·&nbsp; auto-generated &nbsp;·&nbsp;
      Do not reply to this email
    </div>
  </div>
</body>
</html>"""


# ── Plain-text digest ─────────────────────────────────────────

def build_digest_text(opportunities: list[dict], show_referrals: bool = True) -> str:
    """
    Plain-text version — readable in terminal and as email fallback.
    """
    date_str = datetime.now().strftime("%A, %d %b %Y")
    lines    = [
        "=" * 60,
        f"  InternHunter Daily Digest — {date_str}",
        f"  {len(opportunities)} new opportunities",
        "=" * 60,
    ]

    if not opportunities:
        lines.append("\n  No new opportunities today. Check back tomorrow!\n")
        return "\n".join(lines)

    for i, o in enumerate(opportunities, 1):
        title    = _safe(o.get("title"),    "Untitled")
        stipend  = _safe(o.get("stipend"))
        deadline = _safe(o.get("deadline"))
        location = _safe(o.get("location"))
        link     = o.get("apply_link") or o.get("link") or "—"
        source   = o.get("source", "other")

        lines += [
            "",
            f"  [{i}] {title}",
            f"      Source:   {source}",
            f"      Stipend:  {stipend}",
            f"      Deadline: {deadline}",
            f"      Location: {location}",
            f"      Apply:    {link}",
        ]

    if show_referrals:
        lines.append(referral_section_text(build_referral_hints(opportunities)))
    lines += ["", "=" * 60, "  InternHunter Bot · auto-generated", "=" * 60]
    return "\n".join(lines)


# ── Save to file ──────────────────────────────────────────────

def save_digest(html: str, text: str, out_dir: str = "data/digest") -> tuple[str, str]:
    """Save HTML and text digests to disk. Returns (html_path, text_path)."""
    import os
    os.makedirs(out_dir, exist_ok=True)
    date_slug = datetime.now().strftime("%Y-%m-%d")
    html_path = os.path.join(out_dir, f"{date_slug}.html")
    text_path = os.path.join(out_dir, f"{date_slug}.txt")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(text)
    return html_path, text_path