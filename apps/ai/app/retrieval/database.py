"""Database helpers for the regulation corpus."""

from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine

LOCAL_DATABASE_URL = (
    "postgresql+psycopg://servicerswitch:servicerswitch@localhost:5432/servicerswitch"
)


def database_engine() -> Engine:
    return create_engine(os.getenv("DATABASE_URL", LOCAL_DATABASE_URL), pool_pre_ping=True)
