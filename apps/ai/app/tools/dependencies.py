"""Narrow dependency ports and safe in-memory stores for agent tools."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Protocol

from pydantic import Field

from app.extraction.models import DocumentType, ExtractionResult
from app.retrieval import SearchResult
from app.schemas.mortgage import CanonicalModel, MortgageAccount
from app.tools.core import AuditScopeError, InformationNotFoundError
from app.tools.engine import ReconciliationEngine


class AuditRecord(CanonicalModel):
    audit_id: str = Field(min_length=1, max_length=128)
    account: MortgageAccount


class StoredExtraction(CanonicalModel):
    audit_id: str = Field(min_length=1, max_length=128)
    document_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
    extraction: ExtractionResult


class MissingInformationRecord(CanonicalModel):
    record_id: str = Field(pattern=r"^missing-\d{6}$")
    audit_id: str = Field(min_length=1, max_length=128)
    document_type: DocumentType
    reason: str = Field(min_length=5, max_length=500)


class AuditDataSource(Protocol):
    """Read only canonical data that belongs to the supplied audit_id."""

    def get_account(self, audit_id: str) -> MortgageAccount: ...

    def get_extraction(self, audit_id: str, document_id: str) -> StoredExtraction: ...


class MutableAuditDataSource(AuditDataSource, Protocol):
    """Audit data source populated by deterministic graph extraction."""

    def store_extraction(self, extraction: StoredExtraction) -> None: ...


class RegulationSearch(Protocol):
    def hybrid(self, query: str, *, limit: int = 5) -> list[SearchResult]: ...


class MissingInformationSink(Protocol):
    def record(
        self,
        audit_id: str,
        document_type: DocumentType,
        reason: str,
    ) -> MissingInformationRecord: ...


@dataclass(frozen=True)
class ToolDependencies:
    audit_data: AuditDataSource
    engine: ReconciliationEngine
    regulations: RegulationSearch
    missing_information: MissingInformationSink


class InMemoryAuditDataSource:
    """Ownership-checking store used by tests and local orchestration."""

    def __init__(
        self,
        audits: list[AuditRecord],
        extractions: list[StoredExtraction],
    ) -> None:
        self._audits = _unique_by(audits, lambda record: record.audit_id, "audit_id")
        self._extractions = _unique_by(
            extractions,
            lambda record: record.document_id,
            "document_id",
        )

    def get_account(self, audit_id: str) -> MortgageAccount:
        try:
            return self._audits[audit_id].account
        except KeyError as error:
            raise InformationNotFoundError(f"audit {audit_id} has no account data") from error

    def get_extraction(self, audit_id: str, document_id: str) -> StoredExtraction:
        try:
            record = self._extractions[document_id]
        except KeyError as error:
            raise InformationNotFoundError(
                f"document {document_id} does not exist in the bound audit"
            ) from error
        if record.audit_id != audit_id:
            raise AuditScopeError("document belongs to a different audit")
        return record

    def store_extraction(self, extraction: StoredExtraction) -> None:
        existing = self._extractions.get(extraction.document_id)
        if existing is not None and existing.audit_id != extraction.audit_id:
            raise AuditScopeError("cannot replace a document owned by another audit")
        self._extractions[extraction.document_id] = extraction


class InMemoryMissingInformationSink:
    """Append-only local sink with deterministic record identifiers."""

    def __init__(self) -> None:
        self.records: list[MissingInformationRecord] = []
        self._lock = Lock()

    def record(
        self,
        audit_id: str,
        document_type: DocumentType,
        reason: str,
    ) -> MissingInformationRecord:
        with self._lock:
            record = MissingInformationRecord(
                record_id=f"missing-{len(self.records) + 1:06d}",
                audit_id=audit_id,
                document_type=document_type,
                reason=reason,
            )
            self.records.append(record)
            return record


def _unique_by[RecordT](
    records: list[RecordT],
    key,
    label: str,
) -> dict[str, RecordT]:
    indexed: dict[str, RecordT] = {}
    for record in records:
        value = key(record)
        if value in indexed:
            raise ValueError(f"duplicate {label}: {value}")
        indexed[value] = record
    return indexed
