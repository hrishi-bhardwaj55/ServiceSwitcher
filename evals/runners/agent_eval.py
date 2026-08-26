"""Evaluate the complete investigator pipeline against synthetic ground truth."""

from __future__ import annotations

import argparse
import math
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal
from uuid import uuid4

from app.agents import AgentDependencies, build_audit_graph, initial_audit_state
from app.agents.cli import document_refs, load_account
from app.agents.documents import FallbackPdfDocumentProcessor
from app.agents.investigator import OpenAIInvestigatorModel
from app.agents.tracing import TrajectoryEvent
from app.embeddings import OpenAIEmbeddingClient
from app.llm import CachedLLMClient, LLMClient, OpenAIResponsesClient
from app.retrieval import PostgresRuleStore, RegulationRetriever, load_corpus
from app.retrieval.database import managed_database_engine
from app.retrieval.ingest import ingest_chunks
from app.schemas.ground_truth import GroundTruthCase
from app.schemas.mortgage import CanonicalModel
from app.tools import ToolDependencies
from app.tools.dependencies import (
    AuditRecord,
    InMemoryAuditDataSource,
    InMemoryMissingInformationSink,
)
from app.tools.engine import HttpReconciliationEngine
from dotenv import load_dotenv
from pydantic import model_validator

EXPECTED_CASE_COUNT = 300
CLEAN_CATEGORY = "CLEAN"
AgentCategory = Literal[
    "ESCROW_BALANCE_MISMATCH",
    "PROPERTY_TAX_PROJECTION_MISMATCH",
    "ESCROW_SHORTAGE_CALCULATION_ERROR",
    "DUPLICATE_TAX_DISBURSEMENT",
    "UNEXPLAINED_PAYMENT_INCREASE",
    "CLEAN",
]
AgentToolName = Literal[
    "get_extracted_field",
    "get_escrow_ledger",
    "get_payment_history",
    "calculate_escrow_continuity",
    "calculate_payment_breakdown",
    "compare_tax_projection",
    "search_regulations",
    "mark_information_missing",
]


class AgentToolExpectation(CanonicalModel):
    category: AgentCategory
    expected_tools: list[AgentToolName]

    @model_validator(mode="after")
    def validate_unique_tools(self) -> AgentToolExpectation:
        if len(self.expected_tools) != len(set(self.expected_tools)):
            raise ValueError("expected tools must be unique")
        return self


@dataclass(frozen=True)
class AgentCaseResult:
    case_id: str
    bucket: str
    expected_findings: frozenset[str]
    predicted_findings: frozenset[str]
    expected_tools: frozenset[str]
    tool_calls: tuple[str, ...]
    steps: int
    cost_usd: Decimal
    latency_seconds: Decimal
    requires_review: bool
    had_tool_error: bool
    had_model_error: bool
    execution_error: str | None = None

    @property
    def task_succeeded(self) -> bool:
        return self.execution_error is None and self.predicted_findings == self.expected_findings

    @property
    def tool_selection_correct(self) -> bool:
        return frozenset(self.tool_calls) == self.expected_tools

    @property
    def unnecessary_tool_calls(self) -> int:
        remaining = set(self.expected_tools)
        unnecessary = 0
        for tool in self.tool_calls:
            if tool in remaining:
                remaining.remove(tool)
            else:
                unnecessary += 1
        return unnecessary


Progress = Callable[[int, int, AgentCaseResult], None]


@dataclass(frozen=True)
class AgentEvaluationMetrics:
    total_cases: int
    faulted_cases: int
    clean_cases: int
    tricky_cases: int
    true_positives: int
    false_positives: int
    false_negatives: int
    clean_false_positive_cases: int
    tricky_false_positive_cases: int
    successful_cases: int
    correct_tool_selection_cases: int
    faulted_correct_tool_selection_cases: int
    total_unnecessary_tool_calls: int
    total_steps: int
    step_values: tuple[int, ...]
    recovery_opportunities: int
    recovered_cases: int
    model_error_cases: int
    total_cost_usd: Decimal
    latency_values: tuple[Decimal, ...]
    review_cases: int
    execution_failures: int

    @property
    def precision(self) -> Decimal:
        return _ratio(self.true_positives, self.true_positives + self.false_positives)

    @property
    def recall(self) -> Decimal:
        return _ratio(self.true_positives, self.true_positives + self.false_negatives)

    @property
    def f1(self) -> Decimal:
        denominator = (2 * self.true_positives) + self.false_positives + self.false_negatives
        return _ratio(2 * self.true_positives, denominator)

    @property
    def clean_false_positive_rate(self) -> Decimal:
        if self.clean_cases == 0:
            return Decimal(0)
        return _ratio(self.clean_false_positive_cases, self.clean_cases)

    @property
    def tricky_false_positive_rate(self) -> Decimal:
        if self.tricky_cases == 0:
            return Decimal(0)
        return _ratio(self.tricky_false_positive_cases, self.tricky_cases)

    @property
    def task_success_rate(self) -> Decimal:
        return _ratio(self.successful_cases, self.total_cases)

    @property
    def tool_selection_accuracy(self) -> Decimal:
        return _ratio(self.correct_tool_selection_cases, self.total_cases)

    @property
    def faulted_tool_selection_accuracy(self) -> Decimal:
        return _ratio(self.faulted_correct_tool_selection_cases, self.faulted_cases)

    @property
    def unnecessary_tool_calls_per_run(self) -> Decimal:
        return Decimal(self.total_unnecessary_tool_calls) / self.total_cases

    @property
    def average_steps(self) -> Decimal:
        return Decimal(self.total_steps) / self.total_cases

    @property
    def p95_steps(self) -> int:
        return int(_nearest_rank(self.step_values, Decimal("0.95")))

    @property
    def failure_recovery_rate(self) -> Decimal | None:
        if self.recovery_opportunities == 0:
            return None
        return Decimal(self.recovered_cases) / self.recovery_opportunities

    @property
    def average_cost_usd(self) -> Decimal:
        return self.total_cost_usd / self.total_cases

    @property
    def p50_latency_seconds(self) -> Decimal:
        return _nearest_rank(self.latency_values, Decimal("0.50"))

    @property
    def p95_latency_seconds(self) -> Decimal:
        return _nearest_rank(self.latency_values, Decimal("0.95"))

    @property
    def review_rate(self) -> Decimal:
        return _ratio(self.review_cases, self.total_cases)


def load_ground_truth(path: Path) -> list[GroundTruthCase]:
    cases: list[GroundTruthCase] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            cases.append(GroundTruthCase.model_validate_json(line))
        except ValueError as error:
            raise ValueError(f"invalid ground truth at {path}:{line_number}") from error
    ids = [case.case_id for case in cases]
    if not cases:
        raise ValueError(f"no ground-truth cases found in {path}")
    if len(ids) != len(set(ids)):
        raise ValueError("ground-truth case ids must be unique")
    return cases


def load_tool_expectations(path: Path) -> dict[str, frozenset[str]]:
    expectations: dict[str, frozenset[str]] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            expectation = AgentToolExpectation.model_validate_json(line)
        except ValueError as error:
            raise ValueError(f"invalid agent dataset at {path}:{line_number}") from error
        if expectation.category in expectations:
            raise ValueError(f"duplicate agent category {expectation.category}")
        expectations[expectation.category] = frozenset(expectation.expected_tools)
    expected_categories = set(AgentCategory.__args__)
    if expectations.keys() != expected_categories:
        missing = sorted(expected_categories - expectations.keys())
        extra = sorted(expectations.keys() - expected_categories)
        raise ValueError(f"agent categories differ; missing={missing}, extra={extra}")
    return expectations


def category_for(case: GroundTruthCase) -> str:
    if not case.expected_findings:
        return CLEAN_CATEGORY
    return case.expected_findings[0]


@dataclass(frozen=True)
class AgentEvaluationRuntime:
    accounts_root: Path
    documents_root: Path
    regulations: RegulationRetriever
    engine: HttpReconciliationEngine
    investigator: OpenAIInvestigatorModel
    extraction_client: LLMClient
    trace_root: Path

    def run_case(
        self,
        case: GroundTruthCase,
        expected_tools: frozenset[str],
    ) -> AgentCaseResult:
        trace_path = self.trace_root / f"{case.case_id}.jsonl"
        started = time.perf_counter()
        execution_error = None
        predicted: frozenset[str] = frozenset()
        steps = 0
        cost = Decimal(0)
        review = True
        try:
            account = load_account(self.accounts_root, case.account_id)
            documents = document_refs(self.documents_root, case.case_id, case.account_id)
            source = InMemoryAuditDataSource(
                [AuditRecord(audit_id=case.case_id, account=account)],
                [],
            )
            dependencies = AgentDependencies(
                tools=ToolDependencies(
                    audit_data=source,
                    engine=self.engine,
                    regulations=self.regulations,
                    missing_information=InMemoryMissingInformationSink(),
                ),
                document_store=source,
                documents=FallbackPdfDocumentProcessor(self.extraction_client),
                investigator=self.investigator,
                trace_root=self.trace_root,
            )
            result = build_audit_graph(dependencies).invoke(
                initial_audit_state(case.case_id, documents),
                {"configurable": {"thread_id": str(uuid4())}},
            )
            predicted = frozenset(
                finding.finding_type for finding in result["final_findings"]
            )
            steps = result["steps_used"]
            cost = result["cost_usd"]
            review = bool(result["requires_review"] or "__interrupt__" in result)
        except Exception as error:  # noqa: BLE001 - preserve the remaining eval cases
            execution_error = type(error).__name__

        events = load_trajectory(trace_path)
        if execution_error is not None and events:
            steps = max(event.steps_used for event in events)
            cost = max(event.cumulative_cost_usd for event in events)
        tool_events = [event for event in events if event.event == "tool_call"]
        latency = Decimal(str(round(time.perf_counter() - started, 6)))
        return AgentCaseResult(
            case_id=case.case_id,
            bucket=case.bucket,
            expected_findings=frozenset(case.expected_findings),
            predicted_findings=predicted,
            expected_tools=expected_tools,
            tool_calls=tuple(event.tool for event in tool_events if event.tool is not None),
            steps=steps,
            cost_usd=cost,
            latency_seconds=latency,
            requires_review=review,
            had_tool_error=any(event.status == "error" for event in tool_events),
            had_model_error=any(
                event.event == "model_resolution" and event.status == "error"
                for event in events
            ),
            execution_error=execution_error,
        )


def load_trajectory(path: Path) -> list[TrajectoryEvent]:
    if not path.is_file():
        return []
    events = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            events.append(TrajectoryEvent.model_validate_json(line))
        except ValueError as error:
            raise ValueError(f"invalid trajectory at {path}:{line_number}") from error
    return events


def execute_cases(
    cases: Sequence[GroundTruthCase],
    expectations: dict[str, frozenset[str]],
    run_case: Callable[[GroundTruthCase, frozenset[str]], AgentCaseResult],
    *,
    workers: int,
    progress: Progress | None = None,
) -> list[AgentCaseResult]:
    if workers < 1:
        raise ValueError("workers must be positive")
    indexed_results: dict[int, AgentCaseResult] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(run_case, case, expectations[category_for(case)]): index
            for index, case in enumerate(cases)
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            index = futures[future]
            result = future.result()
            indexed_results[index] = result
            if progress is not None:
                progress(completed, len(cases), result)
    return [indexed_results[index] for index in range(len(cases))]


def calculate_metrics(results: Sequence[AgentCaseResult]) -> AgentEvaluationMetrics:
    if not results:
        raise ValueError("agent evaluation requires at least one result")
    case_ids = [result.case_id for result in results]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("agent evaluation result ids must be unique")

    true_positives = sum(
        len(result.expected_findings & result.predicted_findings) for result in results
    )
    false_positives = sum(
        len(result.predicted_findings - result.expected_findings) for result in results
    )
    false_negatives = sum(
        len(result.expected_findings - result.predicted_findings) for result in results
    )
    clean = [result for result in results if result.bucket != "faulted"]
    tricky = [result for result in results if result.bucket == "clean_but_tricky"]
    recoveries = [result for result in results if result.had_tool_error]
    return AgentEvaluationMetrics(
        total_cases=len(results),
        faulted_cases=sum(result.bucket == "faulted" for result in results),
        clean_cases=len(clean),
        tricky_cases=len(tricky),
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        clean_false_positive_cases=sum(bool(result.predicted_findings) for result in clean),
        tricky_false_positive_cases=sum(bool(result.predicted_findings) for result in tricky),
        successful_cases=sum(result.task_succeeded for result in results),
        correct_tool_selection_cases=sum(result.tool_selection_correct for result in results),
        faulted_correct_tool_selection_cases=sum(
            result.tool_selection_correct for result in results if result.bucket == "faulted"
        ),
        total_unnecessary_tool_calls=sum(result.unnecessary_tool_calls for result in results),
        total_steps=sum(result.steps for result in results),
        step_values=tuple(result.steps for result in results),
        recovery_opportunities=len(recoveries),
        recovered_cases=sum(result.task_succeeded for result in recoveries),
        model_error_cases=sum(result.had_model_error for result in results),
        total_cost_usd=sum((result.cost_usd for result in results), Decimal(0)),
        latency_values=tuple(result.latency_seconds for result in results),
        review_cases=sum(result.requires_review for result in results),
        execution_failures=sum(result.execution_error is not None for result in results),
    )


def render_report(metrics: AgentEvaluationMetrics, *, model: str) -> str:
    recovery = (
        "n/a (0 tool-error cases)"
        if metrics.failure_recovery_rate is None
        else (
            f"{_percent(metrics.failure_recovery_rate)} "
            f"({metrics.recovered_cases}/{metrics.recovery_opportunities})"
        )
    )
    return f"""# End-to-end investigator evaluation

Model: `{model}`. Dataset: {metrics.total_cases} synthetic audits ({metrics.faulted_cases}
faulted, {metrics.clean_cases} clean including {metrics.tricky_cases} clean-but-tricky).
Correctness is scored directly against ground truth; no LLM judge is used.

## Finding quality

| Metric | Result |
|---|---:|
| Precision | {_percent(metrics.precision)} |
| Recall | {_percent(metrics.recall)} |
| F1 | {_percent(metrics.f1)} |
| Task success (exact finding set) | {_percent(metrics.task_success_rate)} |
| Clean-case false-positive rate | {_percent(metrics.clean_false_positive_rate)} |
| Clean-but-tricky false-positive rate | {_percent(metrics.tricky_false_positive_rate)} |

Counts: {metrics.true_positives} true positives, {metrics.false_positives} false
positives, {metrics.false_negatives} false negatives, and {metrics.execution_failures}
execution failures.

## Agent behavior and operations

| Metric | Result |
|---|---:|
| Exact tool-set accuracy | {_percent(metrics.tool_selection_accuracy)} |
| Exact tool-set accuracy, faulted cases | {_percent(metrics.faulted_tool_selection_accuracy)} |
| Unnecessary tool calls per run | {metrics.unnecessary_tool_calls_per_run:.3f} |
| Average / p95 steps | {metrics.average_steps:.3f} / {metrics.p95_steps} |
| Failure recovery rate | {recovery} |
| Fail-closed model-error cases | {metrics.model_error_cases} |
| Human-review rate | {_percent(metrics.review_rate)} |
| Model cost per audit (mean) | ${metrics.average_cost_usd:.6f} |
| Latency p50 / p95 | {metrics.p50_latency_seconds:.3f}s / {metrics.p95_latency_seconds:.3f}s |

Model cost includes investigator input/output tokens priced by the C11 boundary;
embedding calls are not included. A tool call is unnecessary when it is outside the
expected category set or repeats a tool already credited for that run.
"""


def write_report(path: Path, report: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")


def _ratio(numerator: int, denominator: int) -> Decimal:
    if denominator == 0:
        return Decimal(1)
    return Decimal(numerator) / Decimal(denominator)


def _nearest_rank(values: Sequence[int] | Sequence[Decimal], percentile: Decimal):
    if not values:
        raise ValueError("percentile requires at least one value")
    rank = max(1, math.ceil(float(percentile * len(values))))
    return sorted(values)[rank - 1]


def _percent(value: Decimal) -> str:
    return f"{value * Decimal(100):.2f}%"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=Path("data/ground_truth/cases.jsonl"),
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("evals/datasets/agent.jsonl"),
    )
    parser.add_argument("--report", type=Path, default=Path("evals/reports/agent.md"))
    parser.add_argument("--accounts", type=Path, default=Path("data/accounts"))
    parser.add_argument("--documents", type=Path, default=Path("data/documents"))
    parser.add_argument("--corpus", type=Path, default=Path("knowledge-base/chunks.jsonl"))
    parser.add_argument("--trace-root", type=Path, default=Path("data/traces/agent-eval"))
    parser.add_argument(
        "--extraction-cache",
        type=Path,
        default=Path("data/traces/extraction_llm_cache.jsonl"),
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument("--expected-count", type=int, default=EXPECTED_CASE_COUNT)
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = _parse_args()
    cases = load_ground_truth(args.ground_truth)
    if args.case_ids:
        requested = set(args.case_ids)
        cases = [case for case in cases if case.case_id in requested]
        missing = sorted(requested - {case.case_id for case in cases})
        if missing:
            raise ValueError(f"unknown requested cases: {missing}")
    elif len(cases) != args.expected_count:
        raise ValueError(f"expected {args.expected_count} cases; found {len(cases)}")
    expectations = load_tool_expectations(args.dataset)
    trace_root = args.trace_root / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    embeddings = OpenAIEmbeddingClient.from_env()
    investigator = OpenAIInvestigatorModel.from_env()
    extraction_provider = OpenAIResponsesClient.from_env()
    extraction_client = CachedLLMClient(
        extraction_provider,
        args.extraction_cache,
        namespace=(
            f"{extraction_provider.api_base}|{extraction_provider.model}|c8-provider-v2"
        ),
    )
    with managed_database_engine() as database:
        corpus = load_corpus(args.corpus)
        ingest_chunks(corpus, embeddings, database)
        runtime = AgentEvaluationRuntime(
            accounts_root=args.accounts,
            documents_root=args.documents,
            regulations=RegulationRetriever(PostgresRuleStore(database), embeddings),
            engine=HttpReconciliationEngine.from_env(),
            investigator=investigator,
            extraction_client=extraction_client,
            trace_root=trace_root,
        )
        results = execute_cases(
            cases,
            expectations,
            runtime.run_case,
            workers=args.workers,
            progress=_print_progress,
        )
    metrics = calculate_metrics(results)
    report = render_report(metrics, model=investigator.model)
    write_report(args.report, report)
    print(report)
    print(f"Trajectories: {trace_root}")
    print(f"Wrote report to {args.report}")


def _print_progress(completed: int, total: int, result: AgentCaseResult) -> None:
    outcome = "ok" if result.task_succeeded else "miss"
    if result.execution_error:
        outcome = f"error:{result.execution_error}"
    print(
        f"[{completed:03d}/{total:03d}] {result.case_id} {outcome} "
        f"steps={result.steps} cost=${result.cost_usd:.6f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
