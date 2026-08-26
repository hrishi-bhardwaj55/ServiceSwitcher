"""Label-proximity matching over PyMuPDF word coordinates."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import pymupdf


@dataclass(frozen=True)
class TextLine:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    block: int
    line: int

    @property
    def center_y(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass(frozen=True)
class ProximityMatch:
    page: int
    text: str
    rectangle: pymupdf.Rect
    confidence: float


def page_lines(page: pymupdf.Page) -> list[TextLine]:
    grouped: dict[tuple[int, int], list[tuple[Any, ...]]] = {}
    for word in page.get_text("words", sort=True):
        grouped.setdefault((int(word[5]), int(word[6])), []).append(word)
    lines: list[TextLine] = []
    for (block, line), words in grouped.items():
        ordered = sorted(words, key=lambda item: item[0])
        lines.append(
            TextLine(
                text=" ".join(str(word[4]) for word in ordered),
                x0=min(float(word[0]) for word in ordered),
                y0=min(float(word[1]) for word in ordered),
                x1=max(float(word[2]) for word in ordered),
                y1=max(float(word[3]) for word in ordered),
                block=block,
                line=line,
            )
        )
    return sorted(lines, key=lambda item: (item.y0, item.x0))


def find_near_label(
    document: pymupdf.Document,
    aliases: tuple[str, ...],
    parser,
) -> tuple[Any, ProximityMatch] | None:
    candidates: list[tuple[float, Any, ProximityMatch]] = []
    normalized_aliases = {_normalized(alias) for alias in aliases}
    for page_number in range(document.page_count):
        page: pymupdf.Page = document.load_page(page_number)
        lines = page_lines(page)
        labels = [line for line in lines if _normalized(line.text) in normalized_aliases]
        for label in labels:
            for line in lines:
                if line is label:
                    continue
                score = _proximity_score(label, line)
                if score is None:
                    continue
                try:
                    parsed = parser(line.text)
                except (TypeError, ValueError):
                    continue
                match = ProximityMatch(
                    page=page_number + 1,
                    text=line.text,
                    rectangle=pymupdf.Rect(line.x0, line.y0, line.x1, line.y1),
                    confidence=score,
                )
                candidates.append((score, parsed, match))
    if not candidates:
        return None
    _, value, match = max(candidates, key=lambda item: item[0])
    return value, match


def find_date_column(
    document: pymupdf.Document, aliases: tuple[str, ...], parser
) -> tuple[tuple[Any, ...], ProximityMatch] | None:
    normalized_aliases = {_normalized(alias) for alias in aliases}
    for page_number in range(document.page_count):
        page: pymupdf.Page = document.load_page(page_number)
        lines = page_lines(page)
        headers = [line for line in lines if _normalized(line.text) in normalized_aliases]
        for header in headers:
            values: list[Any] = []
            matched_lines: list[TextLine] = []
            for line in lines:
                if not (header.y1 < line.y0 <= header.y1 + 220):
                    continue
                if abs(line.x0 - header.x0) > 18:
                    continue
                try:
                    values.append(parser(line.text))
                    matched_lines.append(line)
                except (TypeError, ValueError):
                    continue
            if values:
                rectangle = pymupdf.Rect(
                    min(line.x0 for line in matched_lines),
                    min(line.y0 for line in matched_lines),
                    max(line.x1 for line in matched_lines),
                    max(line.y1 for line in matched_lines),
                )
                source = "; ".join(line.text for line in matched_lines)
                return tuple(values), ProximityMatch(
                    page=page_number + 1,
                    text=source,
                    rectangle=rectangle,
                    confidence=0.94,
                )
    return None


def _proximity_score(label: TextLine, value: TextLine) -> float | None:
    same_row = abs(label.center_y - value.center_y) <= 4
    if same_row and value.x0 >= label.x1 + 8:
        distance_penalty = min((value.x0 - label.x1) / 5000, 0.04)
        return 0.99 - distance_penalty

    vertical_gap = value.y0 - label.y1
    aligned = abs(value.x0 - label.x0) <= 22
    if aligned and -1 <= vertical_gap <= 12:
        return 0.96 - min(max(vertical_gap, 0) / 500, 0.02)
    return None


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
