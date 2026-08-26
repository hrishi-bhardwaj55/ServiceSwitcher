"""Tests for the canonical mortgage account contract."""

from datetime import date
from decimal import Decimal

from app.schemas import Payment


def test_money_serializes_without_binary_float_loss() -> None:
    payment = Payment(
        date=date(2024, 1, 1),
        total=Decimal("2100.30"),
        principal=Decimal("700.10"),
        interest=Decimal("900.10"),
        escrow=Decimal("500.10"),
    )

    assert payment.model_dump_json() == (
        '{"date":"2024-01-01","total":"2100.30","principal":"700.10",'
        '"interest":"900.10","escrow":"500.10"}'
    )
