"""Inject an undocumented recurring post-transfer payment surcharge."""

from decimal import Decimal

from app.schemas import MortgageAccount

from data.faults.common import FaultInjection, payment_residual
from data.generator.money import money


def inject(account: MortgageAccount, variant: int = 0) -> FaultInjection:
    transfer_date = account.servicing_periods[1].start_date
    target_residual = money(
        Decimal("50.00") + Decimal(variant % 40) * Decimal("1.29")
    )
    surcharge = money(target_residual - payment_residual(account))
    payments = [
        payment
        if payment.date < transfer_date
        else payment.model_copy(update={"total": money(payment.total + surcharge)})
        for payment in account.payments
    ]
    return FaultInjection(
        account=account.model_copy(update={"payments": payments}),
        finding_type="UNEXPLAINED_PAYMENT_INCREASE",
        impact_total=money(target_residual * Decimal(12)),
        monthly_impact=target_residual,
        evidence_documents=(
            "doc_old_servicer_statement",
            "doc_new_servicer_statement",
            "doc_escrow_analysis",
        ),
    )
