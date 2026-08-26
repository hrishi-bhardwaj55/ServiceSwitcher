"""Shared immutable transformations used by fault injectors."""

from dataclasses import dataclass
from decimal import Decimal

from app.schemas import EscrowAnalysis, EscrowTransaction, MortgageAccount
from app.schemas.ground_truth import FindingType

from data.generator.money import money


@dataclass(frozen=True)
class FaultInjection:
    account: MortgageAccount
    finding_type: FindingType
    impact_total: Decimal
    monthly_impact: Decimal
    evidence_documents: tuple[str, ...]


def rechain_ledger(ledger: list[EscrowTransaction]) -> list[EscrowTransaction]:
    """Sort transactions and derive every balance from signed amounts."""

    priorities = {
        "ADJUSTMENT": 0,
        "DEPOSIT": 1,
        "TAX_DISBURSEMENT": 2,
        "INSURANCE_DISBURSEMENT": 3,
    }
    balance = Decimal("0.00")
    rechained: list[EscrowTransaction] = []
    for transaction in sorted(
        ledger,
        key=lambda item: (
            item.date,
            priorities[item.type],
            item.payee or "",
            item.amount,
        ),
    ):
        balance = money(balance + transaction.amount)
        rechained.append(transaction.model_copy(update={"balance_after": balance}))
    return rechained


def replace_new_analysis(
    account: MortgageAccount,
    analysis: EscrowAnalysis,
) -> MortgageAccount:
    """Apply a new-servicer analysis to later payments and ledger deposits."""

    transfer_date = account.servicing_periods[1].start_date
    new_escrow = money(
        analysis.stated_monthly_escrow + analysis.stated_shortage_monthly
    )
    payments = [
        payment
        if payment.date < transfer_date
        else payment.model_copy(
            update={
                "escrow": new_escrow,
                "total": money(payment.principal + payment.interest + new_escrow),
            }
        )
        for payment in account.payments
    ]
    ledger = [
        transaction.model_copy(update={"amount": new_escrow})
        if transaction.type == "DEPOSIT" and transaction.date >= transfer_date
        else transaction
        for transaction in account.escrow_ledger
    ]
    analyses = [*account.escrow_analyses[:-1], analysis]
    return account.model_copy(
        update={
            "payments": payments,
            "escrow_ledger": rechain_ledger(ledger),
            "escrow_analyses": analyses,
        }
    )


def payment_residual(account: MortgageAccount) -> Decimal:
    """Recompute the documented monthly payment-change residual."""

    transfer_date = account.servicing_periods[1].start_date
    old_payment = max(
        (payment for payment in account.payments if payment.date < transfer_date),
        key=lambda payment: payment.date,
    )
    new_payment = min(
        (payment for payment in account.payments if payment.date >= transfer_date),
        key=lambda payment: payment.date,
    )
    old_analysis, new_analysis = account.escrow_analyses[-2:]
    payment_change = money(new_payment.total - old_payment.total)
    principal_interest_change = money(
        new_payment.principal
        + new_payment.interest
        - old_payment.principal
        - old_payment.interest
    )
    tax_change = money(
        (new_analysis.projected_annual_tax - old_analysis.projected_annual_tax)
        / Decimal(12)
    )
    insurance_change = money(
        (
            new_analysis.projected_annual_insurance
            - old_analysis.projected_annual_insurance
        )
        / Decimal(12)
    )
    return money(
        payment_change
        - principal_interest_change
        - tax_change
        - insurance_change
        - new_analysis.stated_shortage_monthly
    )
