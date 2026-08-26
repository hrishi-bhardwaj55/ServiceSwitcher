"""Evaluate a one-call long-context baseline over all rendered audit documents."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import time
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pymupdf
from app.agents.cli import document_refs
from app.agents.investigator import ModelUsage
from app.schemas.ground_truth import GroundTruthCase
from app.schemas.mortgage import CanonicalModel
from app.tools.engine import EngineFinding
from dotenv import load_dotenv
from pydantic import Field, ValidationError

from evals.runners.agent_eval import load_ground_truth

DEFAULT_API_BASE = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_TIMEOUT_SECONDS = 90
DEFAULT_TRANSPORT_ATTEMPTS = 3
MAX_OUTPUT_TOKENS = 8_000
EXPECTED_CASE_COUNT = 300
PROMPT_VERSION = "c13-naive-v2"
JsonObject = dict[str, object]
Transport = Callable[[str, Mapping[str, str], JsonObject, int], Mapping[str, object]]

SYSTEM_INSTRUCTIONS = """Review the supplied mortgage-servicing transfer documents.
Identify servicing discrepancies and return them in the required schema. Use only
values visible in the documents. Calculate differences and monthly impact when the
documents support them. Return no findings when the documents are compliant. This is
a single-pass review: you have no tools, reconciliation engine, or regulation search."""


class BaselinePage(CanonicalModel):
    page: int = Field(ge=1)
    text: str


class BaselineDocument(CanonicalModel):
    document_id: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    pages: list[BaselinePage] = Field(min_length=1)


class BaselineRequest(CanonicalModel):
    audit_id: str = Field(pattern=r"^CASE-\d{4}$")
    documents: list[BaselineDocument] = Field(min_length=1)


class BaselineFinding(EngineFinding):
    """Engine-compatible finding with OpenAI-strict required nullable fields."""

    actual_value: float | None
    servicer_value: float | None
    difference: float | None
    monthly_impact: float | None
    recommended_action: str | None = Field(min_length=1)


class BaselineResponse(CanonicalModel):
    findings: list[BaselineFinding]


class BaselineDecision(CanonicalModel):
    response: BaselineResponse
    usage: ModelUsage
    latency_seconds: Decimal = Field(ge=0)


class BaselineCacheRecord(CanonicalModel):
    key: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision: BaselineDecision


class OpenAIBaselineClient:
    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_MODEL,
        api_base: str = DEFAULT_API_BASE,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        transport_attempts: int = DEFAULT_TRANSPORT_ATTEMPTS,
        transport: Transport | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        if not model.startswith("gpt-5.4-mini"):
            raise ValueError("baseline pricing is configured only for gpt-5.4-mini")
        if transport_attempts < 1:
            raise ValueError("transport_attempts must be at least one")
        self.api_key = api_key
        self.model = model
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout
        self.transport_attempts = transport_attempts
        self.transport = transport or _post_json
        self.sleeper = sleeper

    @classmethod
    def from_env(cls) -> OpenAIBaselineClient:
        api_key = os.getenv("BASELINE_API_KEY") or os.getenv("LLM_API_KEY", "")
        if not api_key:
            raise RuntimeError("BASELINE_API_KEY or LLM_API_KEY is required")
        return cls(
            api_key=api_key,
            model=os.getenv("BASELINE_MODEL") or os.getenv("LLM_MODEL", DEFAULT_MODEL),
            api_base=os.getenv("BASELINE_API_BASE")
            or os.getenv("LLM_API_BASE", DEFAULT_API_BASE),
        )

    def evaluate(self, request: BaselineRequest) -> BaselineDecision:
        payload = self._payload(request)
        started = time.perf_counter()
        response = None
        for attempt in range(self.transport_attempts):
            try:
                response = self.transport(
                    f"{self.api_base}/responses",
                    {
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    payload,
                    self.timeout,
                )
                break
            except Exception as error:
                if attempt + 1 == self.transport_attempts:
                    message = str(error).replace(self.api_key, "[REDACTED]")
                    raise RuntimeError(
                        f"baseline provider failed after {self.transport_attempts} "
                        f"attempts: {message}"
                    ) from error
                self.sleeper(0.25 * (2**attempt))
        if response is None:
            raise RuntimeError("baseline provider returned no response")
        latency = Decimal(str(round(time.perf_counter() - started, 6)))
        return BaselineDecision(
            response=BaselineResponse.model_validate_json(_output_text(response)),
            usage=_parse_usage(response),
            latency_seconds=latency,
        )

    def _payload(self, request: BaselineRequest) -> JsonObject:
        return {
            "model": self.model,
            "store": False,
            "instructions": SYSTEM_INSTRUCTIONS,
            "input": _render_documents(request),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "servicing_discrepancies",
                    "strict": True,
                    "schema": BaselineResponse.model_json_schema(),
                }
            },
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "reasoning": {"effort": "none"},
            "safety_identifier": hashlib.sha256(request.audit_id.encode()).hexdigest()[:32],
        }


class CachedBaselineClient:
    def __init__(self, delegate: OpenAIBaselineClient, path: Path) -> None:
        self.delegate = delegate
        self.path = path
        self._lock = Lock()
        self._decisions = self._load()
        self.hits = 0
        self.misses = 0

    @property
    def model(self) -> str:
        return self.delegate.model

    def evaluate(self, request: BaselineRequest) -> BaselineDecision:
        key = self._key(request)
        with self._lock:
            cached = self._decisions.get(key)
            if cached is not None:
                self.hits += 1
                return cached
        decision = self.delegate.evaluate(request)
        with self._lock:
            cached = self._decisions.get(key)
            if cached is not None:
                self.hits += 1
                return cached
            self.misses += 1
            record = BaselineCacheRecord(key=key, decision=decision)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(record.model_dump_json() + "\n")
                handle.flush()
            self._decisions[key] = decision
        return decision

    def _key(self, request: BaselineRequest) -> str:
        payload = json.dumps(self.delegate._payload(request), sort_keys=True)
        material = f"{self.delegate.api_base}|{PROMPT_VERSION}\0{payload}".encode()
        return hashlib.sha256(material).hexdigest()

    def _load(self) -> dict[str, BaselineDecision]:
        if not self.path.is_file():
            return {}
        decisions = {}
        for line_number, line in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(), 1
        ):
            try:
                record = BaselineCacheRecord.model_validate_json(line)
            except ValueError as error:
                raise ValueError(f"invalid baseline cache at {self.path}:{line_number}") from error
            decisions[record.key] = record.decision
        return decisions


@dataclass(frozen=True)
class BaselineCaseResult:
    case_id: str
    bucket: str
    expected_findings: frozenset[str]
    predicted_findings: frozenset[str]
    cost_usd: Decimal
    latency_seconds: Decimal
    execution_error: str | None = None

    @property
    def task_succeeded(self) -> bool:
        return self.execution_error is None and self.predicted_findings == self.expected_findings


@dataclass(frozen=True)
class BaselineMetrics:
    total_cases: int
    faulted_cases: int
    clean_cases: int
    tricky_cases: int
    true_positives: int
    false_positives: int
    false_negatives: int
    successful_cases: int
    clean_false_positive_cases: int
    tricky_false_positive_cases: int
    total_cost_usd: Decimal
    latency_values: tuple[Decimal, ...]
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
    def task_success_rate(self) -> Decimal:
        return _ratio(self.successful_cases, self.total_cases)

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
    def average_cost_usd(self) -> Decimal:
        return self.total_cost_usd / self.total_cases

    @property
    def p50_latency_seconds(self) -> Decimal:
        return _nearest_rank(self.latency_values, Decimal("0.50"))

    @property
    def p95_latency_seconds(self) -> Decimal:
        return _nearest_rank(self.latency_values, Decimal("0.95"))


@dataclass(frozen=True)
class AgentComparison:
    precision: str
    recall: str
    f1: str
    task_success: str
    clean_false_positive_rate: str
    tricky_false_positive_rate: str
    mean_cost: str
    p50_latency: str
    p95_latency: str


def load_case_documents(root: Path, case: GroundTruthCase) -> BaselineRequest:
    documents = []
    for reference in document_refs(root, case.case_id, case.account_id):
        with pymupdf.open(reference.path) as pdf:
            pages = [
                BaselinePage(page=index + 1, text=page.get_text("text", sort=True))
                for index, page in enumerate(pdf)
            ]
        documents.append(
            BaselineDocument(
                document_id=reference.document_id,
                filename=reference.path.name,
                pages=pages,
            )
        )
    return BaselineRequest(audit_id=case.case_id, documents=documents)


def run_case(
    case: GroundTruthCase,
    documents_root: Path,
    client: CachedBaselineClient,
) -> BaselineCaseResult:
    try:
        decision = client.evaluate(load_case_documents(documents_root, case))
        predicted = frozenset(
            finding.finding_type
            for finding in decision.response.findings
            if finding.finding_type != "EXPLAINED"
        )
        return BaselineCaseResult(
            case_id=case.case_id,
            bucket=case.bucket,
            expected_findings=frozenset(case.expected_findings),
            predicted_findings=predicted,
            cost_usd=decision.usage.cost_usd,
            latency_seconds=decision.latency_seconds,
        )
    except Exception as error:  # noqa: BLE001 - one case cannot abort the benchmark
        return BaselineCaseResult(
            case_id=case.case_id,
            bucket=case.bucket,
            expected_findings=frozenset(case.expected_findings),
            predicted_findings=frozenset(),
            cost_usd=Decimal(0),
            latency_seconds=Decimal(0),
            execution_error=_error_label(error),
        )


def execute_cases(
    cases: Sequence[GroundTruthCase],
    documents_root: Path,
    client: CachedBaselineClient,
    *,
    workers: int,
) -> list[BaselineCaseResult]:
    if workers < 1:
        raise ValueError("workers must be positive")
    indexed = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(run_case, case, documents_root, client): index
            for index, case in enumerate(cases)
        }
        for completed, future in enumerate(as_completed(futures), 1):
            result = future.result()
            indexed[futures[future]] = result
            outcome = "ok" if result.task_succeeded else "miss"
            if result.execution_error:
                outcome = f"error:{result.execution_error}"
            print(
                f"[{completed:03d}/{len(cases):03d}] {result.case_id} {outcome} "
                f"cost=${result.cost_usd:.6f}",
                flush=True,
            )
    return [indexed[index] for index in range(len(cases))]


def calculate_metrics(results: Sequence[BaselineCaseResult]) -> BaselineMetrics:
    if not results:
        raise ValueError("baseline evaluation requires at least one result")
    ids = [result.case_id for result in results]
    if len(ids) != len(set(ids)):
        raise ValueError("baseline result ids must be unique")
    clean = [result for result in results if result.bucket != "faulted"]
    tricky = [result for result in results if result.bucket == "clean_but_tricky"]
    return BaselineMetrics(
        total_cases=len(results),
        faulted_cases=sum(result.bucket == "faulted" for result in results),
        clean_cases=len(clean),
        tricky_cases=len(tricky),
        true_positives=sum(
            len(result.expected_findings & result.predicted_findings) for result in results
        ),
        false_positives=sum(
            len(result.predicted_findings - result.expected_findings) for result in results
        ),
        false_negatives=sum(
            len(result.expected_findings - result.predicted_findings) for result in results
        ),
        successful_cases=sum(result.task_succeeded for result in results),
        clean_false_positive_cases=sum(bool(result.predicted_findings) for result in clean),
        tricky_false_positive_cases=sum(bool(result.predicted_findings) for result in tricky),
        total_cost_usd=sum((result.cost_usd for result in results), Decimal(0)),
        latency_values=tuple(result.latency_seconds for result in results),
        execution_failures=sum(result.execution_error is not None for result in results),
    )


def load_agent_comparison(path: Path) -> AgentComparison:
    report = path.read_text(encoding="utf-8")

    def value(label: str) -> str:
        match = re.search(rf"^\| {re.escape(label)} \| ([^|]+) \|$", report, re.MULTILINE)
        if match is None:
            raise ValueError(f"agent report is missing {label}")
        return match.group(1).strip()

    latency = value("Latency p50 / p95")
    latency_match = re.fullmatch(r"([0-9.]+s) / ([0-9.]+s)", latency)
    if latency_match is None:
        raise ValueError("agent report has invalid latency")
    return AgentComparison(
        precision=value("Precision"),
        recall=value("Recall"),
        f1=value("F1"),
        task_success=value("Task success (exact finding set)"),
        clean_false_positive_rate=value("Clean-case false-positive rate"),
        tricky_false_positive_rate=value("Clean-but-tricky false-positive rate"),
        mean_cost=value("Model cost per audit (mean)"),
        p50_latency=latency_match.group(1),
        p95_latency=latency_match.group(2),
    )


def render_baseline_report(metrics: BaselineMetrics, model: str) -> str:
    return f"""# Naive long-context baseline

Model: `{model}`. One structured provider call per audit over concatenated text from
all five PDFs. No tools, reconciliation engine, retrieval, or LLM judge are used.

| Metric | Result |
|---|---:|
| Cases | {metrics.total_cases} |
| Precision | {_percent(metrics.precision)} |
| Recall | {_percent(metrics.recall)} |
| F1 | {_percent(metrics.f1)} |
| Exact finding-set task success | {_percent(metrics.task_success_rate)} |
| Clean-case false-positive rate | {_percent(metrics.clean_false_positive_rate)} |
| Clean-but-tricky false-positive rate | {_percent(metrics.tricky_false_positive_rate)} |
| Mean model cost per audit | ${metrics.average_cost_usd:.6f} |
| Latency p50 / p95 | {metrics.p50_latency_seconds:.3f}s / {metrics.p95_latency_seconds:.3f}s |
| Execution failures | {metrics.execution_failures} |
"""


def render_comparison(metrics: BaselineMetrics, agent: AgentComparison) -> str:
    return f"""# Agent versus naive baseline

Both systems use `gpt-5.4-mini` and the same 300 labeled audits. Correctness is
scored directly against ground truth. The baseline makes one long-context call over
PDF text; the agent uses extraction, deterministic reconciliation, retrieval, and
bounded tools.

| Metric | Agent | Naive baseline |
|---|---:|---:|
| Precision | {agent.precision} | {_percent(metrics.precision)} |
| Recall | {agent.recall} | {_percent(metrics.recall)} |
| F1 | {agent.f1} | {_percent(metrics.f1)} |
| Exact finding-set task success | {agent.task_success} | {_percent(metrics.task_success_rate)} |
| Clean-case false-positive rate | {agent.clean_false_positive_rate} | {_percent(metrics.clean_false_positive_rate)} |
| Clean-but-tricky false-positive rate | {agent.tricky_false_positive_rate} | {_percent(metrics.tricky_false_positive_rate)} |
| Mean model cost per audit | {agent.mean_cost} | ${metrics.average_cost_usd:.6f} |
| Latency p50 | {agent.p50_latency} | {metrics.p50_latency_seconds:.3f}s |
| Latency p95 | {agent.p95_latency} | {metrics.p95_latency_seconds:.3f}s |

The agent cost covers investigator tokens and excludes embeddings and cached C8
extraction calls. Baseline cost covers its single provider call. See the underlying
agent and baseline reports for scope and limitations.
"""


def _render_documents(request: BaselineRequest) -> str:
    parts = [f"Audit: {request.audit_id}"]
    for document in request.documents:
        for page in document.pages:
            parts.append(
                f"=== {document.document_id} | {document.filename} | PAGE {page.page} ===\n"
                f"{page.text}"
            )
    return "\n\n".join(parts)


def _output_text(response: Mapping[str, object]) -> str:
    direct = response.get("output_text")
    if isinstance(direct, str) and direct:
        return direct
    output = response.get("output", [])
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, Mapping) or item.get("type") != "message":
                continue
            content = item.get("content", [])
            if not isinstance(content, list):
                continue
            for block in content:
                if isinstance(block, Mapping) and block.get("type") == "output_text":
                    text = block.get("text")
                    if isinstance(text, str) and text:
                        return text
    raise ValueError("baseline provider response contains no output text")


def _parse_usage(response: Mapping[str, object]) -> ModelUsage:
    usage = response.get("usage")
    if not isinstance(usage, Mapping):
        raise TypeError("baseline provider response contains no usage")
    details = usage.get("input_tokens_details")
    cached = details.get("cached_tokens", 0) if isinstance(details, Mapping) else 0
    return ModelUsage(
        input_tokens=usage.get("input_tokens", -1),
        cached_input_tokens=cached,
        output_tokens=usage.get("output_tokens", -1),
    )


def _post_json(
    url: str,
    headers: Mapping[str, str],
    payload: JsonObject,
    timeout: int,
) -> Mapping[str, object]:
    request = Request(
        url,
        data=json.dumps(payload).encode(),
        headers=dict(headers),
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            result = json.load(response)
    except HTTPError as error:
        body = error.read(2_000).decode(errors="replace")
        raise RuntimeError(f"provider returned HTTP {error.code}: {body}") from error
    except URLError as error:
        raise RuntimeError(f"cannot reach baseline provider: {error}") from error
    if not isinstance(result, Mapping):
        raise TypeError("baseline provider response is not a JSON object")
    return result


def _ratio(numerator: int, denominator: int) -> Decimal:
    if denominator == 0:
        return Decimal(1)
    return Decimal(numerator) / Decimal(denominator)


def _error_label(error: Exception) -> str:
    if isinstance(error, ValidationError):
        issue = error.errors(include_input=False)[0]
        location = ".".join(str(part) for part in issue["loc"]) or "root"
        return f"ValidationError:{issue['type']}@{location}"[:160]
    return type(error).__name__


def _nearest_rank(values: Sequence[Decimal], percentile: Decimal) -> Decimal:
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
    parser.add_argument("--documents", type=Path, default=Path("data/documents"))
    parser.add_argument(
        "--cache",
        type=Path,
        default=Path("data/traces/baseline_llm_cache.jsonl"),
    )
    parser.add_argument("--report", type=Path, default=Path("evals/reports/baseline.md"))
    parser.add_argument(
        "--comparison",
        type=Path,
        default=Path("evals/reports/comparison.md"),
    )
    parser.add_argument(
        "--agent-report",
        type=Path,
        default=Path("evals/reports/agent.md"),
    )
    parser.add_argument("--expected-count", type=int, default=EXPECTED_CASE_COUNT)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--case", action="append", dest="case_ids")
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
    client = CachedBaselineClient(OpenAIBaselineClient.from_env(), args.cache)
    results = execute_cases(cases, args.documents, client, workers=args.workers)
    metrics = calculate_metrics(results)
    baseline_report = render_baseline_report(metrics, client.model)
    comparison = render_comparison(metrics, load_agent_comparison(args.agent_report))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(baseline_report, encoding="utf-8")
    args.comparison.write_text(comparison, encoding="utf-8")
    print(baseline_report)
    print(f"Provider cache: {client.hits} hits, {client.misses} misses")
    print(f"Wrote reports to {args.report} and {args.comparison}")


if __name__ == "__main__":
    main()
