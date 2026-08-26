import json
from decimal import Decimal
from pathlib import Path

import pytest

from evals.runners.engine_eval import (
    EvaluationCase,
    evaluate_cases,
    predicted_values,
    render_report,
    transfer_date,
)

FIXTURE = Path(__file__).parents[1] / "fixtures" / "engine_eval_five_cases.json"


@pytest.fixture
def five_case_fixture():
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cases = [
        EvaluationCase(
            case_id=case["case_id"],
            account_id=case["account_id"],
            bucket=case["bucket"],
            expected_findings=frozenset(case["expected_findings"]),
            expected_impact_total=Decimal(case["expected_impact_total"]),
        )
        for case in raw["cases"]
    ]
    accounts = {
        case.account_id: {
            "account_id": case.account_id,
            "servicing_periods": [
                {"start_date": "2024-01-01"},
                {"start_date": "2024-06-01"},
            ],
        }
        for case in cases
    }
    return cases, accounts, raw["responses"]


def test_runner_scores_five_case_fixture(five_case_fixture):
    cases, accounts, responses = five_case_fixture

    def reconcile(account, requested_transfer_date):
        assert requested_transfer_date == "2024-06-01"
        return responses[account["account_id"]]

    metrics, results = evaluate_cases(cases, accounts, reconcile)

    assert len(results) == 5
    assert metrics.total_cases == 5
    assert metrics.faulted_cases == 2
    assert metrics.clean_cases == 3
    assert metrics.true_positives == 1
    assert metrics.false_positives == 2
    assert metrics.false_negatives == 1
    assert metrics.precision == Decimal(1) / Decimal(3)
    assert metrics.recall == Decimal("0.5")
    assert metrics.f1 == Decimal("0.4")
    assert metrics.false_positive_rate == Decimal(1) / Decimal(3)
    assert metrics.impact_mean_absolute_error == Decimal("12.00")
    assert not metrics.meets_target


def test_explained_outcome_is_not_scored_as_a_finding():
    finding_types, impact = predicted_values(
        {
            "findings": [
                {"finding_type": "EXPLAINED", "difference": "99.00"},
                {"finding_type": "ESCROW_BALANCE_MISMATCH", "difference": "-2.50"},
            ]
        }
    )

    assert finding_types == {"ESCROW_BALANCE_MISMATCH"}
    assert impact == Decimal("2.50")


def test_report_records_target_verdict(five_case_fixture):
    cases, accounts, responses = five_case_fixture
    metrics, _ = evaluate_cases(
        cases,
        accounts,
        lambda account, _: responses[account["account_id"]],
    )

    report = render_report(metrics)

    assert "Precision | 33.33%" in report
    assert "Financial-impact mean absolute error | $12.0000" in report
    assert "**Acceptance verdict: FAIL.**" in report


def test_transfer_date_requires_two_servicing_periods():
    with pytest.raises(ValueError, match="has no servicing transfer"):
        transfer_date({"account_id": "SS-0001", "servicing_periods": []})
