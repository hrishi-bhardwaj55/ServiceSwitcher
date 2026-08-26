"""Inject an escrow balance discontinuity at servicing transfer."""

from decimal import Decimal

from app.schemas import MortgageAccount

from data.faults.common import FaultInjection, replace_new_analysis
from data.generator.escrow import build_analysis
from data.generator.money import money


def inject(account: MortgageAccount, variant: int = 0) -> FaultInjection:
    current = account.escrow_analyses[-1]
    discrepancy = money(Decimal("75.00") + Decimal(variant % 40) * Decimal("2.37"))
    false_balance = money(current.current_balance + discrepancy)
    tax_bill = next(bill for bill in account.tax_bills if bill.tax_year == 2025)
    policy = next(
        policy for policy in account.insurance_policies if policy.renewal_date.year == 2025
    )
    principal_and_interest = money(
        account.payments[0].principal + account.payments[0].interest
    )
    false_analysis = build_analysis(
        servicer_id=current.servicer_id,
        analysis_date=current.analysis_date,
        current_balance=false_balance,
        annual_tax=current.projected_annual_tax,
        annual_insurance=current.projected_annual_insurance,
        tax_due_months=tuple(due_date.month for due_date in tax_bill.due_dates),
        insurance_due_month=policy.renewal_date.month,
        principal_and_interest=principal_and_interest,
    )
    return FaultInjection(
        account=replace_new_analysis(account, false_analysis),
        finding_type="ESCROW_BALANCE_MISMATCH",
        impact_total=discrepancy,
        monthly_impact=Decimal("0.00"),
        evidence_documents=(
            "doc_old_servicer_statement",
            "doc_new_servicer_statement",
        ),
    )
