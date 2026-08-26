"""Validate every invariant in generated ServicerSwitch mortgage accounts."""

from __future__ import annotations

import argparse
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal, localcontext
from pathlib import Path

from app.schemas import EscrowAnalysis, EscrowTransaction, MortgageAccount
from pydantic import ValidationError

CENT = Decimal("0.01")
TWELVE = Decimal(12)
VALID_TAX_MONTHS = {(12,), (6, 12), (3, 6, 9, 12)}


@dataclass(frozen=True)
class AnnualEscrowPlan:
    tax_total: Decimal
    insurance_total: Decimal
    charges: tuple[tuple[int, Decimal], ...]


def _money(value: Decimal | int) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def _monthly_payment(principal: Decimal, annual_rate: Decimal, term_months: int) -> Decimal:
    monthly_rate = annual_rate / TWELVE
    with localcontext() as context:
        context.prec = 50
        growth = (Decimal(1) + monthly_rate) ** term_months
        payment = principal * monthly_rate * growth / (growth - Decimal(1))
    return _money(payment)


def _closed_form_balance(
    principal: Decimal,
    annual_rate: Decimal,
    scheduled_payment: Decimal,
    periods: int,
) -> Decimal:
    monthly_rate = annual_rate / TWELVE
    with localcontext() as context:
        context.prec = 50
        growth = (Decimal(1) + monthly_rate) ** periods
        balance = principal * growth - scheduled_payment * (
            (growth - Decimal(1)) / monthly_rate
        )
    return _money(balance)


def _split_money(total: Decimal, parts: int) -> list[Decimal]:
    total_cents = int(_money(total) / CENT)
    base_cents, remainder = divmod(total_cents, parts)
    return [
        _money(Decimal(base_cents + (1 if index < remainder else 0)) * CENT)
        for index in range(parts)
    ]


def _projection_months(analysis_date: date) -> list[date]:
    first = date(analysis_date.year, analysis_date.month, 1)
    if analysis_date.day > 1:
        first = _add_months(first, 1)
    return [_add_months(first, offset) for offset in range(12)]


def _analysis_expected_values(
    analysis: EscrowAnalysis,
    principal_and_interest: Decimal,
    tax_due_months: tuple[int, ...],
    insurance_due_month: int,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    tax_installments = _split_money(
        analysis.projected_annual_tax,
        len(tax_due_months),
    )
    charges = [
        (month, amount)
        for month, amount in zip(tax_due_months, tax_installments, strict=True)
    ]
    charges.append((insurance_due_month, analysis.projected_annual_insurance))
    return _analysis_expected_values_for_charges(
        analysis,
        principal_and_interest,
        charges,
    )


def _analysis_expected_values_for_charges(
    analysis: EscrowAnalysis,
    principal_and_interest: Decimal,
    charges: list[tuple[int, Decimal]] | tuple[tuple[int, Decimal], ...],
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    monthly_escrow = _money(
        (analysis.projected_annual_tax + analysis.projected_annual_insurance) / TWELVE
    )
    balance = analysis.current_balance
    low_balance = balance

    for month in _projection_months(analysis.analysis_date):
        balance = _money(balance + monthly_escrow)
        for due_month, amount in charges:
            if month.month == due_month:
                balance = _money(balance - amount)
        low_balance = min(low_balance, balance)

    cushion = _money(
        (analysis.projected_annual_tax + analysis.projected_annual_insurance)
        / Decimal(6)
    )
    shortage = max(_money(cushion - low_balance), Decimal("0.00"))
    shortage_monthly = _money(shortage / TWELVE)
    new_total_payment = _money(
        principal_and_interest + monthly_escrow + shortage_monthly
    )
    return monthly_escrow, shortage, shortage_monthly, new_total_payment


def validate_ledger_chain(ledger: list[EscrowTransaction]) -> list[str]:
    """Return balance-chain and transaction-sign errors for an escrow ledger."""

    errors: list[str] = []
    balance = Decimal("0.00")
    previous_date: date | None = None

    for index, transaction in enumerate(ledger):
        if previous_date is not None and transaction.date < previous_date:
            errors.append(f"escrow_ledger[{index}] is out of chronological order")
        expected_balance = _money(balance + transaction.amount)
        if transaction.balance_after != expected_balance:
            errors.append(
                f"escrow_ledger[{index}] balance is {transaction.balance_after}; "
                f"expected {expected_balance}"
            )
        if transaction.type == "DEPOSIT" and transaction.amount <= 0:
            errors.append(f"escrow_ledger[{index}] deposit must be positive")
        if transaction.type.endswith("DISBURSEMENT") and transaction.amount >= 0:
            errors.append(f"escrow_ledger[{index}] disbursement must be negative")
        balance = transaction.balance_after
        previous_date = transaction.date

    return errors


def _validate_terms_and_payments(account: MortgageAccount, errors: list[str]) -> Decimal:
    if not Decimal("180000.00") <= account.original_principal <= Decimal("750000.00"):
        errors.append("original_principal is outside $180,000-$750,000")
    if not Decimal("0.030") <= account.annual_rate <= Decimal("0.075"):
        errors.append("annual_rate is outside 3.0%-7.5%")
    if account.term_months not in {180, 360}:
        errors.append("term_months must be 180 or 360")
    if len(account.payments) != 18:
        errors.append(f"expected 18 payments; found {len(account.payments)}")

    scheduled_payment = _monthly_payment(
        account.original_principal,
        account.annual_rate,
        account.term_months,
    )
    balance = account.original_principal
    for index, payment in enumerate(account.payments):
        expected_date = _add_months(account.origination_date, index)
        if payment.date != expected_date:
            errors.append(
                f"payments[{index}] date is {payment.date}; expected {expected_date}"
            )
        if payment.total != _money(payment.principal + payment.interest + payment.escrow):
            errors.append(f"payments[{index}] total does not equal principal+interest+escrow")

        expected_interest = _money(balance * account.annual_rate / TWELVE)
        if payment.interest != expected_interest:
            errors.append(
                f"payments[{index}] interest is {payment.interest}; "
                f"expected {expected_interest}"
            )
        expected_principal = _money(scheduled_payment - expected_interest)
        if payment.principal != expected_principal:
            errors.append(
                f"payments[{index}] principal is {payment.principal}; "
                f"expected {expected_principal}"
            )
        balance = _money(balance - payment.principal)

    if account.current_principal != balance:
        errors.append(
            f"current_principal is {account.current_principal}; chained balance is {balance}"
        )
    contractual_balance = _closed_form_balance(
        account.original_principal,
        account.annual_rate,
        scheduled_payment,
        len(account.payments),
    )
    if account.current_principal != contractual_balance:
        errors.append(
            f"current_principal is {account.current_principal}; "
            f"closed-form balance is {contractual_balance}"
        )
    return scheduled_payment


def _validate_servicing(account: MortgageAccount, errors: list[str]) -> date | None:
    if len(account.servicing_periods) != 2:
        errors.append(
            f"expected exactly one transfer (two servicing periods); "
            f"found {len(account.servicing_periods)} periods"
        )
        return None

    old_period, new_period = account.servicing_periods
    transfer_date = new_period.start_date
    if old_period.servicer_id == new_period.servicer_id:
        errors.append("servicing transfer must change servicer_id")
    if old_period.start_date != account.origination_date:
        errors.append("first servicing period must start at origination")
    if old_period.end_date != transfer_date - timedelta(days=1):
        errors.append("servicing periods are not contiguous at transfer")
    if new_period.end_date is not None:
        errors.append("current servicing period must have no end date")

    payment_number = next(
        (
            index
            for index, payment in enumerate(account.payments, start=1)
            if payment.date == transfer_date
        ),
        None,
    )
    if payment_number is None or not 6 <= payment_number <= 12:
        errors.append("transfer must occur on payment month 6 through 12")
    return transfer_date


def _validate_deposits(account: MortgageAccount, errors: list[str]) -> None:
    deposits = [transaction for transaction in account.escrow_ledger if transaction.type == "DEPOSIT"]
    if len(deposits) != len(account.payments):
        errors.append(
            f"expected {len(account.payments)} escrow deposits; found {len(deposits)}"
        )
        return

    for index, (payment, deposit) in enumerate(zip(account.payments, deposits, strict=True)):
        if deposit.date != payment.date:
            errors.append(f"deposit[{index}] date does not match payment date")
        if deposit.amount != payment.escrow:
            errors.append(f"deposit[{index}] amount does not match payment escrow")


def _validate_bills(
    account: MortgageAccount,
    errors: list[str],
) -> dict[int, AnnualEscrowPlan] | None:
    tax_years = {bill.tax_year for bill in account.tax_bills}
    if tax_years != {2024, 2025}:
        errors.append("tax_bills must cover 2024 and 2025")
        return None
    if not account.payments:
        errors.append("payment history is required to validate disbursements")
        return None

    history_end = _add_months(account.payments[-1].date, 1) - timedelta(days=1)
    expected_tax: list[tuple[date, Decimal, str]] = []
    tax_charges: dict[int, list[tuple[int, Decimal]]] = {2024: [], 2025: []}
    tax_totals: dict[int, Decimal] = {2024: Decimal("0.00"), 2025: Decimal("0.00")}
    for bill in account.tax_bills:
        if any(due_date.year != bill.tax_year for due_date in bill.due_dates):
            errors.append(f"{bill.tax_year} tax due date has the wrong year")
        installments = _split_money(bill.annual_amount, len(bill.due_dates))
        tax_totals[bill.tax_year] = _money(
            tax_totals[bill.tax_year] + bill.annual_amount
        )
        for due_date, installment in zip(bill.due_dates, installments, strict=True):
            tax_charges[bill.tax_year].append((due_date.month, installment))
            if account.origination_date <= due_date <= history_end:
                expected_tax.append((due_date, -installment, bill.authority))
    for year, annual_total in tax_totals.items():
        if not Decimal("2400.00") <= annual_total <= Decimal("14000.00"):
            errors.append(f"{year} total annual tax is outside $2,400-$14,000")

    actual_tax = [
        (transaction.date, transaction.amount, transaction.payee or "")
        for transaction in account.escrow_ledger
        if transaction.type == "TAX_DISBURSEMENT"
    ]
    if actual_tax != sorted(expected_tax):
        errors.append("tax disbursements do not exactly match scheduled due dates and amounts")

    policies_by_year = {
        year: [
            policy
            for policy in account.insurance_policies
            if policy.renewal_date.year == year
        ]
        for year in (2024, 2025)
    }
    if any(len(policies) != 1 for policies in policies_by_year.values()):
        errors.append("insurance_policies must contain one policy for 2024 and 2025")
        return None

    expected_insurance: list[tuple[date, Decimal, str]] = []
    plans: dict[int, AnnualEscrowPlan] = {}
    for year, policies in policies_by_year.items():
        policy = policies[0]
        if not Decimal("900.00") <= policy.annual_premium <= Decimal("4200.00"):
            errors.append("annual insurance premium is outside $900-$4,200")
        if account.origination_date <= policy.renewal_date <= history_end:
            expected_insurance.append(
                (policy.renewal_date, -policy.annual_premium, policy.carrier)
            )
        plans[year] = AnnualEscrowPlan(
            tax_total=tax_totals[year],
            insurance_total=policy.annual_premium,
            charges=(
                *tax_charges[year],
                (policy.renewal_date.month, policy.annual_premium),
            ),
        )
    actual_insurance = [
        (transaction.date, transaction.amount, transaction.payee or "")
        for transaction in account.escrow_ledger
        if transaction.type == "INSURANCE_DISBURSEMENT"
    ]
    if actual_insurance != sorted(expected_insurance):
        errors.append(
            "insurance disbursements do not exactly match renewal dates and premiums"
        )
    return plans


def _validate_analysis_values(
    analysis: EscrowAnalysis,
    principal_and_interest: Decimal,
    charges: tuple[tuple[int, Decimal], ...],
    errors: list[str],
    label: str,
) -> None:
    monthly, shortage, shortage_monthly, total = _analysis_expected_values_for_charges(
        analysis,
        principal_and_interest,
        charges,
    )
    comparisons = {
        "stated_monthly_escrow": (analysis.stated_monthly_escrow, monthly),
        "stated_shortage": (analysis.stated_shortage, shortage),
        "stated_shortage_monthly": (
            analysis.stated_shortage_monthly,
            shortage_monthly,
        ),
        "new_total_payment": (analysis.new_total_payment, total),
    }
    for field, (actual, expected) in comparisons.items():
        if actual != expected:
            errors.append(f"{label} {field} is {actual}; expected {expected}")


def _validate_transfer_and_analyses(
    account: MortgageAccount,
    transfer_date: date | None,
    principal_and_interest: Decimal,
    annual_plans: dict[int, AnnualEscrowPlan] | None,
    errors: list[str],
) -> None:
    if transfer_date is None or annual_plans is None:
        return
    if len(account.escrow_analyses) != 3:
        errors.append(f"expected three escrow analyses; found {len(account.escrow_analyses)}")
        return

    old_period, new_period = account.servicing_periods
    initial, old_transfer, new_transfer = account.escrow_analyses
    opening = next(
        (
            transaction
            for transaction in account.escrow_ledger
            if transaction.type == "ADJUSTMENT" and transaction.payee == "OPENING_BALANCE"
        ),
        None,
    )
    transfer_markers = [
        transaction
        for transaction in account.escrow_ledger
        if transaction.type == "ADJUSTMENT"
        and (transaction.payee or "").startswith("SERVICING_TRANSFER:")
    ]
    if opening is None:
        errors.append("escrow ledger is missing its opening balance adjustment")
    elif (
        opening.date != account.origination_date - timedelta(days=1)
        or opening.amount != opening.balance_after
    ):
        errors.append("opening balance adjustment is inconsistent")
    if len(transfer_markers) != 1:
        errors.append("escrow ledger must contain exactly one transfer marker")
        return
    transfer_marker = transfer_markers[0]
    if transfer_marker.date != transfer_date or transfer_marker.amount != Decimal("0.00"):
        errors.append("transfer marker must be a zero-dollar adjustment on the transfer date")

    expected_analysis_identity = [
        (initial, old_period.servicer_id, account.origination_date),
        (old_transfer, old_period.servicer_id, transfer_date - timedelta(days=1)),
        (new_transfer, new_period.servicer_id, transfer_date),
    ]
    for analysis, servicer_id, analysis_date in expected_analysis_identity:
        if analysis.servicer_id != servicer_id or analysis.analysis_date != analysis_date:
            errors.append("escrow analysis is assigned to the wrong servicer or date")

    if opening is not None and initial.current_balance != opening.balance_after:
        errors.append("initial analysis does not start from the opening escrow balance")
    if old_transfer.current_balance != transfer_marker.balance_after:
        errors.append("old-servicer analysis does not use the transfer balance")
    if new_transfer.current_balance != transfer_marker.balance_after:
        errors.append("new-servicer analysis does not preserve the transfer balance")
    if old_transfer.current_balance != new_transfer.current_balance:
        errors.append("escrow balance is discontinuous across servicing transfer")

    expected_plans = [annual_plans[2024], annual_plans[2024], annual_plans[2025]]
    for label, analysis, plan in zip(
        ("initial analysis", "old transfer analysis", "new transfer analysis"),
        account.escrow_analyses,
        expected_plans,
        strict=True,
    ):
        if analysis.projected_annual_tax != plan.tax_total:
            errors.append(f"{label} projected tax does not match the applicable bill")
        if analysis.projected_annual_insurance != plan.insurance_total:
            errors.append(f"{label} projected insurance does not match the policy")
        _validate_analysis_values(
            analysis,
            principal_and_interest,
            plan.charges,
            errors,
            label,
        )

    old_deposit = _money(initial.stated_monthly_escrow + initial.stated_shortage_monthly)
    new_deposit = _money(
        new_transfer.stated_monthly_escrow + new_transfer.stated_shortage_monthly
    )
    for index, payment in enumerate(account.payments):
        expected_deposit = old_deposit if payment.date < transfer_date else new_deposit
        if payment.escrow != expected_deposit:
            errors.append(
                f"payments[{index}] escrow does not match the applicable analysis"
            )


def validate_account(account: MortgageAccount) -> list[str]:
    """Return all invariant violations found in one account."""

    errors: list[str] = []
    principal_and_interest = _validate_terms_and_payments(account, errors)
    transfer_date = _validate_servicing(account, errors)
    errors.extend(validate_ledger_chain(account.escrow_ledger))
    _validate_deposits(account, errors)
    annual_plans = _validate_bills(account, errors)
    _validate_transfer_and_analyses(
        account,
        transfer_date,
        principal_and_interest,
        annual_plans,
        errors,
    )
    return errors


@dataclass(frozen=True)
class ValidationReport:
    total: int
    valid: int
    errors: dict[str, list[str]]

    @property
    def ok(self) -> bool:
        return self.total == self.valid and not self.errors


def validate_directory(input_path: Path, expected_count: int = 300) -> ValidationReport:
    """Load and validate a complete generated account directory."""

    files = sorted(input_path.glob("account-*.json"))
    errors: dict[str, list[str]] = {}
    accounts: list[MortgageAccount] = []
    if len(files) != expected_count:
        errors["collection"] = [
            f"expected {expected_count} account files; found {len(files)}"
        ]

    for path in files:
        try:
            account = MortgageAccount.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValidationError, ValueError) as error:
            errors[path.name] = [f"cannot load canonical account: {error}"]
            continue
        account_errors = validate_account(account)
        if path.name != f"account-{account.account_id.removeprefix('SS-')}.json":
            account_errors.append("filename does not match account_id")
        if account_errors:
            errors[path.name] = account_errors
        accounts.append(account)

    account_ids = [account.account_id for account in accounts]
    collection_errors = errors.setdefault("collection", [])
    if len(set(account_ids)) != len(account_ids):
        collection_errors.append("account_id values are not unique")
    if len(accounts) >= 5:
        if {account.term_months for account in accounts} != {180, 360}:
            collection_errors.append("collection does not vary mortgage terms")
        tax_patterns = {
            tuple(due_date.month for due_date in account.tax_bills[0].due_dates)
            for account in accounts
        }
        if tax_patterns != VALID_TAX_MONTHS:
            collection_errors.append("collection does not include all tax schedules")
        transfer_numbers = {
            next(
                index
                for index, payment in enumerate(account.payments, start=1)
                if payment.date == account.servicing_periods[1].start_date
            )
            for account in accounts
        }
        if transfer_numbers != set(range(6, 13)):
            collection_errors.append("collection does not vary transfer months 6 through 12")
        reassessed = sum(
            account.tax_bills[1].annual_amount
            >= _money(account.tax_bills[0].annual_amount * Decimal("1.40"))
            for account in accounts
        )
        ratio = Decimal(reassessed) / Decimal(len(accounts))
        if not Decimal("0.18") <= ratio <= Decimal("0.22"):
            collection_errors.append(
                f"legitimate reassessment ratio is {ratio:.1%}; expected roughly 20%"
            )
        if len({account.original_principal for account in accounts}) < len(accounts) * 9 // 10:
            collection_errors.append("collection does not sufficiently vary principal")
        if len({account.annual_rate for account in accounts}) < len(accounts) * 9 // 10:
            collection_errors.append("collection does not sufficiently vary interest rates")
    if not collection_errors:
        errors.pop("collection", None)

    valid = sum(
        path.name not in errors
        for path in files
        if path.name != "collection"
    )
    return ValidationReport(total=len(files), valid=valid, errors=errors)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/accounts"))
    parser.add_argument("--expected-count", type=int, default=300)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    report = validate_directory(args.input, args.expected_count)
    if report.ok:
        print(f"Validated {report.valid}/{report.total} accounts: all invariants hold")
        return

    for source, source_errors in list(report.errors.items())[:50]:
        for error in source_errors:
            print(f"ERROR {source}: {error}")
    raise SystemExit(
        f"Validation failed: {report.valid}/{report.total} accounts passed"
    )


if __name__ == "__main__":
    main()
