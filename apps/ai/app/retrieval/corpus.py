"""Load and validate the curated regulation corpus."""

from __future__ import annotations

import json
from pathlib import Path

from app.retrieval.models import RuleChunk

MIN_CHUNKS = 30
MAX_CHUNKS = 50


def load_corpus(path: str | Path) -> list[RuleChunk]:
    corpus_path = Path(path)
    chunks: list[RuleChunk] = []
    with corpus_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                chunks.append(RuleChunk.model_validate_json(line))
            except (ValueError, json.JSONDecodeError) as error:
                raise ValueError(f"invalid corpus record at {corpus_path}:{line_number}") from error
    if not MIN_CHUNKS <= len(chunks) <= MAX_CHUNKS:
        raise ValueError(
            f"corpus must contain {MIN_CHUNKS}-{MAX_CHUNKS} chunks; found {len(chunks)}"
        )
    ids = [chunk.id for chunk in chunks]
    if len(ids) != len(set(ids)):
        raise ValueError("corpus chunk ids must be unique")
    return chunks
