"""Seed the measured regulation corpus from checked-in C9 embedding vectors."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from sqlalchemy import Engine

from app.retrieval.corpus import load_corpus
from app.retrieval.database import DATABASE_DIMENSIONS, managed_database_engine
from app.retrieval.ingest import embedding_text, ingest_chunks
from app.retrieval.models import RuleChunk


class StoredEmbeddingClient:
    """Serve a fixed, validated vector for each exact corpus input."""

    dimensions = DATABASE_DIMENSIONS

    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self.vectors = vectors

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            return [self.vectors[text] for text in texts]
        except KeyError as error:
            raise ValueError("stored embeddings do not match the corpus") from error


def load_stored_vectors(path: Path, chunks: list[RuleChunk]) -> dict[str, list[float]]:
    by_id: dict[str, list[float]] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        record = json.loads(line)
        if not isinstance(record, dict) or set(record) != {"id", "embedding"}:
            raise ValueError(f"invalid stored embedding record on line {line_number}")
        chunk_id = record["id"]
        raw_vector = record["embedding"]
        if not isinstance(chunk_id, str) or not isinstance(raw_vector, list):
            raise ValueError(f"invalid stored embedding types on line {line_number}")
        if chunk_id in by_id:
            raise ValueError(f"duplicate stored embedding id: {chunk_id}")
        vector = [float(value) for value in raw_vector]
        if len(vector) != DATABASE_DIMENSIONS or not all(math.isfinite(v) for v in vector):
            raise ValueError(f"invalid stored vector for {chunk_id}")
        by_id[chunk_id] = vector

    expected_ids = {chunk.id for chunk in chunks}
    if set(by_id) != expected_ids:
        missing = sorted(expected_ids - set(by_id))
        extra = sorted(set(by_id) - expected_ids)
        raise ValueError(
            f"stored embedding ids differ from corpus; missing={missing}, extra={extra}"
        )
    return {embedding_text(chunk): by_id[chunk.id] for chunk in chunks}


def seed_demo(corpus_path: Path, embeddings_path: Path, engine: Engine) -> int:
    chunks = load_corpus(corpus_path)
    client = StoredEmbeddingClient(load_stored_vectors(embeddings_path, chunks))
    return ingest_chunks(chunks, client, engine)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=Path("knowledge-base/chunks.jsonl"))
    parser.add_argument(
        "--embeddings",
        type=Path,
        default=Path("knowledge-base/demo-embeddings.jsonl"),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    with managed_database_engine() as engine:
        count = seed_demo(args.corpus, args.embeddings, engine)
    print(f"Seeded {count} measured regulation chunks without provider access")


if __name__ == "__main__":
    main()
