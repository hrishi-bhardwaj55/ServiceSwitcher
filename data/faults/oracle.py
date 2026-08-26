"""Independent structured-data oracle used to validate injected labels."""

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from itertools import combinations

from app.schemas import MortgageAccount
from app.schemas.ground_truth import FindingType

from data.faults.common import payment_residual
from data.generator.money import money
from data.generator.validate import _analysis_expected_values


@dataclass(frozen=True)
class ObservedFinding:
    finding_type: FindingType
    impact_total: Decimal
    monthly_impact: Decimal


def evaluate(account: MortgageAccount) -> list[ObservedFinding]:
    """Evaluate all five v1 finding rules against one structured account."""

    findings: list[ObservedFinding] = []
    old_analysis, new_analysis = account.escrow_analyses[-2:]

    balance_difference = money(
        abs(new_analysis.current_balance - old_analysis.current_balance)
    )
    if balance_difference > Decimal("1.00"):
        findings.append(
            ObservedFinding(
                finding_type="ESCROW_BALANCE_MISMATCH",
                impact_total=balance_difference,
                monthly_impact=Decimal("0.00"),
            )
        )

    applicable_tax = money(
        sum(
            (
                bill.annual_amount
                for bill in account.tax_bills
                if bill.tax_year == 2025
            ),
            Decimal("0.00"),
        )
    )
    tax_difference = money(abs(new_analysis.projected_annual_tax - applicable_tax))
    tax_tolerance = max(Decimal("25.00"), money(applicable_tax * Decimal("0.01")))
    if tax_difference > tax_tolerance:
        findings.append(
            ObservedFinding(
                finding_type="PROPERTY_TAX_PROJECTION_MISMATCH",
                impact_total=tax_difference,
                monthly_impact=money(tax_difference / Decimal(12)),
            )
        )

    tax_bill = next(bill for bill in account.tax_bills if bill.tax_year == 2025)
    policy = next(
        policy for policy in account.insurance_policies if policy.renewal_date.year == 2025
    )
    principal_and_interest = money(
        account.payments[0].principal + account.payments[0].interest
    )
    _, expected_shortage, _, _ = _analysis_expected_values(
        new_analysis,
        principal_and_interest,
        tuple(due_date.month for due_date in tax_bill.due_dates),
        policy.renewal_date.month,
    )
    shortage_difference = money(abs(new_analysis.stated_shortage - expected_shortage))
    if shortage_difference > Decimal("10.00"):
        findings.append(
            ObservedFinding(
                finding_type="ESCROW_SHORTAGE_CALCULATION_ERROR",
                impact_total=shortage_difference,
                monthly_impact=money(shortage_difference / Decimal(12)),
            )
        )

    tax_transactions = [
        transaction
        for transaction in account.escrow_ledger
        if transaction.type == "TAX_DISBURSEMENT"
    ]
    duplicate_impact = Decimal("0.00")
    for first, second in combinations(tax_transactions, 2):
        if first.payee != second.payee:
            continue
        if abs(second.date - first.date) > timedelta(days=45):
            continue
        larger = max(abs(first.amount), abs(second.amount))
        if larger and abs(abs(first.amount) - abs(second.amount)) <= larger * Decimal("0.02"):
            duplicate_impact = max(duplicate_impact, abs(second.amount))
    if duplicate_impact:
        findings.append(
            ObservedFinding(
                finding_type="DUPLICATE_TAX_DISBURSEMENT",
                impact_total=money(duplicate_impact),
                monthly_impact=Decimal("0.00"),
            )
        )

    residual = payment_residual(account)
    transfer_date = account.servicing_periods[1].start_date
    old_payment = max(
        (payment for payment in account.payments if payment.date < transfer_date),
        key=lambda payment: payment.date,
    )
    new_payment = min(
        (payment for payment in account.payments if payment.date >= transfer_date),
        key=lambda payment: payment.date,
    )
    increase = money(new_payment.total - old_payment.total)
    payment_tolerance = max(Decimal("10.00"), money(increase * Decimal("0.02")))
    if residual > payment_tolerance:
        findings.append(
            ObservedFinding(
                finding_type="UNEXPLAINED_PAYMENT_INCREASE",
                impact_total=money(residual * Decimal(12)),
                monthly_impact=residual,
            )
        )

    return findings
