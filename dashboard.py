"""
dashboard.py — InternHunter AI local dashboard.
Run: streamlit run dashboard.py
"""
import sys, os, subprocess, time
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

from internhunter.database import (
    init_db, get_stats, get_new_opportunities,
    get_by_stipend, get_by_location, get_by_role,
    mark_applied, get_conn
)
from internhunter.config import (
    USER_NAME, USER_EMAIL, USER_COLLEGE, USER_BRANCH,
    USER_YEAR, USER_SKILLS, USER_GITHUB, USER_LINKEDIN
)
import sqlite3

# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title  = "InternHunter AI",
    page_icon   = "🚀",
    layout      = "wide",
    initial_sidebar_state = "expanded",
)

# ── Custom CSS ────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* Dark sidebar */
[data-testid="stSidebar"] {
    background: #0d1117 !important;
    border-right: 1px solid #21262d;
}
[data-testid="stSidebar"] * { color: #e6edf3 !important; }
[data-testid="stSidebar"] .stButton button {
    background: #238636 !important;
    color: white !important;
    border: none !important;
    width: 100%;
    font-weight: 600;
    padding: 0.6rem;
    border-radius: 6px;
    font-size: 14px;
}
[data-testid="stSidebar"] .stButton button:hover {
    background: #2ea043 !important;
}

/* Main area */
.main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

/* Header */
.dash-header {
    background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 20px 28px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 16px;
}
.dash-title {
    font-family: 'Space Mono', monospace;
    font-size: 22px;
    font-weight: 700;
    color: #58a6ff;
    margin: 0;
}
.dash-sub { font-size: 13px; color: #8b949e; margin: 2px 0 0; }

/* Stat cards */
.stat-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 16px 20px;
    text-align: center;
}
.stat-num {
    font-family: 'Space Mono', monospace;
    font-size: 32px;
    font-weight: 700;
    margin: 0;
    line-height: 1;
}
.stat-label {
    font-size: 11px;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 6px;
}
.num-blue   { color: #58a6ff; }
.num-green  { color: #3fb950; }
.num-purple { color: #d2a8ff; }
.num-orange { color: #ffa657; }

/* Opportunity cards */
.opp-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
    transition: border-color 0.2s;
}
.opp-card:hover { border-color: #58a6ff; }
.opp-title {
    font-weight: 600;
    font-size: 15px;
    color: #e6edf3;
    margin-bottom: 6px;
}
.opp-meta { font-size: 12px; color: #8b949e; }
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    margin-right: 6px;
}
.badge-internshala { background: #0d6efd22; color: #58a6ff; border: 1px solid #0d6efd44; }
.badge-linkedin    { background: #0a66c222; color: #58a6ff; border: 1px solid #0a66c244; }
.badge-unstop      { background: #6f42c122; color: #d2a8ff; border: 1px solid #6f42c144; }
.badge-wellfound   { background: #e67e2222; color: #ffa657; border: 1px solid #e67e2244; }
.badge-other       { background: #21262d;   color: #8b949e; border: 1px solid #30363d; }
.stipend-high   { color: #3fb950; font-weight: 600; }
.stipend-mid    { color: #ffa657; font-weight: 600; }
.stipend-low    { color: #8b949e; }
.section-title  {
    font-family: 'Space Mono', monospace;
    font-size: 13px;
    font-weight: 700;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin: 20px 0 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #21262d;
}
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────

def _all_opportunities(limit=100):
    init_db()
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM opportunities ORDER BY id DESC LIMIT ?", (limit,)
        )
        return [dict(r) for r in cur.fetchall()]


def _badge(source: str) -> str:
    cls = {
        "internshala.com":  "badge-internshala",
        "linkedin.com/jobs":"badge-linkedin",
        "unstop.com":       "badge-unstop",
        "wellfound.com":    "badge-wellfound",
    }.get(source, "badge-other")
    label = source.replace(".com","").replace(".co.in","").replace("/jobs","").title()
    return f'<span class="badge {cls}">{label}</span>'


def _stipend_class(stipend: str) -> str:
    if stipend == "Not mentioned": return "stipend-low"
    import re
    m = re.search(r"\d+", stipend.replace(",",""))
    if not m: return "stipend-low"
    n = int(m.group())
    if n >= 15000: return "stipend-high"
    if n >= 8000:  return "stipend-mid"
    return "stipend-low"


def _run_pipeline():
    """Run scheduler in a subprocess so Streamlit doesn't block."""
    result = subprocess.run(
        [sys.executable, "-m", "internhunter.scheduler"],
        capture_output=True, text=True, cwd=os.path.dirname(__file__)
    )
    return result.returncode == 0, result.stdout + result.stderr


# ── Sidebar ───────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🚀 InternHunter AI")
    st.markdown("---")

    # Navigation
    page = st.radio(
        "Navigate",
        ["📋 Opportunities", "⚡ Pipeline", "👤 Profile"],
        label_visibility="collapsed"
    )

    st.markdown("---")

    # Quick stats in sidebar
    init_db()
    stats = get_stats()
    st.markdown(f"**{stats['total']}** total &nbsp;·&nbsp; **{stats['new']}** new")
    st.markdown(f"**{stats['applied']}** applied &nbsp;·&nbsp; **{stats['with_stipend']}** with stipend")

    st.markdown("---")
    st.markdown('<p style="font-size:11px;color:#484f58">Auto-runs daily at 9:30 AM IST via GitHub Actions</p>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  PAGE 1 — Opportunities
# ══════════════════════════════════════════════════════════════

if page == "📋 Opportunities":

    # Header
    st.markdown("""
    <div class="dash-header">
      <div>
        <p class="dash-title">🚀 InternHunter AI</p>
        <p class="dash-sub">Your automated internship discovery engine</p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Stat cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="stat-card"><p class="stat-num num-blue">{stats["total"]}</p><p class="stat-label">Total Found</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-card"><p class="stat-num num-green">{stats["new"]}</p><p class="stat-label">New Today</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-card"><p class="stat-num num-purple">{stats["applied"]}</p><p class="stat-label">Applied</p></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="stat-card"><p class="stat-num num-orange">{stats["with_stipend"]}</p><p class="stat-label">With Stipend</p></div>', unsafe_allow_html=True)

    st.markdown("") # spacer

    # Filters
    st.markdown('<p class="section-title">Filter</p>', unsafe_allow_html=True)
    f1, f2, f3, f4 = st.columns([2, 2, 2, 1])
    with f1:
        search_role = st.text_input("Role keyword", placeholder="e.g. machine learning")
    with f2:
        search_loc = st.text_input("Location", placeholder="e.g. bangalore")
    with f3:
        min_stip = st.number_input("Min stipend (₹/month)", min_value=0, step=5000, value=0)
    with f4:
        show_all = st.checkbox("Show all", value=True, help="Include already-notified rows")

    # Load data
    if search_role:
        opps = get_by_role(search_role, limit=50)
    elif search_loc:
        opps = get_by_location(search_loc, limit=50)
    elif min_stip > 0:
        opps = get_by_stipend(min_amount=min_stip, limit=50)
    elif show_all:
        opps = _all_opportunities(limit=100)
    else:
        opps = get_new_opportunities(limit=50)

    # Results
    st.markdown(f'<p class="section-title">Results — {len(opps)} opportunities</p>', unsafe_allow_html=True)

    if not opps:
        st.info("No opportunities found. Run the pipeline to fetch new listings.")
    else:
        for opp in opps:
            stipend  = opp.get("stipend",  "Not mentioned")
            deadline = opp.get("deadline", "Not mentioned")
            location = opp.get("location", "Not mentioned")
            title    = opp.get("title",    "Untitled")
            link     = opp.get("apply_link") or opp.get("link","#")
            source   = opp.get("source","other")
            opp_id   = opp.get("id")
            status   = opp.get("status","new")

            stip_display = stipend if stipend != "Not mentioned" else "—"
            dead_display = deadline if deadline != "Not mentioned" else "—"
            loc_display  = location if location != "Not mentioned" else "—"

            col_main, col_btn = st.columns([5, 1])
            with col_main:
                st.markdown(f"""
                <div class="opp-card">
                  <div class="opp-title">{title}</div>
                  <div class="opp-meta">
                    {_badge(source)}
                    <span class="{_stipend_class(stipend)}">{stip_display}</span>
                    &nbsp;·&nbsp; 📅 {dead_display}
                    &nbsp;·&nbsp; 📍 {loc_display}
                    {"&nbsp;·&nbsp; ✅ applied" if status == 'applied' else ""}
                  </div>
                </div>
                """, unsafe_allow_html=True)

            with col_btn:
                st.markdown("<div style='margin-top:8px'>", unsafe_allow_html=True)
                c_apply, c_link = st.columns(2)
                with c_link:
                    st.link_button("↗", link, use_container_width=True)
                with c_apply:
                    if status != "applied":
                        if st.button("✓", key=f"apply_{opp_id}", help="Mark as applied"):
                            mark_applied(opp_id, method="company_site")
                            st.rerun()
                    else:
                        st.button("✓", key=f"applied_{opp_id}", disabled=True)
                st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  PAGE 2 — Pipeline
# ══════════════════════════════════════════════════════════════

elif page == "⚡ Pipeline":

    st.markdown('<p class="dash-title" style="font-family:\'Space Mono\',monospace;color:#58a6ff">⚡ Pipeline Control</p>', unsafe_allow_html=True)
    st.markdown("Trigger a full scrape → parse → store → email run.")
    st.markdown("---")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("##### Run pipeline")
        st.markdown("Uses ~6 Serper API credits. Takes 20–40 seconds.")
        if st.button("🚀 Run Pipeline Now", type="primary", use_container_width=True):
            with st.spinner("Running pipeline… this takes ~30 seconds"):
                ok, output = _run_pipeline()
            if ok:
                st.success("Pipeline completed successfully!")
            else:
                st.error("Pipeline encountered errors — see log below")
            st.code(output[-3000:], language="text")   # last 3000 chars of output

        st.markdown("---")
        st.markdown("##### Last run stats")
        stats = get_stats()
        for k, v in stats.items():
            st.markdown(f"`{k}` &nbsp; **{v}**")

    with col2:
        st.markdown("##### Live log tail")
        log_path = "logs/daily.log"
        if os.path.exists(log_path):
            with open(log_path, encoding="utf-8") as f:
                lines = f.readlines()
            last50 = "".join(lines[-50:])
            st.code(last50, language="text")
            st.caption(f"Showing last 50 of {len(lines)} lines from {log_path}")
        else:
            st.info("No log file yet — run the pipeline first.")


# ══════════════════════════════════════════════════════════════
#  PAGE 3 — Profile
# ══════════════════════════════════════════════════════════════

elif page == "👤 Profile":

    st.markdown('<p class="dash-title" style="font-family:\'Space Mono\',monospace;color:#58a6ff">👤 Your Profile</p>', unsafe_allow_html=True)
    st.markdown("Changes here update the session only. To make permanent, edit your `.env` file.")
    st.markdown("---")

    # Read current values from .env / config
    col1, col2 = st.columns(2)

    with col1:
        name    = st.text_input("Full Name",     value=USER_NAME)
        email   = st.text_input("Email",         value=USER_EMAIL)
        college = st.text_input("College",       value=USER_COLLEGE)
        branch  = st.text_input("Branch",        value=USER_BRANCH)
        year    = st.text_input("Year",          value=USER_YEAR)

    with col2:
        skills_str = st.text_area(
            "Skills (one per line)",
            value="\n".join(USER_SKILLS),
            height=120
        )
        github   = st.text_input("GitHub URL",   value=USER_GITHUB)
        linkedin = st.text_input("LinkedIn URL", value=USER_LINKEDIN)

    st.markdown("---")

    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button("💾 Save to .env", type="primary", use_container_width=True):
            skills_list = [s.strip() for s in skills_str.splitlines() if s.strip()]
            env_content = f"""# InternHunter AI — auto-updated from dashboard
USER_NAME={name}
USER_EMAIL={email}
USER_COLLEGE={college}
USER_BRANCH={branch}
USER_YEAR={year}
USER_SKILLS={','.join(skills_list)}
USER_GITHUB={github}
USER_LINKEDIN={linkedin}
USER_RESUME_PATH=assets/resume.pdf

SERPER_API_KEY={os.getenv('SERPER_API_KEY','')}
OPENAI_API_KEY={os.getenv('OPENAI_API_KEY','')}

GMAIL_USER={os.getenv('GMAIL_USER','')}
GMAIL_APP_PASS={os.getenv('GMAIL_APP_PASS','')}
"""
            env_path = os.path.join(os.path.dirname(__file__), ".env")
            with open(env_path, "w") as f:
                f.write(env_content)
            st.success("✅ Saved to .env — restart the server for changes to take effect.")

    with c2:
        st.info("💡 After saving, run `Ctrl+C` then `streamlit run dashboard.py` to reload the new profile values.")

    # Cold email preview
    st.markdown("---")
    st.markdown("##### Cold email preview")
    preview_company = st.text_input("Company name for preview", value="Google DeepMind")
    preview_role    = st.text_input("Role for preview",         value="Machine Learning Intern")

    if preview_company and preview_role:
        from internhunter.mailer import draft_cold_email
        draft = draft_cold_email(
            {"role": preview_role, "company": preview_company},
            {
                "name": name, "email": email, "college": college,
                "branch": branch, "year": year,
                "skills": [s.strip() for s in skills_str.splitlines() if s.strip()],
                "github": github, "linkedin": linkedin,
            }
        )
        st.markdown(f"**Subject:** `{draft['subject']}`")
        st.text_area("Email body", value=draft["text"], height=250)
        st.download_button(
            "⬇ Download as .txt",
            data=f"Subject: {draft['subject']}\n\n{draft['text']}",
            file_name=f"cold_email_{preview_company.lower().replace(' ','_')}.txt",
            mime="text/plain"
        )
