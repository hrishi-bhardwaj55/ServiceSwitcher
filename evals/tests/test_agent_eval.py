from decimal import Decimal
from pathlib import Path

import pytest

from evals.runners.agent_eval import (
    AgentCaseResult,
    calculate_metrics,
    execute_cases,
    load_ground_truth,
    load_tool_expectations,
    load_trajectory,
    render_report,
)

ROOT = Path(__file__).parents[2]


def _result(
    case_id,
    bucket,
    expected,
    predicted,
    expected_tools,
    tool_calls,
    *,
    steps=0,
    cost="0",
    latency="1",
    review=False,
    tool_error=False,
    execution_error=None,
):
    return AgentCaseResult(
        case_id=case_id,
        bucket=bucket,
        expected_findings=frozenset(expected),
        predicted_findings=frozenset(predicted),
        expected_tools=frozenset(expected_tools),
        tool_calls=tuple(tool_calls),
        steps=steps,
        cost_usd=Decimal(cost),
        latency_seconds=Decimal(latency),
        requires_review=review,
        had_tool_error=tool_error,
        execution_error=execution_error,
    )


def test_agent_dataset_covers_every_finding_category_and_clean():
    cases = load_ground_truth(ROOT / "data" / "ground_truth" / "cases.jsonl")
    expectations = load_tool_expectations(ROOT / "evals" / "datasets" / "agent.jsonl")

    assert len(cases) == 300
    assert len(expectations) == 6
    assert expectations["CLEAN"] == frozenset()
    assert expectations["PROPERTY_TAX_PROJECTION_MISMATCH"] == {
        "compare_tax_projection"
    }
    assert expectations["ESCROW_SHORTAGE_CALCULATION_ERROR"] == {
        "get_extracted_field"
    }


def test_metrics_score_findings_tools_recovery_cost_and_percentiles():
    results = [
        _result(
            "CASE-1",
            "faulted",
            ["A"],
            ["A"],
            ["tool_a"],
            ["tool_a"],
            steps=1,
            cost="0.01",
            latency="1",
            tool_error=True,
        ),
        _result(
            "CASE-2",
            "faulted",
            ["B"],
            ["C"],
            ["tool_b"],
            ["tool_b", "tool_b", "extra"],
            steps=3,
            cost="0.03",
            latency="4",
            review=True,
        ),
        _result(
            "CASE-3",
            "clean",
            [],
            [],
            [],
            [],
            latency="2",
        ),
        _result(
            "CASE-4",
            "clean_but_tricky",
            [],
            ["D"],
            [],
            ["extra"],
            steps=1,
            cost="0.02",
            latency="3",
            execution_error="provider failed",
        ),
    ]

    metrics = calculate_metrics(results)

    assert metrics.precision == Decimal(1) / Decimal(3)
    assert metrics.recall == Decimal("0.5")
    assert metrics.f1 == Decimal("0.4")
    assert metrics.task_success_rate == Decimal("0.5")
    assert metrics.clean_false_positive_rate == Decimal("0.5")
    assert metrics.tricky_false_positive_rate == Decimal(1)
    assert metrics.tool_selection_accuracy == Decimal("0.5")
    assert metrics.total_unnecessary_tool_calls == 3
    assert metrics.unnecessary_tool_calls_per_run == Decimal("0.75")
    assert metrics.average_steps == Decimal("1.25")
    assert metrics.p95_steps == 3
    assert metrics.failure_recovery_rate == Decimal(1)
    assert metrics.average_cost_usd == Decimal("0.015")
    assert metrics.p50_latency_seconds == Decimal(2)
    assert metrics.p95_latency_seconds == Decimal(4)
    assert metrics.review_rate == Decimal("0.25")
    assert metrics.execution_failures == 1


def test_duplicate_case_results_and_empty_result_set_are_rejected():
    with pytest.raises(ValueError, match="at least one"):
        calculate_metrics([])

    result = _result("CASE-1", "clean", [], [], [], [])
    with pytest.raises(ValueError, match="unique"):
        calculate_metrics([result, result])


def test_report_states_direct_scoring_and_operational_metrics():
    metrics = calculate_metrics([_result("CASE-1", "clean", [], [], [], [])])

    report = render_report(metrics, model="test-model")

    assert "no LLM judge is used" in report
    assert "Exact tool-set accuracy | 100.00%" in report
    assert "Failure recovery rate | n/a" in report
    assert "Model cost per audit (mean) | $0.000000" in report


def test_execute_cases_applies_category_expectations_and_preserves_order():
    cases = load_ground_truth(ROOT / "data" / "ground_truth" / "cases.jsonl")[:2]
    expectations = load_tool_expectations(ROOT / "evals" / "datasets" / "agent.jsonl")

    def run_case(case, expected_tools):
        return _result(
            case.case_id,
            case.bucket,
            case.expected_findings,
            case.expected_findings,
            expected_tools,
            expected_tools,
        )

    results = execute_cases(cases, expectations, run_case, workers=2)

    assert [result.case_id for result in results] == [case.case_id for case in cases]
    assert all(result.tool_selection_correct for result in results)


def test_trajectory_loader_validates_jsonl(tmp_path):
    path = tmp_path / "CASE-1.jsonl"
    path.write_text(
        '{"timestamp":"2026-01-01T00:00:00Z","audit_id":"CASE-1",'
        '"event":"tool_call","finding_type":"A","status":"ok",'
        '"tool":"get_extracted_field","arguments":{},"result_summary":"ok",'
        '"input_tokens":1,"output_tokens":1,"cost_usd":"0.1",'
        '"cumulative_cost_usd":"0.1","steps_used":1}\n',
        encoding="utf-8",
    )

    events = load_trajectory(path)

    assert len(events) == 1
    assert events[0].tool == "get_extracted_field"

    path.write_text("not-json\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid trajectory"):
        load_trajectory(path)
