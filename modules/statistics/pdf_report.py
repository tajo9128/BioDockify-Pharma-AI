"""
Statistics PDF Report Generator for BioDockify AI

Produces publication-quality PDF reports of statistical analysis results
with a BioDockify Pharma AI letterhead. Designed for regulatory submissions,
thesis appendices, and research documentation.

Features:
  - BioDockify letterhead on every page (DNA-helix motif + brand colors)
  - Results rendered as formatted tables
  - Methodology + interpretation sections
  - Optional embedded matplotlib charts
  - Page numbering + footer with compliance notice
  - GLP/GCP/FDA/EMA-friendly layout

Dependencies: reportlab (already in requirements), matplotlib (optional charts)
This is an ADD-ON module — no Agent Zero core files touched.
"""

from __future__ import annotations

import io
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm, cm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, Image as RLImage, KeepTogether,
    )
    from reportlab.pdfgen import canvas
    from reportlab.graphics.shapes import Drawing, Line, Circle, String
    from reportlab.graphics import renderPDF
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logging.getLogger(__name__).warning("reportlab not installed — PDF report generation disabled")

logger = logging.getLogger(__name__)

# BioDockify brand palette (matches the favicon / webui theme)
BRAND_DARK = colors.HexColor("#0a1628")     # deep navy (favicon bg)
BRAND_PRIMARY = colors.HexColor("#6C3483")  # purple (primary accent)
BRAND_ACCENT = colors.HexColor("#1ABC9C")   # teal (DNA helix)
BRAND_LIGHT = colors.HexColor("#F4F6F8")    # light panel
BRAND_TEXT = colors.HexColor("#1B2631")     # body text
BRAND_MUTED = colors.HexColor("#7F8C8D")    # muted text
BRAND_TABLE_HEADER = colors.HexColor("#2C3E50")
BRAND_TABLE_ALT = colors.HexColor("#ECF0F1")


def _draw_helix_motif(c: canvas.Canvas, x: float, y: float, height: float = 8 * mm):
    """Draw a small DNA-double-helix motif (matches favicon concept)."""
    w = height * 0.5
    steps = 6
    c.saveState()
    c.setStrokeColor(BRAND_ACCENT)
    c.setLineWidth(0.8)
    for i in range(steps + 1):
        t = i / steps
        py = y + t * height
        # two sinusoidal backbones crossing
        offset = (t * 3.14) % 3.14
        x1 = x + (w * 0.5) + (w * 0.4) * _cos(offset)
        x2 = x + (w * 0.5) - (w * 0.4) * _cos(offset)
        c.line(x1, py, x2, py)  # rung (base pair)
    # backbones
    c.setStrokeColor(BRAND_PRIMARY)
    points1, points2 = [], []
    for i in range(steps * 4 + 1):
        t = i / (steps * 4)
        py = y + t * height
        offset = (t * 3.14 * steps * 0.5) % 3.14
        points1.append((x + (w * 0.5) + (w * 0.4) * _cos(offset), py))
        points2.append((x + (w * 0.5) - (w * 0.4) * _cos(offset), py))
    p1 = c.beginPath()
    p1.moveTo(*points1[0])
    for pt in points1[1:]:
        p1.lineTo(*pt)
    c.drawPath(p1, stroke=1, fill=0)
    p2 = c.beginPath()
    p2.moveTo(*points2[0])
    for pt in points2[1:]:
        p2.lineTo(*pt)
    c.drawPath(p2, stroke=1, fill=0)
    c.restoreState()


def _cos(x: float) -> float:
    import math
    return math.cos(x)


# Page width for letterhead layout
PAGE_W, PAGE_H = A4


def _letterhead_and_footer(canv: canvas.Canvas, doc):
    """Draw the BioDockify letterhead (header) and footer on every page."""
    canv.saveState()

    # ---------- HEADER / LETTERHEAD ----------
    # Top color band
    canv.setFillColor(BRAND_DARK)
    canv.rect(0, PAGE_H - 24 * mm, PAGE_W, 24 * mm, fill=1, stroke=0)
    # Accent stripe under the band
    canv.setFillColor(BRAND_PRIMARY)
    canv.rect(0, PAGE_H - 25 * mm, PAGE_W, 1 * mm, fill=1, stroke=0)

    # DNA helix motif (left)
    _draw_helix_motif(canv, 15 * mm, PAGE_H - 17 * mm, height=9 * mm)

    # Brand name + tagline
    canv.setFillColor(colors.white)
    canv.setFont("Helvetica-Bold", 16)
    canv.drawString(30 * mm, PAGE_H - 13 * mm, "BioDockify Pharma AI")
    canv.setFont("Helvetica", 8)
    canv.setFillColor(colors.HexColor("#BDC3C7"))
    canv.drawString(30 * mm, PAGE_H - 18 * mm, "Pharmaceutical Research & Statistical Analysis")

    # Right side: report meta
    canv.setFont("Helvetica", 7)
    canv.setFillColor(colors.HexColor("#BDC3C7"))
    canv.drawRightString(PAGE_W - 15 * mm, PAGE_H - 13 * mm, "Statistical Analysis Report")
    canv.drawRightString(PAGE_W - 15 * mm, PAGE_H - 17 * mm,
                         datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))

    # ---------- FOOTER ----------
    canv.setStrokeColor(BRAND_MUTED)
    canv.setLineWidth(0.4)
    canv.line(15 * mm, 15 * mm, PAGE_W - 15 * mm, 15 * mm)
    canv.setFillColor(BRAND_MUTED)
    canv.setFont("Helvetica", 7)
    canv.drawString(15 * mm, 11 * mm,
                    "BioDockify Pharma AI  |  GLP/GCP/FDA/EMA-compliant statistical reporting")
    canv.drawRightString(PAGE_W - 15 * mm, 11 * mm, f"Page {doc.page}")
    canv.drawCentredString(PAGE_W / 2, 7 * mm,
                           "Generated by BioDockify AI — verify before regulatory submission")

    canv.restoreState()


def _build_styles() -> Dict[str, ParagraphStyle]:
    """Return paragraph styles for the report."""
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "BioTitle", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=16, textColor=BRAND_DARK, spaceAfter=4, alignment=TA_LEFT,
        ),
        "subtitle": ParagraphStyle(
            "BioSubtitle", parent=base["Normal"], fontName="Helvetica",
            fontSize=9, textColor=BRAND_MUTED, spaceAfter=12,
        ),
        "h2": ParagraphStyle(
            "BioH2", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=12, textColor=BRAND_PRIMARY, spaceBefore=12, spaceAfter=4,
        ),
        "h3": ParagraphStyle(
            "BioH3", parent=base["Heading3"], fontName="Helvetica-Bold",
            fontSize=10, textColor=BRAND_DARK, spaceBefore=8, spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "BioBody", parent=base["Normal"], fontName="Helvetica",
            fontSize=9.5, textColor=BRAND_TEXT, leading=14, spaceAfter=4,
        ),
        "interp": ParagraphStyle(
            "BioInterp", parent=base["Normal"], fontName="Helvetica-Oblique",
            fontSize=9, textColor=BRAND_DARK, leading=13, spaceAfter=6,
            leftIndent=8, borderColor=BRAND_ACCENT, borderWidth=0,
            backColor=BRAND_LIGHT, borderPadding=4,
        ),
        "meta": ParagraphStyle(
            "BioMeta", parent=base["Normal"], fontName="Helvetica",
            fontSize=8, textColor=BRAND_MUTED,
        ),
    }
    return styles


def _flatten(value: Any) -> str:
    """Render any value (incl. lists/dicts/None) as a compact string for cells."""
    if value is None:
        return "—"
    if isinstance(value, float):
        if abs(value) < 0.0001 and value != 0:
            return f"{value:.2e}"
        return f"{value:.4f}".rstrip("0").rstrip(".")
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        return "; ".join(f"{k}={_flatten(v)}" for k, v in value.items())
    return str(value)


def _dict_to_table(data: Dict[str, Any], key_col: str = "Field",
                   val_col: str = "Value") -> Table:
    """Render a flat dict as a 2-column key/value table."""
    rows = [[key_col, val_col]]
    for k, v in data.items():
        rows.append([str(k), _flatten(v)])
    t = Table(rows, colWidths=[55 * mm, 115 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_TABLE_HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, 0), "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_TABLE_ALT]),
        ("GRID", (0, 0), (-1, -1), 0.3, BRAND_MUTED),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _records_to_table(records: List[Dict[str, Any]],
                      columns: Optional[List[str]] = None) -> Table:
    """Render a list of dict records as a multi-column data table."""
    if not records:
        return _dict_to_table({"note": "No data rows."})
    if columns is None:
        # preserve insertion order, union of keys
        seen, cols = set(), []
        for r in records:
            for k in r.keys():
                if k not in seen:
                    seen.add(k)
                    cols.append(k)
        columns = cols
    header = [str(c) for c in columns]
    rows = [header]
    for r in records:
        rows.append([_flatten(r.get(c)) for c in columns])
    n_cols = len(columns)
    col_w = (170 * mm) / max(n_cols, 1)
    t = Table(rows, colWidths=[col_w] * n_cols, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_TABLE_HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_TABLE_ALT]),
        ("GRID", (0, 0), (-1, -1), 0.3, BRAND_MUTED),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def generate_statistics_report(
    title: str,
    analysis_type: str,
    results: Union[Dict[str, Any], List[Dict[str, Any]]],
    interpretation: str = "",
    methodology: str = "",
    metadata: Optional[Dict[str, Any]] = None,
    table_records: Optional[List[Dict[str, Any]]] = None,
    table_columns: Optional[List[str]] = None,
    chart_path: Optional[str] = None,
    output_buffer: Optional[io.BytesIO] = None,
) -> io.BytesIO:
    """Generate a BioDockify-letterhead PDF statistics report.

    Parameters
    ----------
    title : report title (e.g. "Bayesian Binomial Test")
    analysis_type : short tag (e.g. "Bayesian", "Survival", "ANOVA")
    results : the analysis result - dict for key/value table, or list of dicts
              for a data table
    interpretation : plain-English interpretation (highlighted box)
    methodology : statistical methodology description
    metadata : extra key/value pairs shown under "Parameters"
    table_records / table_columns : explicit tabular data (overrides results if given)
    chart_path : path to a matplotlib chart image to embed
    output_buffer : if given, write here; otherwise a new BytesIO

    Returns the BytesIO buffer positioned at 0 (ready to serve/download).

    Raises ImportError if reportlab is not installed.
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab is required for PDF report generation. Install with: pip install reportlab")
    buf = output_buffer or io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=32 * mm, bottomMargin=22 * mm,
        title=f"BioDockify — {title}",
        author="BioDockify Pharma AI",
    )
    s = _build_styles()
    story: List = []

    # --- Title block ---
    story.append(Paragraph(title, s["title"]))
    story.append(Paragraph(
        f"Analysis type: <b>{analysis_type}</b>  •  "
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        s["subtitle"],
    ))

    # --- Methodology ---
    if methodology:
        story.append(Paragraph("Methodology", s["h2"]))
        story.append(Paragraph(methodology, s["body"]))

    # --- Parameters / metadata ---
    if metadata:
        story.append(Paragraph("Parameters", s["h2"]))
        story.append(_dict_to_table(metadata))

    # --- Results table ---
    story.append(Paragraph("Results", s["h2"]))
    if table_records is not None:
        story.append(_records_to_table(table_records, table_columns))
    elif isinstance(results, list):
        story.append(_records_to_table(results))
    elif isinstance(results, dict):
        story.append(_dict_to_table(results))

    # --- Optional chart ---
    if chart_path:
        try:
            story.append(Spacer(1, 6))
            img = RLImage(chart_path, width=160 * mm, height=90 * mm,
                          kind="proportional")
            story.append(KeepTogether([Paragraph("Visualization", s["h3"]), img]))
        except Exception as exc:
            logger.warning("Could not embed chart %s: %s", chart_path, exc)

    # --- Interpretation (highlighted) ---
    if interpretation:
        story.append(Spacer(1, 6))
        story.append(Paragraph("Interpretation", s["h2"]))
        story.append(Paragraph(interpretation, s["interp"]))

    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "This report was generated automatically by BioDockify Pharma AI. "
        "Statistical results should be independently verified before use in "
        "regulatory submissions (FDA/EMA/ICH).",
        s["meta"],
    ))

    doc.build(story, onFirstPage=_letterhead_and_footer,
              onLaterPages=_letterhead_and_footer)
    buf.seek(0)
    return buf


__all__ = ["generate_statistics_report"]
