"""Keyword-signature document classifier."""

from __future__ import annotations

from dataclasses import dataclass

from app.extraction.models import DocumentType


class UnclassifiedDocumentError(ValueError):
    """Raised when text has no unambiguous document signature."""


@dataclass(frozen=True)
class Classification:
    document_type: DocumentType
    confidence: float
    matched_signatures: tuple[str, ...]


SIGNATURES: dict[DocumentType, tuple[str, ...]] = {
    "OLD_SERVICER_STATEMENT": (
        "final mortgage statement",
        "final loan account statement",
        "recent escrow activity",
        "final statement issued before the servicing transfer",
    ),
    "NEW_SERVICER_STATEMENT": (
        "mortgage account statement",
        "monthly loan account statement",
        "post-transfer escrow activity",
        "first payment accepted after transfer",
    ),
    "TRANSFER_NOTICE": (
        "notice of servicing transfer",
        "servicing assignment advice",
        "effective transfer date",
        "service change date",
    ),
    "ESCROW_ANALYSIS": (
        "annual escrow account analysis",
        "escrow computation disclosure",
        "projected annual property tax",
        "12-month projected trial balance",
    ),
    "PROPERTY_TAX_BILL": (
        "property tax bill",
        "real property tax assessment",
        "installment schedule",
        "annual amount due",
        "total tax levy",
    ),
}


def classify_document(text: str) -> Classification:
    normalized = " ".join(text.casefold().split())
    matches = {
        document_type: tuple(
            signature for signature in signatures if signature in normalized
        )
        for document_type, signatures in SIGNATURES.items()
    }
    ranked = sorted(matches.items(), key=lambda item: len(item[1]), reverse=True)
    document_type, matched = ranked[0]
    runner_up = len(ranked[1][1])
    if not matched or len(matched) == runner_up:
        raise UnclassifiedDocumentError("document has no unique keyword signature")
    coverage = len(matched) / len(SIGNATURES[document_type])
    margin = (len(matched) - runner_up) / len(SIGNATURES[document_type])
    confidence = min(0.99, 0.70 + (0.20 * coverage) + (0.09 * margin))
    return Classification(document_type, confidence, matched)
