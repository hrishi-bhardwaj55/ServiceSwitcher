"""Embedding provider boundary."""

from __future__ import annotations

from typing import Protocol


class EmbeddingClient(Protocol):
    dimensions: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed non-empty texts in input order."""
