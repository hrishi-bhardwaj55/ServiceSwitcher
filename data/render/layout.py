"""Shared low-level drawing helpers for PDF template families."""

from __future__ import annotations

from collections.abc import Sequence

from reportlab.lib import colors
from reportlab.lib.colors import Color
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, Table, TableStyle

PAGE_WIDTH = 8.5 * inch
PAGE_HEIGHT = 11 * inch
MARGIN = 0.65 * inch
DEFAULT_GRID = colors.HexColor("#CBD5E1")
DEFAULT_ALTERNATING = colors.HexColor("#F8FAFC")


def footer(canvas: Canvas, page: int, *, color: Color, font: str = "Helvetica") -> None:
    canvas.setStrokeColor(color)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 35, PAGE_WIDTH - MARGIN, 35)
    canvas.setFillColor(color)
    canvas.setFont(font, 7)
    canvas.drawString(MARGIN, 23, "SYNTHETIC DEMONSTRATION DOCUMENT - NOT A REAL ACCOUNT")
    canvas.drawRightString(PAGE_WIDTH - MARGIN, 23, f"Page {page}")


def fit_text(value: str, font: str, size: float, width: float) -> str:
    if stringWidth(value, font, size) <= width:
        return value
    suffix = "..."
    candidate = value
    while candidate and stringWidth(f"{candidate}{suffix}", font, size) > width:
        candidate = candidate[:-1]
    return f"{candidate}{suffix}"


def draw_table(
    canvas: Canvas,
    *,
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    x: float,
    top: float,
    widths: Sequence[float],
    header_background: Color,
    body_font: str = "Helvetica",
    header_font: str = "Helvetica-Bold",
    font_size: float = 7,
    grid_color: Color = DEFAULT_GRID,
    alternating: Color = DEFAULT_ALTERNATING,
) -> float:
    data = [list(headers), *[list(row) for row in rows]]
    table = Table(data, colWidths=list(widths), repeatRows=1)
    commands: list[tuple] = [
        ("BACKGROUND", (0, 0), (-1, 0), header_background),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), header_font),
        ("FONTNAME", (0, 1), (-1, -1), body_font),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("LEADING", (0, 0), (-1, -1), font_size + 2),
        ("GRID", (0, 0), (-1, -1), 0.4, grid_color),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for row_index in range(2, len(data), 2):
        commands.append(("BACKGROUND", (0, row_index), (-1, row_index), alternating))
    table.setStyle(TableStyle(commands))
    _, height = table.wrapOn(canvas, sum(widths), PAGE_HEIGHT)
    table.drawOn(canvas, x, top - height)
    return top - height


def draw_paragraph(
    canvas: Canvas,
    text: str,
    *,
    x: float,
    top: float,
    width: float,
    font: str = "Helvetica",
    size: float = 9,
    leading: float = 13,
    color: Color = colors.black,
) -> float:
    style = ParagraphStyle(
        "inline",
        fontName=font,
        fontSize=size,
        leading=leading,
        textColor=color,
        spaceAfter=0,
        spaceBefore=0,
    )
    paragraph = Paragraph(text, style)
    _, height = paragraph.wrap(width, PAGE_HEIGHT)
    paragraph.drawOn(canvas, x, top - height)
    return top - height
