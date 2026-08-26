"""Deterministic embedding fake used by tests."""

from __future__ import annotations


class DeterministicFakeEmbeddingClient:
    def __init__(self, vectors: dict[str, list[float]], *, dimensions: int) -> None:
        self.vectors = vectors
        self.dimensions = dimensions
        self.requests: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.requests.append(texts)
        result: list[list[float]] = []
        for text in texts:
            if text not in self.vectors:
                raise AssertionError(f"no fake embedding configured for {text!r}")
            vector = self.vectors[text]
            if len(vector) != self.dimensions:
                raise AssertionError("fake embedding has the wrong dimensions")
            result.append(vector)
        return result
