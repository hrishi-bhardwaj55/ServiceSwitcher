"""Family A: clean, modern, single-column document templates."""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas

from data.render.content import DocumentContent, expected_page_count
from data.render.layout import (
    MARGIN,
    PAGE_HEIGHT,
    PAGE_WIDTH,
    draw_paragraph,
    draw_table,
    footer,
)

NAVY = HexColor("#153B5B")
TEAL = HexColor("#008C8C")
PALE = HexColor("#EAF7F6")
MUTED = HexColor("#52606D")


def render(canvas: Canvas, content: DocumentContent) -> None:
    pages = expected_page_count(_family(), content.document_type)
    _header(canvas, content, page=1)
    y = PAGE_HEIGHT - 1.72 * inch
    y = _section(canvas, "LOAN OVERVIEW", y)
    y = _fields(canvas, content.summary, y)
    if content.details:
        y = _section(canvas, "PAYMENT DETAILS", y - 10)
        y = _fields(canvas, content.details, y)
    if pages == 1:
        y = _table_and_notes(canvas, content, y - 10)
    footer(canvas, 1, color=NAVY)

    if pages == 2:
        canvas.showPage()
        _header(canvas, content, page=2)
        y = PAGE_HEIGHT - 1.72 * inch
        y = _table_and_notes(canvas, content, y)
        footer(canvas, 2, color=NAVY)


def _family():
    from data.render.content import TemplateFamily

    return TemplateFamily.A


def _header(canvas: Canvas, content: DocumentContent, *, page: int) -> None:
    canvas.setFillColor(NAVY)
    canvas.rect(0, PAGE_HEIGHT - 1.15 * inch, PAGE_WIDTH, 1.15 * inch, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(MARGIN, PAGE_HEIGHT - 0.42 * inch, content.issuer.upper())
    canvas.setFont("Helvetica-Bold", 20)
    canvas.drawString(MARGIN, PAGE_HEIGHT - 0.82 * inch, content.title)
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(
        PAGE_WIDTH - MARGIN,
        PAGE_HEIGHT - 0.42 * inch,
        f"ACCOUNT {content.account_id}  |  {page}",
    )
    canvas.setFillColor(TEAL)
    canvas.rect(MARGIN, PAGE_HEIGHT - 1.25 * inch, 1.2 * inch, 0.08 * inch, stroke=0, fill=1)


def _section(canvas: Canvas, title: str, y: float) -> float:
    canvas.setFillColor(TEAL)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(MARGIN, y, title)
    canvas.setStrokeColor(PALE)
    canvas.line(MARGIN, y - 5, PAGE_WIDTH - MARGIN, y - 5)
    return y - 20


def _fields(canvas: Canvas, fields, y: float) -> float:
    for field in fields:
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 9)
        canvas.drawString(MARGIN + 8, y, field.label)
        canvas.setFillColor(NAVY)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawRightString(PAGE_WIDTH - MARGIN - 8, y, field.value)
        canvas.setStrokeColor(HexColor("#E5E7EB"))
        canvas.line(MARGIN + 8, y - 7, PAGE_WIDTH - MARGIN - 8, y - 7)
        y -= 24
    return y


def _table_and_notes(canvas: Canvas, content: DocumentContent, y: float) -> float:
    if content.table_rows:
        y = _section(canvas, content.table_title.upper(), y)
        columns = len(content.table_headers)
        available = PAGE_WIDTH - (2 * MARGIN)
        if columns == 5:
            widths = [0.95, 1.55, 1.0, 2.5, 1.2]
        else:
            widths = [available / inch / columns] * columns
        y = draw_table(
            canvas,
            headers=content.table_headers,
            rows=content.table_rows,
            x=MARGIN,
            top=y,
            widths=[value * inch for value in widths],
            header_background=NAVY,
        )
    if content.notes:
        y = _section(canvas, "NOTES", y - 18)
        for note in content.notes:
            y = draw_paragraph(
                canvas,
                f"- {note}",
                x=MARGIN + 8,
                top=y,
                width=PAGE_WIDTH - (2 * MARGIN) - 16,
                size=8,
                leading=11,
                color=MUTED,
            ) - 6
    return y
