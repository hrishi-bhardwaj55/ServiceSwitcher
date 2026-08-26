"""Legitimate transformations for clean-but-tricky false-positive cases."""

from datetime import date, timedelta
from decimal import Decimal

from app.schemas import InsurancePolicy, MortgageAccount, Payment, TaxBill

from data.generator.escrow import build_analysis_for_charges
from data.generator.generate import (
    PendingTransaction,
    _bill_transactions,
    _materialize_ledger,
)
from data.generator.money import money, split_money


def _annual_plan(
    tax_bills: list[TaxBill],
    policies: list[InsurancePolicy],
    year: int,
) -> tuple[Decimal, Decimal, list[tuple[int, Decimal]]]:
    charges: list[tuple[int, Decimal]] = []
    annual_tax = Decimal("0.00")
    for bill in (bill for bill in tax_bills if bill.tax_year == year):
        annual_tax = money(annual_tax + bill.annual_amount)
        installments = split_money(bill.annual_amount, len(bill.due_dates))
        charges.extend(
            (due_date.month, installment)
            for due_date, installment in zip(
                bill.due_dates,
                installments,
                strict=True,
            )
        )
    policy = next(policy for policy in policies if policy.renewal_date.year == year)
    charges.append((policy.renewal_date.month, policy.annual_premium))
    return annual_tax, policy.annual_premium, charges


def rebuild_escrow(
    account: MortgageAccount,
    *,
    tax_bills: list[TaxBill] | None = None,
    policies: list[InsurancePolicy] | None = None,
) -> MortgageAccount:
    """Recompute every escrow-dependent field after a legitimate source change."""

    tax_bills = tax_bills or account.tax_bills
    policies = policies or account.insurance_policies
    old_servicer, new_servicer = (
        period.servicer_id for period in account.servicing_periods
    )
    transfer_date = account.servicing_periods[1].start_date
    principal_and_interest = money(
        account.payments[0].principal + account.payments[0].interest
    )
    old_tax, old_insurance, old_charges = _annual_plan(tax_bills, policies, 2024)
    new_tax, new_insurance, new_charges = _annual_plan(tax_bills, policies, 2025)
    opening = next(
        transaction
        for transaction in account.escrow_ledger
        if transaction.type == "ADJUSTMENT" and transaction.payee == "OPENING_BALANCE"
    )
    initial_analysis = build_analysis_for_charges(
        servicer_id=old_servicer,
        analysis_date=account.origination_date,
        current_balance=opening.amount,
        annual_tax=old_tax,
        annual_insurance=old_insurance,
        charges=old_charges,
        principal_and_interest=principal_and_interest,
    )
    old_deposit = money(
        initial_analysis.stated_monthly_escrow
        + initial_analysis.stated_shortage_monthly
    )
    last_payment_date = account.payments[-1].date
    history_end = last_payment_date.replace(day=28) + timedelta(days=4)
    history_end = history_end - timedelta(days=history_end.day)
    bill_transactions = _bill_transactions(
        tax_bills,
        policies,
        account.origination_date,
        history_end,
    )
    old_deposits = [
        PendingTransaction(
            date=payment.date,
            type="DEPOSIT",
            amount=old_deposit,
            payee=old_servicer,
            priority=1,
        )
        for payment in account.payments
        if payment.date < transfer_date
    ]
    transfer_balance = opening.amount
    for transaction in [*old_deposits, *bill_transactions]:
        if transaction.date < transfer_date:
            transfer_balance = money(transfer_balance + transaction.amount)
    old_transfer_analysis = build_analysis_for_charges(
        servicer_id=old_servicer,
        analysis_date=transfer_date - timedelta(days=1),
        current_balance=transfer_balance,
        annual_tax=old_tax,
        annual_insurance=old_insurance,
        charges=old_charges,
        principal_and_interest=principal_and_interest,
    )
    new_transfer_analysis = build_analysis_for_charges(
        servicer_id=new_servicer,
        analysis_date=transfer_date,
        current_balance=transfer_balance,
        annual_tax=new_tax,
        annual_insurance=new_insurance,
        charges=new_charges,
        principal_and_interest=principal_and_interest,
    )
    new_deposit = money(
        new_transfer_analysis.stated_monthly_escrow
        + new_transfer_analysis.stated_shortage_monthly
    )

    payments: list[Payment] = []
    deposits: list[PendingTransaction] = []
    for payment in account.payments:
        escrow = old_deposit if payment.date < transfer_date else new_deposit
        servicer = old_servicer if payment.date < transfer_date else new_servicer
        payments.append(
            payment.model_copy(
                update={
                    "escrow": escrow,
                    "total": money(payment.principal + payment.interest + escrow),
                }
            )
        )
        deposits.append(
            PendingTransaction(
                date=payment.date,
                type="DEPOSIT",
                amount=escrow,
                payee=servicer,
                priority=1,
            )
        )

    opening_transaction = PendingTransaction(
        date=account.origination_date - timedelta(days=1),
        type="ADJUSTMENT",
        amount=opening.amount,
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
    return account.model_copy(
        update={
            "payments": payments,
            "escrow_ledger": _materialize_ledger(
                [
                    opening_transaction,
                    transfer_transaction,
                    *deposits,
                    *bill_transactions,
                ]
            ),
            "tax_bills": tax_bills,
            "insurance_policies": policies,
            "escrow_analyses": [
                initial_analysis,
                old_transfer_analysis,
                new_transfer_analysis,
            ],
        }
    )


def with_insurance_premium_jump(
    account: MortgageAccount,
    variant: int,
) -> MortgageAccount:
    old_premium = money(Decimal("1500.00") + Decimal(variant) * Decimal("37.00"))
    new_premium = money(old_premium * Decimal("1.60"))
    policies = [
        policy.model_copy(
            update={
                "annual_premium": old_premium
                if policy.renewal_date.year == 2024
                else new_premium
            }
        )
        for policy in account.insurance_policies
    ]
    return rebuild_escrow(account, policies=policies)


def with_distinct_tax_authorities(
    account: MortgageAccount,
    variant: int,
) -> MortgageAccount:
    del variant
    bills: list[TaxBill] = []
    for year in (2024, 2025):
        annual_total = money(
            sum(
                (
                    bill.annual_amount
                    for bill in account.tax_bills
                    if bill.tax_year == year
                ),
                Decimal("0.00"),
            )
        )
        county_amount = money(annual_total * Decimal("0.55"))
        school_amount = money(annual_total - county_amount)
        bills.extend(
            [
                TaxBill(
                    authority="County Revenue Office",
                    tax_year=year,
                    annual_amount=county_amount,
                    due_dates=[date(year, 6, 15)],
                ),
                TaxBill(
                    authority="Unified School District",
                    tax_year=year,
                    annual_amount=school_amount,
                    due_dates=[date(year, 8, 4)],
                ),
            ]
        )
    return rebuild_escrow(account, tax_bills=bills)


def with_fully_explained_payment_increase(
    account: MortgageAccount,
    variant: int,
) -> MortgageAccount:
    old_tax = money(Decimal("6000.00") + Decimal(variant) * Decimal("50.00"))
    new_tax = money(old_tax + Decimal("3600.00"))
    original_by_year = {
        bill.tax_year: bill for bill in account.tax_bills if bill.tax_year in {2024, 2025}
    }
    bills = [
        original_by_year[year].model_copy(
            update={"annual_amount": old_tax if year == 2024 else new_tax}
        )
        for year in (2024, 2025)
    ]
    return rebuild_escrow(account, tax_bills=bills)
