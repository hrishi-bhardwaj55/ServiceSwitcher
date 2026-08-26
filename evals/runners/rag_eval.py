"""Compare vector-only and hybrid regulation retrieval."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from app.embeddings import OpenAIEmbeddingClient
from app.retrieval import (
    PostgresRuleStore,
    RegulationRetriever,
    SearchResult,
    load_corpus,
)
from app.retrieval.database import database_engine
from app.schemas.mortgage import CanonicalModel
from pydantic import Field

VECTOR_ONLY = "Vector only"
HYBRID = "Hybrid (vector + tsvector RRF)"
TOP_K = 5


class RetrievalCase(CanonicalModel):
    case_id: str = Field(pattern=r"^rag-\d{3}$")
    query: str = Field(min_length=10)
    required_sources: list[str] = Field(min_length=1)


@dataclass
class RetrievalMetrics:
    cases: int = 0
    recall_sum: Decimal = Decimal(0)
    precision_sum: Decimal = Decimal(0)
    reciprocal_rank_sum: Decimal = Decimal(0)

    @property
    def recall_at_5(self) -> Decimal:
        return self.recall_sum / self.cases

    @property
    def precision_at_5(self) -> Decimal:
        return self.precision_sum / self.cases

    @property
    def mrr(self) -> Decimal:
        return self.reciprocal_rank_sum / self.cases


def load_cases(path: str | Path) -> list[RetrievalCase]:
    dataset_path = Path(path)
    cases: list[RetrievalCase] = []
    with dataset_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                cases.append(RetrievalCase.model_validate_json(line))
            except ValueError as error:
                raise ValueError(
                    f"invalid retrieval case at {dataset_path}:{line_number}"
                ) from error
    ids = [case.case_id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("retrieval case ids must be unique")
    return cases


def validate_labels(cases: list[RetrievalCase], corpus_ids: set[str]) -> None:
    unknown = {
        source
        for case in cases
        for source in case.required_sources
        if source not in corpus_ids
    }
    if unknown:
        raise ValueError(f"retrieval cases reference unknown sources: {sorted(unknown)}")


def evaluate(
    cases: list[RetrievalCase], retriever: RegulationRetriever
) -> dict[str, RetrievalMetrics]:
    metrics = {VECTOR_ONLY: RetrievalMetrics(), HYBRID: RetrievalMetrics()}
    for case in cases:
        vector_results, hybrid_results = retriever.compare(case.query, limit=TOP_K)
        _score(metrics[VECTOR_ONLY], case, vector_results)
        _score(metrics[HYBRID], case, hybrid_results)
    return metrics


def _score(
    metrics: RetrievalMetrics,
    case: RetrievalCase,
    results: list[SearchResult],
) -> None:
    required = set(case.required_sources)
    ranked = [result.chunk.id for result in results]
    hits = required & set(ranked)
    reciprocal_rank = Decimal(0)
    for rank, chunk_id in enumerate(ranked, start=1):
        if chunk_id in required:
            reciprocal_rank = Decimal(1) / rank
            break
    metrics.cases += 1
    metrics.recall_sum += Decimal(len(hits)) / len(required)
    metrics.precision_sum += Decimal(len(hits)) / TOP_K
    metrics.reciprocal_rank_sum += reciprocal_rank


def render_report(metrics: dict[str, RetrievalMetrics], model: str, chunks: int) -> str:
    vector = metrics[VECTOR_ONLY]
    hybrid = metrics[HYBRID]
    selected = max(
        (VECTOR_ONLY, HYBRID),
        key=lambda strategy: (
            metrics[strategy].recall_at_5,
            metrics[strategy].mrr,
            metrics[strategy].precision_at_5,
        ),
    )
    selected_label = "vector-only" if selected == VECTOR_ONLY else "hybrid"
    return f"""# Regulation retrieval evaluation

Embedding model: `{model}` at 512 dimensions. Corpus: {chunks} chunks. Dataset:
{vector.cases} labeled queries. Each metric is the macro average across cases.

| Strategy | Recall@5 | Precision@5 | MRR |
|---|---:|---:|---:|
| Vector only | {_percent(vector.recall_at_5)} | {_percent(vector.precision_at_5)} | {_decimal(vector.mrr)} |
| Hybrid (vector + `tsvector` RRF) | {_percent(hybrid.recall_at_5)} | {_percent(hybrid.precision_at_5)} | {_decimal(hybrid.mrr)} |

Production choice: **{selected_label} retrieval**. The selection rule prioritizes
Recall@5, then MRR, then Precision@5. See `docs/evals.md` for the decision record and
benchmark limitations.
"""


def _percent(value: Decimal) -> str:
    return f"{value * Decimal(100):.2f}%"


def _decimal(value: Decimal) -> str:
    return f"{value:.4f}"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("evals/datasets/rag.jsonl"))
    parser.add_argument("--corpus", type=Path, default=Path("knowledge-base/chunks.jsonl"))
    parser.add_argument("--report", type=Path, default=Path("evals/reports/rag.md"))
    parser.add_argument("--expected-cases", type=int, default=25)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    cases = load_cases(args.dataset)
    if len(cases) != args.expected_cases:
        raise ValueError(f"expected {args.expected_cases} retrieval cases; found {len(cases)}")
    corpus = load_corpus(args.corpus)
    validate_labels(cases, {chunk.id for chunk in corpus})
    embeddings = OpenAIEmbeddingClient.from_env()
    retriever = RegulationRetriever(PostgresRuleStore(database_engine()), embeddings)
    metrics = evaluate(cases, retriever)
    report = render_report(metrics, embeddings.model, len(corpus))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote report to {args.report}")


if __name__ == "__main__":
    main()
