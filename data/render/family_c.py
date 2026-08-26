"""Family C: held-out, detail-first templates with value-over-label summaries."""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas

from data.render.content import DocumentContent
from data.render.layout import (
    MARGIN,
    PAGE_HEIGHT,
    PAGE_WIDTH,
    draw_paragraph,
    draw_table,
    fit_text,
    footer,
)

PLUM = HexColor("#542C5D")
GOLD = HexColor("#C8902F")
CREAM = HexColor("#FFF8E8")
MIST = HexColor("#F4EEF6")
INK = HexColor("#2E2430")


def render(canvas: Canvas, content: DocumentContent) -> None:
    _detail_page(canvas, content)
    canvas.showPage()
    _summary_page(canvas, content)


def _detail_page(canvas: Canvas, content: DocumentContent) -> None:
    _page_header(canvas, content, "DETAIL SCHEDULE", page=1)
    y = PAGE_HEIGHT - 1.65 * inch
    canvas.setFillColor(INK)
    canvas.setFont("Times-Bold", 13)
    canvas.drawString(MARGIN, y, "Supporting detail")
    y -= 18
    canvas.setFont("Times-Roman", 8)
    canvas.setFillColor(PLUM)
    canvas.drawString(MARGIN, y, "SUMMARY FOLLOWS ON PAGE 2")
    y -= 24

    if content.table_rows:
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
            header_background=PLUM,
            body_font="Times-Roman",
            header_font="Times-Bold",
            font_size=7,
            grid_color=GOLD,
            alternating=CREAM,
        )

    if content.details:
        canvas.setFillColor(GOLD)
        canvas.setFont("Times-Bold", 8)
        canvas.drawString(MARGIN, y - 20, "SUPPORTING VALUES")
        y -= 38
        for field in content.details:
            canvas.setFillColor(INK)
            canvas.setFont("Times-Bold", 9)
            canvas.drawString(MARGIN, y, field.value)
            canvas.setFillColor(PLUM)
            canvas.setFont("Times-Roman", 6.5)
            canvas.drawString(MARGIN, y - 10, field.label.upper())
            y -= 28

    if content.notes:
        canvas.setFillColor(GOLD)
        canvas.setFont("Times-Bold", 8)
        canvas.drawString(MARGIN, y - 6, "DISCLOSURES AND NOTES")
        y -= 22
        for note in content.notes:
            y = draw_paragraph(
                canvas,
                f"* {note}",
                x=MARGIN,
                top=y,
                width=PAGE_WIDTH - (2 * MARGIN),
                font="Times-Roman",
                size=8,
                leading=11,
                color=INK,
            ) - 5
    footer(canvas, 1, color=PLUM, font="Times-Roman")


def _summary_page(canvas: Canvas, content: DocumentContent) -> None:
    _page_header(canvas, content, "ACCOUNT SUMMARY", page=2)
    box_x = MARGIN
    box_top = PAGE_HEIGHT - 1.55 * inch
    box_width = PAGE_WIDTH - (2 * MARGIN)
    canvas.setFillColor(CREAM)
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(1.5)
    canvas.roundRect(box_x, box_top - 0.65 * inch, box_width, 0.65 * inch, 8, fill=1, stroke=1)
    canvas.setFillColor(PLUM)
    canvas.setFont("Times-Bold", 17)
    canvas.drawString(box_x + 16, box_top - 25, content.account_id)
    canvas.setFont("Times-Roman", 8)
    canvas.drawString(box_x + 16, box_top - 40, "ACCOUNT REFERENCE")
    canvas.setFont("Times-Bold", 10)
    canvas.drawRightString(box_x + box_width - 16, box_top - 25, content.issuer)
    canvas.setFont("Times-Roman", 7)
    canvas.drawRightString(box_x + box_width - 16, box_top - 40, "DOCUMENT ISSUER")

    y = box_top - 0.98 * inch
    gap = 14
    width = (box_width - gap) / 2
    row_height = 58
    for index in range(0, len(content.summary), 2):
        row = content.summary[index : index + 2]
        for column, field in enumerate(row):
            x = box_x + column * (width + gap)
            canvas.setFillColor(MIST if index % 4 == 0 else colors.white)
            canvas.setStrokeColor(HexColor("#DCCEE0"))
            canvas.roundRect(x, y - 42, width, 48, 5, fill=1, stroke=1)
            canvas.setFillColor(INK)
            canvas.setFont("Times-Bold", 12)
            canvas.drawString(
                x + 10,
                y - 12,
                fit_text(field.value, "Times-Bold", 12, width - 20),
            )
            canvas.setFillColor(PLUM)
            canvas.setFont("Times-Roman", 6.5)
            canvas.drawString(
                x + 10,
                y - 28,
                fit_text(field.label, "Times-Roman", 6.5, width - 20),
            )
        y -= row_height

    canvas.setFillColor(INK)
    canvas.setFont("Times-Roman", 7)
    canvas.drawString(MARGIN, 53, "* Values are summarized from the detail schedule on page 1.")
    footer(canvas, 2, color=PLUM, font="Times-Roman")


def _page_header(canvas: Canvas, content: DocumentContent, eyebrow: str, *, page: int) -> None:
    canvas.setFillColor(PLUM)
    canvas.rect(0, PAGE_HEIGHT - 1.05 * inch, PAGE_WIDTH, 1.05 * inch, stroke=0, fill=1)
    canvas.setFillColor(GOLD)
    canvas.rect(0, PAGE_HEIGHT - 1.12 * inch, PAGE_WIDTH, 0.07 * inch, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Times-Roman", 7)
    canvas.drawString(MARGIN, PAGE_HEIGHT - 0.34 * inch, eyebrow)
    canvas.setFont("Times-Bold", 17)
    canvas.drawString(MARGIN, PAGE_HEIGHT - 0.70 * inch, content.title)
    canvas.setFont("Times-Roman", 8)
    canvas.drawRightString(PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 0.34 * inch, f"{page} / 2")
