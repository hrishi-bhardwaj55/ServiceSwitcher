"""Typed extraction results with document provenance."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.mortgage import CanonicalModel

DocumentType = Literal[
    "OLD_SERVICER_STATEMENT",
    "NEW_SERVICER_STATEMENT",
    "TRANSFER_NOTICE",
    "ESCROW_ANALYSIS",
    "PROPERTY_TAX_BILL",
]
FieldName = Literal[
    "principal_balance",
    "interest_rate",
    "monthly_payment",
    "escrow_balance",
    "projected_annual_tax",
    "projected_annual_insurance",
    "stated_shortage",
    "transfer_date",
    "old_servicer_name",
    "new_servicer_name",
    "tax_authority",
    "annual_tax_amount",
    "due_dates",
]

MONEY_FIELDS = {
    "principal_balance",
    "monthly_payment",
    "escrow_balance",
    "projected_annual_tax",
    "projected_annual_insurance",
    "stated_shortage",
    "annual_tax_amount",
}
TEXT_FIELDS = {"old_servicer_name", "new_servicer_name", "tax_authority"}


class BoundingBox(CanonicalModel):
    x0: float = Field(ge=0)
    y0: float = Field(ge=0)
    x1: float = Field(ge=0)
    y1: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_extent(self) -> BoundingBox:
        if self.x1 <= self.x0 or self.y1 <= self.y0:
            raise ValueError("bounding box must have positive width and height")
        return self


class ExtractedField(CanonicalModel):
    field_name: FieldName
    value: Decimal | date | str | tuple[date, ...]
    page: int = Field(ge=1)
    bounding_box: BoundingBox | None = None
    confidence: float = Field(ge=0, le=1)
    source_text: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_value_type(self) -> ExtractedField:
        if self.field_name in MONEY_FIELDS | {"interest_rate"} and not isinstance(
            self.value, Decimal
        ):
            raise TypeError(f"{self.field_name} must contain a Decimal")
        if self.field_name == "transfer_date" and not isinstance(self.value, date):
            raise TypeError("transfer_date must contain a date")
        if self.field_name == "due_dates" and not (
            isinstance(self.value, tuple)
            and self.value
            and all(isinstance(item, date) for item in self.value)
        ):
            raise TypeError("due_dates must contain a non-empty tuple of dates")
        if self.field_name in TEXT_FIELDS and not isinstance(self.value, str):
            raise TypeError(f"{self.field_name} must contain text")
        return self


class ExtractionResult(CanonicalModel):
    document_type: DocumentType
    classification_confidence: float = Field(ge=0, le=1)
    fields: list[ExtractedField]
    model_fallback_triggered: bool = False
    requires_review: bool = False
    review_reasons: tuple[str, ...] = ()

    def field_map(self) -> dict[FieldName, ExtractedField]:
        return {field.field_name: field for field in self.fields}
