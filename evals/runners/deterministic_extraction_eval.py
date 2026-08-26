"""Evaluate deterministic PDF extraction on the two development template families."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import cast

from app.extraction import DocumentType as ExtractionDocumentType
from app.extraction import extract_document
from app.extraction.classifier import UnclassifiedDocumentError

from data.render.content import DOCUMENT_TYPES, TemplateFamily, family_for_account
from data.render.ground_truth import expected_extraction_fields
from data.render.render import EXPECTED_ACCOUNT_COUNT, load_accounts

CLASSIFICATION_ACCURACY_FLOOR = Decimal("0.99")
FIELD_ACCURACY_FLOOR = Decimal("0.98")
EVALUATED_FAMILIES = (TemplateFamily.A, TemplateFamily.B)


@dataclass
class FamilyMetrics:
    accounts: int = 0
    documents: int = 0
    correct_classifications: int = 0
    field_total: Counter[str] = field(default_factory=Counter)
    field_correct: Counter[str] = field(default_factory=Counter)
    provenance_valid: int = 0

    @property
    def classification_accuracy(self) -> Decimal:
        return _ratio(self.correct_classifications, self.documents)

    @property
    def total_fields(self) -> int:
        return self.field_total.total()

    @property
    def correct_fields(self) -> int:
        return self.field_correct.total()

    @property
    def field_accuracy(self) -> Decimal:
        return _ratio(self.correct_fields, self.total_fields)

    @property
    def provenance_coverage(self) -> Decimal:
        return _ratio(self.provenance_valid, self.total_fields)

    @property
    def meets_floor(self) -> bool:
        return (
            self.classification_accuracy >= CLASSIFICATION_ACCURACY_FLOOR
            and self.field_accuracy >= FIELD_ACCURACY_FLOOR
            and self.provenance_coverage == Decimal(1)
        )


def _ratio(numerator: int, denominator: int) -> Decimal:
    if denominator == 0:
        return Decimal(1)
    return Decimal(numerator) / Decimal(denominator)


def evaluate(accounts: list[dict], documents: Path) -> dict[TemplateFamily, FamilyMetrics]:
    metrics = {family: FamilyMetrics() for family in EVALUATED_FAMILIES}
    for account in accounts:
        family = family_for_account(account["account_id"])
        if family not in metrics:
            continue
        family_metrics = metrics[family]
        family_metrics.accounts += 1
        for rendered_type in DOCUMENT_TYPES:
            document_type = cast(ExtractionDocumentType, rendered_type.value.upper())
            expected = expected_extraction_fields(account, document_type)
            family_metrics.documents += 1
            family_metrics.field_total.update(expected.keys())
            path = documents / account["account_id"] / rendered_type.filename
            try:
                result = extract_document(path)
            except UnclassifiedDocumentError:
                continue
            if result.document_type == document_type:
                family_metrics.correct_classifications += 1
            extracted = result.field_map()
            for field_name, expected_value in expected.items():
                field = extracted.get(field_name)
                if field is None:
                    continue
                if field.value == expected_value:
                    family_metrics.field_correct[field_name] += 1
                if (
                    field.page >= 1
                    and field.bounding_box.x1 > field.bounding_box.x0
                    and field.bounding_box.y1 > field.bounding_box.y0
                ):
                    family_metrics.provenance_valid += 1
    return metrics


def render_report(metrics: dict[TemplateFamily, FamilyMetrics]) -> str:
    combined = _combine(metrics.values())
    a = metrics[TemplateFamily.A]
    b = metrics[TemplateFamily.B]
    field_names = sorted(combined.field_total)
    field_rows = "\n".join(
        f"| `{field_name}` | {_field_result(a, field_name)} | "
        f"{_field_result(b, field_name)} | {_field_result(combined, field_name)} |"
        for field_name in field_names
    )
    verdict = "PASS" if all(item.meets_floor for item in (*metrics.values(), combined)) else "FAIL"
    return f"""# Deterministic extraction evaluation

This report measures keyword classification and label-proximity field extraction on
the two development template families. No LLM or held-out documents are used.

## Corpus

| Family | Accounts | Documents | Expected fields |
|---|---:|---:|---:|
| A | {a.accounts} | {a.documents} | {a.total_fields} |
| B | {b.accounts} | {b.documents} | {b.total_fields} |
| Overall | {combined.accounts} | {combined.documents} | {combined.total_fields} |

## Summary

| Metric | Family A | Family B | Overall | Floor |
|---|---:|---:|---:|---:|
| Document classification | {_percent(a.classification_accuracy)} | {_percent(b.classification_accuracy)} | {_percent(combined.classification_accuracy)} | 99.00% |
| Field extraction | {_percent(a.field_accuracy)} | {_percent(b.field_accuracy)} | {_percent(combined.field_accuracy)} | 98.00% |
| Page and bounding-box provenance coverage | {_percent(a.provenance_coverage)} | {_percent(b.provenance_coverage)} | {_percent(combined.provenance_coverage)} | 100.00% |

## Per-field accuracy

| Field | Family A | Family B | Overall |
|---|---:|---:|---:|
{field_rows}

**Acceptance verdict: {verdict}.**
"""


def _combine(groups) -> FamilyMetrics:
    combined = FamilyMetrics()
    for metrics in groups:
        combined.accounts += metrics.accounts
        combined.documents += metrics.documents
        combined.correct_classifications += metrics.correct_classifications
        combined.field_total.update(metrics.field_total)
        combined.field_correct.update(metrics.field_correct)
        combined.provenance_valid += metrics.provenance_valid
    return combined


def _field_result(metrics: FamilyMetrics, field_name: str) -> str:
    correct = metrics.field_correct[field_name]
    total = metrics.field_total[field_name]
    return f"{_percent(_ratio(correct, total))} ({correct}/{total})"


def _percent(value: Decimal) -> str:
    return f"{value * Decimal(100):.2f}%"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accounts", type=Path, default=Path("data/accounts"))
    parser.add_argument("--documents", type=Path, default=Path("data/documents"))
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("evals/reports/extraction_deterministic.md"),
    )
    parser.add_argument("--expected-count", type=int, default=EXPECTED_ACCOUNT_COUNT)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    accounts = load_accounts(args.accounts)
    if len(accounts) != args.expected_count:
        raise ValueError(f"expected {args.expected_count} accounts; found {len(accounts)}")
    metrics = evaluate(accounts, args.documents)
    report = render_report(metrics)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote report to {args.report}")
    if not all(item.meets_floor for item in metrics.values()):
        raise SystemExit("deterministic extraction did not meet the C7 accuracy floors")


if __name__ == "__main__":
    main()
