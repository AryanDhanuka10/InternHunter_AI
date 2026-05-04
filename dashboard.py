"""
dashboard.py — InternHunter AI Streamlit frontend.

KEY FEATURES:
  - No max stipend filter (removed)
  - Unmark applied button
  - Stipend + deadline visible on every card (from stored data)
  - Domain-filtered results only
  - Pipeline password-protected
  - Public digest page (read-only, share this with others)
"""
import os, sys, json, re
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

API_URL           = os.getenv("API_URL","").rstrip("/")
CLOUD_MODE        = bool(API_URL)
PIPELINE_PASSWORD = os.getenv("PIPELINE_PASSWORD","internhunter2026")

if not CLOUD_MODE:
    from internhunter.database import (
        init_db, get_stats, get_new_opportunities,
        get_top_opportunities, mark_applied, unmark_applied,
        get_conn, get_opportunities_filtered,
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
.stat-card{background:#161b22;border:1px solid #21262d;border-radius:10px;padding:16px;text-align:center}
.stat-num{font-family:'Space Mono',monospace;font-size:28px;font-weight:700;margin:0;line-height:1}
.stat-label{font-size:11px;color:#8b949e;text-transform:uppercase;letter-spacing:1px;margin-top:5px}
.num-blue{color:#58a6ff}.num-green{color:#3fb950}.num-purple{color:#d2a8ff}.num-orange{color:#ffa657}

/* Opportunity card */
.opp-card{background:#161b22;border:1px solid #21262d;border-radius:10px;
          padding:14px 18px;margin-bottom:8px;transition:border-color .2s}
.opp-card:hover{border-color:#58a6ff}
.opp-card.applied{border-color:#238636;background:#0d2818}
.opp-card.expired{border-color:#6e3e3e;background:#1a0e0e}
.opp-title{font-weight:600;font-size:14px;color:#e6edf3;margin-bottom:4px;
           white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.opp-role{font-size:11px;color:#8b949e;margin-bottom:8px}

/* Field rows inside card */
.fields-row{display:flex;gap:16px;flex-wrap:wrap;margin-top:6px}
.field-block{display:flex;flex-direction:column;min-width:100px}
.field-lbl{font-size:10px;color:#8b949e;text-transform:uppercase;
           letter-spacing:.6px;margin-bottom:2px}
.field-val{font-size:12px;color:#e6edf3;font-weight:500}
.field-val.green{color:#3fb950}.field-val.amber{color:#ffa657}
.field-val.purple{color:#d2a8ff}.field-val.grey{color:#8b949e}

/* Badges */
.badge{display:inline-block;padding:2px 8px;border-radius:12px;
       font-size:10px;font-weight:600;margin-right:4px}
.bi{background:#0d6efd22;color:#58a6ff;border:1px solid #0d6efd44}
.bu{background:#6f42c122;color:#d2a8ff;border:1px solid #6f42c144}
.bl{background:#0a66c222;color:#58a6ff;border:1px solid #0a66c244}
.bg{background:#23863622;color:#3fb950;border:1px solid #23863644}
.bo{background:#21262d;color:#8b949e;border:1px solid #30363d}
.bintl{background:#7b2ff722;color:#d2a8ff;border:1px solid #7b2ff744}
.bapplied{background:#23863622;color:#3fb950;border:1px solid #23863644}
.bexpired{background:#c5221f22;color:#ff6b6b;border:1px solid #c5221f44}
.bscore{background:#1f6feb22;color:#58a6ff;border:1px solid #1f6feb44;font-family:monospace}

.filter-tip{background:#1f6feb11;border-left:3px solid #1f6feb;
            padding:8px 12px;border-radius:0 6px 6px 0;
            font-size:12px;color:#8b949e;margin-bottom:12px}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────

def _api(path, method="GET", **kw):
    try:
        r = getattr(_req, method.lower())(f"{API_URL}{path}", timeout=15, **kw)
        r.raise_for_status(); return r.json()
    except Exception as e:
        st.error(f"API error: {e}"); return None

def _get_stats():
    if CLOUD_MODE: return _api("/api/actions/stats") or {}
    init_db(); return get_stats()

def _safe(v, fb="—"):
    s = (v or "").strip()
    return s if s and s != "Not mentioned" else fb

def _stipend_val(s):
    if not s or s=="Not mentioned": return 0
    m = re.search(r"\d+", str(s).replace(",",""))
    return int(m.group()) if m else 0

def _stipend_class(s):
    v = _stipend_val(s)
    if v == 0: return "grey"
    if v >= 83000: return "purple"   # international USD
    if v >= 15000: return "green"
    return "amber"

def _badge(source, is_intl=False):
    if is_intl: return '<span class="badge bintl">🌍 Remote</span>'
    cls = {"internshala.com":"bi","unstop.com":"bu","linkedin.com":"bl",
           "wellfound.com":"bg","naukri.com":"bo","hirist.tech":"bo",
           "foundit.in":"bo","cutshort.io":"bg"}.get(source,"bo")
    label = (source.replace(".com","").replace(".co.in","")
             .replace("/jobs","").title())[:12]
    return f'<span class="badge {cls}">{label}</span>'

def _do_mark_applied(opp_id):
    if CLOUD_MODE:
        _api(f"/api/opportunities/{opp_id}/apply","POST",
             json={"method":"company_site"})
    else:
        mark_applied(opp_id, method="company_site")

def _do_unmark(opp_id):
    if CLOUD_MODE:
        _api(f"/api/opportunities/{opp_id}/unmark","POST")
    else:
        unmark_applied(opp_id)


# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🚀 InternHunter AI")
    st.caption("☁ Cloud" if CLOUD_MODE else "💻 Local")
    st.markdown("---")
    page = st.radio("Navigate", [
        "📋 Opportunities",
        "✅ Applied",
        "📄 Digest",
        "⚡ Pipeline",
        "👤 Profile",
    ], label_visibility="collapsed")
    st.markdown("---")
    stats = _get_stats()
    st.markdown(
        f"**{stats.get('total',0)}** total  ·  **{stats.get('new',0)}** new\n\n"
        f"**{stats.get('applied',0)}** applied  ·  "
        f"**{stats.get('with_stipend',0)}** with stipend"
    )
    st.markdown("---")
    st.caption("Auto-runs 9:30 AM IST · GitHub Actions")


# ══════════════════════════════════════════════════════════════
#  PAGE 1 — Opportunities
# ══════════════════════════════════════════════════════════════

def _opp_card_html(opp, show_unmark=False):
    title    = _safe(opp.get("title",""), "Untitled")
    role     = _safe(opp.get("role",""), "")
    stipend  = _safe(opp.get("stipend",""))
    duration = _safe(opp.get("duration",""))
    deadline = _safe(opp.get("deadline",""))
    location = _safe(opp.get("location",""))
    source   = opp.get("source","other")
    is_intl  = bool(opp.get("is_international"))
    status   = opp.get("status","new")
    score    = opp.get("score",0)
    expired  = bool(opp.get("expired"))
    link     = opp.get("apply_link") or opp.get("link","#")

    card_cls = "opp-card applied" if status=="applied" else (
               "opp-card expired" if expired else "opp-card")

    stip_cls = _stipend_class(opp.get("stipend",""))

    badges = _badge(source, is_intl)
    if status == "applied": badges += '<span class="badge bapplied">✓ Applied</span>'
    if expired:             badges += '<span class="badge bexpired">⚠ Expired</span>'
    badges += f'<span class="badge bscore">⭐{score}</span>'

    # Truncate title for display
    display_title = title[:80] + ("…" if len(title) > 80 else "")

    return f"""
    <div class="{card_cls}">
      <div class="opp-title">{display_title}</div>
      <div class="opp-role">{role}</div>
      <div style="margin-bottom:8px">{badges}</div>
      <div class="fields-row">
        <div class="field-block">
          <span class="field-lbl">Stipend</span>
          <span class="field-val {stip_cls}">{stipend}</span>
        </div>
        <div class="field-block">
          <span class="field-lbl">Duration</span>
          <span class="field-val">{duration}</span>
        </div>
        <div class="field-block">
          <span class="field-lbl">Deadline</span>
          <span class="field-val" style="{'color:#ff6b6b' if expired else ''}">{deadline}</span>
        </div>
        <div class="field-block">
          <span class="field-lbl">Location</span>
          <span class="field-val">{location[:35]}</span>
        </div>
      </div>
    </div>"""


if page == "📋 Opportunities":

    st.markdown("""<div style='background:#161b22;border:1px solid #21262d;
        border-radius:12px;padding:16px 22px;margin-bottom:16px'>
        <p style='font-family:Space Mono,monospace;font-size:18px;
        color:#58a6ff;margin:0'>🚀 InternHunter AI</p>
        <p style='font-size:12px;color:#8b949e;margin:3px 0 0'>
        Internship finder · ML, Data Science, Backend, AI domains only
        </p></div>""", unsafe_allow_html=True)

    # Stats
    c1,c2,c3,c4 = st.columns(4)
    for col,val,lbl,cls in [
        (c1,stats.get("total",0),"Total Found","num-blue"),
        (c2,stats.get("new",0),"New Today","num-green"),
        (c3,stats.get("applied",0),"Applied","num-purple"),
        (c4,stats.get("with_stipend",0),"With Stipend","num-orange"),
    ]:
        col.markdown(
            f'<div class="stat-card"><p class="stat-num {cls}">{val}</p>'
            f'<p class="stat-label">{lbl}</p></div>',
            unsafe_allow_html=True)

    st.markdown("")

    # ── Filters ───────────────────────────────────────────────
    st.markdown('<div class="filter-tip">ℹ️ Filters search your <b>stored database</b> — '
                'results come from your last pipeline run. '
                'Run pipeline to get today\'s fresh listings.</div>',
                unsafe_allow_html=True)

    with st.expander("🔍 Filters", expanded=True):
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            f_role = st.text_input("Role contains",
                placeholder="machine learning, backend, NLP…")
        with fc2:
            f_loc = st.text_input("Location",
                placeholder="remote, bangalore, delhi…")
        with fc3:
            f_min_stip = st.number_input("Min stipend ₹/month",
                min_value=0, step=5000, value=0)

        fc4, fc5, fc6 = st.columns(3)
        with fc4:
            f_intl = st.checkbox("🌍 International remote only")
        with fc5:
            f_show_expired = st.checkbox("Show expired listings")
        with fc6:
            f_show_all = st.checkbox("Show all (incl. notified)", value=True)

        sort_by = st.selectbox("Sort by",
            ["⭐ Score (best first)","📅 Newest first","💰 Stipend high→low"])

    # Load data
    if CLOUD_MODE:
        params = {"limit":100,"all":str(f_show_all).lower()}
        if f_role:     params["role"]        = f_role
        if f_loc:      params["location"]    = f_loc
        if f_min_stip: params["min_stipend"] = f_min_stip
        opps = _api("/api/opportunities/", params=params) or []
    else:
        init_db()
        opps = get_opportunities_filtered(
            role=f_role, location=f_loc, min_stipend=f_min_stip,
            show_expired=f_show_expired, international_only=f_intl,
            limit=100)
        if not f_show_all:
            opps = [o for o in opps if not o.get("notified")]

    # Sort
    if "Score"   in sort_by: opps.sort(key=lambda x: x.get("score",0), reverse=True)
    elif "Newest" in sort_by: opps.sort(key=lambda x: x.get("id",0), reverse=True)
    elif "Stipend" in sort_by: opps.sort(key=lambda x: _stipend_val(x.get("stipend","")), reverse=True)

    st.markdown(f'<p style="font-size:11px;color:#8b949e;text-transform:uppercase;'
                f'letter-spacing:1px;margin:12px 0 8px">'
                f'{len(opps)} opportunities</p>', unsafe_allow_html=True)

    if not opps:
        st.info("No results. Try relaxing filters or run the pipeline for fresh listings.")
    else:
        for opp in opps:
            opp_id = opp.get("id")
            status = opp.get("status","new")
            link   = opp.get("apply_link") or opp.get("link","#")

            col_card, col_btns = st.columns([5, 1])
            with col_card:
                st.markdown(_opp_card_html(opp), unsafe_allow_html=True)
            with col_btns:
                st.markdown("<div style='margin-top:12px'>", unsafe_allow_html=True)
                st.link_button("↗ Open", link, use_container_width=True)
                if status != "applied":
                    if st.button("✓ Apply", key=f"ap_{opp_id}",
                                 use_container_width=True, type="primary"):
                        _do_mark_applied(opp_id)
                        st.rerun()
                else:
                    if st.button("↩ Unmark", key=f"un_{opp_id}",
                                 use_container_width=True):
                        _do_unmark(opp_id)
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  PAGE 2 — Applied Tracker
# ══════════════════════════════════════════════════════════════

elif page == "✅ Applied":
    st.markdown('<p style="font-family:Space Mono,monospace;font-size:18px;'
                'color:#58a6ff">✅ Applied Internships</p>', unsafe_allow_html=True)
    st.markdown("All internships you have marked as applied. Click ↩ Unmark to move back to New.")
    st.markdown("---")

    if CLOUD_MODE:
        applied_opps = _api("/api/opportunities/?status=applied&limit=50") or []
    else:
        init_db()
        with get_conn() as conn:
            conn.row_factory = sqlite3.Row
            applied_opps = [dict(r) for r in conn.execute(
                "SELECT * FROM opportunities WHERE status='applied' ORDER BY id DESC"
            ).fetchall()]

    if not applied_opps:
        st.info("No applied internships yet. Go to Opportunities and mark some as applied.")
    else:
        st.markdown(f"**{len(applied_opps)}** applications tracked")
        for opp in applied_opps:
            opp_id = opp.get("id")
            link   = opp.get("apply_link") or opp.get("link","#")
            col_card, col_btns = st.columns([5,1])
            with col_card:
                st.markdown(_opp_card_html(opp, show_unmark=True), unsafe_allow_html=True)
            with col_btns:
                st.markdown("<div style='margin-top:12px'>", unsafe_allow_html=True)
                st.link_button("↗ Open", link, use_container_width=True)
                if st.button("↩ Unmark", key=f"unapply_{opp_id}",
                             use_container_width=True):
                    _do_unmark(opp_id)
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  PAGE 3 — Public Digest (share this with anyone)
# ══════════════════════════════════════════════════════════════

elif page == "📄 Digest":
    st.markdown('<p style="font-family:Space Mono,monospace;font-size:18px;'
                'color:#58a6ff">📄 Daily Digest</p>', unsafe_allow_html=True)

    st.success(
        "🔗 **Share this page!** Anyone with your Streamlit app URL can browse "
        "today's internships here — no login needed, no pipeline triggered, "
        "zero API credits used."
    )

    from datetime import datetime
    st.markdown(f"**Last updated:** {datetime.now().strftime('%d %b %Y')}")
    st.markdown("---")

    # Load top scored listings
    if CLOUD_MODE:
        opps = _api("/api/opportunities/?all=true&limit=30") or []
        opps.sort(key=lambda x: x.get("score",0), reverse=True)
    else:
        init_db()
        with get_conn() as conn:
            conn.row_factory = sqlite3.Row
            opps = [dict(r) for r in conn.execute(
                "SELECT * FROM opportunities WHERE (expired=0 OR expired IS NULL) "
                "ORDER BY score DESC, id DESC LIMIT 30"
            ).fetchall()]

    if not opps:
        st.info("No opportunities yet. Run the pipeline to populate.")
    else:
        # Download PDF button
        digest_dir = "data/digest"
        if os.path.isdir(digest_dir):
            pdfs = sorted([f for f in os.listdir(digest_dir) if f.endswith(".pdf")],
                          reverse=True)
            if pdfs:
                with open(os.path.join(digest_dir, pdfs[0]), "rb") as f:
                    st.download_button(
                        "⬇ Download PDF Digest",
                        data=f.read(),
                        file_name=pdfs[0],
                        mime="application/pdf",
                        type="primary",
                    )
                st.caption(f"Latest digest: {pdfs[0]}")

        st.markdown(f"### Today's Top {len(opps)} Internships")

        for i, opp in enumerate(opps, 1):
            title    = _safe(opp.get("title",""), "Untitled")
            stipend  = _safe(opp.get("stipend",""))
            duration = _safe(opp.get("duration",""))
            deadline = _safe(opp.get("deadline",""))
            location = _safe(opp.get("location",""))
            source   = opp.get("source","other")
            is_intl  = bool(opp.get("is_international"))
            link     = opp.get("apply_link") or opp.get("link","#")
            stip_cls = _stipend_class(opp.get("stipend",""))

            col_n, col_info, col_btn = st.columns([0.4, 5, 1])
            with col_n:
                st.markdown(f"<p style='font-size:22px;font-weight:700;color:#8b949e;"
                            f"margin-top:12px;text-align:right'>{i}</p>",
                            unsafe_allow_html=True)
            with col_info:
                st.markdown(f"""<div class="opp-card">
                  <div class="opp-title">{title[:80]}</div>
                  <div style="margin-bottom:6px">{_badge(source, is_intl)}</div>
                  <div class="fields-row">
                    <div class="field-block">
                      <span class="field-lbl">Stipend</span>
                      <span class="field-val {stip_cls}">{stipend}</span>
                    </div>
                    <div class="field-block">
                      <span class="field-lbl">Duration</span>
                      <span class="field-val">{duration}</span>
                    </div>
                    <div class="field-block">
                      <span class="field-lbl">Deadline</span>
                      <span class="field-val">{deadline}</span>
                    </div>
                    <div class="field-block">
                      <span class="field-lbl">Location</span>
                      <span class="field-val">{location[:35]}</span>
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)
            with col_btn:
                st.markdown("<div style='margin-top:14px'>", unsafe_allow_html=True)
                st.link_button("Apply →", link, use_container_width=True, type="primary")
                st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  PAGE 4 — Pipeline (password gated)
# ══════════════════════════════════════════════════════════════

elif page == "⚡ Pipeline":
    st.markdown('<p style="font-family:Space Mono,monospace;font-size:18px;'
                'color:#58a6ff">⚡ Pipeline Control</p>', unsafe_allow_html=True)
    st.warning(
        "🔒 **Your eyes only.** Each run uses ~14 Serper API credits. "
        "GitHub Actions runs this automatically at 9:30 AM IST daily."
    )

    pwd = st.text_input("Pipeline password", type="password")
    if pwd and pwd != PIPELINE_PASSWORD:
        st.error("Incorrect password")
        st.stop()

    if pwd == PIPELINE_PASSWORD:
        st.success("✅ Authenticated")
        col1, col2 = st.columns([1,2])
        with col1:
            if st.button("🚀 Run Pipeline Now", type="primary", use_container_width=True):
                with st.spinner("Running… (~40 seconds)"):
                    if CLOUD_MODE:
                        result = _api("/api/actions/run-pipeline?async_run=true", method="POST")
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
                if ok:
                    st.success("Pipeline executed successfully!")
                else:
                    st.error("Pipeline failed. Check the logs below.")
                # Display the actual output
                st.code(output[-4000:], language="text")
            st.markdown("---")
            s = _get_stats()
            for k,v in s.items():
                st.markdown(f"`{k}` **{v}**")
        with col2:
            st.markdown("##### Log")
            if not CLOUD_MODE and os.path.exists("logs/daily.log"):
                lines = open("logs/daily.log").readlines()
                st.code("".join(lines[-60:]), language="text")
            elif CLOUD_MODE:
                ld = _api("/api/actions/logs?lines=60")
                if ld: st.code("\n".join(ld.get("lines",[])), language="text")
            else:
                st.info("No log yet.")
    else:
        st.info("Enter password to unlock pipeline controls.")


# ══════════════════════════════════════════════════════════════
#  PAGE 5 — Profile
# ══════════════════════════════════════════════════════════════

elif page == "👤 Profile":
    st.markdown('<p style="font-family:Space Mono,monospace;font-size:18px;'
                'color:#58a6ff">👤 Your Profile</p>', unsafe_allow_html=True)
    if CLOUD_MODE:
        st.info("Cloud mode — edit values in Streamlit secrets to change profile.")

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
        github   = st.text_input("GitHub",   value=USER_GITHUB)
        linkedin = st.text_input("LinkedIn", value=USER_LINKEDIN)

    if not CLOUD_MODE:
        st.markdown("---")
        if st.button("💾 Save to .env", type="primary"):
            skills_list = [s.strip() for s in skills_str.splitlines() if s.strip()]
            lines = [
                f"USER_NAME={name}", f"USER_EMAIL={email}",
                f"USER_COLLEGE={college}", f"USER_BRANCH={branch}",
                f"USER_YEAR={year}",
                f"USER_SKILLS={','.join(skills_list)}",
                f"USER_GITHUB={github}", f"USER_LINKEDIN={linkedin}",
                f"USER_RESUME_PATH=assets/resume.pdf",
                f"SERPER_API_KEY={os.getenv('SERPER_API_KEY','')}",
                f"GMAIL_USER={os.getenv('GMAIL_USER','')}",
                f"GMAIL_APP_PASS={os.getenv('GMAIL_APP_PASS','')}",
                f"PIPELINE_PASSWORD={os.getenv('PIPELINE_PASSWORD','internhunter2026')}",
            ]
            with open(".env","w") as f: f.write("\n".join(lines)+"\n")
            st.success("✅ Saved — restart dashboard to reload values.")

    st.markdown("---")
    st.markdown("##### Cold email preview")
    p1,p2 = st.columns(2)
    with p1: pco   = st.text_input("Company", value="Google DeepMind")
    with p2: prole = st.text_input("Role",    value="Machine Learning Intern")
    if pco and prole:
        try:
            from internhunter.mailer import draft_cold_email
            d = draft_cold_email(
                {"role":prole,"company":pco},
                {"name":name,"email":email,"college":college,"branch":branch,
                 "year":year,
                 "skills":[s.strip() for s in skills_str.splitlines() if s.strip()],
                 "github":github,"linkedin":linkedin}
            )
            st.markdown(f"**Subject:** `{d['subject']}`")
            st.text_area("Body", value=d["text"], height=200)
            st.download_button("⬇ Download .txt",
                data=f"Subject: {d['subject']}\n\n{d['text']}",
                file_name=f"cold_{pco.lower().replace(' ','_')}.txt")
        except ImportError:
            st.warning("Cold email preview available in local mode only.")