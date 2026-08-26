from pathlib import Path

import pytest

from app.embeddings import DeterministicFakeEmbeddingClient
from app.retrieval import load_corpus
from app.retrieval.ingest import DATABASE_DIMENSIONS, embedding_text, vector_literal

CORPUS = Path(__file__).parents[4] / "knowledge-base" / "chunks.jsonl"


def test_embedding_text_preserves_title_section_and_content():
    chunk = load_corpus(CORPUS)[0]

    rendered = embedding_text(chunk)

    assert chunk.title in rendered
    assert chunk.section in rendered
    assert chunk.content in rendered


def test_vector_literal_requires_database_dimensions():
    with pytest.raises(ValueError, match="expected 512"):
        vector_literal([0.0, 1.0])

    rendered = vector_literal([0.0] * DATABASE_DIMENSIONS)
    assert rendered.startswith("[")
    assert rendered.endswith("]")
    assert rendered.count(",") == DATABASE_DIMENSIONS - 1


def test_fake_embedding_client_is_strict_and_deterministic():
    client = DeterministicFakeEmbeddingClient(
        {"escrow": [1.0, 0.0]}, dimensions=2
    )

    assert client.embed(["escrow"]) == [[1.0, 0.0]]
    with pytest.raises(AssertionError, match="no fake embedding"):
        client.embed(["transfer"])
