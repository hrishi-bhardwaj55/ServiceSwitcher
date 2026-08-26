"""Inject a property-tax projection inconsistent with the supplied bill."""

from decimal import Decimal

from app.schemas import MortgageAccount

from data.faults.common import FaultInjection, replace_new_analysis
from data.generator.escrow import build_analysis
from data.generator.money import money


def inject(account: MortgageAccount, variant: int = 0) -> FaultInjection:
    current = account.escrow_analyses[-1]
    discrepancy = money(Decimal("600.00") + Decimal(variant % 40) * Decimal("13.17"))
    false_projection = money(current.projected_annual_tax + discrepancy)
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
        current_balance=current.current_balance,
        annual_tax=false_projection,
        annual_insurance=current.projected_annual_insurance,
        tax_due_months=tuple(due_date.month for due_date in tax_bill.due_dates),
        insurance_due_month=policy.renewal_date.month,
        principal_and_interest=principal_and_interest,
    )
    return FaultInjection(
        account=replace_new_analysis(account, false_analysis),
        finding_type="PROPERTY_TAX_PROJECTION_MISMATCH",
        impact_total=discrepancy,
        monthly_impact=money(discrepancy / Decimal(12)),
        evidence_documents=("doc_property_tax_bill", "doc_escrow_analysis"),
    )
