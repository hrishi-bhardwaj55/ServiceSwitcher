"""End-to-end tests for fault corpus generation and label validation."""

from collections import Counter
from decimal import Decimal
from pathlib import Path

import pytest
from app.schemas import GroundTruthCase, MortgageAccount

from data.faults.inject import build_cases, write_cases
from data.faults.validate import validate_ground_truth
from data.generator.generate import generate_accounts, write_accounts


@pytest.fixture(scope="module")
def clean_accounts() -> list[MortgageAccount]:
    return generate_accounts()


def test_case_builder_is_deterministic_and_has_exact_buckets(
    clean_accounts: list[MortgageAccount],
) -> None:
    first_accounts, first_cases = build_cases(clean_accounts)
    second_accounts, second_cases = build_cases(clean_accounts)

    assert [account.model_dump_json() for account in first_accounts] == [
        account.model_dump_json() for account in second_accounts
    ]
    assert [case.model_dump_json() for case in first_cases] == [
        case.model_dump_json() for case in second_cases
    ]
    assert Counter(case.bucket for case in first_cases) == {
        "faulted": 200,
        "clean": 60,
        "clean_but_tricky": 40,
    }
    assert Counter(
        finding for case in first_cases for finding in case.expected_findings
    ) == {
        "ESCROW_BALANCE_MISMATCH": 40,
        "PROPERTY_TAX_PROJECTION_MISMATCH": 40,
        "ESCROW_SHORTAGE_CALCULATION_ERROR": 40,
        "DUPLICATE_TAX_DISBURSEMENT": 40,
        "UNEXPLAINED_PAYMENT_INCREASE": 40,
    }
    assert Counter(
        case.tricky_condition
        for case in first_cases
        if case.bucket == "clean_but_tricky"
    ) == {
        "LEGITIMATE_TAX_REASSESSMENT": 8,
        "LEGITIMATE_INSURANCE_PREMIUM_JUMP": 10,
        "DISTINCT_TAX_AUTHORITIES_CLOSE_TOGETHER": 10,
        "FULLY_EXPLAINED_PAYMENT_INCREASE": 12,
    }


def test_clean_bucket_is_not_mutated(clean_accounts: list[MortgageAccount]) -> None:
    case_accounts, _ = build_cases(clean_accounts)

    for index in range(200, 260):
        assert case_accounts[index].model_dump_json() == clean_accounts[index].model_dump_json()


def test_written_corpus_validates_300_of_300(
    clean_accounts: list[MortgageAccount],
    tmp_path: Path,
) -> None:
    accounts, cases = build_cases(clean_accounts)
    accounts_path = tmp_path / "accounts"
    cases_path = tmp_path / "ground_truth" / "cases.jsonl"
    write_accounts(accounts, accounts_path)
    write_cases(cases, cases_path)

    report = validate_ground_truth(accounts_path, cases_path)

    assert report.ok
    assert report.valid == 300


def test_validator_rejects_incorrect_impact_label(
    clean_accounts: list[MortgageAccount],
    tmp_path: Path,
) -> None:
    accounts, cases = build_cases(clean_accounts)
    first = cases[0]
    cases[0] = GroundTruthCase.model_validate(
        first.model_dump()
        | {"expected_impact_total": first.expected_impact_total + Decimal("0.01")}
    )
    accounts_path = tmp_path / "accounts"
    cases_path = tmp_path / "cases.jsonl"
    write_accounts(accounts, accounts_path)
    write_cases(cases, cases_path)

    report = validate_ground_truth(accounts_path, cases_path)

    assert not report.ok
    assert any(
        "expected_impact_total" in error
        for source_errors in report.errors.values()
        for error in source_errors
    )
