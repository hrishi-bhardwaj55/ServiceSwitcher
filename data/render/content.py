"""Family-independent document content derived from canonical accounts."""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Any

CENT = Decimal("0.01")


class TemplateFamily(StrEnum):
    A = "A"
    B = "B"
    C = "C"


class DocumentType(StrEnum):
    OLD_SERVICER_STATEMENT = "old_servicer_statement"
    NEW_SERVICER_STATEMENT = "new_servicer_statement"
    TRANSFER_NOTICE = "transfer_notice"
    ESCROW_ANALYSIS = "escrow_analysis"
    PROPERTY_TAX_BILL = "property_tax_bill"

    @property
    def filename(self) -> str:
        return f"{self.value}.pdf"


DOCUMENT_TYPES = tuple(DocumentType)


@dataclass(frozen=True)
class Field:
    label: str
    value: str


@dataclass(frozen=True)
class DocumentContent:
    document_type: DocumentType
    title: str
    account_id: str
    issuer: str
    summary: tuple[Field, ...]
    details: tuple[Field, ...]
    table_title: str | None
    table_headers: tuple[str, ...]
    table_rows: tuple[tuple[str, ...], ...]
    notes: tuple[str, ...]
    required_values: tuple[str, ...]


TITLES: dict[TemplateFamily, dict[DocumentType, str]] = {
    TemplateFamily.A: {
        DocumentType.OLD_SERVICER_STATEMENT: "Final Mortgage Statement",
        DocumentType.NEW_SERVICER_STATEMENT: "Mortgage Account Statement",
        DocumentType.TRANSFER_NOTICE: "Notice of Servicing Transfer",
        DocumentType.ESCROW_ANALYSIS: "Annual Escrow Account Analysis",
        DocumentType.PROPERTY_TAX_BILL: "Property Tax Bill",
    },
    TemplateFamily.B: {
        DocumentType.OLD_SERVICER_STATEMENT: "FINAL LOAN ACCOUNT STATEMENT",
        DocumentType.NEW_SERVICER_STATEMENT: "MONTHLY LOAN ACCOUNT STATEMENT",
        DocumentType.TRANSFER_NOTICE: "SERVICING ASSIGNMENT ADVICE",
        DocumentType.ESCROW_ANALYSIS: "ESCROW COMPUTATION DISCLOSURE",
        DocumentType.PROPERTY_TAX_BILL: "REAL PROPERTY TAX ASSESSMENT",
    },
    TemplateFamily.C: {
        DocumentType.OLD_SERVICER_STATEMENT: "Closing Account Review",
        DocumentType.NEW_SERVICER_STATEMENT: "Current Account Review",
        DocumentType.TRANSFER_NOTICE: "Your Loan Servicing Is Changing",
        DocumentType.ESCROW_ANALYSIS: "Escrow Projection and Payment Review",
        DocumentType.PROPERTY_TAX_BILL: "Tax Obligation Summary",
    },
}


LABELS: dict[TemplateFamily, dict[str, str]] = {
    TemplateFamily.A: {
        "account": "Account Number",
        "servicer": "Servicer",
        "principal": "Current Principal Balance",
        "rate": "Annual Interest Rate",
        "payment_date": "Payment Date",
        "payment": "Total Monthly Payment",
        "principal_paid": "Principal",
        "interest_paid": "Interest",
        "escrow_paid": "Escrow",
        "escrow_balance": "Escrow Account Balance",
        "old_servicer": "Current Servicer",
        "new_servicer": "New Servicer",
        "transfer_date": "Effective Transfer Date",
        "last_old_date": "Last Date for Old Servicer",
        "first_new_date": "First Date for New Servicer",
        "analysis_date": "Analysis Date",
        "tax_projection": "Projected Annual Property Tax",
        "insurance_projection": "Projected Annual Insurance",
        "shortage": "Stated Escrow Shortage",
        "monthly_escrow": "Base Monthly Escrow",
        "shortage_monthly": "Monthly Shortage Payment",
        "new_payment": "New Total Payment",
        "authority": "Taxing Authority",
        "tax_year": "Tax Year",
        "annual_tax": "Annual Amount Due",
    },
    TemplateFamily.B: {
        "account": "LOAN NO.",
        "servicer": "ACCOUNT SERVICED BY",
        "principal": "UNPAID PRINCIPAL",
        "rate": "NOTE RATE",
        "payment_date": "POSTING DATE",
        "payment": "PAYMENT AMOUNT",
        "principal_paid": "PRIN APPLIED",
        "interest_paid": "INT APPLIED",
        "escrow_paid": "ESCROW APPLIED",
        "escrow_balance": "ESCROW BALANCE",
        "old_servicer": "TRANSFEROR",
        "new_servicer": "TRANSFEREE",
        "transfer_date": "SERVICE CHANGE DATE",
        "last_old_date": "TRANSFEROR CUTOFF",
        "first_new_date": "TRANSFEREE START",
        "analysis_date": "COMPUTATION DATE",
        "tax_projection": "EST. TAX - 12 MO.",
        "insurance_projection": "EST. HAZARD INS. - 12 MO.",
        "shortage": "AGGREGATE SHORTAGE",
        "monthly_escrow": "MONTHLY ESCROW REQ.",
        "shortage_monthly": "SHORTAGE INSTALLMENT",
        "new_payment": "REVISED PAYMENT",
        "authority": "LEVYING BODY",
        "tax_year": "LEVY YEAR",
        "annual_tax": "TOTAL TAX LEVY",
    },
    TemplateFamily.C: {
        "account": "ACCOUNT ID*",
        "servicer": "PREPARED BY*",
        "principal": "PRINCIPAL OUTSTANDING*",
        "rate": "INTEREST RATE*",
        "payment_date": "PAYMENT DATE*",
        "payment": "MONTHLY PAYMENT*",
        "principal_paid": "PRINCIPAL PORTION*",
        "interest_paid": "INTEREST PORTION*",
        "escrow_paid": "ESCROW PORTION*",
        "escrow_balance": "ESCROW ON HAND*",
        "old_servicer": "FROM SERVICER*",
        "new_servicer": "TO SERVICER*",
        "transfer_date": "TRANSFER EFFECTIVE*",
        "last_old_date": "FINAL OLD-SERVICER DATE*",
        "first_new_date": "FIRST NEW-SERVICER DATE*",
        "analysis_date": "REVIEW DATE*",
        "tax_projection": "ANNUAL TAX ESTIMATE*",
        "insurance_projection": "ANNUAL INSURANCE ESTIMATE*",
        "shortage": "ESCROW SHORTAGE*",
        "monthly_escrow": "MONTHLY ESCROW*",
        "shortage_monthly": "SHORTAGE INSTALLMENT*",
        "new_payment": "UPDATED PAYMENT*",
        "authority": "TAX OFFICE*",
        "tax_year": "TAX PERIOD*",
        "annual_tax": "TOTAL DUE*",
    },
}


def family_for_account(account_id: str) -> TemplateFamily:
    """Assign a stable 40/40/20 family split without correlating with case buckets."""

    try:
        number = int(account_id.removeprefix("SS-"))
    except ValueError as error:
        raise ValueError(f"invalid account id for family assignment: {account_id}") from error
    slot = (number - 1) % 5
    if slot < 2:
        return TemplateFamily.A
    if slot < 4:
        return TemplateFamily.B
    return TemplateFamily.C


def expected_page_count(family: TemplateFamily, document_type: DocumentType) -> int:
    if family == TemplateFamily.C:
        return 2
    if family == TemplateFamily.B:
        return 1
    if document_type in {
        DocumentType.OLD_SERVICER_STATEMENT,
        DocumentType.NEW_SERVICER_STATEMENT,
        DocumentType.ESCROW_ANALYSIS,
    }:
        return 2
    return 1


def build_content(
    account: dict[str, Any], document_type: DocumentType, family: TemplateFamily
) -> DocumentContent:
    builders = {
        DocumentType.OLD_SERVICER_STATEMENT: _old_statement,
        DocumentType.NEW_SERVICER_STATEMENT: _new_statement,
        DocumentType.TRANSFER_NOTICE: _transfer_notice,
        DocumentType.ESCROW_ANALYSIS: _escrow_analysis,
        DocumentType.PROPERTY_TAX_BILL: _property_tax_bill,
    }
    return builders[document_type](account, family)


def _old_statement(account: dict[str, Any], family: TemplateFamily) -> DocumentContent:
    old_period, new_period = account["servicing_periods"][:2]
    old_analysis = account["escrow_analyses"][-2]
    payment = max(
        (item for item in account["payments"] if item["date"] < new_period["start_date"]),
        key=lambda item: item["date"],
    )
    ledger = [item for item in account["escrow_ledger"] if item["date"] < new_period["start_date"]]
    summary = _fields(
        family,
        account=account["account_id"],
        servicer=_servicer(old_period["servicer_id"]),
        principal=_money(account["current_principal"]),
        rate=_rate(account["annual_rate"]),
        payment=_money(payment["total"]),
        escrow_balance=_money(old_analysis["current_balance"]),
    )
    details = _fields(
        family,
        payment_date=_date(payment["date"], family),
        principal_paid=_money(payment["principal"]),
        interest_paid=_money(payment["interest"]),
        escrow_paid=_money(payment["escrow"]),
    )
    rows = tuple(_ledger_row(item, family) for item in ledger[-8:])
    return _content(
        document_type=DocumentType.OLD_SERVICER_STATEMENT,
        family=family,
        account=account,
        issuer=_servicer(old_period["servicer_id"]),
        summary=summary,
        details=details,
        table_title="Recent Escrow Activity",
        table_headers=("Date", "Activity", "Amount", "Payee", "Balance"),
        table_rows=rows,
        notes=("This is the final statement issued before the servicing transfer.",),
    )


def _new_statement(account: dict[str, Any], family: TemplateFamily) -> DocumentContent:
    new_period = account["servicing_periods"][1]
    new_analysis = account["escrow_analyses"][-1]
    payment = min(
        (item for item in account["payments"] if item["date"] >= new_period["start_date"]),
        key=lambda item: item["date"],
    )
    ledger = [item for item in account["escrow_ledger"] if item["date"] >= new_period["start_date"]]
    summary = _fields(
        family,
        account=account["account_id"],
        servicer=_servicer(new_period["servicer_id"]),
        principal=_money(account["current_principal"]),
        rate=_rate(account["annual_rate"]),
        payment=_money(payment["total"]),
        escrow_balance=_money(new_analysis["current_balance"]),
    )
    details = _fields(
        family,
        payment_date=_date(payment["date"], family),
        principal_paid=_money(payment["principal"]),
        interest_paid=_money(payment["interest"]),
        escrow_paid=_money(payment["escrow"]),
        shortage_monthly=_money(new_analysis["stated_shortage_monthly"]),
    )
    rows = tuple(_ledger_row(item, family) for item in ledger[:8])
    return _content(
        document_type=DocumentType.NEW_SERVICER_STATEMENT,
        family=family,
        account=account,
        issuer=_servicer(new_period["servicer_id"]),
        summary=summary,
        details=details,
        table_title="Post-Transfer Escrow Activity",
        table_headers=("Date", "Activity", "Amount", "Payee", "Balance"),
        table_rows=rows,
        notes=("Payment components reflect the first payment accepted after transfer.",),
    )


def _transfer_notice(account: dict[str, Any], family: TemplateFamily) -> DocumentContent:
    old_period, new_period = account["servicing_periods"][:2]
    old_name = _servicer(old_period["servicer_id"])
    new_name = _servicer(new_period["servicer_id"])
    summary = _fields(
        family,
        account=account["account_id"],
        old_servicer=old_name,
        new_servicer=new_name,
        transfer_date=_date(new_period["start_date"], family),
    )
    details = _fields(
        family,
        last_old_date=_date(old_period["end_date"], family),
        first_new_date=_date(new_period["start_date"], family),
    )
    notes = (
        f"Send payments before the effective date to {old_name}.",
        f"Send payments on or after the effective date to {new_name}.",
        "The transfer changes who services the loan; it does not change the loan terms.",
        "Questions may be directed to the servicing contact shown with this notice.",
    )
    return _content(
        document_type=DocumentType.TRANSFER_NOTICE,
        family=family,
        account=account,
        issuer=old_name,
        summary=summary,
        details=details,
        table_title=None,
        table_headers=(),
        table_rows=(),
        notes=notes,
    )


def _escrow_analysis(account: dict[str, Any], family: TemplateFamily) -> DocumentContent:
    analysis = account["escrow_analyses"][-1]
    issuer = _servicer(analysis["servicer_id"])
    summary = _fields(
        family,
        account=account["account_id"],
        servicer=issuer,
        analysis_date=_date(analysis["analysis_date"], family),
        escrow_balance=_money(analysis["current_balance"]),
        tax_projection=_money(analysis["projected_annual_tax"]),
        insurance_projection=_money(analysis["projected_annual_insurance"]),
        shortage=_money(analysis["stated_shortage"]),
        monthly_escrow=_money(analysis["stated_monthly_escrow"]),
        shortage_monthly=_money(analysis["stated_shortage_monthly"]),
        new_payment=_money(analysis["new_total_payment"]),
    )
    cushion = (
        Decimal(analysis["projected_annual_tax"])
        + Decimal(analysis["projected_annual_insurance"])
    ) / Decimal(6)
    details = (
        Field("Selected Cushion", _money(cushion.quantize(CENT, rounding=ROUND_HALF_UP))),
        Field("Projection Term", "12 months"),
        Field("Shortage Repayment Term", "12 months"),
    )
    rows = _projection_rows(account, family)
    return _content(
        document_type=DocumentType.ESCROW_ANALYSIS,
        family=family,
        account=account,
        issuer=issuer,
        summary=summary,
        details=details,
        table_title="12-Month Projected Trial Balance",
        table_headers=("Month", "Deposit", "Disbursements", "Ending Balance"),
        table_rows=rows,
        notes=(
            "Projected disbursements include property tax and hazard insurance.",
            "The shortage installment is shown separately from base monthly escrow.",
        ),
    )


def _property_tax_bill(account: dict[str, Any], family: TemplateFamily) -> DocumentContent:
    bill = max(account["tax_bills"], key=lambda item: item["tax_year"])
    summary = _fields(
        family,
        account=account["account_id"],
        authority=bill["authority"],
        tax_year=str(bill["tax_year"]),
        annual_tax=_money(bill["annual_amount"]),
    )
    installments = _split_money(Decimal(bill["annual_amount"]), len(bill["due_dates"]))
    rows = tuple(
        (str(index), _date(due_date, family), _money(amount), "Open")
        for index, (due_date, amount) in enumerate(
            zip(bill["due_dates"], installments, strict=True), 1
        )
    )
    details = (
        Field("Parcel Reference", f"PARCEL-{account['account_id'].removeprefix('SS-')}"),
        Field("Assessment Status", "Final"),
    )
    return _content(
        document_type=DocumentType.PROPERTY_TAX_BILL,
        family=family,
        account=account,
        issuer=bill["authority"],
        summary=summary,
        details=details,
        table_title="Installment Schedule",
        table_headers=("Installment", "Due Date", "Amount", "Status"),
        table_rows=rows,
        notes=("Retain this bill with your annual escrow records.",),
    )


def _content(
    *,
    document_type: DocumentType,
    family: TemplateFamily,
    account: dict[str, Any],
    issuer: str,
    summary: tuple[Field, ...],
    details: tuple[Field, ...],
    table_title: str | None,
    table_headers: tuple[str, ...],
    table_rows: tuple[tuple[str, ...], ...],
    notes: tuple[str, ...],
) -> DocumentContent:
    required = tuple(
        dict.fromkeys(
            [
                account["account_id"],
                issuer,
                *(field.value for field in summary),
                *(field.value for field in details),
            ]
        )
    )
    return DocumentContent(
        document_type=document_type,
        title=TITLES[family][document_type],
        account_id=account["account_id"],
        issuer=issuer,
        summary=summary,
        details=details,
        table_title=table_title,
        table_headers=table_headers,
        table_rows=table_rows,
        notes=notes,
        required_values=required,
    )


def _fields(family: TemplateFamily, **values: str) -> tuple[Field, ...]:
    return tuple(Field(LABELS[family][key], value) for key, value in values.items())


def _servicer(value: str) -> str:
    return value.replace("-", " ").title()


def _money(value: str | Decimal) -> str:
    amount = Decimal(value)
    sign = "-" if amount < 0 else ""
    return f"{sign}${abs(amount):,.2f}"


def _rate(value: str | Decimal) -> str:
    return f"{Decimal(value) * Decimal(100):.4f}%"


def _date(value: str, family: TemplateFamily) -> str:
    parsed = date.fromisoformat(value)
    if family == TemplateFamily.A:
        return f"{parsed.strftime('%B')} {parsed.day}, {parsed.year}"
    if family == TemplateFamily.B:
        return parsed.strftime("%m/%d/%Y")
    return parsed.strftime("%b %d, %Y")


def _ledger_row(item: dict[str, Any], family: TemplateFamily) -> tuple[str, ...]:
    activity = item["type"].replace("_", " ").title()
    payee = (item.get("payee") or "-").replace("SERVICING_TRANSFER:", "Transfer: ")
    if len(payee) > 25:
        payee = f"{payee[:22]}..."
    return (
        _date(item["date"], family),
        activity,
        _money(item["amount"]),
        payee,
        _money(item["balance_after"]),
    )


def _split_money(total: Decimal, count: int) -> list[Decimal]:
    base = (total / count).quantize(CENT, rounding=ROUND_HALF_UP)
    values = [base for _ in range(count)]
    values[-1] += total - sum(values, Decimal(0))
    return values


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def _projection_rows(
    account: dict[str, Any], family: TemplateFamily
) -> tuple[tuple[str, ...], ...]:
    analysis = account["escrow_analyses"][-1]
    tax_bill = max(account["tax_bills"], key=lambda item: item["tax_year"])
    policy = max(account["insurance_policies"], key=lambda item: item["renewal_date"])
    tax_installments = _split_money(
        Decimal(analysis["projected_annual_tax"]), len(tax_bill["due_dates"])
    )
    charges: dict[int, Decimal] = {}
    for due_date, amount in zip(tax_bill["due_dates"], tax_installments, strict=True):
        month = date.fromisoformat(due_date).month
        charges[month] = charges.get(month, Decimal(0)) + amount
    insurance_month = date.fromisoformat(policy["renewal_date"]).month
    charges[insurance_month] = charges.get(insurance_month, Decimal(0)) + Decimal(
        analysis["projected_annual_insurance"]
    )

    balance = Decimal(analysis["current_balance"])
    monthly = Decimal(analysis["stated_monthly_escrow"])
    start = date.fromisoformat(analysis["analysis_date"])
    rows: list[tuple[str, ...]] = []
    for offset in range(12):
        month = _add_months(start, offset)
        disbursement = charges.get(month.month, Decimal(0))
        balance = (balance + monthly - disbursement).quantize(CENT, rounding=ROUND_HALF_UP)
        rows.append(
            (
                _date(month.isoformat(), family),
                _money(monthly),
                _money(disbursement),
                _money(balance),
            )
        )
    return tuple(rows)
