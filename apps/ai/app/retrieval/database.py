"""Database helpers for the regulation corpus."""

from __future__ import annotations

import math
import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine

LOCAL_DATABASE_URL = (
    "postgresql+psycopg://servicerswitch:servicerswitch@localhost:5432/servicerswitch"
)
DATABASE_DIMENSIONS = 512


def vector_literal(vector: list[float]) -> str:
    """Validate and serialize an embedding for a pgvector cast parameter."""
    if len(vector) != DATABASE_DIMENSIONS:
        raise ValueError(
            f"expected {DATABASE_DIMENSIONS} embedding dimensions; found {len(vector)}"
        )
    if not all(math.isfinite(value) for value in vector):
        raise ValueError("embedding values must be finite")
    return "[" + ",".join(format(value, ".9g") for value in vector) + "]"


def database_engine() -> Engine:
    return create_engine(os.getenv("DATABASE_URL", LOCAL_DATABASE_URL), pool_pre_ping=True)


@contextmanager
def managed_database_engine() -> Iterator[Engine]:
    """Create an engine and always close its pooled database connections."""
    engine = database_engine()
    try:
        yield engine
    finally:
        engine.dispose()
