"""Deterministic document classifier and field extractor."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pymupdf

from app.extraction.classifier import classify_document
from app.extraction.models import (
    BoundingBox,
    DocumentType,
    ExtractedField,
    ExtractionResult,
    FieldName,
)
from app.extraction.normalizers import (
    normalize_date,
    normalize_money,
    normalize_rate,
    normalize_text,
)
from app.extraction.proximity import ProximityMatch, find_date_column, find_near_label

ParserKind = Literal["money", "rate", "date", "text", "dates"]


@dataclass(frozen=True)
class FieldRule:
    field_name: FieldName
    aliases: tuple[str, ...]
    parser: ParserKind


FIELD_RULES: dict[DocumentType, tuple[FieldRule, ...]] = {
    "OLD_SERVICER_STATEMENT": (
        FieldRule("principal_balance", ("Current Principal Balance", "Unpaid Principal"), "money"),
        FieldRule("interest_rate", ("Annual Interest Rate", "Note Rate"), "rate"),
        FieldRule("monthly_payment", ("Total Monthly Payment", "Payment Amount"), "money"),
        FieldRule("escrow_balance", ("Escrow Account Balance", "Escrow Balance"), "money"),
    ),
    "NEW_SERVICER_STATEMENT": (
        FieldRule("principal_balance", ("Current Principal Balance", "Unpaid Principal"), "money"),
        FieldRule("interest_rate", ("Annual Interest Rate", "Note Rate"), "rate"),
        FieldRule("monthly_payment", ("Total Monthly Payment", "Payment Amount"), "money"),
        FieldRule("escrow_balance", ("Escrow Account Balance", "Escrow Balance"), "money"),
    ),
    "TRANSFER_NOTICE": (
        FieldRule("old_servicer_name", ("Current Servicer", "Transferor"), "text"),
        FieldRule("new_servicer_name", ("New Servicer", "Transferee"), "text"),
        FieldRule("transfer_date", ("Effective Transfer Date", "Service Change Date"), "date"),
    ),
    "ESCROW_ANALYSIS": (
        FieldRule(
            "projected_annual_tax",
            ("Projected Annual Property Tax", "Est. Tax - 12 Mo."),
            "money",
        ),
        FieldRule(
            "projected_annual_insurance",
            ("Projected Annual Insurance", "Est. Hazard Ins. - 12 Mo."),
            "money",
        ),
        FieldRule("stated_shortage", ("Stated Escrow Shortage", "Aggregate Shortage"), "money"),
    ),
    "PROPERTY_TAX_BILL": (
        FieldRule("tax_authority", ("Taxing Authority", "Levying Body"), "text"),
        FieldRule("annual_tax_amount", ("Annual Amount Due", "Total Tax Levy"), "money"),
        FieldRule("due_dates", ("Due Date",), "dates"),
    ),
}

PARSERS = {
    "money": normalize_money,
    "rate": normalize_rate,
    "date": normalize_date,
    "text": normalize_text,
}


def extract_document(path: str | Path) -> ExtractionResult:
    with pymupdf.open(path) as document:
        text = "\n".join(page.get_text("text", sort=True) for page in document)
        classification = classify_document(text)
        fields = [
            extracted
            for rule in FIELD_RULES[classification.document_type]
            if (extracted := _extract_rule(document, rule)) is not None
        ]
    return ExtractionResult(
        document_type=classification.document_type,
        classification_confidence=classification.confidence,
        fields=fields,
    )


def _extract_rule(document: pymupdf.Document, rule: FieldRule) -> ExtractedField | None:
    if rule.parser == "dates":
        result = find_date_column(document, rule.aliases, normalize_date)
    else:
        result = find_near_label(document, rule.aliases, PARSERS[rule.parser])
    if result is None:
        return None
    value, match = result
    return _field(rule.field_name, value, match)


def _field(field_name: FieldName, value: Any, match: ProximityMatch) -> ExtractedField:
    rectangle = match.rectangle
    return ExtractedField(
        field_name=field_name,
        value=value,
        page=match.page,
        bounding_box=BoundingBox(
            x0=rectangle.x0,
            y0=rectangle.y0,
            x1=rectangle.x1,
            y1=rectangle.y1,
        ),
        confidence=match.confidence,
        source_text=match.text,
    )
