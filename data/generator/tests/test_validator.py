"""Mutation tests that prove the validator rejects inconsistent account data."""

from datetime import timedelta
from decimal import Decimal

import pytest
from app.schemas import MortgageAccount

from data.generator.generate import generate_accounts
from data.generator.money import money
from data.generator.validate import validate_account


@pytest.fixture(scope="module")
def account() -> MortgageAccount:
    return generate_accounts(count=1, seed=73)[0]


def test_validator_rejects_payment_component_mismatch(account: MortgageAccount) -> None:
    changed = account.payments[0].model_copy(
        update={"total": money(account.payments[0].total + Decimal("0.01"))}
    )
    mutated = account.model_copy(update={"payments": [changed, *account.payments[1:]]})

    assert any("principal+interest+escrow" in error for error in validate_account(mutated))


def test_validator_rejects_broken_ledger_chain(account: MortgageAccount) -> None:
    changed = account.escrow_ledger[4].model_copy(
        update={
            "balance_after": money(
                account.escrow_ledger[4].balance_after + Decimal("100.00")
            )
        }
    )
    ledger = account.escrow_ledger.copy()
    ledger[4] = changed
    mutated = account.model_copy(update={"escrow_ledger": ledger})

    assert any("chained balance" in error or "balance is" in error for error in validate_account(mutated))


def test_validator_rejects_disbursement_on_wrong_date(account: MortgageAccount) -> None:
    index = next(
        index
        for index, transaction in enumerate(account.escrow_ledger)
        if transaction.type == "TAX_DISBURSEMENT"
    )
    ledger = account.escrow_ledger.copy()
    ledger[index] = ledger[index].model_copy(
        update={"date": ledger[index].date + timedelta(days=1)}
    )
    mutated = account.model_copy(update={"escrow_ledger": ledger})

    assert any("tax disbursements" in error for error in validate_account(mutated))


def test_validator_rejects_transfer_balance_discontinuity(account: MortgageAccount) -> None:
    analyses = account.escrow_analyses.copy()
    analyses[2] = analyses[2].model_copy(
        update={"current_balance": money(analyses[2].current_balance + Decimal("1.00"))}
    )
    mutated = account.model_copy(update={"escrow_analyses": analyses})

    assert any("preserve the transfer balance" in error for error in validate_account(mutated))
