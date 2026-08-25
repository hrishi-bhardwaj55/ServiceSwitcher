"""Establish the initial empty schema.

Revision ID: 0001
Revises:
Create Date: 2026-08-25
"""

from collections.abc import Sequence

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Leave database tables for their owning future chunk."""


def downgrade() -> None:
    """The initial migration has no database objects to remove."""
