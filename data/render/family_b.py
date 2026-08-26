"""Family B: dense legacy, two-column document templates."""

from __future__ import annotations

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

INK = HexColor("#202020")
GRAY = HexColor("#5A5A5A")
LIGHT = HexColor("#E7E4DD")
PAPER = HexColor("#FAF8F1")


def render(canvas: Canvas, content: DocumentContent) -> None:
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, stroke=0, fill=1)
    canvas.setStrokeColor(INK)
    canvas.setLineWidth(1.2)
    canvas.rect(MARGIN - 10, 45, PAGE_WIDTH - (2 * MARGIN) + 20, PAGE_HEIGHT - 85)
    _header(canvas, content)

    fields = [*content.summary, *content.details]
    y = PAGE_HEIGHT - 1.55 * inch
    canvas.setFont("Courier-Bold", 8)
    canvas.setFillColor(INK)
    canvas.drawString(MARGIN, y, "ACCOUNT SNAPSHOT / PAYMENT DATA")
    y -= 14
    y = _two_column_fields(canvas, fields, y)

    if content.table_rows:
        canvas.setFont("Courier-Bold", 8)
        canvas.drawString(MARGIN, y - 7, content.table_title.upper())
        y -= 18
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
            header_background=INK,
            body_font="Courier",
            header_font="Courier-Bold",
            font_size=6.5,
            grid_color=GRAY,
            alternating=LIGHT,
        )

    if content.notes:
        canvas.setFont("Times-Bold", 8)
        canvas.drawString(MARGIN, y - 14, "IMPORTANT ACCOUNT NOTES")
        y -= 26
        for index, note in enumerate(content.notes, 1):
            y = draw_paragraph(
                canvas,
                f"{index}. {note}",
                x=MARGIN,
                top=y,
                width=PAGE_WIDTH - (2 * MARGIN),
                font="Times-Roman",
                size=7.5,
                leading=10,
                color=INK,
            ) - 3
    footer(canvas, 1, color=INK, font="Courier")


def _header(canvas: Canvas, content: DocumentContent) -> None:
    top = PAGE_HEIGHT - 0.92 * inch
    canvas.setFillColor(INK)
    canvas.setFont("Times-Bold", 15)
    canvas.drawString(MARGIN, top, content.title)
    canvas.setFont("Courier", 7.5)
    canvas.drawRightString(PAGE_WIDTH - MARGIN, top, f"REF {content.account_id}")
    canvas.setStrokeColor(INK)
    canvas.setLineWidth(2)
    canvas.line(MARGIN, top - 9, PAGE_WIDTH - MARGIN, top - 9)
    canvas.setFont("Times-Italic", 8)
    canvas.drawString(MARGIN, top - 24, f"Prepared by {content.issuer} - retain for your records")


def _two_column_fields(canvas: Canvas, fields, y: float) -> float:
    gap = 14
    width = (PAGE_WIDTH - (2 * MARGIN) - gap) / 2
    row_height = 32
    for index in range(0, len(fields), 2):
        row = fields[index : index + 2]
        for column, field in enumerate(row):
            x = MARGIN + column * (width + gap)
            canvas.setFillColor(LIGHT)
            canvas.rect(x, y - 22, width, 28, stroke=0, fill=1)
            canvas.setStrokeColor(GRAY)
            canvas.rect(x, y - 22, width, 28, stroke=1, fill=0)
            canvas.setFillColor(GRAY)
            canvas.setFont("Courier", 6.5)
            canvas.drawString(x + 5, y - 2, fit_text(field.label, "Courier", 6.5, width - 10))
            canvas.setFillColor(INK)
            canvas.setFont("Courier-Bold", 8)
            canvas.drawString(x + 5, y - 15, fit_text(field.value, "Courier-Bold", 8, width - 10))
        y -= row_height
    return y
