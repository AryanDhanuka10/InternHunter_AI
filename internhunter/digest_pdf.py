"""
digest_pdf.py — Export the daily digest as a clean PDF using ReportLab.

Usage:
    from internhunter.digest_pdf import build_digest_pdf, attach_pdf_to_email
    path = build_digest_pdf(opportunities, stats=get_stats())

NOTE: ReportLab's built-in fonts (Helvetica, Times) do not include the
rupee symbol (Rs.). We use "Rs." throughout instead.
"""
import os, re, logging
from datetime import datetime
from reportlab.lib.pagesizes   import A4
from reportlab.lib.units        import cm
from reportlab.lib              import colors
from reportlab.lib.styles       import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums        import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus         import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)

logger = logging.getLogger(__name__)

# ── Brand colours ─────────────────────────────────────────────
BLUE   = colors.HexColor("#1a73e8")
DBLUE  = colors.HexColor("#0d47a1")
GREEN  = colors.HexColor("#1a7f37")
AMBER  = colors.HexColor("#b76e00")
GREY   = colors.HexColor("#666666")
LGREY  = colors.HexColor("#f1f3f4")
WHITE  = colors.white
BLACK  = colors.HexColor("#1a1a1a")

W, H   = A4
MARGIN = 1.8 * cm


# ── Style helpers ─────────────────────────────────────────────

def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("PDFTitle",
            fontName="Helvetica-Bold", fontSize=20, textColor=WHITE,
            leading=24, spaceAfter=0, alignment=TA_LEFT),
        "subtitle": ParagraphStyle("PDFSub",
            fontName="Helvetica", fontSize=11, textColor=colors.HexColor("#cce0ff"),
            leading=14, spaceAfter=0, alignment=TA_LEFT),
        "section": ParagraphStyle("PDFSection",
            fontName="Helvetica-Bold", fontSize=10, textColor=GREY,
            spaceBefore=14, spaceAfter=6, leading=12,
            textTransform="uppercase"),
        "cell_title": ParagraphStyle("CellTitle",
            fontName="Helvetica-Bold", fontSize=9, textColor=BLACK, leading=12),
        "cell_body": ParagraphStyle("CellBody",
            fontName="Helvetica", fontSize=8, textColor=GREY, leading=11),
        "hint": ParagraphStyle("Hint",
            fontName="Helvetica", fontSize=8, textColor=BLACK,
            leading=12, leftIndent=6),
        "url": ParagraphStyle("URL",
            fontName="Helvetica", fontSize=7, textColor=BLUE,
            leading=10, leftIndent=6),
        "footer": ParagraphStyle("Footer",
            fontName="Helvetica", fontSize=8, textColor=GREY,
            alignment=TA_CENTER),
    }


def _stipend_safe(stipend: str) -> str:
    """Replace rupee symbol with 'Rs.' for ReportLab compatibility."""
    if not stipend or stipend == "Not mentioned":
        return "-"
    return stipend.replace("₹", "Rs.").replace("/month", "/mo")


def _stipend_color(stipend: str) -> colors.Color:
    if not stipend or stipend == "Not mentioned":
        return GREY
    m = re.search(r"\d+", stipend.replace(",", ""))
    if not m:
        return GREY
    n = int(m.group())
    return GREEN if n >= 15000 else AMBER


def _safe(v: str, fallback: str = "-") -> str:
    s = (v or "").strip()
    return s if s and s != "Not mentioned" else fallback


def _page_header_footer(canvas, doc):
    """Draw running header and footer on every page."""
    canvas.saveState()
    # Footer line
    canvas.setStrokeColor(colors.HexColor("#e0e0e0"))
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 1.2*cm, W - MARGIN, 1.2*cm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(GREY)
    canvas.drawString(MARGIN, 0.7*cm, "InternHunter AI  ·  auto-generated")
    canvas.drawRightString(W - MARGIN, 0.7*cm,
        f"Page {doc.page}  ·  {datetime.now().strftime('%d %b %Y')}")
    canvas.restoreState()


# ── Public API ────────────────────────────────────────────────

def build_digest_pdf(
    opportunities: list[dict],
    stats: dict = None,
    referral_hints: list[dict] = None,
    out_dir: str = "data/digest",
) -> str:
    """
    Build a PDF digest and save to out_dir/YYYY-MM-DD.pdf.
    Returns the saved file path.
    """
    os.makedirs(out_dir, exist_ok=True)
    date_slug = datetime.now().strftime("%Y-%m-%d")
    out_path  = os.path.join(out_dir, f"{date_slug}.pdf")

    doc = SimpleDocTemplate(
        out_path, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN,  bottomMargin=2*cm,
    )

    S     = _styles()
    story = []

    # ── Cover header block ────────────────────────────────────
    story.append(_header_block(S, len(opportunities)))

    # ── Stats row ─────────────────────────────────────────────
    if stats:
        story.append(Spacer(1, 0.4*cm))
        story.append(_stats_table(stats))

    # ── Opportunities table ───────────────────────────────────
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("INTERNSHIP OPPORTUNITIES", S["section"]))
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor("#e0e0e0"), spaceAfter=6))

    if opportunities:
        story.append(_opportunities_table(opportunities, S))
    else:
        story.append(Paragraph("No new opportunities found today.", S["cell_body"]))

    # ── Referral section ──────────────────────────────────────
    if referral_hints:
        story.append(Spacer(1, 0.6*cm))
        story.append(Paragraph("REFERRAL FINDER", S["section"]))
        story.append(HRFlowable(width="100%", thickness=0.5,
                                 color=colors.HexColor("#e0e0e0"), spaceAfter=6))
        story.append(_referral_table(referral_hints, S))

    doc.build(story, onFirstPage=_page_header_footer,
                     onLaterPages=_page_header_footer)
    logger.info(f"PDF saved → {out_path}")
    return out_path


# ── Building blocks ───────────────────────────────────────────

def _header_block(S, count: int):
    """Blue gradient header box."""
    date_str = datetime.now().strftime("%A, %d %b %Y")
    data = [[
        Paragraph("InternHunter AI · Daily Digest", S["title"]),
        Paragraph(f"{date_str}  ·  {count} opportunit{'y' if count==1 else 'ies'}",
                  S["subtitle"]),
    ]]
    t = Table(data, colWidths=[W - 2*MARGIN])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), BLUE),
        ("TOPPADDING",    (0,0), (-1,-1), 14),
        ("BOTTOMPADDING", (0,0), (-1,-1), 14),
        ("LEFTPADDING",   (0,0), (-1,-1), 16),
        ("RIGHTPADDING",  (0,0), (-1,-1), 16),
        ("ROUNDEDCORNERS",(0,0), (-1,-1), [6,6,6,6]),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    return t


def _stats_table(stats: dict):
    """4-column stats summary row."""
    keys    = ["total", "new", "applied", "with_stipend"]
    labels  = ["Total Found", "New Today", "Applied", "With Stipend"]
    colours = [BLUE, GREEN, AMBER, colors.HexColor("#6f42c1")]

    cells = []
    for key, label, colour in zip(keys, labels, colours):
        val = stats.get(key, 0)
        cells.append([
            Paragraph(f'<font color="#{colour.hexval()[2:]}" size="18"><b>{val}</b></font>', 
                      ParagraphStyle("SN", fontName="Helvetica-Bold",
                                     fontSize=18, alignment=TA_CENTER, leading=22)),
            Paragraph(label, ParagraphStyle("SL", fontName="Helvetica",
                                             fontSize=8, textColor=GREY,
                                             alignment=TA_CENTER, leading=10)),
        ])

    col_w = (W - 2*MARGIN) / 4
    t = Table([[c[0] for c in cells], [c[1] for c in cells]],
              colWidths=[col_w]*4)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), LGREY),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
        ("ROUNDEDCORNERS",(0,0), (-1,-1), [6,6,6,6]),
    ]))
    return t


def _opportunities_table(opportunities: list[dict], S):
    """Main opportunities table — one row per listing."""
    col_w = W - 2*MARGIN
    COL   = [col_w*0.40, col_w*0.16, col_w*0.18, col_w*0.16, col_w*0.10]

    # Header
    hstyle = ParagraphStyle("TH", fontName="Helvetica-Bold",
                             fontSize=8, textColor=WHITE, leading=10)
    headers = [Paragraph(h, hstyle) for h in
               ["Opportunity", "Stipend", "Deadline", "Location", "Source"]]

    rows = [headers]
    for opp in opportunities:
        title    = _safe(opp.get("title"), "Untitled")[:80]
        role     = _safe(opp.get("role"))
        stipend  = _stipend_safe(opp.get("stipend",""))
        deadline = _safe(opp.get("deadline"))
        location = _safe(opp.get("location"))
        source   = (opp.get("source","other")
                    .replace(".com","").replace(".co.in","")
                    .replace("/jobs","").title())

        stip_col = _stipend_color(opp.get("stipend",""))

        title_para = Paragraph(
            f'<b>{title}</b><br/><font size="7" color="#666666">{role}</font>',
            S["cell_title"]
        )
        stip_para = Paragraph(
            f'<font color="#{stip_col.hexval()[2:]}"><b>{stipend}</b></font>',
            S["cell_body"]
        )
        rows.append([
            title_para,
            stip_para,
            Paragraph(deadline, S["cell_body"]),
            Paragraph(location, S["cell_body"]),
            Paragraph(source,   S["cell_body"]),
        ])

    t = Table(rows, colWidths=COL, repeatRows=1)

    # Build row background alternation
    style_cmds = [
        ("BACKGROUND",    (0,0), (-1,0),  BLUE),
        ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,0),  8),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#e0e0e0")),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LGREY]),
    ]
    t.setStyle(TableStyle(style_cmds))
    return t


def _referral_table(hints: list[dict], S):
    """Referral hints table — company / hint / URL."""
    col_w = W - 2*MARGIN
    COL   = [col_w*0.18, col_w*0.44, col_w*0.38]

    hstyle = ParagraphStyle("RTH", fontName="Helvetica-Bold",
                             fontSize=8, textColor=WHITE, leading=10)
    headers = [Paragraph(h, hstyle) for h in ["Company", "Hint", "Alumni Search URL"]]
    rows    = [headers]

    for h in hints:
        company   = h.get("company","")
        hint_text = h.get("hint","")
        url       = h.get("linkedin_people","")
        rows.append([
            Paragraph(f"<b>{company}</b>", S["cell_title"]),
            Paragraph(hint_text,            S["hint"]),
            Paragraph(url[:65],             S["url"]),
        ])

    t = Table(rows, colWidths=COL, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  DBLUE),
        ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#e0e0e0")),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LGREY]),
    ]))
    return t


# ── Email attachment helper ───────────────────────────────────

def attach_pdf_to_email(msg, pdf_path: str) -> bool:
    """
    Attach a PDF file to an existing MIMEMultipart email message.
    Returns True if attached, False if file not found.
    """
    from email.mime.base import MIMEBase
    from email           import encoders

    if not pdf_path or not os.path.exists(pdf_path):
        logger.warning(f"PDF not found at {pdf_path} — skipping attachment")
        return False

    with open(pdf_path, "rb") as f:
        part = MIMEBase("application", "pdf")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    filename = os.path.basename(pdf_path)
    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
    msg.attach(part)
    logger.info(f"Attached PDF: {filename}")
    return True
