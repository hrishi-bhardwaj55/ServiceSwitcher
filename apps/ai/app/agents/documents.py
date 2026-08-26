"""Deterministic, model-inaccessible PDF classification and extraction boundary."""

from __future__ import annotations

from typing import Protocol

import pymupdf

from app.agents.models import DocumentRef
from app.extraction.classifier import Classification, classify_document
from app.extraction.extractor import extract_document
from app.extraction.models import ExtractionResult


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
        except pymupdf.FileDataError as error:
            raise ValueError(f"document {document.document_id} is not a readable PDF") from error

    def classify(self, document: DocumentRef) -> Classification:
        with pymupdf.open(document.path) as pdf:
            text = "\n".join(page.get_text("text", sort=True) for page in pdf)
        return classify_document(text)

    def extract(self, document: DocumentRef) -> ExtractionResult:
        return extract_document(document.path)
