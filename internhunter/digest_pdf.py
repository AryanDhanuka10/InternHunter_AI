"""
digest_pdf.py — Professional card-style PDF digest using ReportLab.
Each opportunity gets its own card with all fields clearly labelled.
"""
import os, re, logging
from datetime import datetime
from reportlab.lib.pagesizes   import A4
from reportlab.lib.units        import cm
from reportlab.lib              import colors
from reportlab.lib.styles       import ParagraphStyle
from reportlab.lib.enums        import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus         import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)

logger = logging.getLogger(__name__)

# ── Brand palette ─────────────────────────────────────────────
BLUE    = colors.HexColor("#1a73e8")
DBLUE   = colors.HexColor("#0d47a1")
LBLUE   = colors.HexColor("#e8f0fe")
GREEN   = colors.HexColor("#1e8e3e")
LGREEN  = colors.HexColor("#e6f4ea")
AMBER   = colors.HexColor("#b06000")
LAMBER  = colors.HexColor("#fef3e2")
PURPLE  = colors.HexColor("#7b2ff7")
LPURPLE = colors.HexColor("#f3e8ff")
GREY    = colors.HexColor("#5f6368")
LGREY   = colors.HexColor("#f8f9fa")
MGREY   = colors.HexColor("#dadce0")
DGREY   = colors.HexColor("#3c4043")
WHITE   = colors.white
BLACK   = colors.HexColor("#202124")
RED     = colors.HexColor("#c5221f")

W, H   = A4
MARGIN = 1.6 * cm
TW     = W - 2 * MARGIN


# ── Styles ────────────────────────────────────────────────────

def _P(name, **kw) -> ParagraphStyle:
    return ParagraphStyle(name, **kw)

def _styles():
    return {
        # Header block
        "hdr_title":  _P("HT", fontName="Helvetica-Bold", fontSize=22,
                          textColor=WHITE, leading=26),
        "hdr_sub":    _P("HS", fontName="Helvetica", fontSize=11,
                          textColor=colors.HexColor("#bdd7ff"), leading=15),
        # Section dividers
        "section":    _P("SEC", fontName="Helvetica-Bold", fontSize=10,
                          textColor=GREY, leading=13, spaceBefore=14, spaceAfter=3,
                          letterSpacing=1.0),
        # Card — opportunity title
        "card_title": _P("CT", fontName="Helvetica-Bold", fontSize=11,
                          textColor=DBLUE, leading=14),
        "card_role":  _P("CR", fontName="Helvetica", fontSize=8.5,
                          textColor=GREY, leading=11),
        # Field label inside card
        "field_lbl":  _P("FL", fontName="Helvetica-Bold", fontSize=7.5,
                          textColor=GREY, leading=10, letterSpacing=0.5),
        # Field value — neutral
        "field_val":  _P("FV", fontName="Helvetica", fontSize=8.5,
                          textColor=DGREY, leading=11),
        # Stipend coloured
        "stip_green": _P("SG", fontName="Helvetica-Bold", fontSize=9,
                          textColor=GREEN, leading=12),
        "stip_amber": _P("SA", fontName="Helvetica-Bold", fontSize=9,
                          textColor=AMBER, leading=12),
        "stip_intl":  _P("SI", fontName="Helvetica-Bold", fontSize=9,
                          textColor=PURPLE, leading=12),
        "stip_none":  _P("SN2", fontName="Helvetica", fontSize=8.5,
                          textColor=GREY, leading=11),
        # Source badge text
        "source":     _P("SRC", fontName="Helvetica-Bold", fontSize=7.5,
                          textColor=BLUE, leading=10),
        # Link
        "link":       _P("LNK", fontName="Helvetica", fontSize=7.5,
                          textColor=BLUE, leading=10),
        # Referral
        "ref_co":     _P("RC", fontName="Helvetica-Bold", fontSize=9,
                          textColor=DGREY, leading=12),
        "ref_hint":   _P("RH", fontName="Helvetica", fontSize=8,
                          textColor=DGREY, leading=11),
        "ref_url":    _P("RU", fontName="Helvetica", fontSize=7.5,
                          textColor=BLUE, leading=10),
        # Stats
        "stat_num":   _P("STN", fontName="Helvetica-Bold", fontSize=22,
                          leading=26, alignment=TA_CENTER),
        "stat_lbl":   _P("STL", fontName="Helvetica", fontSize=8,
                          textColor=GREY, leading=10, alignment=TA_CENTER),
        # Footer
        "footer":     _P("FT", fontName="Helvetica", fontSize=7.5,
                          textColor=GREY, alignment=TA_CENTER),
    }


# ── Helpers ───────────────────────────────────────────────────

def _rupee(s: str) -> str:
    """Replace ₹ with Rs. — ReportLab built-in fonts lack rupee glyph."""
    if not s or s == "Not mentioned": return "-"
    return s.replace("₹","Rs.").replace("/month","/mo")


def _stip_style(s: str, styles: dict) -> ParagraphStyle:
    if not s or s == "Not mentioned": return styles["stip_none"]
    m = re.search(r"\d+", s.replace(",",""))
    if not m: return styles["stip_none"]
    n = int(m.group())
    if n >= 83000: return styles["stip_intl"]
    if n >= 15000: return styles["stip_green"]
    return styles["stip_amber"]


def _safe(v, fb="-") -> str:
    s = (v or "").strip()
    return s if s and s != "Not mentioned" else fb


def _src_label(source: str, is_intl: bool) -> str:
    if is_intl: return "Intl Remote"
    label = (source.replace(".com","").replace(".co.in","")
             .replace("/jobs","").replace("."," ").title())
    return label[:16]


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(MGREY)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN, 1.4*cm, W-MARGIN, 1.4*cm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GREY)
    canvas.drawString(MARGIN, 0.85*cm, "InternHunter AI  ·  auto-generated daily digest")
    canvas.drawRightString(W-MARGIN, 0.85*cm,
        f"Page {doc.page}  ·  {datetime.now().strftime('%d %b %Y')}")
    canvas.restoreState()


# ── Card builder ──────────────────────────────────────────────

def _opp_card(opp: dict, idx: int, S: dict):
    """
    Build one opportunity as a self-contained card (KeepTogether).
    Layout:
      [#  Title / Role]          [Source badge]
      [Stipend] [Duration] [Deadline] [Location]
      [Apply link]
    """
    title    = _safe(opp.get("title",""), "Untitled")
    role     = _safe(opp.get("role",""), "")
    stipend  = _rupee(opp.get("stipend",""))
    duration = _safe(opp.get("duration",""))
    deadline = _safe(opp.get("deadline",""))
    location = _safe(opp.get("location",""))
    link     = opp.get("apply_link") or opp.get("link","")
    source   = opp.get("source","other")
    is_intl  = bool(opp.get("is_international"))
    score    = opp.get("score", 0)
    expired  = bool(opp.get("expired"))

    stip_style = _stip_style(opp.get("stipend",""), S)
    src_label  = _src_label(source, is_intl)

    # ── Row 1: number + title + source badge ──────────────────
    title_cell = [
        Paragraph(f"<b>{idx}. {title[:80]}</b>", S["card_title"]),
        Paragraph(role[:50], S["card_role"]),
    ]
    badge_bg   = LPURPLE if is_intl else LBLUE
    badge_clr  = PURPLE  if is_intl else BLUE
    badge_cell = Table(
        [[Paragraph(src_label, _P("BL", fontName="Helvetica-Bold",
                                  fontSize=7.5, textColor=badge_clr,
                                  leading=10, alignment=TA_CENTER))]],
        colWidths=[2.8*cm]
    )
    badge_cell.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), badge_bg),
        ("TOPPADDING",    (0,0),(-1,-1), 3),
        ("BOTTOMPADDING", (0,0),(-1,-1), 3),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("RIGHTPADDING",  (0,0),(-1,-1), 6),
        ("ROUNDEDCORNERS",(0,0),(-1,-1), [4,4,4,4]),
    ]))

    row1 = Table(
        [[Table([[p] for p in title_cell], colWidths=[TW-3.2*cm]), badge_cell]],
        colWidths=[TW-3.2*cm, 3.2*cm]
    )
    row1.setStyle(TableStyle([
        ("VALIGN",  (0,0),(-1,-1), "TOP"),
        ("LEFTPADDING",  (0,0),(-1,-1), 0),
        ("RIGHTPADDING", (0,0),(-1,-1), 0),
        ("TOPPADDING",   (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
    ]))

    # ── Row 2: fields grid ────────────────────────────────────
    expired_note = "  [EXPIRED]" if expired else ""
    fields = [
        ("STIPEND",  Paragraph(stipend + ("" if not expired else ""),
                               stip_style)),
        ("DURATION", Paragraph(duration, S["field_val"])),
        ("DEADLINE", Paragraph(
            f'<font color="#c5221f">{deadline}{expired_note}</font>'
            if expired else deadline, S["field_val"])),
        ("LOCATION", Paragraph(location[:40], S["field_val"])),
    ]
    fw = TW / 4
    labels = [Paragraph(lbl, S["field_lbl"]) for lbl, _ in fields]
    values = [val for _, val in fields]

    fields_table = Table(
        [labels, values],
        colWidths=[fw]*4
    )
    fields_table.setStyle(TableStyle([
        ("TOPPADDING",    (0,0),(-1,-1), 3),
        ("BOTTOMPADDING", (0,0),(-1,-1), 3),
        ("LEFTPADDING",   (0,0),(-1,-1), 0),
        ("RIGHTPADDING",  (0,0),(-1,-1), 4),
        ("LINEABOVE",     (0,0),(-1,0),  0.3, MGREY),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
    ]))

    # ── Row 3: score + apply link ─────────────────────────────
    score_clr  = GREEN if score >= 40 else (AMBER if score >= 20 else GREY)
    score_para = Paragraph(
        f'<font color="#{score_clr.hexval()[2:]}">Score {score}</font>',
        _P("SC", fontName="Helvetica", fontSize=7.5, textColor=score_clr, leading=10)
    )
    link_short = (link[:65] + "...") if len(link) > 65 else link
    link_para  = Paragraph(
        f'Apply: <font color="#1a73e8">{link_short}</font>',
        S["link"]
    )
    bottom_row = Table(
        [[score_para, link_para]],
        colWidths=[2*cm, TW-2*cm]
    )
    bottom_row.setStyle(TableStyle([
        ("TOPPADDING",    (0,0),(-1,-1), 2),
        ("BOTTOMPADDING", (0,0),(-1,-1), 0),
        ("LEFTPADDING",   (0,0),(-1,-1), 0),
        ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
    ]))

    # ── Assemble card ─────────────────────────────────────────
    card_bg = LAMBER if expired else (LPURPLE if is_intl else WHITE)
    card_border = AMBER if expired else (PURPLE if is_intl else MGREY)

    card = Table(
        [[row1], [Spacer(1, 0.15*cm)], [fields_table],
         [Spacer(1, 0.1*cm)], [bottom_row]],
        colWidths=[TW]
    )
    card.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), card_bg),
        ("BOX",           (0,0),(-1,-1), 0.8, card_border),
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 10),
        ("LEFTPADDING",   (0,0),(-1,-1), 12),
        ("RIGHTPADDING",  (0,0),(-1,-1), 12),
        ("ROUNDEDCORNERS",(0,0),(-1,-1), [5,5,5,5]),
    ]))
    return KeepTogether([card, Spacer(1, 0.25*cm)])


# ── Public API ────────────────────────────────────────────────

def build_digest_pdf(
    opportunities: list[dict],
    stats: dict = None,
    referral_hints: list[dict] = None,
    out_dir: str = "data/digest",
) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{datetime.now().strftime('%Y-%m-%d')}.pdf")

    doc = SimpleDocTemplate(path, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=1.4*cm, bottomMargin=2*cm)

    S     = _styles()
    story = []

    # ── Cover header ──────────────────────────────────────────
    date_str = datetime.now().strftime("%A, %d %b %Y")
    n        = len(opportunities)
    hdr = Table([[
        Paragraph("InternHunter AI", S["hdr_title"]),
        Paragraph(f"Daily Digest  ·  {date_str}",   S["hdr_sub"]),
        Paragraph(f"{n} opportunit{'y' if n==1 else 'ies'}", S["hdr_sub"]),
    ]], colWidths=[TW])
    hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), BLUE),
        ("TOPPADDING",    (0,0),(-1,-1), 14),
        ("BOTTOMPADDING", (0,0),(-1,-1), 14),
        ("LEFTPADDING",   (0,0),(-1,-1), 16),
        ("RIGHTPADDING",  (0,0),(-1,-1), 16),
        ("ROUNDEDCORNERS",(0,0),(-1,-1), [6,6,6,6]),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 0.4*cm))

    # ── Stats row ─────────────────────────────────────────────
    if stats:
        keys   = ["total","new","applied","with_stipend"]
        labels = ["Total Found","New Today","Applied","With Stipend"]
        clrs   = [BLUE, GREEN, AMBER, PURPLE]
        cw     = TW / 4
        nums   = [Paragraph(
                    f'<font color="#{c.hexval()[2:]}" size="20"><b>{stats.get(k,0)}</b></font>',
                    S["stat_num"]) for k,c in zip(keys,clrs)]
        lbls   = [Paragraph(l, S["stat_lbl"]) for l in labels]
        st = Table([nums, lbls], colWidths=[cw]*4)
        st.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), LGREY),
            ("TOPPADDING",    (0,0),(-1,-1), 8),
            ("BOTTOMPADDING", (0,0),(-1,-1), 8),
            ("ALIGN",         (0,0),(-1,-1), "CENTER"),
            ("BOX",           (0,0),(-1,-1), 0.5, MGREY),
            ("LINEBELOW",     (0,0),(-1,0),  0.3, MGREY),
        ]))
        story.append(st)
        story.append(Spacer(1, 0.5*cm))

    # ── Opportunity cards ─────────────────────────────────────
    story.append(Paragraph("INTERNSHIP OPPORTUNITIES", S["section"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MGREY, spaceAfter=6))

    if opportunities:
        for i, opp in enumerate(opportunities, 1):
            story.append(_opp_card(opp, i, S))
    else:
        story.append(Paragraph("No new opportunities found today.", S["field_val"]))

    # ── Referral section ──────────────────────────────────────
    if referral_hints:
        story.append(Spacer(1, 0.4*cm))
        story.append(Paragraph("REFERRAL FINDER", S["section"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=MGREY, spaceAfter=6))
        story.append(Paragraph(
            "Search LinkedIn for alumni at these companies and ask for a referral.",
            _P("RI", fontName="Helvetica", fontSize=8, textColor=GREY,
               leading=11, spaceAfter=6)
        ))
        cw = [TW*0.18, TW*0.44, TW*0.38]
        hrow = [Paragraph(h, _P("RH2", fontName="Helvetica-Bold", fontSize=8,
                                 textColor=WHITE, leading=11))
                for h in ["Company","Hint","LinkedIn Alumni URL"]]
        rows = [hrow]
        for h in referral_hints:
            rows.append([
                Paragraph(f"<b>{h.get('company','')}</b>", S["ref_co"]),
                Paragraph(h.get("hint","")[:120],          S["ref_hint"]),
                Paragraph(h.get("linkedin_people","")[:70],S["ref_url"]),
            ])
        rt = Table(rows, colWidths=cw, repeatRows=1)
        rt.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,0),  DBLUE),
            ("TOPPADDING",    (0,0),(-1,-1), 6),
            ("BOTTOMPADDING", (0,0),(-1,-1), 6),
            ("LEFTPADDING",   (0,0),(-1,-1), 6),
            ("RIGHTPADDING",  (0,0),(-1,-1), 6),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ("GRID",          (0,0),(-1,-1), 0.25, MGREY),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LGREY]),
        ]))
        story.append(rt)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    logger.info(f"PDF → {path}  ({os.path.getsize(path):,} bytes)")
    return path


def attach_pdf_to_email(msg, pdf_path: str) -> bool:
    from email.mime.base import MIMEBase
    from email           import encoders
    if not pdf_path or not os.path.exists(pdf_path):
        logger.warning(f"PDF not found: {pdf_path}")
        return False
    with open(pdf_path, "rb") as f:
        part = MIMEBase("application","pdf")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition",
                    f'attachment; filename="{os.path.basename(pdf_path)}"')
    msg.attach(part)
    logger.info(f"PDF attached: {os.path.basename(pdf_path)}")
    return True