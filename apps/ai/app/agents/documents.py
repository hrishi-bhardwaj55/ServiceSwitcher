"""Deterministic, model-inaccessible PDF classification and extraction boundary."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pymupdf

from app.agents.models import DocumentRef
from app.extraction.classifier import Classification, classify_document
from app.extraction.extractor import extract_document
from app.extraction.fallback import HybridExtractionResult, extract_with_fallback
from app.extraction.models import ExtractedField, ExtractionResult
from app.llm.protocol import LLMClient
from app.security import validate_document_text


class DocumentProcessor(Protocol):
    def validate(self, document: DocumentRef) -> None: ...

    def classify(self, document: DocumentRef) -> Classification: ...

    def extract(self, document: DocumentRef) -> ExtractionResult: ...


class PdfDocumentProcessor:
    """Read only explicit PDF references supplied by the trusted audit framework."""

    def validate(self, document: DocumentRef) -> None:
        path = document.path
        if path.suffix.casefold() != ".pdf":
            raise ValueError(f"document {document.document_id} is not a PDF")
        if not path.is_file():
            raise ValueError(f"document {document.document_id} does not exist")
        try:
            with pymupdf.open(path) as pdf:
                if pdf.page_count < 1:
                    raise ValueError(f"document {document.document_id} has no pages")
                text = "\n".join(page.get_text("text", sort=True) for page in pdf)
        except pymupdf.FileDataError as error:
            raise ValueError(f"document {document.document_id} is not a readable PDF") from error
        validate_document_text(text, expected_account_id=document.account_id)

    def classify(self, document: DocumentRef) -> Classification:
        with pymupdf.open(document.path) as pdf:
            text = "\n".join(page.get_text("text", sort=True) for page in pdf)
        return classify_document(text)

    def extract(self, document: DocumentRef) -> ExtractionResult:
        return extract_document(document.path)


class FallbackPdfDocumentProcessor(PdfDocumentProcessor):
    """Use the C8 confidence-gated fallback and cache one result per document."""

    def __init__(self, client: LLMClient) -> None:
        self.client = client
        self._cache: dict[Path, HybridExtractionResult] = {}

    def classify(self, document: DocumentRef) -> Classification:
        result = self._hybrid(document.path)
        return Classification(
            document_type=result.document_type,
            confidence=result.classification_confidence,
            matched_signatures=(result.classification_source,),
        )

    def extract(self, document: DocumentRef) -> ExtractionResult:
        result = self._hybrid(document.path)
        reasons = []
        if result.classification_requires_review:
            reasons.append("model-backed classification requires review")
        if result.missing_fields:
            reasons.append(f"missing fields: {', '.join(result.missing_fields)}")
        if result.rejected_fields:
            reasons.append(f"rejected fields: {', '.join(result.rejected_fields)}")
        if any(field.requires_review for field in result.fields):
            reasons.append("one or more model-backed fields require review")
        return ExtractionResult(
            document_type=result.document_type,
            classification_confidence=result.classification_confidence,
            fields=[
                ExtractedField(
                    field_name=field.field_name,
                    value=field.value,
                    page=field.page,
                    bounding_box=field.bounding_box,
                    confidence=field.confidence,
                    source_text=field.source_text,
                )
                for field in result.fields
            ],
            model_fallback_triggered=result.llm_fallback_triggered,
            requires_review=result.requires_review,
            review_reasons=tuple(reasons),
        )

    def _hybrid(self, path: Path) -> HybridExtractionResult:
        resolved = path.resolve()
        result = self._cache.get(resolved)
        if result is None:
            result = extract_with_fallback(resolved, self.client)
            self._cache[resolved] = result
        return result
