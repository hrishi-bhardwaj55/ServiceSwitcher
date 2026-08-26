"""Clean-but-tricky cases must remain valid and produce no findings."""

from datetime import timedelta
from decimal import Decimal

from data.faults.common import payment_residual
from data.faults.oracle import evaluate
from data.faults.tricky import (
    with_distinct_tax_authorities,
    with_fully_explained_payment_increase,
    with_insurance_premium_jump,
)
from data.generator.generate import generate_accounts
from data.generator.money import money
from data.generator.validate import validate_account


def test_legitimate_tax_reassessment_is_clean() -> None:
    account = generate_accounts(count=261)[260]

    assert account.tax_bills[1].annual_amount >= money(
        account.tax_bills[0].annual_amount * Decimal("1.40")
    )
    assert validate_account(account) == []
    assert evaluate(account) == []


def test_insurance_premium_jump_is_clean() -> None:
    account = with_insurance_premium_jump(generate_accounts(count=262)[261], variant=4)
    premiums = {
        policy.renewal_date.year: policy.annual_premium
        for policy in account.insurance_policies
    }

    assert premiums[2025] == money(premiums[2024] * Decimal("1.60"))
    assert validate_account(account) == []
    assert evaluate(account) == []


def test_close_tax_disbursements_to_distinct_authorities_are_clean() -> None:
    account = with_distinct_tax_authorities(generate_accounts(count=263)[262], variant=0)
    transactions = [
        transaction
        for transaction in account.escrow_ledger
        if transaction.type == "TAX_DISBURSEMENT" and transaction.date.year == 2024
    ]

    assert len(transactions) == 2
    assert transactions[1].date - transactions[0].date == timedelta(days=50)
    assert transactions[0].payee != transactions[1].payee
    assert validate_account(account) == []
    assert evaluate(account) == []


def test_documented_payment_increase_is_fully_explained() -> None:
    account = with_fully_explained_payment_increase(
        generate_accounts(count=264)[263],
        variant=3,
    )
    transfer_date = account.servicing_periods[1].start_date
    old_total = next(
        payment.total
        for payment in reversed(account.payments)
        if payment.date < transfer_date
    )
    new_total = next(
        payment.total for payment in account.payments if payment.date >= transfer_date
    )

    assert new_total > old_total
    assert payment_residual(account) <= Decimal("10.00")
    assert validate_account(account) == []
    assert evaluate(account) == []
