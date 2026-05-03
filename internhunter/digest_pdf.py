"""
digest_pdf.py — Clean, well-formatted PDF digest using ReportLab.
Uses Rs. instead of ₹ (ReportLab built-in fonts don't support rupee glyph).
"""
import os, re, logging
from datetime import datetime
from reportlab.lib.pagesizes   import A4
from reportlab.lib.units        import cm
from reportlab.lib              import colors
from reportlab.lib.styles       import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums        import TA_LEFT, TA_CENTER
from reportlab.platypus         import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

logger = logging.getLogger(__name__)

# ── Colours ───────────────────────────────────────────────────
BLUE    = colors.HexColor("#1a73e8")
DBLUE   = colors.HexColor("#0d47a1")
GREEN   = colors.HexColor("#1a7f37")
AMBER   = colors.HexColor("#b76e00")
GREY    = colors.HexColor("#5f6368")
LGREY   = colors.HexColor("#f8f9fa")
MGREY   = colors.HexColor("#e8eaed")
WHITE   = colors.white
BLACK   = colors.HexColor("#202124")
INTL    = colors.HexColor("#6f42c1")   # purple for international

W, H    = A4
MARGIN  = 1.5 * cm
TW      = W - 2 * MARGIN   # table width


def _s():
    """Return style dict."""
    return {
        "h_white":   ParagraphStyle("HW", fontName="Helvetica-Bold",
                                    fontSize=8, textColor=WHITE, leading=11),
        "cell_b":    ParagraphStyle("CB", fontName="Helvetica-Bold",
                                    fontSize=8, textColor=BLACK, leading=11),
        "cell_sm":   ParagraphStyle("CS", fontName="Helvetica",
                                    fontSize=7.5, textColor=GREY, leading=10),
        "cell_role": ParagraphStyle("CR", fontName="Helvetica",
                                    fontSize=7, textColor=GREY, leading=10),
        "green_b":   ParagraphStyle("GB", fontName="Helvetica-Bold",
                                    fontSize=8, textColor=GREEN, leading=11),
        "amber_b":   ParagraphStyle("AB", fontName="Helvetica-Bold",
                                    fontSize=8, textColor=AMBER, leading=11),
        "grey_sm":   ParagraphStyle("GS", fontName="Helvetica",
                                    fontSize=7.5, textColor=GREY, leading=10),
        "url":       ParagraphStyle("URL", fontName="Helvetica",
                                    fontSize=7, textColor=BLUE, leading=10),
        "hint":      ParagraphStyle("HT", fontName="Helvetica",
                                    fontSize=7.5, textColor=BLACK, leading=11),
        "section":   ParagraphStyle("SEC", fontName="Helvetica-Bold",
                                    fontSize=9, textColor=GREY, leading=12,
                                    spaceBefore=12, spaceAfter=4),
        "footer":    ParagraphStyle("FT", fontName="Helvetica",
                                    fontSize=7, textColor=GREY, alignment=TA_CENTER),
        "intl":      ParagraphStyle("IL", fontName="Helvetica-Bold",
                                    fontSize=8, textColor=INTL, leading=11),
    }


def _stipend_safe(s: str) -> str:
    if not s or s == "Not mentioned": return "-"
    return s.replace("₹", "Rs.").replace("/month", "/mo")


def _stipend_style_key(s: str) -> str:
    if not s or s == "Not mentioned": return "grey_sm"
    m = re.search(r"\d+", s.replace(",",""))
    if not m: return "grey_sm"
    n = int(m.group())
    if n >= 83000: return "intl"    # international (USD converted)
    if n >= 15000: return "green_b"
    return "amber_b"


def _safe(v, fb="-"):
    s = (v or "").strip()
    return s if s and s != "Not mentioned" else fb


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(MGREY)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 1.3*cm, W-MARGIN, 1.3*cm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(GREY)
    canvas.drawString(MARGIN, 0.8*cm, "InternHunter AI  ·  auto-generated")
    canvas.drawRightString(W-MARGIN, 0.8*cm,
        f"Page {doc.page}  ·  {datetime.now().strftime('%d %b %Y')}")
    canvas.restoreState()


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
        topMargin=MARGIN, bottomMargin=2*cm)

    S     = _s()
    story = []

    # ── Header ────────────────────────────────────────────────
    story.append(_header(len(opportunities)))
    story.append(Spacer(1, 0.3*cm))

    # ── Stats ─────────────────────────────────────────────────
    if stats:
        story.append(_stats_row(stats, S))
        story.append(Spacer(1, 0.4*cm))

    # ── Opportunities ─────────────────────────────────────────
    story.append(Paragraph("INTERNSHIP OPPORTUNITIES", S["section"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MGREY, spaceAfter=4))

    if opportunities:
        story.append(_opp_table(opportunities, S))
    else:
        story.append(Paragraph("No new opportunities found today.", S["cell_sm"]))

    # ── Referrals ─────────────────────────────────────────────
    if referral_hints:
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph("REFERRAL FINDER", S["section"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=MGREY, spaceAfter=4))
        story.append(_referral_table(referral_hints, S))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    logger.info(f"PDF → {path}")
    return path


# ── Building blocks ───────────────────────────────────────────

def _header(count: int):
    date_str = datetime.now().strftime("%A, %d %b %Y")
    data = [[
        Paragraph(f"<b>InternHunter AI</b>  ·  Daily Digest",
                  ParagraphStyle("HDR", fontName="Helvetica-Bold",
                                 fontSize=16, textColor=WHITE, leading=20)),
        Paragraph(f"{date_str}  ·  {count} opportunit{'y' if count==1 else 'ies'}",
                  ParagraphStyle("HSUB", fontName="Helvetica",
                                 fontSize=10, textColor=colors.HexColor("#cce0ff"),
                                 leading=14, alignment=TA_LEFT)),
    ]]
    t = Table(data, colWidths=[TW])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), BLUE),
        ("TOPPADDING",    (0,0),(-1,-1), 12),
        ("BOTTOMPADDING", (0,0),(-1,-1), 12),
        ("LEFTPADDING",   (0,0),(-1,-1), 14),
        ("RIGHTPADDING",  (0,0),(-1,-1), 14),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    return t


def _stats_row(stats: dict, S):
    keys    = ["total","new","applied","with_stipend"]
    labels  = ["Total","New Today","Applied","With Stipend"]
    clrs    = [BLUE, GREEN, AMBER, INTL]
    col_w   = TW / 4

    num_row, lbl_row = [], []
    for key, label, clr in zip(keys, labels, clrs):
        v = stats.get(key, 0)
        num_row.append(Paragraph(
            f'<font color="#{clr.hexval()[2:]}" size="20"><b>{v}</b></font>',
            ParagraphStyle("SN", fontName="Helvetica-Bold", fontSize=20,
                           alignment=TA_CENTER, leading=24)))
        lbl_row.append(Paragraph(label,
            ParagraphStyle("SL", fontName="Helvetica", fontSize=8,
                           textColor=GREY, alignment=TA_CENTER, leading=10)))

    t = Table([num_row, lbl_row], colWidths=[col_w]*4)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), LGREY),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("LINEBELOW",     (0,0),(-1,0),  0.3, MGREY),
        ("BOX",           (0,0),(-1,-1), 0.5, MGREY),
    ]))
    return t


def _opp_table(opps: list[dict], S):
    # Column widths: Title(35%) Stipend(15%) Duration(12%) Deadline(15%) Location(16%) Source(7%)
    COLS = [TW*0.35, TW*0.15, TW*0.12, TW*0.15, TW*0.16, TW*0.07]

    hdrs = ["Opportunity", "Stipend", "Duration", "Deadline", "Location", "Src"]
    rows = [[Paragraph(h, S["h_white"]) for h in hdrs]]

    for opp in opps:
        title     = _safe(opp.get("title",""), "Untitled")[:70]
        role      = _safe(opp.get("role",""), "")[:40]
        stipend   = _stipend_safe(opp.get("stipend",""))
        duration  = _safe(opp.get("duration",""))
        deadline  = _safe(opp.get("deadline",""))
        location  = _safe(opp.get("location",""))[:35]
        source    = (opp.get("source","other")
                     .replace(".com","").replace(".co.in","")
                     .replace("/jobs","").title())[:8]
        intl      = opp.get("is_international", False)
        stk       = _stipend_style_key(opp.get("stipend",""))

        title_para = Paragraph(
            f'<b>{title}</b><br/>'
            f'<font size="6.5" color="#5f6368">{role}'
            f'{"  🌍" if intl else ""}</font>',
            S["cell_b"]
        )
        rows.append([
            title_para,
            Paragraph(stipend,  S[stk]),
            Paragraph(duration, S["cell_sm"]),
            Paragraph(deadline, S["cell_sm"]),
            Paragraph(location, S["cell_sm"]),
            Paragraph(source,   S["cell_sm"]),
        ])

    t = Table(rows, colWidths=COLS, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  DBLUE),
        ("TEXTCOLOR",     (0,0),(-1,0),  WHITE),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 5),
        ("RIGHTPADDING",  (0,0),(-1,-1), 5),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("GRID",          (0,0),(-1,-1), 0.25, MGREY),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LGREY]),
        ("LINEBELOW",     (0,0),(-1,0),  1,    BLUE),
    ]))
    return t


def _referral_table(hints: list[dict], S):
    COLS = [TW*0.18, TW*0.42, TW*0.40]
    hdrs = ["Company", "Hint", "LinkedIn Alumni URL"]
    rows = [[Paragraph(h, S["h_white"]) for h in hdrs]]

    for h in hints:
        rows.append([
            Paragraph(f"<b>{h.get('company','')}</b>", S["cell_b"]),
            Paragraph(h.get("hint",""),                 S["hint"]),
            Paragraph(h.get("linkedin_people","")[:70], S["url"]),
        ])

    t = Table(rows, colWidths=COLS, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  DBLUE),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 5),
        ("RIGHTPADDING",  (0,0),(-1,-1), 5),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("GRID",          (0,0),(-1,-1), 0.25, MGREY),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LGREY]),
    ]))
    return t


def attach_pdf_to_email(msg, pdf_path: str) -> bool:
    from email.mime.base import MIMEBase
    from email           import encoders
    if not pdf_path or not os.path.exists(pdf_path):
        logger.warning(f"PDF not found: {pdf_path}")
        return False
    with open(pdf_path,"rb") as f:
        part = MIMEBase("application","pdf")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition",
                    f'attachment; filename="{os.path.basename(pdf_path)}"')
    msg.attach(part)
    logger.info(f"PDF attached: {os.path.basename(pdf_path)}")
    return True