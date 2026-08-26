"""Structured request and response contracts for extraction providers."""

from __future__ import annotations

from pydantic import Field, model_validator

from app.extraction.models import DocumentType, FieldName
from app.schemas.mortgage import CanonicalModel


class LLMPage(CanonicalModel):
    page: int = Field(ge=1)
    text: str = Field(min_length=1)


class LLMExtractionRequest(CanonicalModel):
    document_type: DocumentType | None = None
    requested_fields: list[FieldName]
    pages: list[LLMPage] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_values(self) -> LLMExtractionRequest:
        if len(self.requested_fields) != len(set(self.requested_fields)):
            raise ValueError("requested fields must be unique")
        page_numbers = [page.page for page in self.pages]
        if len(page_numbers) != len(set(page_numbers)):
            raise ValueError("page numbers must be unique")
        return self


class LLMFieldCandidate(CanonicalModel):
    field_name: FieldName
    raw_value: str = Field(min_length=1)
    page: int = Field(ge=1)
    confidence: float = Field(ge=0, le=1)


class LLMExtractionResponse(CanonicalModel):
    document_type: DocumentType
    classification_confidence: float = Field(ge=0, le=1)
    fields: list[LLMFieldCandidate]

    @model_validator(mode="after")
    def validate_unique_fields(self) -> LLMExtractionResponse:
        names = [field.field_name for field in self.fields]
        if len(names) != len(set(names)):
            raise ValueError("LLM response fields must be unique")
        return self
