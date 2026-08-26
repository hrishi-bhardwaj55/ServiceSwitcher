"""Evaluate the deterministic engine against structured ground truth."""

from __future__ import annotations

import argparse
import json
import shutil
import socket
import subprocess
import tempfile
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

EXPLAINED = "EXPLAINED"
DEFAULT_ENGINE_URL = "http://127.0.0.1:8080"
EXPECTED_CASE_COUNT = 300
HTTP_TIMEOUT_SECONDS = 10
STARTUP_TIMEOUT_SECONDS = 60

JsonObject = dict[str, Any]
Reconcile = Callable[[JsonObject, str], Mapping[str, Any]]


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    account_id: str
    bucket: str
    expected_findings: frozenset[str]
    expected_impact_total: Decimal


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    bucket: str
    expected_findings: frozenset[str]
    predicted_findings: frozenset[str]
    expected_impact_total: Decimal
    predicted_impact_total: Decimal


@dataclass(frozen=True)
class EvaluationMetrics:
    total_cases: int
    faulted_cases: int
    clean_cases: int
    true_positives: int
    false_positives: int
    false_negatives: int
    clean_false_positive_cases: int
    total_absolute_impact_error: Decimal
    engine_versions: tuple[str, ...]

    @property
    def precision(self) -> Decimal:
        denominator = self.true_positives + self.false_positives
        return _ratio(self.true_positives, denominator)

    @property
    def recall(self) -> Decimal:
        denominator = self.true_positives + self.false_negatives
        return _ratio(self.true_positives, denominator)

    @property
    def f1(self) -> Decimal:
        denominator = (2 * self.true_positives) + self.false_positives + self.false_negatives
        return _ratio(2 * self.true_positives, denominator)

    @property
    def false_positive_rate(self) -> Decimal:
        return _ratio(self.clean_false_positive_cases, self.clean_cases)

    @property
    def impact_mean_absolute_error(self) -> Decimal:
        return self.total_absolute_impact_error / Decimal(self.total_cases)

    @property
    def meets_target(self) -> bool:
        return (
            self.precision == Decimal(1)
            and self.recall == Decimal(1)
            and self.false_positive_rate == Decimal(0)
            and self.impact_mean_absolute_error < Decimal("0.01")
        )


def _ratio(numerator: int, denominator: int) -> Decimal:
    if denominator == 0:
        return Decimal(1)
    return Decimal(numerator) / Decimal(denominator)


def load_cases(path: Path) -> list[EvaluationCase]:
    cases: list[EvaluationCase] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
            cases.append(
                EvaluationCase(
                    case_id=raw["case_id"],
                    account_id=raw["account_id"],
                    bucket=raw["bucket"],
                    expected_findings=frozenset(raw["expected_findings"]),
                    expected_impact_total=Decimal(raw["expected_impact_total"]),
                )
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise ValueError(f"invalid ground truth at {path}:{line_number}: {error}") from error
    if not cases:
        raise ValueError(f"no ground-truth cases found in {path}")
    return cases


def load_accounts(path: Path) -> dict[str, JsonObject]:
    accounts: dict[str, JsonObject] = {}
    for account_path in sorted(path.glob("account-*.json")):
        try:
            account = json.loads(account_path.read_text(encoding="utf-8"))
            account_id = account["account_id"]
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise ValueError(f"invalid account at {account_path}: {error}") from error
        if account_id in accounts:
            raise ValueError(f"duplicate account_id {account_id} in {path}")
        accounts[account_id] = account
    if not accounts:
        raise ValueError(f"no account JSON files found in {path}")
    return accounts


def transfer_date(account: Mapping[str, Any]) -> str:
    periods = account.get("servicing_periods")
    if not isinstance(periods, list) or len(periods) < 2:
        raise ValueError(f"account {account.get('account_id')} has no servicing transfer")
    date = periods[1].get("start_date")
    if not isinstance(date, str):
        raise TypeError(f"account {account.get('account_id')} has no transfer start date")
    return date


def predicted_values(response: Mapping[str, Any]) -> tuple[frozenset[str], Decimal]:
    findings = response.get("findings")
    if not isinstance(findings, list):
        raise TypeError("engine response has no findings list")

    finding_types: set[str] = set()
    impact_total = Decimal("0.00")
    for finding in findings:
        if not isinstance(finding, Mapping):
            raise TypeError("engine response contains a non-object finding")
        finding_type = finding.get("finding_type")
        if not isinstance(finding_type, str):
            raise TypeError("engine finding has no finding_type")
        if finding_type == EXPLAINED:
            continue
        try:
            impact = abs(Decimal(finding["difference"]))
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"{finding_type} finding has invalid difference") from error
        finding_types.add(finding_type)
        impact_total += impact
    return frozenset(finding_types), impact_total


def evaluate_cases(
    cases: Sequence[EvaluationCase],
    accounts: Mapping[str, JsonObject],
    reconcile: Reconcile,
) -> tuple[EvaluationMetrics, list[CaseResult]]:
    results: list[CaseResult] = []
    versions: set[str] = set()
    seen_case_ids: set[str] = set()

    for case in cases:
        if case.case_id in seen_case_ids:
            raise ValueError(f"duplicate case_id {case.case_id}")
        seen_case_ids.add(case.case_id)
        try:
            account = accounts[case.account_id]
        except KeyError as error:
            raise ValueError(f"missing account {case.account_id} for {case.case_id}") from error
        response = reconcile(account, transfer_date(account))
        predicted_findings, predicted_impact = predicted_values(response)
        version = response.get("engine_version")
        if isinstance(version, str):
            versions.add(version)
        results.append(
            CaseResult(
                case_id=case.case_id,
                bucket=case.bucket,
                expected_findings=case.expected_findings,
                predicted_findings=predicted_findings,
                expected_impact_total=case.expected_impact_total,
                predicted_impact_total=predicted_impact,
            )
        )

    true_positives = sum(
        len(result.expected_findings & result.predicted_findings) for result in results
    )
    false_positives = sum(
        len(result.predicted_findings - result.expected_findings) for result in results
    )
    false_negatives = sum(
        len(result.expected_findings - result.predicted_findings) for result in results
    )
    clean_results = [result for result in results if result.bucket != "faulted"]
    clean_false_positives = sum(bool(result.predicted_findings) for result in clean_results)
    impact_error = sum(
        (
            abs(result.predicted_impact_total - result.expected_impact_total)
            for result in results
        ),
        Decimal("0.00"),
    )
    return (
        EvaluationMetrics(
            total_cases=len(results),
            faulted_cases=len(results) - len(clean_results),
            clean_cases=len(clean_results),
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
            clean_false_positive_cases=clean_false_positives,
            total_absolute_impact_error=impact_error,
            engine_versions=tuple(sorted(versions)),
        ),
        results,
    )


class HttpEngineClient:
    def __init__(self, base_url: str, timeout: int = HTTP_TIMEOUT_SECONDS) -> None:
        self.reconcile_url = f"{base_url.rstrip('/')}/reconcile"
        self.timeout = timeout

    def reconcile(self, account: JsonObject, transfer: str) -> Mapping[str, Any]:
        request = Request(
            self.reconcile_url,
            data=json.dumps({"account": account, "transfer_date": transfer}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except HTTPError as error:
            body = error.read().decode(errors="replace")
            raise RuntimeError(
                f"engine returned HTTP {error.code} for {account.get('account_id')}: {body}"
            ) from error
        except URLError as error:
            raise RuntimeError(f"cannot reach engine at {self.reconcile_url}: {error}") from error
        if not isinstance(payload, Mapping):
            raise TypeError("engine response is not a JSON object")
        return payload


def _available_port() -> int:
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        return int(server.getsockname()[1])


def _wait_for_engine(base_url: str, process: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    health_url = f"{base_url}/health"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"engine stopped during startup with exit code {process.returncode}")
        try:
            with urlopen(health_url, timeout=1) as response:
                if response.status == 200:
                    return
        except (HTTPError, URLError, TimeoutError):
            time.sleep(0.2)
    raise RuntimeError(f"engine did not become healthy within {STARTUP_TIMEOUT_SECONDS}s")


@contextmanager
def managed_engine(jar: Path) -> Iterator[str]:
    java = shutil.which("java")
    if java is None:
        raise RuntimeError("java is required to launch the reconciliation engine")
    if not jar.is_file():
        raise ValueError(f"engine jar does not exist: {jar}")
    port = _available_port()
    base_url = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryFile() as log:
        process = subprocess.Popen(
            [java, "-jar", str(jar), f"--server.port={port}"],
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            _wait_for_engine(base_url, process)
            yield base_url
        except Exception as error:
            log.seek(0)
            output = log.read().decode(errors="replace")
            if output:
                error.add_note(f"engine log:\n{output[-4000:]}")
            raise
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def render_report(metrics: EvaluationMetrics) -> str:
    versions = ", ".join(f"`{version}`" for version in metrics.engine_versions) or "unknown"
    verdict = "PASS" if metrics.meets_target else "FAIL"
    return f"""# Deterministic engine evaluation

This report measures the reconciliation engine directly against structured account
data. It does not include PDF rendering, extraction, retrieval, or AI behavior.

## Corpus

| Cases | Faulted | Clean (including tricky) | Engine version |
|---:|---:|---:|---|
| {metrics.total_cases} | {metrics.faulted_cases} | {metrics.clean_cases} | {versions} |

## Results

| Metric | Result | Target |
|---|---:|---:|
| Precision | {_percent(metrics.precision)} | 100.00% |
| Recall | {_percent(metrics.recall)} | 100.00% |
| F1 | {_percent(metrics.f1)} | 100.00% |
| Clean-case false-positive rate | {_percent(metrics.false_positive_rate)} | 0.00% |
| Financial-impact mean absolute error | ${metrics.impact_mean_absolute_error:.4f} | < $0.01 |

Counts: {metrics.true_positives} true positives, {metrics.false_positives} false
positives, {metrics.false_negatives} false negatives, and
{metrics.clean_false_positive_cases}/{metrics.clean_cases} clean cases with a false
positive.

**Acceptance verdict: {verdict}.**
"""


def _percent(value: Decimal) -> str:
    return f"{value * Decimal(100):.2f}%"


def write_report(path: Path, report: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accounts", type=Path, default=Path("data/accounts"))
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=Path("data/ground_truth/cases.jsonl"),
    )
    parser.add_argument("--report", type=Path, default=Path("evals/reports/engine.md"))
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--engine-url")
    source.add_argument("--engine-jar", type=Path)
    parser.add_argument("--expected-count", type=int, default=EXPECTED_CASE_COUNT)
    return parser.parse_args()


def _run(args: argparse.Namespace, engine_url: str) -> EvaluationMetrics:
    cases = load_cases(args.ground_truth)
    accounts = load_accounts(args.accounts)
    if len(cases) != args.expected_count:
        raise ValueError(f"expected {args.expected_count} cases; found {len(cases)}")
    if len(accounts) != args.expected_count:
        raise ValueError(f"expected {args.expected_count} accounts; found {len(accounts)}")
    client = HttpEngineClient(engine_url)
    metrics, _ = evaluate_cases(cases, accounts, client.reconcile)
    write_report(args.report, render_report(metrics))
    return metrics


def main() -> None:
    args = _parse_args()
    if args.engine_jar:
        with managed_engine(args.engine_jar) as engine_url:
            metrics = _run(args, engine_url)
    else:
        metrics = _run(args, args.engine_url or DEFAULT_ENGINE_URL)
    print(render_report(metrics))
    print(f"Wrote report to {args.report}")
    if not metrics.meets_target:
        raise SystemExit("engine evaluation did not meet the C5 acceptance target")


if __name__ == "__main__":
    main()
