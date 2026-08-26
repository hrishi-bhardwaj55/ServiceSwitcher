"""Typed state and durable contracts for the audit investigation graph."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import TypedDict

from pydantic import Field

from app.retrieval import RuleChunk
from app.schemas.mortgage import CanonicalModel
from app.tools.engine import EngineFinding


class DocumentRef(CanonicalModel):
    audit_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
    document_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
    path: Path


class AuditState(TypedDict):
    audit_id: str
    documents: list[DocumentRef]
    extracted_values: dict[str, dict[str, object]]
    deterministic_findings: list[EngineFinding]
    ambiguous_findings: list[EngineFinding]
    retrieved_rules: list[RuleChunk]
    final_findings: list[EngineFinding]
    missing_information: list[str]
    requires_review: bool
    steps_used: int
    cost_usd: Decimal


class HumanReviewDecision(CanonicalModel):
    approved: bool
    notes: str = Field(default="", max_length=1_000)


def initial_audit_state(audit_id: str, documents: list[DocumentRef]) -> AuditState:
    if not documents:
        raise ValueError("an audit requires at least one document")
    if any(document.audit_id != audit_id for document in documents):
        raise ValueError("every document must belong to the audit state")
    document_ids = [document.document_id for document in documents]
    if len(document_ids) != len(set(document_ids)):
        raise ValueError("document ids must be unique within an audit")
    return AuditState(
        audit_id=audit_id,
        documents=documents,
        extracted_values={},
        deterministic_findings=[],
        ambiguous_findings=[],
        retrieved_rules=[],
        final_findings=[],
        missing_information=[],
        requires_review=False,
        steps_used=0,
        cost_usd=Decimal("0"),
    )
