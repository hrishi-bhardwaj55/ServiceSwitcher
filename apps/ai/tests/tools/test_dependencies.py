from datetime import date
from decimal import Decimal

import pytest

from app.extraction.models import BoundingBox, ExtractedField, ExtractionResult
from app.schemas.mortgage import MortgageAccount
from app.tools import AuditScopeError, InformationNotFoundError
from app.tools.dependencies import (
    AuditRecord,
    InMemoryAuditDataSource,
    InMemoryMissingInformationSink,
    StoredExtraction,
)


def _account(account_id: str) -> MortgageAccount:
    return MortgageAccount(
        account_id=account_id,
        original_principal=Decimal("200000.00"),
        current_principal=Decimal("190000.00"),
        annual_rate=Decimal("0.05"),
        term_months=360,
        origination_date=date(2024, 1, 1),
        servicing_periods=[
            {
                "servicer_id": "OLD",
                "start_date": date(2024, 1, 1),
                "end_date": date(2024, 5, 31),
            }
        ],
        payments=[],
        escrow_ledger=[],
        tax_bills=[],
        insurance_policies=[],
        escrow_analyses=[],
    )


def _extraction(audit_id: str, document_id: str) -> StoredExtraction:
    return StoredExtraction(
        audit_id=audit_id,
        document_id=document_id,
        extraction=ExtractionResult(
            document_type="OLD_SERVICER_STATEMENT",
            classification_confidence=1.0,
            fields=[
                ExtractedField(
                    field_name="escrow_balance",
                    value=Decimal("1200.00"),
                    page=1,
                    bounding_box=BoundingBox(x0=1, y0=1, x1=2, y1=2),
                    confidence=0.99,
                    source_text="$1,200.00",
                )
            ],
        ),
    )


def test_audit_data_source_enforces_document_ownership():
    source = InMemoryAuditDataSource(
        [AuditRecord(audit_id="audit-a", account=_account("SS-A"))],
        [_extraction("audit-b", "foreign-document")],
    )

    assert source.get_account("audit-a").account_id == "SS-A"
    with pytest.raises(AuditScopeError, match="different audit"):
        source.get_extraction("audit-a", "foreign-document")
    with pytest.raises(InformationNotFoundError, match="does not exist"):
        source.get_extraction("audit-a", "missing-document")


def test_in_memory_stores_reject_duplicate_resource_ids():
    audit = AuditRecord(audit_id="audit-a", account=_account("SS-A"))
    with pytest.raises(ValueError, match="duplicate audit_id"):
        InMemoryAuditDataSource([audit, audit], [])

    document = _extraction("audit-a", "statement")
    with pytest.raises(ValueError, match="duplicate document_id"):
        InMemoryAuditDataSource([audit], [document, document])


def test_missing_information_sink_is_append_only_and_audit_labeled():
    sink = InMemoryMissingInformationSink()

    first = sink.record(
        "audit-a",
        "PROPERTY_TAX_BILL",
        "The borrower did not upload the current tax bill.",
    )
    second = sink.record(
        "audit-a",
        "TRANSFER_NOTICE",
        "The transfer notice is required to establish timing.",
    )

    assert first.record_id == "missing-000001"
    assert second.record_id == "missing-000002"
    assert sink.records == [first, second]
