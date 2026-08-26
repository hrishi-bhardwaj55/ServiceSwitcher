"""Implement the eight narrow C10 agent-tool operations."""

from __future__ import annotations

from app.tools.core import InformationNotFoundError
from app.tools.dependencies import ToolDependencies
from app.tools.schemas import (
    CalculateEscrowContinuityArgs,
    CalculatePaymentBreakdownArgs,
    CompareTaxProjectionArgs,
    GetEscrowLedgerArgs,
    GetExtractedFieldArgs,
    GetPaymentHistoryArgs,
    MarkInformationMissingArgs,
    SearchRegulationsArgs,
)


def get_extracted_field(
    arguments: GetExtractedFieldArgs,
    audit_id: str,
    dependencies: ToolDependencies,
) -> object:
    """Return one extracted value and its page, box, source text, and confidence."""
    document = dependencies.audit_data.get_extraction(audit_id, arguments.document_id)
    field = document.extraction.field_map().get(arguments.field_name)
    if field is None:
        raise InformationNotFoundError(
            f"document {arguments.document_id} has no extracted {arguments.field_name}"
        )
    return {
        "document_id": document.document_id,
        "document_type": document.extraction.document_type,
        "field": field,
    }


def get_escrow_ledger(
    arguments: GetEscrowLedgerArgs,
    audit_id: str,
    dependencies: ToolDependencies,
) -> object:
    """Return bound-audit escrow entries in an inclusive date range; do no arithmetic."""
    account = dependencies.audit_data.get_account(audit_id)
    entries = [
        entry
        for entry in account.escrow_ledger
        if arguments.start_date <= entry.date <= arguments.end_date
    ]
    return {
        "account_id": account.account_id,
        "start_date": arguments.start_date,
        "end_date": arguments.end_date,
        "count": len(entries),
        "entries": entries,
    }


def get_payment_history(
    arguments: GetPaymentHistoryArgs,
    audit_id: str,
    dependencies: ToolDependencies,
) -> object:
    """Return bound-audit mortgage payments in an inclusive date range."""
    account = dependencies.audit_data.get_account(audit_id)
    payments = [
        payment
        for payment in account.payments
        if arguments.start_date <= payment.date <= arguments.end_date
    ]
    return {
        "account_id": account.account_id,
        "start_date": arguments.start_date,
        "end_date": arguments.end_date,
        "count": len(payments),
        "payments": payments,
    }


def calculate_escrow_continuity(
    arguments: CalculateEscrowContinuityArgs,
    audit_id: str,
    dependencies: ToolDependencies,
) -> object:
    """Ask the deterministic engine whether escrow value continued across transfer."""
    result = _reconcile(arguments.transfer_date.isoformat(), audit_id, dependencies)
    findings = [
        finding
        for finding in result.findings
        if finding.finding_type == "ESCROW_BALANCE_MISMATCH"
    ]
    return {
        "transfer_date": arguments.transfer_date,
        "engine_version": result.engine_version,
        "findings": findings,
    }


def calculate_payment_breakdown(
    arguments: CalculatePaymentBreakdownArgs,
    audit_id: str,
    dependencies: ToolDependencies,
) -> object:
    """Ask the deterministic engine to decompose the payment change at transfer."""
    result = _reconcile(arguments.transfer_date.isoformat(), audit_id, dependencies)
    return {
        "transfer_date": arguments.transfer_date,
        "engine_version": result.engine_version,
        "payment_decomposition": result.payment_decomposition,
    }


def compare_tax_projection(
    arguments: CompareTaxProjectionArgs,
    audit_id: str,
    dependencies: ToolDependencies,
) -> object:
    """Ask the deterministic engine to compare projected tax with the actual tax bill."""
    result = _reconcile(arguments.transfer_date.isoformat(), audit_id, dependencies)
    findings = [
        finding
        for finding in result.findings
        if finding.finding_type == "PROPERTY_TAX_PROJECTION_MISMATCH"
    ]
    return {
        "transfer_date": arguments.transfer_date,
        "engine_version": result.engine_version,
        "findings": findings,
    }


def search_regulations(
    arguments: SearchRegulationsArgs,
    audit_id: str,
    dependencies: ToolDependencies,
) -> object:
    """Return top hybrid regulation chunks with source metadata; do not give legal advice."""
    del audit_id  # Scope is enforced by ScopedAgentTool before this global search.
    results = dependencies.regulations.hybrid(arguments.query, limit=arguments.limit)
    return {"query": arguments.query, "count": len(results), "results": results}


def mark_information_missing(
    arguments: MarkInformationMissingArgs,
    audit_id: str,
    dependencies: ToolDependencies,
) -> object:
    """Record why a required document is absent; never fabricate its contents."""
    return dependencies.missing_information.record(
        audit_id,
        arguments.document_type,
        arguments.reason,
    )


def _reconcile(transfer_date: str, audit_id: str, dependencies: ToolDependencies):
    account = dependencies.audit_data.get_account(audit_id)
    return dependencies.engine.reconcile(account, transfer_date)
