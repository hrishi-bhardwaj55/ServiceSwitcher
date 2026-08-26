"""Vector-only and hybrid reciprocal-rank-fusion retrieval."""

from __future__ import annotations

from typing import Protocol

from pydantic import Field
from sqlalchemy import Engine, text

from app.embeddings import EmbeddingClient
from app.retrieval.ingest import vector_literal
from app.retrieval.models import RuleChunk
from app.schemas.mortgage import CanonicalModel

DEFAULT_LIMIT = 5
DEFAULT_CANDIDATE_LIMIT = 20
RRF_K = 60


class SearchResult(CanonicalModel):
    chunk: RuleChunk
    score: float = Field(ge=-1)


class RuleStore(Protocol):
    def vector_candidates(self, vector: list[float], limit: int) -> list[SearchResult]: ...

    def text_candidates(self, query: str, limit: int) -> list[SearchResult]: ...


class PostgresRuleStore:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def vector_candidates(self, vector: list[float], limit: int) -> list[SearchResult]:
        statement = text(
            """
            SELECT id, source, section, title, url, content,
                   1 - (embedding <=> CAST(:embedding AS vector)) AS score
            FROM regulation_chunks
            ORDER BY embedding <=> CAST(:embedding AS vector), id
            LIMIT :limit
            """
        )
        with self.engine.connect() as connection:
            rows = connection.execute(
                statement,
                {"embedding": vector_literal(vector), "limit": limit},
            ).mappings()
            return [_result_from_row(row) for row in rows]

    def text_candidates(self, query: str, limit: int) -> list[SearchResult]:
        statement = text(
            """
            WITH query AS (SELECT websearch_to_tsquery('english', :query) AS value)
            SELECT id, source, section, title, url, content,
                   ts_rank_cd(search_vector, query.value) AS score
            FROM regulation_chunks, query
            WHERE search_vector @@ query.value
            ORDER BY score DESC, id
            LIMIT :limit
            """
        )
        with self.engine.connect() as connection:
            rows = connection.execute(
                statement,
                {"query": query, "limit": limit},
            ).mappings()
            return [_result_from_row(row) for row in rows]


class RegulationRetriever:
    def __init__(self, store: RuleStore, embeddings: EmbeddingClient) -> None:
        self.store = store
        self.embeddings = embeddings

    def vector_only(self, query: str, *, limit: int = DEFAULT_LIMIT) -> list[SearchResult]:
        vector = self.embeddings.embed([_validate_query(query)])[0]
        return self.store.vector_candidates(vector, limit)

    def hybrid(
        self,
        query: str,
        *,
        limit: int = DEFAULT_LIMIT,
        candidate_limit: int = DEFAULT_CANDIDATE_LIMIT,
    ) -> list[SearchResult]:
        validated = _validate_query(query)
        vector = self.embeddings.embed([validated])[0]
        vector_results = self.store.vector_candidates(vector, candidate_limit)
        text_results = self.store.text_candidates(validated, candidate_limit)
        return reciprocal_rank_fusion(vector_results, text_results, limit=limit)

    def compare(
        self,
        query: str,
        *,
        limit: int = DEFAULT_LIMIT,
        candidate_limit: int = DEFAULT_CANDIDATE_LIMIT,
    ) -> tuple[list[SearchResult], list[SearchResult]]:
        """Run both strategies with one shared query embedding."""
        validated = _validate_query(query)
        vector = self.embeddings.embed([validated])[0]
        vector_results = self.store.vector_candidates(vector, candidate_limit)
        text_results = self.store.text_candidates(validated, candidate_limit)
        hybrid_results = reciprocal_rank_fusion(
            vector_results,
            text_results,
            limit=limit,
        )
        return vector_results[:limit], hybrid_results


def reciprocal_rank_fusion(
    vector_results: list[SearchResult],
    text_results: list[SearchResult],
    *,
    limit: int = DEFAULT_LIMIT,
) -> list[SearchResult]:
    chunks: dict[str, RuleChunk] = {}
    scores: dict[str, float] = {}
    for results in (vector_results, text_results):
        for rank, result in enumerate(results, start=1):
            chunk_id = result.chunk.id
            chunks[chunk_id] = result.chunk
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1 / (RRF_K + rank)
    ordered = sorted(scores, key=lambda chunk_id: (-scores[chunk_id], chunk_id))
    return [
        SearchResult(chunk=chunks[chunk_id], score=scores[chunk_id])
        for chunk_id in ordered[:limit]
    ]


def _validate_query(query: str) -> str:
    stripped = query.strip()
    if not stripped:
        raise ValueError("retrieval query must not be empty")
    return stripped


def _result_from_row(row) -> SearchResult:
    return SearchResult(
        chunk=RuleChunk(
            id=row["id"],
            source=row["source"],
            section=row["section"],
            title=row["title"],
            url=row["url"],
            content=row["content"],
        ),
        score=float(row["score"]),
    )
