"""Generate deterministic, internally consistent synthetic mortgage accounts."""

from __future__ import annotations

import argparse
import os
import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Literal

from app.schemas import (
    EscrowAnalysis,
    EscrowTransaction,
    InsurancePolicy,
    MortgageAccount,
    Payment,
    ServicingPeriod,
    TaxBill,
)

from data.generator.escrow import add_months, build_analysis
from data.generator.money import (
    amortize,
    closed_form_balance,
    money,
    split_money,
)

DEFAULT_COUNT = 300
DEFAULT_SEED = 20250825
HISTORY_MONTHS = 18
ORIGINATION_DATE = date(2024, 1, 1)
INSURANCE_DUE_MONTH = 4
TAX_SCHEDULES: dict[str, tuple[int, ...]] = {
    "annual": (12,),
    "semiannual": (6, 12),
    "quarterly": (3, 6, 9, 12),
}
SERVICERS = (
    "ATLANTIC-HOME",
    "CEDAR-MORTGAGE",
    "HARBOR-LOAN",
    "SUMMIT-SERVICING",
    "WILLOW-FINANCIAL",
)

TransactionType = Literal[
    "DEPOSIT",
    "TAX_DISBURSEMENT",
    "INSURANCE_DISBURSEMENT",
    "ADJUSTMENT",
]


@dataclass(frozen=True)
class PendingTransaction:
    date: date
    type: TransactionType
    amount: Decimal
    payee: str | None
    priority: int


@dataclass(frozen=True)
class LoanTerms:
    principal: Decimal
    annual_rate: Decimal
    term_months: int


def _select_loan_terms(rng: random.Random, term_months: int) -> LoanTerms:
    """Choose terms whose cent-rounded recurrence matches the contractual formula."""

    for _ in range(10_000):
        principal = money(Decimal(rng.randint(18_000_000, 75_000_000)) / Decimal(100))
        annual_rate = Decimal(rng.randint(30_000, 75_000)) / Decimal(1_000_000)
        payment, lines = amortize(
            principal,
            annual_rate,
            term_months,
            HISTORY_MONTHS,
        )
        contractual = closed_form_balance(
            principal,
            annual_rate,
            payment,
            HISTORY_MONTHS,
        )
        if lines[-1].balance_after == contractual:
            return LoanTerms(principal, annual_rate, term_months)

    raise RuntimeError("could not select cent-consistent loan terms")


def _tax_bill(
    *,
    year: int,
    annual_amount: Decimal,
    due_months: tuple[int, ...],
) -> TaxBill:
    return TaxBill(
        authority="County Revenue Office",
        tax_year=year,
        annual_amount=annual_amount,
        due_dates=[date(year, month, 15) for month in due_months],
    )


def _bill_transactions(
    tax_bills: list[TaxBill],
    policies: list[InsurancePolicy],
    history_start: date,
    history_end: date,
) -> list[PendingTransaction]:
    transactions: list[PendingTransaction] = []

    for bill in tax_bills:
        installments = split_money(bill.annual_amount, len(bill.due_dates))
        for due_date, amount in zip(bill.due_dates, installments, strict=True):
            if history_start <= due_date <= history_end:
                transactions.append(
                    PendingTransaction(
                        date=due_date,
                        type="TAX_DISBURSEMENT",
                        amount=-amount,
                        payee=bill.authority,
                        priority=2,
                    )
                )

    for policy in policies:
        if history_start <= policy.renewal_date <= history_end:
            transactions.append(
                PendingTransaction(
                    date=policy.renewal_date,
                    type="INSURANCE_DISBURSEMENT",
                    amount=-policy.annual_premium,
                    payee=policy.carrier,
                    priority=3,
                )
            )

    return transactions


def _materialize_ledger(
    transactions: list[PendingTransaction],
) -> list[EscrowTransaction]:
    balance = Decimal("0.00")
    ledger: list[EscrowTransaction] = []

    for transaction in sorted(
        transactions,
        key=lambda item: (item.date, item.priority, item.type, item.payee or ""),
    ):
        balance = money(balance + transaction.amount)
        ledger.append(
            EscrowTransaction(
                date=transaction.date,
                type=transaction.type,
                amount=transaction.amount,
                payee=transaction.payee,
                balance_after=balance,
            )
        )

    return ledger


def _balance_before(
    opening_balance: Decimal,
    transactions: list[PendingTransaction],
    boundary: date,
) -> Decimal:
    balance = opening_balance
    for transaction in transactions:
        if transaction.date < boundary:
            balance = money(balance + transaction.amount)
    return balance


def _starting_balance(
    *,
    rng: random.Random,
    annual_tax: Decimal,
    annual_insurance: Decimal,
    tax_due_months: tuple[int, ...],
    principal_and_interest: Decimal,
) -> tuple[Decimal, EscrowAnalysis]:
    zero_balance_analysis = build_analysis(
        servicer_id="TEMP",
        analysis_date=ORIGINATION_DATE,
        current_balance=Decimal("0.00"),
        annual_tax=annual_tax,
        annual_insurance=annual_insurance,
        tax_due_months=tax_due_months,
        insurance_due_month=INSURANCE_DUE_MONTH,
        principal_and_interest=principal_and_interest,
    )
    cushion = money((annual_tax + annual_insurance) / Decimal(6))
    variation_cents = rng.randint(-int(cushion * 25), int(cushion * 25))
    opening_balance = max(
        money(zero_balance_analysis.stated_shortage + Decimal(variation_cents) / 100),
        Decimal("0.01"),
    )
    initial_analysis = build_analysis(
        servicer_id="TEMP",
        analysis_date=ORIGINATION_DATE,
        current_balance=opening_balance,
        annual_tax=annual_tax,
        annual_insurance=annual_insurance,
        tax_due_months=tax_due_months,
        insurance_due_month=INSURANCE_DUE_MONTH,
        principal_and_interest=principal_and_interest,
    )
    return opening_balance, initial_analysis


def generate_account(index: int, rng: random.Random) -> MortgageAccount:
    """Generate one deterministic account from a shared pseudo-random stream."""

    term_months = 180 if index % 2 == 0 else 360
    loan_terms = _select_loan_terms(rng, term_months)
    principal_and_interest, amortization = amortize(
        loan_terms.principal,
        loan_terms.annual_rate,
        loan_terms.term_months,
        HISTORY_MONTHS,
    )

    schedule_name = tuple(TAX_SCHEDULES)[index % len(TAX_SCHEDULES)]
    tax_due_months = TAX_SCHEDULES[schedule_name]
    reassessed = index % 5 == 0
    old_tax_limit = 9_000 if reassessed else 14_000
    old_tax = money(rng.randint(2_400, old_tax_limit))
    if reassessed:
        reassessment_factor = Decimal(140 + index % 16) / Decimal(100)
        new_tax = money(old_tax * reassessment_factor)
    else:
        new_tax = old_tax
    annual_insurance = money(rng.randint(900, 4_200))

    tax_bills = [
        _tax_bill(year=2024, annual_amount=old_tax, due_months=tax_due_months),
        _tax_bill(year=2025, annual_amount=new_tax, due_months=tax_due_months),
    ]
    policies = [
        InsurancePolicy(
            carrier="Beacon Mutual Insurance",
            annual_premium=annual_insurance,
            renewal_date=date(year, INSURANCE_DUE_MONTH, 20),
        )
        for year in (2024, 2025)
    ]

    transfer_payment_number = 6 + index % 7
    transfer_date = add_months(ORIGINATION_DATE, transfer_payment_number - 1)
    old_servicer = SERVICERS[index % len(SERVICERS)]
    new_servicer = SERVICERS[(index + 2) % len(SERVICERS)]

    opening_balance, initial_analysis = _starting_balance(
        rng=rng,
        annual_tax=old_tax,
        annual_insurance=annual_insurance,
        tax_due_months=tax_due_months,
        principal_and_interest=principal_and_interest,
    )
    initial_analysis = initial_analysis.model_copy(update={"servicer_id": old_servicer})
    old_monthly_deposit = money(
        initial_analysis.stated_monthly_escrow
        + initial_analysis.stated_shortage_monthly
    )

    last_payment_date = add_months(ORIGINATION_DATE, HISTORY_MONTHS - 1)
    history_end = add_months(last_payment_date, 1) - timedelta(days=1)
    bill_transactions = _bill_transactions(
        tax_bills,
        policies,
        ORIGINATION_DATE,
        history_end,
    )
    old_deposits = [
        PendingTransaction(
            date=add_months(ORIGINATION_DATE, payment_index),
            type="DEPOSIT",
            amount=old_monthly_deposit,
            payee=old_servicer,
            priority=1,
        )
        for payment_index in range(transfer_payment_number - 1)
    ]
    transfer_balance = _balance_before(
        opening_balance,
        [*old_deposits, *bill_transactions],
        transfer_date,
    )

    old_transfer_analysis = build_analysis(
        servicer_id=old_servicer,
        analysis_date=transfer_date - timedelta(days=1),
        current_balance=transfer_balance,
        annual_tax=old_tax,
        annual_insurance=annual_insurance,
        tax_due_months=tax_due_months,
        insurance_due_month=INSURANCE_DUE_MONTH,
        principal_and_interest=principal_and_interest,
    )
    new_transfer_analysis = build_analysis(
        servicer_id=new_servicer,
        analysis_date=transfer_date,
        current_balance=transfer_balance,
        annual_tax=new_tax,
        annual_insurance=annual_insurance,
        tax_due_months=tax_due_months,
        insurance_due_month=INSURANCE_DUE_MONTH,
        principal_and_interest=principal_and_interest,
    )
    new_monthly_deposit = money(
        new_transfer_analysis.stated_monthly_escrow
        + new_transfer_analysis.stated_shortage_monthly
    )

    payments: list[Payment] = []
    deposit_transactions: list[PendingTransaction] = []
    for payment_index, line in enumerate(amortization):
        payment_date = add_months(ORIGINATION_DATE, payment_index)
        escrow = (
            old_monthly_deposit if payment_date < transfer_date else new_monthly_deposit
        )
        servicer = old_servicer if payment_date < transfer_date else new_servicer
        payments.append(
            Payment(
                date=payment_date,
                total=money(line.principal + line.interest + escrow),
                principal=line.principal,
                interest=line.interest,
                escrow=escrow,
            )
        )
        deposit_transactions.append(
            PendingTransaction(
                date=payment_date,
                type="DEPOSIT",
                amount=escrow,
                payee=servicer,
                priority=1,
            )
        )

    opening_transaction = PendingTransaction(
        date=ORIGINATION_DATE - timedelta(days=1),
        type="ADJUSTMENT",
        amount=opening_balance,
        payee="OPENING_BALANCE",
        priority=0,
    )
    transfer_transaction = PendingTransaction(
        date=transfer_date,
        type="ADJUSTMENT",
        amount=Decimal("0.00"),
        payee=f"SERVICING_TRANSFER:{old_servicer}->{new_servicer}",
        priority=0,
    )
    ledger = _materialize_ledger(
        [
            opening_transaction,
            transfer_transaction,
            *deposit_transactions,
            *bill_transactions,
        ]
    )

    return MortgageAccount(
        account_id=f"SS-{index + 1:04d}",
        original_principal=loan_terms.principal,
        current_principal=amortization[-1].balance_after,
        annual_rate=loan_terms.annual_rate,
        term_months=loan_terms.term_months,
        origination_date=ORIGINATION_DATE,
        servicing_periods=[
            ServicingPeriod(
                servicer_id=old_servicer,
                start_date=ORIGINATION_DATE,
                end_date=transfer_date - timedelta(days=1),
            ),
            ServicingPeriod(
                servicer_id=new_servicer,
                start_date=transfer_date,
                end_date=None,
            ),
        ],
        payments=payments,
        escrow_ledger=ledger,
        tax_bills=tax_bills,
        insurance_policies=policies,
        escrow_analyses=[
            initial_analysis,
            old_transfer_analysis,
            new_transfer_analysis,
        ],
    )


def generate_accounts(count: int = DEFAULT_COUNT, seed: int = DEFAULT_SEED) -> list[MortgageAccount]:
    """Generate ``count`` accounts reproducibly from ``seed``."""

    if count <= 0:
        raise ValueError("count must be positive")
    rng = random.Random(seed)
    return [generate_account(index, rng) for index in range(count)]


def write_accounts(accounts: list[MortgageAccount], output: Path) -> None:
    """Atomically write account JSON and remove stale generator outputs."""

    output.mkdir(parents=True, exist_ok=True)
    expected_names: set[str] = set()
    for account in accounts:
        filename = f"account-{account.account_id.removeprefix('SS-')}.json"
        expected_names.add(filename)
        target = output / filename
        temporary = output / f".{filename}.tmp"
        temporary.write_text(account.model_dump_json(indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, target)

    for stale in output.glob("account-*.json"):
        if stale.name not in expected_names:
            stale.unlink()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/accounts"))
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    accounts = generate_accounts(args.count, args.seed)
    write_accounts(accounts, args.output)
    print(f"Generated {len(accounts)} accounts in {args.output}")


if __name__ == "__main__":
    main()
