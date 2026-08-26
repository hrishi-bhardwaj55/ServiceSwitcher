"""Inject a stated shortage that disagrees with the aggregate analysis."""

from decimal import Decimal

from app.schemas import MortgageAccount

from data.faults.common import FaultInjection, replace_new_analysis
from data.generator.money import money


def inject(account: MortgageAccount, variant: int = 0) -> FaultInjection:
    current = account.escrow_analyses[-1]
    discrepancy = money(Decimal("240.00") + Decimal(variant % 40) * Decimal("9.11"))
    false_shortage = money(current.stated_shortage + discrepancy)
    false_shortage_monthly = money(false_shortage / Decimal(12))
    principal_and_interest = money(
        account.payments[0].principal + account.payments[0].interest
    )
    false_analysis = current.model_copy(
        update={
            "stated_shortage": false_shortage,
            "stated_shortage_monthly": false_shortage_monthly,
            "new_total_payment": money(
                principal_and_interest
                + current.stated_monthly_escrow
                + false_shortage_monthly
            ),
        }
    )
    return FaultInjection(
        account=replace_new_analysis(account, false_analysis),
        finding_type="ESCROW_SHORTAGE_CALCULATION_ERROR",
        impact_total=discrepancy,
        monthly_impact=money(discrepancy / Decimal(12)),
        evidence_documents=("doc_escrow_analysis",),
    )
