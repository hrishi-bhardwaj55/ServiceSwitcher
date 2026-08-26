"""Collection-level tests for deterministic synthetic account generation."""

from decimal import Decimal

import pytest
from app.schemas import MortgageAccount

from data.generator.generate import generate_accounts
from data.generator.validate import validate_account


@pytest.fixture(scope="module")
def accounts() -> list[MortgageAccount]:
    return generate_accounts()


def test_generator_is_byte_stable_for_a_fixed_seed() -> None:
    first = [account.model_dump_json() for account in generate_accounts(count=12, seed=41)]
    second = [account.model_dump_json() for account in generate_accounts(count=12, seed=41)]

    assert first == second


def test_generated_collection_has_required_variation(
    accounts: list[MortgageAccount],
) -> None:
    assert len(accounts) == 300
    assert len({account.account_id for account in accounts}) == 300
    assert {account.term_months for account in accounts} == {180, 360}
    assert {
        tuple(due_date.month for due_date in account.tax_bills[0].due_dates)
        for account in accounts
    } == {(12,), (6, 12), (3, 6, 9, 12)}
    assert {
        next(
            index
            for index, payment in enumerate(account.payments, start=1)
            if payment.date == account.servicing_periods[1].start_date
        )
        for account in accounts
    } == set(range(6, 13))
    assert sum(
        account.tax_bills[1].annual_amount
        >= account.tax_bills[0].annual_amount * Decimal("1.40")
        for account in accounts
    ) == 60


def test_validator_accepts_all_generated_accounts(accounts: list[MortgageAccount]) -> None:
    failures = {
        account.account_id: errors
        for account in accounts
        if (errors := validate_account(account))
    }

    assert failures == {}
