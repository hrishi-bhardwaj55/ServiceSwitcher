"""Build the 300-case faulted, clean, and clean-but-tricky corpus."""

from __future__ import annotations

import argparse
import os
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

from app.schemas import GroundTruthCase, MortgageAccount

from data.faults.common import FaultInjection
from data.faults.duplicate_tax import inject as inject_duplicate_tax
from data.faults.escrow_balance import inject as inject_escrow_balance
from data.faults.property_tax import inject as inject_property_tax
from data.faults.shortage import inject as inject_shortage
from data.faults.tricky import (
    with_distinct_tax_authorities,
    with_fully_explained_payment_increase,
    with_insurance_premium_jump,
)
from data.faults.unexplained_payment import inject as inject_unexplained_payment
from data.generator.generate import write_accounts

EXPECTED_COUNT = 300
FAULTED_COUNT = 200
CLEAN_COUNT = 60
Injector = Callable[[MortgageAccount, int], FaultInjection]
INJECTORS: tuple[Injector, ...] = (
    inject_escrow_balance,
    inject_property_tax,
    inject_shortage,
    inject_duplicate_tax,
    inject_unexplained_payment,
)


def load_accounts(input_path: Path) -> list[MortgageAccount]:
    files = sorted(input_path.glob("account-*.json"))
    if len(files) != EXPECTED_COUNT:
        raise ValueError(f"expected {EXPECTED_COUNT} clean accounts; found {len(files)}")
    return [
        MortgageAccount.model_validate_json(path.read_text(encoding="utf-8"))
        for path in files
    ]


def _tricky_assignments(
    accounts: list[MortgageAccount],
) -> dict[int, tuple[str, int]]:
    tricky_indexes = list(range(FAULTED_COUNT + CLEAN_COUNT, EXPECTED_COUNT))
    reassessments = [
        index
        for index in tricky_indexes
        if accounts[index].tax_bills[1].annual_amount
        >= accounts[index].tax_bills[0].annual_amount * Decimal("1.40")
    ]
    remaining = [index for index in tricky_indexes if index not in reassessments]
    assignments = {
        index: ("LEGITIMATE_TAX_REASSESSMENT", variant)
        for variant, index in enumerate(reassessments)
    }
    for variant, index in enumerate(remaining[:10]):
        assignments[index] = ("LEGITIMATE_INSURANCE_PREMIUM_JUMP", variant)
    for variant, index in enumerate(remaining[10:20]):
        assignments[index] = ("DISTINCT_TAX_AUTHORITIES_CLOSE_TOGETHER", variant)
    for variant, index in enumerate(remaining[20:]):
        assignments[index] = ("FULLY_EXPLAINED_PAYMENT_INCREASE", variant)
    return assignments


def build_cases(
    clean_accounts: list[MortgageAccount],
) -> tuple[list[MortgageAccount], list[GroundTruthCase]]:
    """Apply deterministic bucket assignments and return accounts plus labels."""

    if len(clean_accounts) != EXPECTED_COUNT:
        raise ValueError(f"expected {EXPECTED_COUNT} clean accounts")
    tricky_assignments = _tricky_assignments(clean_accounts)
    case_accounts: list[MortgageAccount] = []
    cases: list[GroundTruthCase] = []

    for index, clean_account in enumerate(clean_accounts):
        common = {
            "case_id": f"CASE-{index + 1:04d}",
            "account_id": clean_account.account_id,
        }
        if index < FAULTED_COUNT:
            injector_index, variant = divmod(index, 40)
            result = INJECTORS[injector_index](clean_account, variant)
            case_account = result.account
            case = GroundTruthCase(
                **common,
                bucket="faulted",
                expected_findings=[result.finding_type],
                expected_impact_total=result.impact_total,
                expected_monthly_impact=result.monthly_impact,
                evidence_documents=list(result.evidence_documents),
            )
        elif index < FAULTED_COUNT + CLEAN_COUNT:
            case_account = clean_account
            case = GroundTruthCase(
                **common,
                bucket="clean",
                expected_findings=[],
                expected_impact_total="0.00",
                expected_monthly_impact="0.00",
                evidence_documents=[],
            )
        else:
            condition, variant = tricky_assignments[index]
            if condition == "LEGITIMATE_INSURANCE_PREMIUM_JUMP":
                case_account = with_insurance_premium_jump(clean_account, variant)
            elif condition == "DISTINCT_TAX_AUTHORITIES_CLOSE_TOGETHER":
                case_account = with_distinct_tax_authorities(clean_account, variant)
            elif condition == "FULLY_EXPLAINED_PAYMENT_INCREASE":
                case_account = with_fully_explained_payment_increase(
                    clean_account,
                    variant,
                )
            else:
                case_account = clean_account
            case = GroundTruthCase(
                **common,
                bucket="clean_but_tricky",
                expected_findings=[],
                expected_impact_total="0.00",
                expected_monthly_impact="0.00",
                evidence_documents=[],
                tricky_condition=condition,
            )
        case_accounts.append(case_account)
        cases.append(case)

    return case_accounts, cases


def write_cases(cases: list[GroundTruthCase], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    serialized = "\n".join(case.model_dump_json() for case in cases) + "\n"
    temporary.write_text(serialized, encoding="utf-8")
    os.replace(temporary, output)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/accounts"))
    parser.add_argument("--output", type=Path, default=Path("data/accounts"))
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=Path("data/ground_truth/cases.jsonl"),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    accounts, cases = build_cases(load_accounts(args.input))
    write_accounts(accounts, args.output)
    write_cases(cases, args.ground_truth)
    print(
        "Injected 200 single-fault cases; preserved 60 clean and built "
        f"40 clean-but-tricky cases in {args.output}"
    )
    print(f"Wrote {len(cases)} labels to {args.ground_truth}")


if __name__ == "__main__":
    main()
