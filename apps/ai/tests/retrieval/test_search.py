from pathlib import Path

import pytest

from app.embeddings import DeterministicFakeEmbeddingClient
from app.retrieval import (
    RegulationRetriever,
    SearchResult,
    load_corpus,
    reciprocal_rank_fusion,
)

CORPUS = Path(__file__).parents[4] / "knowledge-base" / "chunks.jsonl"


class FakeStore:
    def __init__(self, vector_results, text_results):
        self.vector_results = vector_results
        self.text_results = text_results
        self.vector_requests = []
        self.text_requests = []

    def vector_candidates(self, vector, limit):
        self.vector_requests.append((vector, limit))
        return self.vector_results[:limit]

    def text_candidates(self, query, limit):
        self.text_requests.append((query, limit))
        return self.text_results[:limit]


def _result(chunk, score):
    return SearchResult(chunk=chunk, score=score)


def test_vector_only_uses_embedding_and_never_calls_text_search():
    chunks = load_corpus(CORPUS)
    store = FakeStore([_result(chunks[0], 0.9)], [])
    embeddings = DeterministicFakeEmbeddingClient({"escrow": [1.0, 0.0]}, dimensions=2)
    retriever = RegulationRetriever(store, embeddings)

    results = retriever.vector_only(" escrow ")

    assert [result.chunk.id for result in results] == [chunks[0].id]
    assert store.vector_requests == [([1.0, 0.0], 5)]
    assert store.text_requests == []


def test_hybrid_uses_both_rankings_and_rrf_rewards_overlap():
    chunks = load_corpus(CORPUS)
    vector = [_result(chunks[0], 0.9), _result(chunks[1], 0.8)]
    full_text = [_result(chunks[1], 0.7), _result(chunks[2], 0.6)]
    store = FakeStore(vector, full_text)
    embeddings = DeterministicFakeEmbeddingClient({"shortage": [0.0, 1.0]}, dimensions=2)
    retriever = RegulationRetriever(store, embeddings)

    results = retriever.hybrid("shortage", limit=3)

    assert results[0].chunk.id == chunks[1].id
    assert {result.chunk.id for result in results} == {
        chunks[0].id,
        chunks[1].id,
        chunks[2].id,
    }
    assert store.vector_requests == [([0.0, 1.0], 20)]
    assert store.text_requests == [("shortage", 20)]


def test_rrf_tie_breaks_by_stable_chunk_id():
    chunks = load_corpus(CORPUS)
    results = reciprocal_rank_fusion(
        [_result(chunks[1], 0.9)],
        [_result(chunks[0], 0.9)],
        limit=2,
    )

    assert [result.chunk.id for result in results] == sorted(
        [chunks[0].id, chunks[1].id]
    )


def test_empty_query_is_rejected_before_provider_call():
    embeddings = DeterministicFakeEmbeddingClient({}, dimensions=2)
    retriever = RegulationRetriever(FakeStore([], []), embeddings)

    with pytest.raises(ValueError, match="must not be empty"):
        retriever.vector_only("  ")

    assert embeddings.requests == []
