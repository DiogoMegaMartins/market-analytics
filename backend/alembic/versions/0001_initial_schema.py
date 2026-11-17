"""Establish the initial migration baseline.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-10
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Intentionally empty: domain tables will be introduced in subsequent revisions.
    pass


def downgrade() -> None:
    # No schema objects are created by this baseline revision.
    pass
