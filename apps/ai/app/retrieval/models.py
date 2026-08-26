"""Typed regulatory knowledge contracts."""

from __future__ import annotations

from pydantic import Field, field_validator

from app.schemas.mortgage import CanonicalModel


class RuleChunk(CanonicalModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    source: str = Field(min_length=3)
    section: str = Field(min_length=3)
    title: str = Field(min_length=5)
    url: str
    content: str = Field(min_length=80, max_length=1600)

    @field_validator("url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        if not value.startswith("https://www.consumerfinance.gov/"):
            raise ValueError("knowledge sources must use an official CFPB HTTPS URL")
        return value
