"""Confidence-gated model fallback and deterministic/LLM cross-checking."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Literal, get_args

import pymupdf
from pydantic import Field, model_validator

from app.extraction.classifier import UnclassifiedDocumentError
from app.extraction.extractor import FIELD_RULES, PARSERS, extract_document
from app.extraction.models import (
    BoundingBox,
    DocumentType,
    ExtractedField,
    FieldName,
)
from app.extraction.normalizers import normalize_date
from app.llm.models import LLMExtractionRequest, LLMFieldCandidate, LLMPage
from app.llm.protocol import LLMClient
from app.schemas.mortgage import CanonicalModel

DEFAULT_CLASSIFICATION_THRESHOLD = 0.80
DEFAULT_FIELD_THRESHOLD = 0.90
ALL_FIELD_NAMES = tuple(get_args(FieldName))
FieldValue = Decimal | date | str | tuple[date, ...]


class FieldAlternative(CanonicalModel):
    source: Literal["DETERMINISTIC", "LLM"]
    value: FieldValue
    page: int = Field(ge=1)
    confidence: float = Field(ge=0, le=1)


class ResolvedField(CanonicalModel):
    field_name: FieldName
    value: FieldValue
    page: int = Field(ge=1)
    bounding_box: BoundingBox | None = None
    confidence: float = Field(ge=0, le=1)
    source: Literal["DETERMINISTIC", "LLM", "CROSS_CHECKED", "CONFLICT"]
    source_text: str = Field(min_length=1)
    requires_review: bool = False
    alternatives: tuple[FieldAlternative, ...] = ()

    @model_validator(mode="after")
    def validate_review_state(self) -> ResolvedField:
        if self.source == "CONFLICT" and not self.requires_review:
            raise ValueError("conflicting fields must require review")
        if self.source != "CONFLICT" and self.alternatives:
            raise ValueError("only conflicting fields may carry alternatives")
        return self


class HybridExtractionResult(CanonicalModel):
    document_type: DocumentType
    classification_confidence: float = Field(ge=0, le=1)
    classification_source: Literal["DETERMINISTIC", "LLM", "CROSS_CHECKED", "CONFLICT"]
    classification_requires_review: bool = False
    fields: list[ResolvedField]
    llm_fallback_triggered: bool
    fallback_requested_fields: tuple[FieldName, ...] = ()
    missing_fields: tuple[FieldName, ...] = ()
    rejected_fields: tuple[FieldName, ...] = ()
    requires_review: bool

    def field_map(self) -> dict[FieldName, ResolvedField]:
        return {field.field_name: field for field in self.fields}


def extract_with_fallback(
    path: str | Path,
    client: LLMClient,
    *,
    classification_threshold: float = DEFAULT_CLASSIFICATION_THRESHOLD,
    field_threshold: float = DEFAULT_FIELD_THRESHOLD,
) -> HybridExtractionResult:
    pages = _read_pages(path)
    deterministic = None
    try:
        deterministic = extract_document(path)
    except UnclassifiedDocumentError:
        pass

    needs_classification = (
        deterministic is None
        or deterministic.classification_confidence < classification_threshold
    )
    deterministic_fields = deterministic.field_map() if deterministic else {}
    expected_names = (
        tuple(rule.field_name for rule in FIELD_RULES[deterministic.document_type])
        if deterministic
        else ALL_FIELD_NAMES
    )
    requested = tuple(
        name
        for name in expected_names
        if name not in deterministic_fields
        or deterministic_fields[name].confidence < field_threshold
    )

    llm_response = None
    if needs_classification or requested:
        llm_response = client.extract(
            LLMExtractionRequest(
                document_type=deterministic.document_type if deterministic else None,
                requested_fields=list(requested),
                pages=pages,
            )
        )

    (
        document_type,
        classification_confidence,
        classification_source,
        classification_review,
    ) = _resolve_classification(deterministic, llm_response)
    classification_review = (
        classification_review
        or classification_confidence < classification_threshold
    )
    valid_names = tuple(rule.field_name for rule in FIELD_RULES[document_type])
    llm_fields, rejected = _normalize_llm_fields(
        llm_response.fields if llm_response else [],
        requested,
        valid_names,
        len(pages),
    )
    fields: list[ResolvedField] = []
    for name in valid_names:
        resolved = _resolve_field(
            deterministic_fields.get(name),
            llm_fields.get(name),
            field_threshold,
        )
        if resolved is not None:
            fields.append(resolved)
    present = {field.field_name for field in fields}
    missing = tuple(name for name in valid_names if name not in present)
    requires_review = bool(
        classification_review
        or missing
        or rejected
        or any(field.requires_review for field in fields)
    )
    return HybridExtractionResult(
        document_type=document_type,
        classification_confidence=classification_confidence,
        classification_source=classification_source,
        classification_requires_review=classification_review,
        fields=fields,
        llm_fallback_triggered=llm_response is not None,
        fallback_requested_fields=requested,
        missing_fields=missing,
        rejected_fields=tuple(sorted(rejected)),
        requires_review=requires_review,
    )


def _read_pages(path: str | Path) -> list[LLMPage]:
    with pymupdf.open(path) as document:
        return [
            LLMPage(page=index + 1, text=page.get_text("text", sort=True))
            for index, page in enumerate(document)
        ]


def _resolve_classification(deterministic, llm_response):
    if deterministic is None and llm_response is None:
        raise UnclassifiedDocumentError("neither extraction path classified the document")
    if deterministic is None:
        return (
            llm_response.document_type,
            llm_response.classification_confidence,
            "LLM",
            False,
        )
    if llm_response is None:
        return (
            deterministic.document_type,
            deterministic.classification_confidence,
            "DETERMINISTIC",
            False,
        )
    if deterministic.document_type == llm_response.document_type:
        return (
            deterministic.document_type,
            max(
                deterministic.classification_confidence,
                llm_response.classification_confidence,
            ),
            "CROSS_CHECKED",
            False,
        )
    return (
        deterministic.document_type,
        min(
            deterministic.classification_confidence,
            llm_response.classification_confidence,
            0.49,
        ),
        "CONFLICT",
        True,
    )


def _normalize_llm_fields(
    candidates: list[LLMFieldCandidate],
    requested: tuple[str, ...],
    valid_names: tuple[str, ...],
    page_count: int,
) -> tuple[dict[str, tuple[FieldValue, LLMFieldCandidate]], set[str]]:
    normalized: dict[str, tuple[FieldValue, LLMFieldCandidate]] = {}
    rejected: set[str] = set()
    allowed = set(requested) & set(valid_names)
    for candidate in candidates:
        if candidate.field_name not in allowed:
            continue
        if candidate.page > page_count:
            rejected.add(candidate.field_name)
            continue
        try:
            value = _normalize_candidate(candidate)
        except ValueError:
            rejected.add(candidate.field_name)
            continue
        normalized[candidate.field_name] = (value, candidate)
    return normalized, rejected


def _normalize_candidate(candidate: LLMFieldCandidate) -> FieldValue:
    parser_kind = next(
        rule.parser
        for rules in FIELD_RULES.values()
        for rule in rules
        if rule.field_name == candidate.field_name
    )
    if parser_kind == "dates":
        values = tuple(
            normalize_date(value)
            for value in candidate.raw_value.split(";")
            if value.strip()
        )
        if not values:
            raise ValueError("due date output is empty")
        return values
    return PARSERS[parser_kind](candidate.raw_value)


def _resolve_field(
    deterministic: ExtractedField | None,
    llm: tuple[FieldValue, LLMFieldCandidate] | None,
    threshold: float,
) -> ResolvedField | None:
    if deterministic is not None and llm is None:
        return _from_deterministic(
            deterministic,
            requires_review=deterministic.confidence < threshold and llm is None,
        )
    if deterministic is None and llm is not None:
        value, candidate = llm
        return ResolvedField(
            field_name=candidate.field_name,
            value=value,
            page=candidate.page,
            confidence=candidate.confidence,
            source="LLM",
            source_text=candidate.raw_value,
            requires_review=candidate.confidence < threshold,
        )
    if deterministic is None or llm is None:
        return None

    llm_value, candidate = llm
    if deterministic.value == llm_value:
        return ResolvedField(
            field_name=deterministic.field_name,
            value=deterministic.value,
            page=deterministic.page,
            bounding_box=deterministic.bounding_box,
            confidence=max(deterministic.confidence, candidate.confidence),
            source="CROSS_CHECKED",
            source_text=deterministic.source_text,
        )
    return ResolvedField(
        field_name=deterministic.field_name,
        value=deterministic.value,
        page=deterministic.page,
        bounding_box=deterministic.bounding_box,
        confidence=min(deterministic.confidence, candidate.confidence, 0.49),
        source="CONFLICT",
        source_text=deterministic.source_text,
        requires_review=True,
        alternatives=(
            FieldAlternative(
                source="DETERMINISTIC",
                value=deterministic.value,
                page=deterministic.page,
                confidence=deterministic.confidence,
            ),
            FieldAlternative(
                source="LLM",
                value=llm_value,
                page=candidate.page,
                confidence=candidate.confidence,
            ),
        ),
    )


def _from_deterministic(
    field: ExtractedField, *, requires_review: bool = False
) -> ResolvedField:
    return ResolvedField(
        field_name=field.field_name,
        value=field.value,
        page=field.page,
        bounding_box=field.bounding_box,
        confidence=field.confidence,
        source="DETERMINISTIC",
        source_text=field.source_text,
        requires_review=requires_review,
    )
