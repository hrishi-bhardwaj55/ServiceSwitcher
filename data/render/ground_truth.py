"""Expected typed fields for deterministic extraction evaluation."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from app.extraction.models import DocumentType


def expected_extraction_fields(
    account: dict[str, Any], document_type: DocumentType
) -> dict[str, Any]:
    old_period, new_period = account["servicing_periods"][:2]
    old_analysis, new_analysis = account["escrow_analyses"][-2:]
    if document_type == "OLD_SERVICER_STATEMENT":
        payment = max(
            (item for item in account["payments"] if item["date"] < new_period["start_date"]),
            key=lambda item: item["date"],
        )
        return _statement_fields(account, payment, old_analysis)
    if document_type == "NEW_SERVICER_STATEMENT":
        payment = min(
            (item for item in account["payments"] if item["date"] >= new_period["start_date"]),
            key=lambda item: item["date"],
        )
        return _statement_fields(account, payment, new_analysis)
    if document_type == "TRANSFER_NOTICE":
        return {
            "old_servicer_name": _servicer(old_period["servicer_id"]),
            "new_servicer_name": _servicer(new_period["servicer_id"]),
            "transfer_date": date.fromisoformat(new_period["start_date"]),
        }
    if document_type == "ESCROW_ANALYSIS":
        return {
            "projected_annual_tax": Decimal(new_analysis["projected_annual_tax"]),
            "projected_annual_insurance": Decimal(
                new_analysis["projected_annual_insurance"]
            ),
            "stated_shortage": Decimal(new_analysis["stated_shortage"]),
        }
    bill = max(account["tax_bills"], key=lambda item: item["tax_year"])
    return {
        "tax_authority": bill["authority"],
        "annual_tax_amount": Decimal(bill["annual_amount"]),
        "due_dates": tuple(date.fromisoformat(value) for value in bill["due_dates"]),
    }


def _statement_fields(
    account: dict[str, Any], payment: dict[str, Any], analysis: dict[str, Any]
) -> dict[str, Decimal]:
    return {
        "principal_balance": Decimal(account["current_principal"]),
        "interest_rate": Decimal(account["annual_rate"]),
        "monthly_payment": Decimal(payment["total"]),
        "escrow_balance": Decimal(analysis["current_balance"]),
    }


def _servicer(value: str) -> str:
    return value.replace("-", " ").title()
