"""Escrow projection calculations shared within account construction."""

from calendar import monthrange
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.schemas import EscrowAnalysis

from data.generator.money import CENT, money, split_money


def add_months(value: date, months: int) -> date:
    """Shift a date by whole calendar months."""

    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def projection_months(analysis_date: date) -> list[date]:
    """Return the twelve payment months following an analysis point."""

    first = date(analysis_date.year, analysis_date.month, 1)
    if analysis_date.day > 1:
        first = add_months(first, 1)
    return [add_months(first, offset) for offset in range(12)]


def projected_low_balance(
    current_balance: Decimal,
    monthly_escrow: Decimal,
    annual_tax: Decimal,
    annual_insurance: Decimal,
    tax_due_months: tuple[int, ...],
    insurance_due_month: int,
    analysis_date: date,
) -> Decimal:
    """Project the lowest month-end balance in the next twelve months."""

    months = projection_months(analysis_date)
    tax_installments = split_money(annual_tax, len(tax_due_months))
    tax_by_month = dict(zip(tax_due_months, tax_installments, strict=True))
    balance = money(current_balance)
    low_balance = balance

    for month in months:
        balance = money(balance + monthly_escrow)
        if month.month in tax_by_month:
            balance = money(balance - tax_by_month[month.month])
        if month.month == insurance_due_month:
            balance = money(balance - annual_insurance)
        low_balance = min(low_balance, balance)

    return low_balance


def build_analysis(
    *,
    servicer_id: str,
    analysis_date: date,
    current_balance: Decimal,
    annual_tax: Decimal,
    annual_insurance: Decimal,
    tax_due_months: tuple[int, ...],
    insurance_due_month: int,
    principal_and_interest: Decimal,
) -> EscrowAnalysis:
    """Calculate a RESPA-style aggregate escrow analysis."""

    monthly_escrow = money((annual_tax + annual_insurance) / Decimal(12))
    low_balance = projected_low_balance(
        current_balance=current_balance,
        monthly_escrow=monthly_escrow,
        annual_tax=annual_tax,
        annual_insurance=annual_insurance,
        tax_due_months=tax_due_months,
        insurance_due_month=insurance_due_month,
        analysis_date=analysis_date,
    )
    cushion = money((annual_tax + annual_insurance) / Decimal(6))
    shortage = max(money(cushion - low_balance), Decimal("0.00"))
    shortage_monthly = (shortage / Decimal(12)).quantize(CENT, rounding=ROUND_HALF_UP)

    return EscrowAnalysis(
        servicer_id=servicer_id,
        analysis_date=analysis_date,
        projected_annual_tax=annual_tax,
        projected_annual_insurance=annual_insurance,
        current_balance=current_balance,
        stated_shortage=shortage,
        stated_monthly_escrow=monthly_escrow,
        stated_shortage_monthly=shortage_monthly,
        new_total_payment=money(
            principal_and_interest + monthly_escrow + shortage_monthly
        ),
    )
