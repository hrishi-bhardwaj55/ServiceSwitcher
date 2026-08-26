"""Property tests for amortization and escrow ledger arithmetic."""

from datetime import date, timedelta
from decimal import Decimal

from app.schemas import EscrowTransaction
from hypothesis import given, settings
from hypothesis import strategies as st

from data.generator.money import amortize, money
from data.generator.validate import validate_ledger_chain


@given(
    principal_cents=st.integers(min_value=18_000_000, max_value=75_000_000),
    rate_units=st.integers(min_value=30_000, max_value=75_000),
    term_months=st.sampled_from((180, 360)),
    periods=st.integers(min_value=1, max_value=60),
)
@settings(max_examples=250, deadline=None)
def test_amortization_recurrence_is_cent_exact(
    principal_cents: int,
    rate_units: int,
    term_months: int,
    periods: int,
) -> None:
    original = money(Decimal(principal_cents) / Decimal(100))
    annual_rate = Decimal(rate_units) / Decimal(1_000_000)
    scheduled_payment, lines = amortize(
        original,
        annual_rate,
        term_months,
        periods,
    )
    balance = original

    for line in lines:
        assert line.interest == money(balance * annual_rate / Decimal(12))
        assert line.principal == money(scheduled_payment - line.interest)
        balance = money(balance - line.principal)
        assert line.balance_after == balance

    assert money(sum((line.principal for line in lines), Decimal("0.00"))) == money(
        original - balance
    )


@given(
    amounts_in_cents=st.lists(
        st.integers(min_value=-2_000_000, max_value=2_000_000),
        min_size=1,
        max_size=60,
    )
)
@settings(max_examples=250, deadline=None)
def test_ledger_chaining_accepts_exact_cumulative_balances(
    amounts_in_cents: list[int],
) -> None:
    balance = Decimal("0.00")
    ledger: list[EscrowTransaction] = []
    for index, amount_in_cents in enumerate(amounts_in_cents):
        amount = money(Decimal(amount_in_cents) / Decimal(100))
        balance = money(balance + amount)
        ledger.append(
            EscrowTransaction(
                date=date(2024, 1, 1) + timedelta(days=index),
                type="ADJUSTMENT",
                amount=amount,
                payee="PROPERTY_TEST",
                balance_after=balance,
            )
        )

    assert validate_ledger_chain(ledger) == []

    corrupted = ledger.copy()
    corrupted[-1] = corrupted[-1].model_copy(
        update={"balance_after": money(corrupted[-1].balance_after + Decimal("0.01"))}
    )
    assert any("balance is" in error for error in validate_ledger_chain(corrupted))
