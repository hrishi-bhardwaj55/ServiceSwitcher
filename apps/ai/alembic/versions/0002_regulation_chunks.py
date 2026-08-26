"""Add pgvector-backed regulation chunks.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-26
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE regulation_chunks (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            section TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            content TEXT NOT NULL,
            embedding vector(512) NOT NULL,
            search_vector tsvector GENERATED ALWAYS AS (
                setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(section, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(content, '')), 'B')
            ) STORED
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_regulation_chunks_embedding ON regulation_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        "CREATE INDEX ix_regulation_chunks_search ON regulation_chunks USING gin (search_vector)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS regulation_chunks")
