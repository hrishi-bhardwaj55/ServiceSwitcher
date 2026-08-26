"""Evaluate confidence-gated extraction in-distribution and on held-out layouts."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import cast

from app.extraction import DocumentType as ExtractionDocumentType
from app.extraction.fallback import HybridExtractionResult, extract_with_fallback
from app.llm import LLMClient, OpenAIResponsesClient

from data.render.content import DOCUMENT_TYPES, TemplateFamily, family_for_account
from data.render.ground_truth import (
    expected_extraction_fields,
    expected_extraction_pages,
)
from data.render.render import EXPECTED_ACCOUNT_COUNT, load_accounts

IN_DISTRIBUTION = "In-distribution (A/B)"
HELD_OUT = "Held-out"
BUCKETS = ((0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01))


@dataclass
class CohortMetrics:
    accounts: set[str] = field(default_factory=set)
    documents: int = 0
    correct_classifications: int = 0
    expected_fields: int = 0
    correct_fields: int = 0
    correct_pages: int = 0
    fallback_documents: int = 0
    observations: list[tuple[float, bool]] = field(default_factory=list)

    @property
    def classification_accuracy(self) -> Decimal:
        return _ratio(self.correct_classifications, self.documents)

    @property
    def field_accuracy(self) -> Decimal:
        return _ratio(self.correct_fields, self.expected_fields)

    @property
    def citation_accuracy(self) -> Decimal:
        return _ratio(self.correct_pages, self.expected_fields)

    @property
    def fallback_rate(self) -> Decimal:
        return _ratio(self.fallback_documents, self.documents)


def _ratio(numerator: int, denominator: int) -> Decimal:
    if denominator == 0:
        return Decimal(1)
    return Decimal(numerator) / Decimal(denominator)


def evaluate(
    accounts: list[dict], documents: Path, client: LLMClient
) -> dict[str, CohortMetrics]:
    metrics = {IN_DISTRIBUTION: CohortMetrics(), HELD_OUT: CohortMetrics()}
    for account in accounts:
        family = family_for_account(account["account_id"])
        cohort_name = HELD_OUT if family == TemplateFamily.C else IN_DISTRIBUTION
        cohort = metrics[cohort_name]
        cohort.accounts.add(account["account_id"])
        for rendered_type in DOCUMENT_TYPES:
            document_type = cast(ExtractionDocumentType, rendered_type.value.upper())
            expected_values = expected_extraction_fields(account, document_type)
            expected_pages = expected_extraction_pages(document_type, family)
            result = extract_with_fallback(
                documents / account["account_id"] / rendered_type.filename,
                client,
            )
            _score_document(
                cohort,
                result,
                document_type,
                expected_values,
                expected_pages,
            )
    return metrics


def _score_document(
    metrics: CohortMetrics,
    result: HybridExtractionResult,
    expected_type: ExtractionDocumentType,
    expected_values: dict,
    expected_pages: dict[str, int],
) -> None:
    metrics.documents += 1
    metrics.expected_fields += len(expected_values)
    metrics.correct_classifications += result.document_type == expected_type
    metrics.fallback_documents += result.llm_fallback_triggered
    extracted = result.field_map()
    for field_name, expected_value in expected_values.items():
        field = extracted.get(field_name)
        correct = field is not None and field.value == expected_value
        metrics.correct_fields += correct
        metrics.correct_pages += bool(
            correct and field is not None and field.page == expected_pages[field_name]
        )
        metrics.observations.append((field.confidence if field else 0.0, correct))


def render_report(metrics: dict[str, CohortMetrics], model: str) -> str:
    development = metrics[IN_DISTRIBUTION]
    held_out = metrics[HELD_OUT]
    return f"""# Extraction evaluation

Model-backed fallback: `{model}`. Metrics are kept separate for development and
held-out layouts; they are never pooled into a single headline number.

| Metric | In-distribution (A/B) | Held-out (Family C) |
|---|---:|---:|
| Accounts | {len(development.accounts)} | {len(held_out.accounts)} |
| Documents | {development.documents} | {held_out.documents} |
| Document classification | {_percent(development.classification_accuracy)} | {_percent(held_out.classification_accuracy)} |
| Field extraction | {_percent(development.field_accuracy)} | {_percent(held_out.field_accuracy)} |
| Citation (page) accuracy | {_percent(development.citation_accuracy)} | {_percent(held_out.citation_accuracy)} |
| LLM fallback trigger rate | {_percent(development.fallback_rate)} | {_percent(held_out.fallback_rate)} |
"""


def render_calibration(metrics: dict[str, CohortMetrics], model: str) -> str:
    rows: list[str] = []
    for lower, upper in BUCKETS:
        label = f"{lower:.1f}-{min(upper, 1.0):.1f}"
        development = _calibration_bucket(metrics[IN_DISTRIBUTION], lower, upper)
        held_out = _calibration_bucket(metrics[HELD_OUT], lower, upper)
        rows.append(f"| {label} | {_calibration_cell(development)} | {_calibration_cell(held_out)} |")
    return f"""# Extraction confidence calibration

Model-backed fallback: `{model}`. Each row compares mean predicted confidence with
observed exact-value accuracy for expected fields in that confidence bucket.
Missing fields enter the lowest bucket with zero confidence.

| Confidence bucket | In-distribution (A/B) | Held-out (Family C) |
|---|---:|---:|
{chr(10).join(rows)}
"""


def _calibration_bucket(
    metrics: CohortMetrics, lower: float, upper: float
) -> tuple[int, Decimal, Decimal]:
    selected = [item for item in metrics.observations if lower <= item[0] < upper]
    if not selected:
        return 0, Decimal(0), Decimal(0)
    mean_confidence = sum((Decimal(str(item[0])) for item in selected), Decimal(0)) / len(
        selected
    )
    accuracy = Decimal(sum(item[1] for item in selected)) / len(selected)
    return len(selected), mean_confidence, accuracy


def _calibration_cell(values: tuple[int, Decimal, Decimal]) -> str:
    count, confidence, accuracy = values
    if count == 0:
        return "n=0"
    return f"n={count}; conf {_percent(confidence)}; acc {_percent(accuracy)}"


def _percent(value: Decimal) -> str:
    return f"{value * Decimal(100):.2f}%"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accounts", type=Path, default=Path("data/accounts"))
    parser.add_argument("--documents", type=Path, default=Path("data/documents"))
    parser.add_argument("--report", type=Path, default=Path("evals/reports/extraction.md"))
    parser.add_argument(
        "--calibration-report",
        type=Path,
        default=Path("evals/reports/calibration.md"),
    )
    parser.add_argument("--expected-count", type=int, default=EXPECTED_ACCOUNT_COUNT)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    accounts = load_accounts(args.accounts)
    if len(accounts) != args.expected_count:
        raise ValueError(f"expected {args.expected_count} accounts; found {len(accounts)}")
    client = OpenAIResponsesClient.from_env()
    metrics = evaluate(accounts, args.documents, client)
    model = os.environ["LLM_MODEL"]
    report = render_report(metrics, model)
    calibration = render_calibration(metrics, model)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    args.calibration_report.write_text(calibration, encoding="utf-8")
    print(report)
    print(f"Wrote reports to {args.report} and {args.calibration_report}")


if __name__ == "__main__":
    main()
