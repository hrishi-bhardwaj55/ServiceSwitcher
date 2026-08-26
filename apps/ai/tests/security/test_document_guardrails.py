from datetime import date
from decimal import Decimal

import pytest

from app.security import (
    DocumentSafetyError,
    validate_document_date,
    validate_document_text,
    validate_model_money,
)


def _tax_bill(extra=""):
    return f"""PROPERTY TAX BILL
ACCOUNT SS-0001
Taxing Authority
County Revenue Office
Annual Amount Due
$3,200.00
Due Date
December 15, 2025
{extra}
"""


def test_document_text_accepts_bound_account_and_safe_values():
    validate_document_text(_tax_bill(), expected_account_id="SS-0001")


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("", "no extractable text"),
        (_tax_bill("ACCOUNT SS-9999"), "cross-account"),
        (_tax_bill("Annual Amount Due\n$3,201.00"), "contradictory"),
        (
            _tax_bill("Annual Amount Due\n$999,999,999,999.99"),
            "allowed monetary range",
        ),
        (_tax_bill("Escrow Account Balance\n-$1.00"), "allowed monetary range"),
        (_tax_bill("Effective Transfer Date\nJanuary 1, 1900"), "date is outside"),
        (_tax_bill("Effective Transfer Date\nJanuary 1, 2099"), "date is outside"),
    ],
)
def test_document_text_rejects_security_anomalies(text, message):
    with pytest.raises(DocumentSafetyError, match=message):
        validate_document_text(text, expected_account_id="SS-0001")


def test_model_value_constraints_are_explicit():
    assert validate_model_money("annual_tax_amount", Decimal("3200.00")) == Decimal(
        "3200.00"
    )
    assert validate_document_date(date(2025, 12, 15)) == date(2025, 12, 15)
    with pytest.raises(ValueError, match="monetary range"):
        validate_model_money("annual_tax_amount", Decimal("999999999999.99"))
