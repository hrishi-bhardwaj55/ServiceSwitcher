"""Strict model-visible argument schemas for the eight C10 tools."""

from __future__ import annotations

from datetime import date

from pydantic import Field, model_validator

from app.extraction.models import DocumentType, FieldName
from app.schemas.mortgage import CanonicalModel


class GetExtractedFieldArgs(CanonicalModel):
    """Select one extracted field from one document in the bound audit."""

    document_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
    field_name: FieldName


class _DateRangeArgs(CanonicalModel):
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_range(self) -> _DateRangeArgs:
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self


class GetEscrowLedgerArgs(_DateRangeArgs):
    """Select escrow transactions in an inclusive date range."""


class GetPaymentHistoryArgs(_DateRangeArgs):
    """Select mortgage payments in an inclusive date range."""


class CalculateEscrowContinuityArgs(CanonicalModel):
    """Request deterministic continuity analysis for the bound audit's transfer."""


class CalculatePaymentBreakdownArgs(CanonicalModel):
    """Request deterministic payment decomposition for the bound audit's transfer."""


class CompareTaxProjectionArgs(CanonicalModel):
    """Request deterministic tax comparison for the bound audit's transfer."""


class SearchRegulationsArgs(CanonicalModel):
    """Search the curated mortgage-servicing regulation knowledge base."""

    query: str = Field(min_length=3, max_length=500)
    limit: int = Field(default=5, ge=1, le=5)


class MarkInformationMissingArgs(CanonicalModel):
    """Record a required document that is absent from the bound audit."""

    document_type: DocumentType
    reason: str = Field(min_length=5, max_length=500)
