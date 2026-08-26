"""Validate the complete fault corpus and machine-readable ground truth."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from app.schemas import GroundTruthCase, MortgageAccount
from pydantic import ValidationError

from data.faults.common import payment_residual
from data.faults.oracle import evaluate
from data.generator.validate import validate_account

EXPECTED_BUCKETS = {"faulted": 200, "clean": 60, "clean_but_tricky": 40}
EXPECTED_FINDINGS = {
    "ESCROW_BALANCE_MISMATCH": 40,
    "PROPERTY_TAX_PROJECTION_MISMATCH": 40,
    "ESCROW_SHORTAGE_CALCULATION_ERROR": 40,
    "DUPLICATE_TAX_DISBURSEMENT": 40,
    "UNEXPLAINED_PAYMENT_INCREASE": 40,
}


@dataclass(frozen=True)
class GroundTruthReport:
    total: int
    valid: int
    errors: dict[str, list[str]]

    @property
    def ok(self) -> bool:
        return self.total == 300 and self.valid == 300 and not self.errors


def _condition_errors(
    account: MortgageAccount,
    case: GroundTruthCase,
) -> list[str]:
    errors: list[str] = []
    if case.tricky_condition == "LEGITIMATE_TAX_REASSESSMENT":
        tax_by_year = {
            year: sum(
                (
                    bill.annual_amount
                    for bill in account.tax_bills
                    if bill.tax_year == year
                ),
                Decimal("0.00"),
            )
            for year in (2024, 2025)
        }
        if tax_by_year[2025] < tax_by_year[2024] * Decimal("1.40"):
            errors.append("tax reassessment is less than 40%")
    elif case.tricky_condition == "LEGITIMATE_INSURANCE_PREMIUM_JUMP":
        premium_by_year = {
            policy.renewal_date.year: policy.annual_premium
            for policy in account.insurance_policies
        }
        if premium_by_year[2025] < premium_by_year[2024] * Decimal("1.40"):
            errors.append("insurance premium jump is less than 40%")
    elif case.tricky_condition == "DISTINCT_TAX_AUTHORITIES_CLOSE_TOGETHER":
        transactions = [
            transaction
            for transaction in account.escrow_ledger
            if transaction.type == "TAX_DISBURSEMENT" and transaction.date.year == 2024
        ]
        if (
            len(transactions) != 2
            or transactions[1].date - transactions[0].date != timedelta(days=50)
            or transactions[0].payee == transactions[1].payee
        ):
            errors.append("distinct-authority tax payments are not exactly 50 days apart")
    elif case.tricky_condition == "FULLY_EXPLAINED_PAYMENT_INCREASE":
        transfer_date = account.servicing_periods[1].start_date
        old_total = max(
            payment.total for payment in account.payments if payment.date < transfer_date
        )
        new_total = min(
            payment.total for payment in account.payments if payment.date >= transfer_date
        )
        if new_total <= old_total or payment_residual(account) > Decimal("10.00"):
            errors.append("payment increase is not fully explained")
    return errors


def validate_ground_truth(
    accounts_path: Path,
    cases_path: Path,
) -> GroundTruthReport:
    errors: dict[str, list[str]] = {}
    cases: list[GroundTruthCase] = []
    try:
        lines = cases_path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        return GroundTruthReport(0, 0, {"collection": [str(error)]})

    for line_number, line in enumerate(lines, start=1):
        try:
            cases.append(GroundTruthCase.model_validate_json(line))
        except (ValidationError, ValueError) as error:
            errors[f"cases.jsonl:{line_number}"] = [str(error)]

    if len(cases) != 300:
        errors.setdefault("collection", []).append(
            f"expected 300 ground-truth cases; found {len(cases)}"
        )
    bucket_counts = Counter(case.bucket for case in cases)
    if dict(bucket_counts) != EXPECTED_BUCKETS:
        errors.setdefault("collection", []).append(
            f"bucket counts are {dict(bucket_counts)}; expected {EXPECTED_BUCKETS}"
        )
    finding_counts = Counter(
        finding for case in cases for finding in case.expected_findings
    )
    if dict(finding_counts) != EXPECTED_FINDINGS:
        errors.setdefault("collection", []).append(
            f"finding counts are {dict(finding_counts)}; expected {EXPECTED_FINDINGS}"
        )
    if len({case.case_id for case in cases}) != len(cases):
        errors.setdefault("collection", []).append("case_id values are not unique")
    if len({case.account_id for case in cases}) != len(cases):
        errors.setdefault("collection", []).append("account_id values are not unique")

    valid = 0
    for case in cases:
        source = f"{case.case_id}/{case.account_id}"
        path = accounts_path / f"account-{case.account_id.removeprefix('SS-')}.json"
        try:
            account = MortgageAccount.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValidationError, ValueError) as error:
            errors[source] = [f"cannot load account: {error}"]
            continue
        case_errors: list[str] = []
        if account.account_id != case.account_id:
            case_errors.append("ground-truth account_id does not match account file")
        observed = evaluate(account)
        observed_types = [finding.finding_type for finding in observed]
        if observed_types != case.expected_findings:
            case_errors.append(
                f"observed findings {observed_types} do not match {case.expected_findings}"
            )
        if case.bucket == "faulted" and len(observed) == 1:
            if observed[0].impact_total != case.expected_impact_total:
                case_errors.append("expected_impact_total does not match oracle")
            if observed[0].monthly_impact != case.expected_monthly_impact:
                case_errors.append("expected_monthly_impact does not match oracle")
            if not case.evidence_documents:
                case_errors.append("faulted case has no evidence document labels")
            if not validate_account(account):
                case_errors.append("faulted account unexpectedly passes clean validation")
        else:
            clean_errors = validate_account(account)
            if clean_errors:
                case_errors.extend(
                    f"clean invariant failed: {error}" for error in clean_errors
                )
            if case.evidence_documents:
                case_errors.append("clean case must not claim evidence documents")
        if case.bucket == "clean_but_tricky":
            case_errors.extend(_condition_errors(account, case))
        if case_errors:
            errors[source] = case_errors
        else:
            valid += 1

    return GroundTruthReport(total=len(cases), valid=valid, errors=errors)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accounts", type=Path, default=Path("data/accounts"))
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=Path("data/ground_truth/cases.jsonl"),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    report = validate_ground_truth(args.accounts, args.ground_truth)
    if report.ok:
        print(
            "Validated 300/300 ground-truth cases: "
            "200 faulted, 60 clean, 40 clean-but-tricky"
        )
        return
    for source, source_errors in list(report.errors.items())[:50]:
        for error in source_errors:
            print(f"ERROR {source}: {error}")
    raise SystemExit(
        f"Ground-truth validation failed: {report.valid}/{report.total} cases passed"
    )


if __name__ == "__main__":
    main()
