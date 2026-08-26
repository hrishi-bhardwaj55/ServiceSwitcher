from datetime import date
from decimal import Decimal

import pytest

from app.extraction.normalizers import (
    normalize_date,
    normalize_money,
    normalize_rate,
    normalize_text,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("$1,234.56", Decimal("1234.56")),
        ("-$75.50", Decimal("-75.50")),
        (" 42 ", Decimal("42.00")),
    ],
)
def test_normalize_money(raw, expected):
    assert normalize_money(raw) == expected


@pytest.mark.parametrize("raw", ["$12.345", "USD 12.00", "twelve dollars", ""])
def test_normalize_money_rejects_ambiguous_values(raw):
    with pytest.raises(ValueError, match="invalid currency"):
        normalize_money(raw)


def test_normalize_rate_returns_fractional_decimal():
    assert normalize_rate("6.3496%") == Decimal("0.063496")


@pytest.mark.parametrize(
    "raw",
    ["June 1, 2024", "Jun 01, 2024", "06/01/2024", "2024-06-01"],
)
def test_normalize_date_supported_formats(raw):
    assert normalize_date(raw) == date(2024, 6, 1)


def test_normalize_date_rejects_impossible_date():
    with pytest.raises(ValueError, match="invalid date"):
        normalize_date("02/30/2025")


def test_normalize_text_collapses_spacing_and_rejects_money():
    assert normalize_text("  County   Revenue Office ") == "County Revenue Office"
    with pytest.raises(ValueError, match="invalid text"):
        normalize_text("$500.00")
