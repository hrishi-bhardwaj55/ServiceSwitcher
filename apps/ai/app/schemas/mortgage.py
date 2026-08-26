"""Canonical mortgage account models from the ServicerSwitch specification."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Money = Annotated[Decimal, Field(max_digits=18, decimal_places=2)]
PositiveMoney = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]
NonNegativeMoney = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)]


class CanonicalModel(BaseModel):
    """Strict structural contract for generated and extracted account data."""

    model_config = ConfigDict(extra="forbid")


class Servicer(CanonicalModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)


class ServicingPeriod(CanonicalModel):
    servicer_id: str = Field(min_length=1)
    start_date: date
    end_date: date | None = None


class Payment(CanonicalModel):
    date: date
    total: PositiveMoney
    principal: PositiveMoney
    interest: NonNegativeMoney
    escrow: PositiveMoney


class EscrowTransaction(CanonicalModel):
    date: date
    type: Literal[
        "DEPOSIT",
        "TAX_DISBURSEMENT",
        "INSURANCE_DISBURSEMENT",
        "ADJUSTMENT",
    ]
    amount: Money
    payee: str | None = None
    balance_after: Money


class TaxBill(CanonicalModel):
    authority: str = Field(min_length=1)
    tax_year: int = Field(ge=1900)
    annual_amount: PositiveMoney
    due_dates: list[date] = Field(min_length=1)


class InsurancePolicy(CanonicalModel):
    carrier: str = Field(min_length=1)
    annual_premium: PositiveMoney
    renewal_date: date


class EscrowAnalysis(CanonicalModel):
    servicer_id: str = Field(min_length=1)
    analysis_date: date
    projected_annual_tax: PositiveMoney
    projected_annual_insurance: PositiveMoney
    current_balance: Money
    stated_shortage: NonNegativeMoney
    stated_monthly_escrow: PositiveMoney
    stated_shortage_monthly: NonNegativeMoney
    new_total_payment: PositiveMoney


class MortgageAccount(CanonicalModel):
    account_id: str = Field(min_length=1)
    original_principal: PositiveMoney
    current_principal: NonNegativeMoney
    annual_rate: Annotated[Decimal, Field(gt=0, lt=1, decimal_places=8)]
    term_months: int = Field(gt=0)
    origination_date: date
    servicing_periods: list[ServicingPeriod] = Field(min_length=1)
    payments: list[Payment]
    escrow_ledger: list[EscrowTransaction]
    tax_bills: list[TaxBill]
    insurance_policies: list[InsurancePolicy]
    escrow_analyses: list[EscrowAnalysis]
