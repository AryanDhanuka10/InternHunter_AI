"""
dashboard.py — InternHunter AI Streamlit frontend.

KEY DESIGN DECISIONS:
  - Visitors NEVER trigger the pipeline (credit protection)
  - Pipeline can only be triggered by YOU (password-gated)
  - Filters work against stored DB data — not LinkedIn search
  - Two modes: LOCAL (direct DB) and CLOUD (HF API)
"""
import os, sys, json, re
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

API_URL    = os.getenv("API_URL","").rstrip("/")
CLOUD_MODE = bool(API_URL)

# ── Pipeline password — set in .env or Streamlit secrets ──────
PIPELINE_PASSWORD = os.getenv("PIPELINE_PASSWORD", "internhunter2026")

if not CLOUD_MODE:
    from internhunter.database import (
        init_db, get_stats, get_new_opportunities,
        get_by_stipend, get_by_location, get_by_role,
        get_top_opportunities, mark_applied, get_conn,
        get_opportunities_filtered,
    )
    from internhunter.config import (
        USER_NAME, USER_EMAIL, USER_COLLEGE, USER_BRANCH,
        USER_YEAR, USER_SKILLS, USER_GITHUB, USER_LINKEDIN,
    )
    import sqlite3
else:
    import requests as _req
    USER_NAME     = os.getenv("USER_NAME","")
    USER_EMAIL    = os.getenv("USER_EMAIL","")
    USER_COLLEGE  = os.getenv("USER_COLLEGE","")
    USER_BRANCH   = os.getenv("USER_BRANCH","")
    USER_YEAR     = os.getenv("USER_YEAR","")
    USER_SKILLS   = os.getenv("USER_SKILLS","").split(",")
    USER_GITHUB   = os.getenv("USER_GITHUB","")
    USER_LINKEDIN = os.getenv("USER_LINKEDIN","")


# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="InternHunter AI",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@700&family=DM+Sans:wght@400;500;600&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif}
[data-testid="stSidebar"]{background:#0d1117!important;border-right:1px solid #21262d}
[data-testid="stSidebar"] *{color:#e6edf3!important}
[data-testid="stSidebar"] .stButton button{
    background:#238636!important;color:white!important;border:none!important;
    width:100%;font-weight:600;padding:.6rem;border-radius:6px}
.stat-card{background:#161b22;border:1px solid #21262d;border-radius:10px;padding:16px;text-align:center}
.stat-num{font-family:'Space Mono',monospace;font-size:30px;font-weight:700;margin:0;line-height:1}
.stat-label{font-size:11px;color:#8b949e;text-transform:uppercase;letter-spacing:1px;margin-top:5px}
.num-blue{color:#58a6ff}.num-green{color:#3fb950}.num-purple{color:#d2a8ff}.num-orange{color:#ffa657}
.opp-card{background:#161b22;border:1px solid #21262d;border-radius:10px;padding:14px 18px;margin-bottom:8px}
.opp-title{font-weight:600;font-size:14px;color:#e6edf3;margin-bottom:5px}
.opp-meta{font-size:12px;color:#8b949e}
.badge{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;margin-right:5px}
.bi{background:#0d6efd22;color:#58a6ff;border:1px solid #0d6efd44}
.bu{background:#6f42c122;color:#d2a8ff;border:1px solid #6f42c144}
.bl{background:#0a66c222;color:#58a6ff;border:1px solid #0a66c244}
.bg{background:#23863622;color:#3fb950;border:1px solid #23863644}
.bo{background:#21262d;color:#8b949e;border:1px solid #30363d}
.bintl{background:#6f42c122;color:#d2a8ff;border:1px solid #6f42c144}
.sh{color:#3fb950;font-weight:600}.sm{color:#ffa657;font-weight:600}.sl{color:#8b949e}
.ro{background:#d9534f22;color:#ff6b6b;border-radius:4px;padding:2px 6px;font-size:11px}
.filter-info{background:#1f6feb22;border:1px solid #1f6feb44;border-radius:8px;
    padding:10px 14px;font-size:12px;color:#58a6ff;margin-bottom:12px}
</style>
""", unsafe_allow_html=True)


# ── API helpers ───────────────────────────────────────────────

def _api(path, method="GET", **kw):
    try:
        r = getattr(_req, method.lower())(f"{API_URL}{path}", timeout=15, **kw)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def _get_stats():
    if CLOUD_MODE: return _api("/api/actions/stats") or {}
    init_db(); return get_stats()


def _stipend_val(s):
    if not s or s == "Not mentioned": return 0
    m = re.search(r"\d+", str(s).replace(",",""))
    return int(m.group()) if m else 0

def _safe(v, fb="—"):
    s = (v or "").strip()
    return s if s and s != "Not mentioned" else fb

def _badge(source, is_intl=False):
    if is_intl: return '<span class="badge bintl">🌍 Intl</span>'
    cls = {"internshala.com":"bi","unstop.com":"bu","linkedin.com":"bl",
           "wellfound.com":"bg","naukri.com":"bo","hirist.tech":"bo",
           "foundit.in":"bo","cutshort.io":"bo"}.get(source,"bo")
    label = source.replace(".com","").replace(".co.in","").replace("/jobs","").title()[:12]
    return f'<span class="badge {cls}">{label}</span>'

def _stip_cls(s):
    v = _stipend_val(s)
    if v == 0: return "sl"
    return "sh" if v >= 15000 else "sm"


# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🚀 InternHunter AI")
    mode = "☁ Cloud" if CLOUD_MODE else "💻 Local"
    st.caption(f"{mode} mode")
    st.markdown("---")
    page = st.radio("Navigate",
        ["📋 Opportunities", "⚡ Pipeline", "👤 Profile"],
        label_visibility="collapsed")
    st.markdown("---")
    stats = _get_stats()
    st.markdown(
        f"**{stats.get('total',0)}** total &nbsp;·&nbsp; **{stats.get('new',0)}** new\n\n"
        f"**{stats.get('applied',0)}** applied &nbsp;·&nbsp; "
        f"**{stats.get('with_stipend',0)}** with stipend"
    )
    st.markdown("---")
    st.caption("🔒 Pipeline only runs for you\n\nAuto-runs at 9:30 AM IST daily via GitHub Actions")


# ══════════════════════════════════════════════════════════════
#  PAGE 1 — Opportunities
# ══════════════════════════════════════════════════════════════

if page == "📋 Opportunities":

    st.markdown("""<div style='background:#161b22;border:1px solid #21262d;border-radius:12px;
        padding:18px 22px;margin-bottom:18px'>
        <p style='font-family:Space Mono,monospace;font-size:18px;color:#58a6ff;margin:0'>
        🚀 InternHunter AI</p>
        <p style='font-size:12px;color:#8b949e;margin:3px 0 0'>
        Automated internship discovery · filters work on stored data, not LinkedIn search</p>
        </div>""", unsafe_allow_html=True)

    # Stats row
    c1,c2,c3,c4 = st.columns(4)
    for col,val,label,cls in [
        (c1, stats.get("total",0),       "Total Found",  "num-blue"),
        (c2, stats.get("new",0),          "New Today",    "num-green"),
        (c3, stats.get("applied",0),      "Applied",      "num-purple"),
        (c4, stats.get("with_stipend",0), "With Stipend", "num-orange"),
    ]:
        col.markdown(
            f'<div class="stat-card"><p class="stat-num {cls}">{val}</p>'
            f'<p class="stat-label">{label}</p></div>',
            unsafe_allow_html=True)

    st.markdown("")

    # ── Filter panel ──────────────────────────────────────────
    st.markdown("""<div class="filter-info">
        ℹ️ Filters search your <b>stored database</b> — not LinkedIn directly.
        Run the pipeline first to populate fresh listings, then filter here.
    </div>""", unsafe_allow_html=True)

    with st.expander("🔍 Filters", expanded=True):
        fc1, fc2 = st.columns(2)
        fc3, fc4 = st.columns(2)
        fc5, fc6 = st.columns(2)

        with fc1:
            f_role = st.text_input("Role contains",
                placeholder="e.g. machine learning",
                help="Searches stored role field — not LinkedIn")
        with fc2:
            f_loc = st.text_input("Location contains",
                placeholder="e.g. remote, bangalore",
                help="Searches stored location field")
        with fc3:
            f_min_stip = st.number_input("Min stipend ₹/month",
                min_value=0, step=5000, value=0,
                help="Filters listings where stipend was extracted and >= this amount")
        with fc4:
            f_max_stip = st.number_input("Max stipend ₹/month",
                min_value=0, step=5000, value=0,
                help="0 = no upper limit")
        with fc5:
            f_intl = st.checkbox("International remote only 🌍")
        with fc6:
            f_show_expired = st.checkbox("Include expired listings",
                help="By default expired listings are hidden")

        f_show_all = st.checkbox("Show all (including already-notified)", value=True)
        sort_by = st.selectbox("Sort by",
            ["Score (best first)", "Newest first", "Stipend (high to low)"])

    # ── Load + filter data ────────────────────────────────────
    if CLOUD_MODE:
        params = {"limit":100,"all": str(f_show_all).lower()}
        if f_role:     params["role"]     = f_role
        if f_loc:      params["location"] = f_loc
        if f_min_stip: params["min_stipend"] = f_min_stip
        opps = _api("/api/opportunities/", params=params) or []
    else:
        init_db()
        opps = get_opportunities_filtered(
            role         = f_role,
            location     = f_loc,
            min_stipend  = f_min_stip,
            show_expired = f_show_expired,
            international_only = f_intl,
            limit        = 100,
        )
        # If show_all=False, further restrict to unnotified
        if not f_show_all:
            opps = [o for o in opps if not o.get("notified")]

    # Max stipend filter (Python side — stipend is a string)
    if f_max_stip > 0:
        opps = [o for o in opps
                if _stipend_val(o.get("stipend","")) <= f_max_stip
                or _stipend_val(o.get("stipend","")) == 0]

    # Sort
    if sort_by == "Score (best first)":
        opps.sort(key=lambda x: x.get("score",0), reverse=True)
    elif sort_by == "Newest first":
        opps.sort(key=lambda x: x.get("id",0), reverse=True)
    elif sort_by == "Stipend (high to low)":
        opps.sort(key=lambda x: _stipend_val(x.get("stipend","")), reverse=True)

    # ── Results ───────────────────────────────────────────────
    st.markdown(f"""<p style='font-size:11px;color:#8b949e;text-transform:uppercase;
        letter-spacing:1px;margin:14px 0 8px'>
        Results — {len(opps)} opportunities found</p>""", unsafe_allow_html=True)

    if not opps:
        st.info("No opportunities match your filters. Try relaxing the criteria or run the pipeline to fetch fresh listings.")
    else:
        for opp in opps:
            title    = _safe(opp.get("title",""), "Untitled")
            stipend  = opp.get("stipend","Not mentioned")
            deadline = _safe(opp.get("deadline",""))
            location = _safe(opp.get("location",""))
            duration = _safe(opp.get("duration",""))
            link     = opp.get("apply_link") or opp.get("link","#")
            source   = opp.get("source","other")
            opp_id   = opp.get("id")
            status   = opp.get("status","new")
            score    = opp.get("score",0)
            is_intl  = bool(opp.get("is_international"))
            expired  = bool(opp.get("expired"))

            col_main, col_btn = st.columns([5,1])
            with col_main:
                expired_tag = '<span class="ro">⚠ Expired</span>' if expired else ""
                st.markdown(f"""<div class="opp-card">
                  <div class="opp-title">{title} {expired_tag}</div>
                  <div class="opp-meta">
                    {_badge(source, is_intl)}
                    <span class="{_stip_cls(stipend)}">{_safe(stipend)}</span>
                    {f"&nbsp;·&nbsp; ⏱ {duration}" if duration != "—" else ""}
                    &nbsp;·&nbsp; 📅 {deadline}
                    &nbsp;·&nbsp; 📍 {location}
                    &nbsp;·&nbsp; ⭐ {score}
                    {"&nbsp;·&nbsp; ✅ applied" if status=='applied' else ""}
                  </div></div>""", unsafe_allow_html=True)
            with col_btn:
                st.markdown("<div style='margin-top:10px'>", unsafe_allow_html=True)
                b1, b2 = st.columns(2)
                with b1: st.link_button("↗", link, use_container_width=True)
                with b2:
                    if status != "applied":
                        if st.button("✓", key=f"app_{opp_id}", help="Mark applied"):
                            if CLOUD_MODE:
                                _api(f"/api/opportunities/{opp_id}/apply",
                                     method="POST", json={"method":"company_site"})
                            else:
                                mark_applied(opp_id, method="company_site")
                            st.rerun()
                    else:
                        st.button("✓", key=f"done_{opp_id}", disabled=True)
                st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  PAGE 2 — Pipeline (password-protected)
# ══════════════════════════════════════════════════════════════

elif page == "⚡ Pipeline":

    st.markdown('<p style="font-family:Space Mono,monospace;font-size:18px;'
                'color:#58a6ff">⚡ Pipeline Control</p>', unsafe_allow_html=True)

    # ── Credit protection warning ─────────────────────────────
    st.warning(
        "🔒 **This page is for you only.** Running the pipeline uses ~14 Serper API "
        "credits (10 Indian + 4 international roles). GitHub Actions runs this "
        "automatically every day at 9:30 AM IST — you don't need to run it manually "
        "unless you want fresh data right now."
    )

    # Password gate
    pwd = st.text_input("Enter pipeline password", type="password",
                        placeholder="Set PIPELINE_PASSWORD in .env or Streamlit secrets")

    if pwd and pwd != PIPELINE_PASSWORD:
        st.error("Incorrect password")
        st.stop()

    if pwd == PIPELINE_PASSWORD:
        st.success("✅ Authenticated")

        col1, col2 = st.columns([1,2])
        with col1:
            st.markdown("##### Run pipeline now")
            st.markdown("Uses ~14 Serper API credits. Takes 30–60 seconds.")
            if st.button("🚀 Run Pipeline", type="primary", use_container_width=True):
                with st.spinner("Running pipeline…"):
                    if CLOUD_MODE:
                        result = _api("/api/actions/run-pipeline", method="POST")
                        ok     = result and not result.get("stages_fail")
                        output = json.dumps(result or {}, indent=2)
                    else:
                        import subprocess
                        res    = subprocess.run(
                            [sys.executable,"-m","internhunter.scheduler"],
                            capture_output=True, text=True,
                            cwd=os.path.dirname(__file__))
                        ok     = res.returncode == 0
                        output = res.stdout + res.stderr
                if ok: st.success("Pipeline completed!")
                else:  st.error("Pipeline had errors")
                st.code(output[-4000:], language="text")

            st.markdown("---")
            st.markdown("##### Stats")
            s = _get_stats()
            for k,v in s.items():
                st.markdown(f"`{k}` &nbsp; **{v}**")

        with col2:
            st.markdown("##### Log tail")
            if not CLOUD_MODE and os.path.exists("logs/daily.log"):
                lines = open("logs/daily.log").readlines()
                st.code("".join(lines[-60:]), language="text")
                st.caption(f"Last 60 of {len(lines)} lines")
            elif CLOUD_MODE:
                log_data = _api("/api/actions/logs?lines=60")
                if log_data:
                    st.code("\n".join(log_data.get("lines",[])), language="text")
            else:
                st.info("No log file yet.")
    else:
        st.info("Enter the pipeline password above to unlock controls. "
                "The dashboard (Opportunities tab) works for everyone without a password.")


# ══════════════════════════════════════════════════════════════
#  PAGE 3 — Profile
# ══════════════════════════════════════════════════════════════

elif page == "👤 Profile":

    st.markdown('<p style="font-family:Space Mono,monospace;font-size:18px;'
                'color:#58a6ff">👤 Your Profile</p>', unsafe_allow_html=True)

    if CLOUD_MODE:
        st.info("☁ Cloud mode — update values in Streamlit secrets to change profile.")
    else:
        st.markdown("Changes save permanently to `.env`.")

    st.markdown("---")
    c1,c2 = st.columns(2)
    with c1:
        name    = st.text_input("Full Name",  value=USER_NAME)
        email   = st.text_input("Email",      value=USER_EMAIL)
        college = st.text_input("College",    value=USER_COLLEGE)
        branch  = st.text_input("Branch",     value=USER_BRANCH)
        year    = st.text_input("Year",       value=USER_YEAR)
    with c2:
        skills_str = st.text_area("Skills (one per line)",
            value="\n".join(USER_SKILLS), height=120)
        github   = st.text_input("GitHub URL",   value=USER_GITHUB)
        linkedin = st.text_input("LinkedIn URL", value=USER_LINKEDIN)

    if not CLOUD_MODE:
        st.markdown("---")
        if st.button("💾 Save to .env", type="primary"):
            skills_list = [s.strip() for s in skills_str.splitlines() if s.strip()]
            lines = [
                f"USER_NAME={name}",         f"USER_EMAIL={email}",
                f"USER_COLLEGE={college}",   f"USER_BRANCH={branch}",
                f"USER_YEAR={year}",
                f"USER_SKILLS={','.join(skills_list)}",
                f"USER_GITHUB={github}",     f"USER_LINKEDIN={linkedin}",
                f"USER_RESUME_PATH=assets/resume.pdf",
                f"SERPER_API_KEY={os.getenv('SERPER_API_KEY','')}",
                f"GMAIL_USER={os.getenv('GMAIL_USER','')}",
                f"GMAIL_APP_PASS={os.getenv('GMAIL_APP_PASS','')}",
                f"PIPELINE_PASSWORD={os.getenv('PIPELINE_PASSWORD','internhunter2026')}",
            ]
            with open(".env","w") as f: f.write("\n".join(lines)+"\n")
            st.success("✅ Saved — restart dashboard to reload.")

    st.markdown("---")
    st.markdown("##### Cold email preview")
    p1,p2 = st.columns(2)
    with p1: pco   = st.text_input("Company", value="Google DeepMind")
    with p2: prole = st.text_input("Role",    value="Machine Learning Intern")

    if pco and prole:
        try:
            from internhunter.mailer import draft_cold_email
            draft = draft_cold_email(
                {"role":prole,"company":pco},
                {"name":name,"email":email,"college":college,"branch":branch,
                 "year":year,"skills":[s.strip() for s in skills_str.splitlines() if s.strip()],
                 "github":github,"linkedin":linkedin}
            )
            st.markdown(f"**Subject:** `{draft['subject']}`")
            st.text_area("Body", value=draft["text"], height=220)
            st.download_button("⬇ Download .txt",
                data=f"Subject: {draft['subject']}\n\n{draft['text']}",
                file_name=f"cold_{pco.lower().replace(' ','_')}.txt")
        except ImportError:
            st.warning("Cold email preview available in local mode only.")