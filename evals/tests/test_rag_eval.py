from decimal import Decimal
from pathlib import Path

from app.embeddings import DeterministicFakeEmbeddingClient
from app.retrieval import RegulationRetriever, SearchResult, load_corpus

from evals.runners.rag_eval import (
    HYBRID,
    VECTOR_ONLY,
    evaluate,
    load_cases,
    validate_labels,
)

ROOT = Path(__file__).parents[2]
CORPUS = ROOT / "knowledge-base" / "chunks.jsonl"
DATASET = ROOT / "evals" / "datasets" / "rag.jsonl"


class FakeStore:
    def __init__(self, chunks):
        self.chunks = chunks

    def vector_candidates(self, vector, limit):
        return [SearchResult(chunk=self.chunks[0], score=0.9)][:limit]

    def text_candidates(self, query, limit):
        return [
            SearchResult(chunk=self.chunks[0], score=0.9),
            SearchResult(chunk=self.chunks[1], score=0.8),
        ][:limit]


def test_rag_dataset_has_25_valid_labeled_cases():
    corpus = load_corpus(CORPUS)
    cases = load_cases(DATASET)

    assert len(cases) == 25
    validate_labels(cases, {chunk.id for chunk in corpus})


def test_metrics_score_ranked_required_sources():
    corpus = load_corpus(CORPUS)
    cases = load_cases(DATASET)[:1]
    required_id = cases[0].required_sources[0]
    required = next(chunk for chunk in corpus if chunk.id == required_id)
    distractor = next(chunk for chunk in corpus if chunk.id != required_id)
    fake = DeterministicFakeEmbeddingClient({cases[0].query: [1.0, 0.0]}, dimensions=2)
    retriever = RegulationRetriever(FakeStore([distractor, required]), fake)

    metrics = evaluate(cases, retriever)

    assert metrics[VECTOR_ONLY].recall_at_5 == Decimal(0)
    assert metrics[HYBRID].recall_at_5 == Decimal(1)
    assert metrics[HYBRID].precision_at_5 == Decimal("0.2")
    assert metrics[HYBRID].mrr == Decimal("0.5")
