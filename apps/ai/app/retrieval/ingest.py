"""Embed and ingest the curated regulation corpus into PostgreSQL/pgvector."""

from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import Engine, text

from app.embeddings import EmbeddingClient, OpenAIEmbeddingClient
from app.retrieval.corpus import load_corpus
from app.retrieval.database import database_engine
from app.retrieval.models import RuleChunk

DATABASE_DIMENSIONS = 512


def embedding_text(chunk: RuleChunk) -> str:
    return f"{chunk.title}\n{chunk.section}\n{chunk.content}"


def vector_literal(vector: list[float]) -> str:
    if len(vector) != DATABASE_DIMENSIONS:
        raise ValueError(
            f"expected {DATABASE_DIMENSIONS} embedding dimensions; found {len(vector)}"
        )
    return "[" + ",".join(format(value, ".9g") for value in vector) + "]"


def ingest_chunks(chunks: list[RuleChunk], client: EmbeddingClient, engine: Engine) -> int:
    if client.dimensions != DATABASE_DIMENSIONS:
        raise ValueError(
            f"embedding client must use {DATABASE_DIMENSIONS} dimensions; "
            f"found {client.dimensions}"
        )
    vectors = client.embed([embedding_text(chunk) for chunk in chunks])
    if len(vectors) != len(chunks):
        raise ValueError("embedding provider returned the wrong number of vectors")
    records = [
        {
            "id": chunk.id,
            "source": chunk.source,
            "section": chunk.section,
            "title": chunk.title,
            "url": chunk.url,
            "content": chunk.content,
            "embedding": vector_literal(vector),
        }
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM regulation_chunks"))
        connection.execute(
            text(
                """
                INSERT INTO regulation_chunks
                    (id, source, section, title, url, content, embedding)
                VALUES
                    (:id, :source, :section, :title, :url, :content,
                     CAST(:embedding AS vector))
                """
            ),
            records,
        )
    return len(records)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corpus",
        type=Path,
        default=Path("knowledge-base/chunks.jsonl"),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    chunks = load_corpus(args.corpus)
    client = OpenAIEmbeddingClient.from_env()
    count = ingest_chunks(chunks, client, database_engine())
    print(
        f"Ingested {count} regulation chunks with {client.model} "
        f"({client.dimensions} dimensions)"
    )


if __name__ == "__main__":
    main()
