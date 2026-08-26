"""Strict currency, rate, and date normalization for extracted text."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")
MONEY_PATTERN = re.compile(r"^\s*(?P<leading>-)?\$?\s*(?P<number>[\d,]+(?:\.\d{1,2})?)\s*$")
RATE_PATTERN = re.compile(r"^\s*(?P<number>\d+(?:\.\d+)?)\s*%\s*$")
DATE_FORMATS = ("%B %d, %Y", "%b %d, %Y", "%m/%d/%Y", "%Y-%m-%d")


def normalize_money(value: str) -> Decimal:
    match = MONEY_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError(f"invalid currency value: {value!r}")
    try:
        amount = Decimal(match.group("number").replace(",", ""))
    except InvalidOperation as error:
        raise ValueError(f"invalid currency value: {value!r}") from error
    if match.group("leading"):
        amount = -amount
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def normalize_rate(value: str) -> Decimal:
    match = RATE_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError(f"invalid percentage value: {value!r}")
    try:
        return Decimal(match.group("number")) / Decimal(100)
    except InvalidOperation as error:
        raise ValueError(f"invalid percentage value: {value!r}") from error


def normalize_date(value: str) -> date:
    normalized = " ".join(value.strip().split())
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(normalized, date_format).date()
        except ValueError:
            continue
    raise ValueError(f"invalid date value: {value!r}")


def normalize_text(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized or any(symbol in normalized for symbol in ("$", "%")):
        raise ValueError(f"invalid text value: {value!r}")
    return normalized
