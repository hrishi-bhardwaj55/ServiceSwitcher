"""Minimal model-provider boundary."""

from __future__ import annotations

from typing import Protocol

from app.llm.models import LLMExtractionRequest, LLMExtractionResponse


class LLMClient(Protocol):
    def extract(self, request: LLMExtractionRequest) -> LLMExtractionResponse:
        """Return schema-validated field candidates for one document."""

