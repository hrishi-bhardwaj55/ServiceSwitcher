"""Inject an unsupported duplicate property-tax disbursement."""

from datetime import timedelta
from decimal import Decimal

from app.schemas import EscrowTransaction, MortgageAccount

from data.faults.common import FaultInjection, rechain_ledger


def inject(account: MortgageAccount, variant: int = 0) -> FaultInjection:
    del variant
    transfer_date = account.servicing_periods[1].start_date
    source = next(
        transaction
        for transaction in account.escrow_ledger
        if transaction.type == "TAX_DISBURSEMENT" and transaction.date >= transfer_date
    )
    duplicate = EscrowTransaction(
        date=source.date + timedelta(days=30),
        type="TAX_DISBURSEMENT",
        amount=source.amount,
        payee=source.payee,
        balance_after=Decimal("0.00"),
    )
    mutated = account.model_copy(
        update={"escrow_ledger": rechain_ledger([*account.escrow_ledger, duplicate])}
    )
    return FaultInjection(
        account=mutated,
        finding_type="DUPLICATE_TAX_DISBURSEMENT",
        impact_total=abs(source.amount),
        monthly_impact=Decimal("0.00"),
        evidence_documents=(
            "doc_new_servicer_statement",
            "doc_property_tax_bill",
        ),
    )
