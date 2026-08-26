"""Independent structured-data oracle used to validate injected labels."""

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from itertools import combinations

from app.schemas import MortgageAccount
from app.schemas.ground_truth import FindingType

from data.faults.common import payment_residual
from data.generator.money import money
from data.generator.validate import (
    _analysis_expected_values_for_charges,
    _split_money,
)


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

    actual_tax_charges: list[tuple[int, Decimal]] = []
    for tax_bill in (bill for bill in account.tax_bills if bill.tax_year == 2025):
        installments = _split_money(tax_bill.annual_amount, len(tax_bill.due_dates))
        actual_tax_charges.extend(
            (due_date.month, installment)
            for due_date, installment in zip(
                tax_bill.due_dates,
                installments,
                strict=True,
            )
        )
    actual_tax_total = sum(
        (amount for _, amount in actual_tax_charges),
        Decimal("0.00"),
    )
    projected_tax_charges: list[tuple[int, Decimal]] = []
    allocated = Decimal("0.00")
    for index, (month, actual_amount) in enumerate(actual_tax_charges):
        if index == len(actual_tax_charges) - 1:
            projected_amount = money(new_analysis.projected_annual_tax - allocated)
        else:
            projected_amount = money(
                new_analysis.projected_annual_tax * actual_amount / actual_tax_total
            )
            allocated = money(allocated + projected_amount)
        projected_tax_charges.append((month, projected_amount))
    charges = projected_tax_charges
    for policy in (
        policy
        for policy in account.insurance_policies
        if policy.renewal_date.year == 2025
    ):
        charges.append(
            (policy.renewal_date.month, new_analysis.projected_annual_insurance)
        )
    principal_and_interest = money(
        account.payments[0].principal + account.payments[0].interest
    )
    _, expected_shortage, _, _ = _analysis_expected_values_for_charges(
        new_analysis,
        principal_and_interest,
        charges,
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
