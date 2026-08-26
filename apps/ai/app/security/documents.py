"""Fail-closed checks for untrusted mortgage-document text."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal

from app.extraction.normalizers import normalize_money

MAX_DOCUMENT_MONEY = Decimal("100000000.00")
MIN_DOCUMENT_DATE = date(1970, 1, 1)
MAX_DOCUMENT_DATE = date(2050, 12, 31)
ACCOUNT_PATTERN = re.compile(r"\bSS-\d{4}\b", re.IGNORECASE)
DATE_PATTERN = re.compile(
    r"\b(?:"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{1,2},\s+\d{4}"
    r"|\d{1,2}/\d{1,2}/\d{4}"
    r"|\d{4}-\d{2}-\d{2}"
    r")\b",
    re.IGNORECASE,
)
DATE_FORMATS = (
    "%B %d, %Y",
    "%b %d, %Y",
    "%m/%d/%Y",
    "%Y-%m-%d",
)
MONEY_ALIASES = {
    "principal_balance": ("current principal balance", "unpaid principal"),
    "monthly_payment": ("total monthly payment", "payment amount"),
    "escrow_balance": ("escrow account balance", "escrow balance"),
    "projected_annual_tax": (
        "projected annual property tax",
        "est. tax - 12 mo.",
    ),
    "projected_annual_insurance": (
        "projected annual insurance",
        "est. hazard ins. - 12 mo.",
    ),
    "stated_shortage": ("stated escrow shortage", "aggregate shortage"),
    "annual_tax_amount": ("annual amount due", "total tax levy"),
}


class DocumentSafetyError(ValueError):
    """Raised when a document must be rejected before model processing."""


def validate_model_money(field_name: str, value: Decimal) -> Decimal:
    """Accept plausible non-negative extracted fields; route anomalies to review."""

    if not value.is_finite() or value < 0 or value > MAX_DOCUMENT_MONEY:
        raise ValueError(f"{field_name} is outside the allowed monetary range")
    return value


def validate_document_date(value: date) -> date:
    if not MIN_DOCUMENT_DATE <= value <= MAX_DOCUMENT_DATE:
        raise ValueError("document date is outside the allowed range")
    return value


def validate_document_text(text: str, *, expected_account_id: str | None = None) -> None:
    """Reject empty, cross-account, conflicting, or out-of-range document content."""

    if not text.strip():
        raise DocumentSafetyError("document has no extractable text")
    if expected_account_id is not None:
        account_ids = {value.upper() for value in ACCOUNT_PATTERN.findall(text)}
        if expected_account_id.upper() not in account_ids:
            raise DocumentSafetyError("document does not contain the trusted account id")
        if account_ids != {expected_account_id.upper()}:
            raise DocumentSafetyError("document contains a cross-account identifier")
    _validate_labelled_money(text)
    _validate_dates(text)


def _validate_labelled_money(text: str) -> None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    values: dict[str, set[Decimal]] = {field: set() for field in MONEY_ALIASES}
    for index, line in enumerate(lines):
        normalized = line.casefold()
        for field_name, aliases in MONEY_ALIASES.items():
            raw = _money_after_alias(line, normalized, aliases)
            if raw is None and normalized in aliases and index + 1 < len(lines):
                raw = lines[index + 1]
            if raw is None:
                continue
            try:
                value = normalize_money(raw)
            except ValueError:
                continue
            try:
                validate_model_money(field_name, value)
            except ValueError as error:
                raise DocumentSafetyError(str(error)) from error
            values[field_name].add(value)
    conflicts = [field for field, observed in values.items() if len(observed) > 1]
    if conflicts:
        raise DocumentSafetyError(
            f"document contains contradictory values for {', '.join(sorted(conflicts))}"
        )


def _money_after_alias(
    line: str,
    normalized: str,
    aliases: tuple[str, ...],
) -> str | None:
    for alias in aliases:
        if not normalized.startswith(alias):
            continue
        remainder = line[len(alias) :].lstrip(" :|")
        if remainder:
            return remainder
    return None


def _validate_dates(text: str) -> None:
    for match in DATE_PATTERN.finditer(text):
        raw = match.group(0)
        for date_format in DATE_FORMATS:
            try:
                parsed = datetime.strptime(raw, date_format).date()
            except ValueError:
                continue
            try:
                validate_document_date(parsed)
            except ValueError as error:
                raise DocumentSafetyError(str(error)) from error
            break
