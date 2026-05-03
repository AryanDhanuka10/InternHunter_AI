"""
dashboard.py — InternHunter AI Streamlit frontend.

Two modes:
  LOCAL  — reads SQLite directly (default when API_URL not set)
  CLOUD  — calls the Hugging Face FastAPI backend via HTTP

Set API_URL in Streamlit Cloud secrets or .env to enable cloud mode:
  API_URL = "https://YOUR-HF-USERNAME-internhunter-api.hf.space"
"""
import os, sys, json, requests as req
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

# ── Mode detection ────────────────────────────────────────────
API_URL = os.getenv("API_URL", "").rstrip("/")
CLOUD_MODE = bool(API_URL)

# Only import local modules when not in cloud mode
if not CLOUD_MODE:
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
else:
    # Cloud mode — pull profile from env/secrets
    USER_NAME     = os.getenv("USER_NAME", "")
    USER_EMAIL    = os.getenv("USER_EMAIL", "")
    USER_COLLEGE  = os.getenv("USER_COLLEGE", "")
    USER_BRANCH   = os.getenv("USER_BRANCH", "")
    USER_YEAR     = os.getenv("USER_YEAR", "")
    USER_SKILLS   = os.getenv("USER_SKILLS", "").split(",")
    USER_GITHUB   = os.getenv("USER_GITHUB", "")
    USER_LINKEDIN = os.getenv("USER_LINKEDIN", "")


# ── API helpers (cloud mode) ──────────────────────────────────

def _api(path: str, method="GET", **kwargs):
    """Call the HF backend. Returns parsed JSON or None on error."""
    try:
        url = f"{API_URL}{path}"
        r = getattr(req, method.lower())(url, timeout=15, **kwargs)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def _get_opps(role="", location="", min_stipend=0, show_all=True):
    if CLOUD_MODE:
        params = {"limit": 50, "all": str(show_all).lower()}
        if role:        params["role"]        = role
        if location:    params["location"]    = location
        if min_stipend: params["min_stipend"] = min_stipend
        return _api("/api/opportunities/", params=params) or []
    else:
        init_db()
        if role:        return get_by_role(role, limit=50)
        if location:    return get_by_location(location, limit=50)
        if min_stipend: return get_by_stipend(min_amount=min_stipend, limit=50)
        if show_all:
            with get_conn() as conn:
                conn.row_factory = sqlite3.Row
                return [dict(r) for r in conn.execute(
                    "SELECT * FROM opportunities ORDER BY score DESC, id DESC LIMIT 100"
                ).fetchall()]
        return get_new_opportunities(limit=50)


def _get_stats():
    if CLOUD_MODE:
        return _api("/api/actions/stats") or {}
    else:
        init_db()
        return get_stats()


def _mark_applied(opp_id, method="company_site"):
    if CLOUD_MODE:
        _api(f"/api/opportunities/{opp_id}/apply", method="POST",
             json={"method": method})
    else:
        mark_applied(opp_id, method=method)


def _run_pipeline():
    if CLOUD_MODE:
        result = _api("/api/actions/run-pipeline?async_run=true", method="POST")
        if result:
            ok = not result.get("stages_fail")
            return ok, json.dumps(result, indent=2)
        return False, "API call failed"
    else:
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "internhunter.scheduler"],
            capture_output=True, text=True,
            cwd=os.path.dirname(__file__)
        )
        return result.returncode == 0, result.stdout + result.stderr


# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="InternHunter AI",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

[data-testid="stSidebar"] { background: #0d1117 !important; border-right: 1px solid #21262d; }
[data-testid="stSidebar"] * { color: #e6edf3 !important; }
[data-testid="stSidebar"] .stButton button {
    background: #238636 !important; color: white !important;
    border: none !important; width: 100%; font-weight: 600;
    padding: 0.6rem; border-radius: 6px;
}

.stat-card { background: #161b22; border: 1px solid #21262d; border-radius: 10px; padding: 16px 20px; text-align: center; }
.stat-num { font-family: 'Space Mono',monospace; font-size: 32px; font-weight: 700; margin: 0; line-height: 1; }
.stat-label { font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; margin-top: 6px; }
.num-blue{color:#58a6ff} .num-green{color:#3fb950} .num-purple{color:#d2a8ff} .num-orange{color:#ffa657}

.opp-card { background: #161b22; border: 1px solid #21262d; border-radius: 10px; padding: 14px 18px; margin-bottom: 10px; }
.opp-title { font-weight: 600; font-size: 15px; color: #e6edf3; margin-bottom: 6px; }
.opp-meta { font-size: 12px; color: #8b949e; }
.badge { display:inline-block; padding:2px 8px; border-radius:12px; font-size:11px; font-weight:600; margin-right:6px; }
.badge-internshala{background:#0d6efd22;color:#58a6ff;border:1px solid #0d6efd44}
.badge-linkedin{background:#0a66c222;color:#58a6ff;border:1px solid #0a66c244}
.badge-unstop{background:#6f42c122;color:#d2a8ff;border:1px solid #6f42c144}
.badge-wellfound{background:#e67e2222;color:#ffa657;border:1px solid #e67e2244}
.badge-other{background:#21262d;color:#8b949e;border:1px solid #30363d}
.sh{color:#3fb950;font-weight:600} .sm{color:#ffa657;font-weight:600} .sl{color:#8b949e}
.mode-badge { padding:3px 10px; border-radius:12px; font-size:11px; font-weight:600; }
.mode-cloud { background:#1f6feb22; color:#58a6ff; border:1px solid #1f6feb44; }
.mode-local { background:#23863622; color:#3fb950; border:1px solid #23863644; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────

def _badge(source):
    cls = {"internshala.com":"badge-internshala","linkedin.com/jobs":"badge-linkedin",
           "unstop.com":"badge-unstop","wellfound.com":"badge-wellfound"}.get(source,"badge-other")
    label = source.replace(".com","").replace(".co.in","").replace("/jobs","").title()
    return f'<span class="badge {cls}">{label}</span>'

def _stip_cls(s):
    if s in ("Not mentioned", "", None, "—"): return "sl"
    import re
    m = re.search(r"\d+", str(s).replace(",",""))
    if not m: return "sl"
    return "sh" if int(m.group()) >= 15000 else "sm"

def _safe(v, fb="—"):
    s = (v or "").strip()
    return s if s and s != "Not mentioned" else fb


# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    mode_html = (f'<span class="mode-badge mode-cloud">☁ Cloud · {API_URL.split("//")[-1][:30]}</span>'
                 if CLOUD_MODE else '<span class="mode-badge mode-local">💻 Local</span>')
    st.markdown(f"### 🚀 InternHunter AI<br>{mode_html}", unsafe_allow_html=True)
    st.markdown("---")
    page = st.radio("Navigate", ["📋 Opportunities", "⚡ Pipeline", "👤 Profile"],
                    label_visibility="collapsed")
    st.markdown("---")
    stats = _get_stats()
    st.markdown(f"**{stats.get('total',0)}** total &nbsp;·&nbsp; **{stats.get('new',0)}** new")
    st.markdown(f"**{stats.get('applied',0)}** applied &nbsp;·&nbsp; **{stats.get('with_stipend',0)}** with stipend")
    st.markdown("---")
    st.caption("Auto-runs daily at 9:30 AM IST via GitHub Actions")


# ══════════════════════════════════════════════════════════════
#  PAGE 1 — Opportunities
# ══════════════════════════════════════════════════════════════
if page == "📋 Opportunities":
    st.markdown("""<div style='background:#161b22;border:1px solid #21262d;border-radius:12px;
        padding:20px 24px;margin-bottom:20px'>
        <p style='font-family:Space Mono,monospace;font-size:20px;color:#58a6ff;margin:0'>
        🚀 InternHunter AI</p>
        <p style='font-size:13px;color:#8b949e;margin:4px 0 0'>
        Your automated internship discovery engine</p></div>""", unsafe_allow_html=True)

    c1,c2,c3,c4 = st.columns(4)
    for col, num, label, cls in [
        (c1, stats.get("total",0),        "Total Found",   "num-blue"),
        (c2, stats.get("new",0),           "New Today",     "num-green"),
        (c3, stats.get("applied",0),       "Applied",       "num-purple"),
        (c4, stats.get("with_stipend",0),  "With Stipend",  "num-orange"),
    ]:
        col.markdown(f'<div class="stat-card"><p class="stat-num {cls}">{num}</p>'
                     f'<p class="stat-label">{label}</p></div>', unsafe_allow_html=True)

    st.markdown("")
    f1,f2,f3,f4 = st.columns([2,2,2,1])
    with f1: search_role = st.text_input("Role", placeholder="e.g. machine learning")
    with f2: search_loc  = st.text_input("Location", placeholder="e.g. bangalore")
    with f3: min_stip    = st.number_input("Min stipend (₹/month)", min_value=0, step=5000, value=0)
    with f4: show_all    = st.checkbox("Show all", value=True)

    opps = _get_opps(role=search_role, location=search_loc,
                     min_stipend=min_stip, show_all=show_all)

    st.markdown(f'<p style="font-size:11px;color:#8b949e;text-transform:uppercase;'
                f'letter-spacing:1px;margin:16px 0 8px">Results — {len(opps)}</p>',
                unsafe_allow_html=True)

    if not opps:
        st.info("No opportunities found. Run the pipeline to fetch new listings.")
    else:
        for opp in opps:
            stipend  = opp.get("stipend","Not mentioned")
            title    = _safe(opp.get("title"), "Untitled")
            link     = opp.get("apply_link") or opp.get("link","#")
            source   = opp.get("source","other")
            opp_id   = opp.get("id")
            status   = opp.get("status","new")
            score    = opp.get("score",0)

            col_main, col_btn = st.columns([5,1])
            with col_main:
                st.markdown(f"""<div class="opp-card">
                  <div class="opp-title">{title}</div>
                  <div class="opp-meta">
                    {_badge(source)}
                    <span class="{_stip_cls(stipend)}">{_safe(stipend)}</span>
                    &nbsp;·&nbsp; 📅 {_safe(opp.get('deadline'))}
                    &nbsp;·&nbsp; 📍 {_safe(opp.get('location'))}
                    &nbsp;·&nbsp; ⭐ {score}
                    {"&nbsp;·&nbsp; ✅ applied" if status=='applied' else ""}
                  </div></div>""", unsafe_allow_html=True)
            with col_btn:
                st.markdown("<div style='margin-top:8px'>", unsafe_allow_html=True)
                ca, cl = st.columns(2)
                with cl: st.link_button("↗", link, use_container_width=True)
                with ca:
                    if status != "applied":
                        if st.button("✓", key=f"apply_{opp_id}", help="Mark as applied"):
                            _mark_applied(opp_id)
                            st.rerun()
                    else:
                        st.button("✓", key=f"done_{opp_id}", disabled=True)
                st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  PAGE 2 — Pipeline
# ══════════════════════════════════════════════════════════════
elif page == "⚡ Pipeline":
    st.markdown('<p style="font-family:Space Mono,monospace;font-size:20px;color:#58a6ff">'
                '⚡ Pipeline Control</p>', unsafe_allow_html=True)

    if CLOUD_MODE:
        st.info(f"☁ Cloud mode — pipeline runs on the HF backend at `{API_URL}`")

    col1, col2 = st.columns([1,2])
    with col1:
        st.markdown("##### Run pipeline")
        st.markdown("Uses ~6 Serper API credits. Takes 20–40 seconds.")
        if st.button("🚀 Run Now", type="primary", use_container_width=True):
            with st.spinner("Running pipeline…"):
                ok, output = _run_pipeline()
            if ok: st.success("Pipeline completed!")
            else:  st.error("Pipeline had errors — see output below")
            st.code(output[-3000:], language="text")

        st.markdown("---")
        st.markdown("##### Stats")
        s = _get_stats()
        for k,v in s.items():
            st.markdown(f"`{k}` &nbsp; **{v}**")

    with col2:
        st.markdown("##### Log tail")
        if not CLOUD_MODE and os.path.exists("logs/daily.log"):
            lines = open("logs/daily.log").readlines()
            st.code("".join(lines[-50:]), language="text")
            st.caption(f"Last 50 of {len(lines)} lines")
        elif CLOUD_MODE:
            log_data = _api("/api/actions/logs?lines=50")
            if log_data:
                st.code("\n".join(log_data.get("lines",[])), language="text")
        else:
            st.info("No log file yet — run the pipeline first.")


# ══════════════════════════════════════════════════════════════
#  PAGE 3 — Profile
# ══════════════════════════════════════════════════════════════
elif page == "👤 Profile":
    st.markdown('<p style="font-family:Space Mono,monospace;font-size:20px;color:#58a6ff">'
                '👤 Your Profile</p>', unsafe_allow_html=True)

    if CLOUD_MODE:
        st.info("☁ Cloud mode — profile is read from Streamlit secrets. "
                "Update values in Settings → Secrets to change them.")
    else:
        st.markdown("Edit profile below. Changes save to `.env` permanently.")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        name    = st.text_input("Full Name",  value=USER_NAME)
        email   = st.text_input("Email",      value=USER_EMAIL)
        college = st.text_input("College",    value=USER_COLLEGE)
        branch  = st.text_input("Branch",     value=USER_BRANCH)
        year    = st.text_input("Year",       value=USER_YEAR)
    with col2:
        skills_str = st.text_area("Skills (one per line)",
                                   value="\n".join(USER_SKILLS), height=120)
        github   = st.text_input("GitHub URL",   value=USER_GITHUB)
        linkedin = st.text_input("LinkedIn URL",  value=USER_LINKEDIN)

    if not CLOUD_MODE:
        st.markdown("---")
        if st.button("💾 Save to .env", type="primary"):
            skills_list = [s.strip() for s in skills_str.splitlines() if s.strip()]
            env_lines = [
                f"USER_NAME={name}", f"USER_EMAIL={email}",
                f"USER_COLLEGE={college}", f"USER_BRANCH={branch}",
                f"USER_YEAR={year}", f"USER_SKILLS={','.join(skills_list)}",
                f"USER_GITHUB={github}", f"USER_LINKEDIN={linkedin}",
                f"USER_RESUME_PATH=assets/resume.pdf",
                f"SERPER_API_KEY={os.getenv('SERPER_API_KEY','')}",
                f"GMAIL_USER={os.getenv('GMAIL_USER','')}",
                f"GMAIL_APP_PASS={os.getenv('GMAIL_APP_PASS','')}",
            ]
            with open(".env","w") as f: f.write("\n".join(env_lines)+"\n")
            st.success("✅ Saved — restart dashboard to reload values.")

    # Cold email preview
    st.markdown("---")
    st.markdown("##### Cold email preview")
    p1,p2 = st.columns(2)
    with p1: preview_co   = st.text_input("Company", value="Google DeepMind")
    with p2: preview_role = st.text_input("Role",    value="Machine Learning Intern")

    if preview_co and preview_role:
        try:
            from internhunter.mailer import draft_cold_email
            draft = draft_cold_email(
                {"role": preview_role, "company": preview_co},
                {"name":name,"email":email,"college":college,"branch":branch,
                 "year":year,"skills":[s.strip() for s in skills_str.splitlines() if s.strip()],
                 "github":github,"linkedin":linkedin}
            )
            st.markdown(f"**Subject:** `{draft['subject']}`")
            st.text_area("Email body", value=draft["text"], height=220)
            st.download_button("⬇ Download .txt",
                data=f"Subject: {draft['subject']}\n\n{draft['text']}",
                file_name=f"cold_email_{preview_co.lower().replace(' ','_')}.txt")
        except ImportError:
            st.warning("Cold email preview requires local mode with full package installed.")