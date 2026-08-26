"""Exact decimal mortgage arithmetic used by the synthetic generator."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, localcontext

CENT = Decimal("0.01")
MONTHS_PER_YEAR = Decimal(12)


def money(value: Decimal | int | str) -> Decimal:
    """Round an exact value to cents with conventional financial half-up rounding."""

    if isinstance(value, float):
        raise TypeError("binary floating-point values are not valid money inputs")
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def monthly_payment(
    principal: Decimal,
    annual_rate: Decimal,
    term_months: int,
) -> Decimal:
    """Return the fixed principal-and-interest payment for an amortizing loan."""

    monthly_rate = annual_rate / MONTHS_PER_YEAR
    if monthly_rate == 0:
        return money(principal / term_months)

    with localcontext() as context:
        context.prec = 50
        growth = (Decimal(1) + monthly_rate) ** term_months
        payment = principal * monthly_rate * growth / (growth - Decimal(1))
    return money(payment)


def closed_form_balance(
    principal: Decimal,
    annual_rate: Decimal,
    scheduled_payment: Decimal,
    periods: int,
) -> Decimal:
    """Return the contractual balance after ``periods`` fixed payments."""

    monthly_rate = annual_rate / MONTHS_PER_YEAR
    if monthly_rate == 0:
        return money(principal - scheduled_payment * periods)

    with localcontext() as context:
        context.prec = 50
        growth = (Decimal(1) + monthly_rate) ** periods
        balance = principal * growth - scheduled_payment * (
            (growth - Decimal(1)) / monthly_rate
        )
    return money(balance)


@dataclass(frozen=True)
class AmortizationLine:
    interest: Decimal
    principal: Decimal
    balance_after: Decimal


def amortize(
    principal: Decimal,
    annual_rate: Decimal,
    term_months: int,
    periods: int,
) -> tuple[Decimal, list[AmortizationLine]]:
    """Build a cent-rounded amortization prefix."""

    scheduled_payment = monthly_payment(principal, annual_rate, term_months)
    balance = principal
    lines: list[AmortizationLine] = []

    for _ in range(periods):
        interest = money(balance * annual_rate / MONTHS_PER_YEAR)
        principal_component = money(scheduled_payment - interest)
        balance = money(balance - principal_component)
        lines.append(
            AmortizationLine(
                interest=interest,
                principal=principal_component,
                balance_after=balance,
            )
        )

    return scheduled_payment, lines


def split_money(total: Decimal, parts: int) -> list[Decimal]:
    """Split an amount into cent-exact installments, assigning remainder cents first."""

    if parts <= 0:
        raise ValueError("parts must be positive")

    total_cents = int(money(total) / CENT)
    base_cents, remainder = divmod(total_cents, parts)
    return [
        money(Decimal(base_cents + (1 if index < remainder else 0)) * CENT)
        for index in range(parts)
    ]
