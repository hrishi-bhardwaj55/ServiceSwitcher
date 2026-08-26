"""Deterministic scripted model client used by tests."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from app.llm.models import LLMExtractionRequest, LLMExtractionResponse


class DeterministicFakeLLM:
    def __init__(self, responses: Iterable[LLMExtractionResponse]) -> None:
        self._responses = deque(responses)
        self.requests: list[LLMExtractionRequest] = []

    @property
    def call_count(self) -> int:
        return len(self.requests)

    def extract(self, request: LLMExtractionRequest) -> LLMExtractionResponse:
        self.requests.append(request)
        if not self._responses:
            raise AssertionError("fake LLM received an unexpected extraction request")
        return self._responses.popleft()

    def assert_exhausted(self) -> None:
        if self._responses:
            raise AssertionError(f"fake LLM has {len(self._responses)} unused responses")
