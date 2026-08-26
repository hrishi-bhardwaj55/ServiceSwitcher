"""Export existing measured C9 vectors for the offline demo seed artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import text

from app.retrieval.database import DATABASE_DIMENSIONS, managed_database_engine


def export_embeddings(output: Path) -> int:
    with managed_database_engine() as engine, engine.connect() as connection:
        rows = connection.execute(
            text("SELECT id, embedding::text FROM regulation_chunks ORDER BY id")
        ).all()
    records = []
    for chunk_id, vector_text in rows:
        vector = json.loads(vector_text)
        if len(vector) != DATABASE_DIMENSIONS:
            raise ValueError(f"stored vector for {chunk_id} has the wrong dimensions")
        records.append(json.dumps({"id": chunk_id, "embedding": vector}, separators=(",", ":")))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(records) + "\n", encoding="utf-8")
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    count = export_embeddings(args.output)
    print(f"Exported {count} measured embeddings to {args.output}")


if __name__ == "__main__":
    main()
