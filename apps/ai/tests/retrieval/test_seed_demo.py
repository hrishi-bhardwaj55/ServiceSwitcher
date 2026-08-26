from __future__ import annotations

import json

import pytest

from app.retrieval.database import DATABASE_DIMENSIONS
from app.retrieval.ingest import embedding_text
from app.retrieval.models import RuleChunk
from app.retrieval.seed_demo import StoredEmbeddingClient, load_stored_vectors


def _chunk(chunk_id: str = "regx-demo") -> RuleChunk:
    return RuleChunk(
        id=chunk_id,
        source="12 CFR § 1024.17",
        section="§ 1024.17(c)",
        title="Escrow account analysis",
        url="https://www.consumerfinance.gov/rules-policy/regulations/1024/17/",
        content="A servicer prepares an escrow analysis using expected disbursements and "
        "provides the borrower an annual statement explaining the account calculation.",
    )


def test_stored_embeddings_are_bound_to_exact_corpus_text(tmp_path) -> None:
    chunk = _chunk()
    path = tmp_path / "embeddings.jsonl"
    path.write_text(
        json.dumps({"id": chunk.id, "embedding": [0.0] * DATABASE_DIMENSIONS}) + "\n",
        encoding="utf-8",
    )

    vectors = load_stored_vectors(path, [chunk])
    client = StoredEmbeddingClient(vectors)

    assert client.embed([embedding_text(chunk)]) == [[0.0] * DATABASE_DIMENSIONS]
    with pytest.raises(ValueError, match="do not match"):
        client.embed(["changed corpus text"])


def test_stored_embeddings_reject_missing_corpus_ids(tmp_path) -> None:
    path = tmp_path / "embeddings.jsonl"
    path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match=r"missing=\['regx-demo'\]"):
        load_stored_vectors(path, [_chunk()])
