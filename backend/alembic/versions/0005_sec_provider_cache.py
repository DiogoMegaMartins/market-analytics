"""Add persistent SEC response cache.

Revision ID: 0005_sec_provider_cache
Revises: 0004_financial_metrics_quality
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_sec_provider_cache"
down_revision = "0004_financial_metrics_quality"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sec_provider_cache",
        sa.Column("provider", sa.String(30), nullable=False, server_default="SEC"),
        sa.Column("cache_key", sa.String(300), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("payload_text", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.UniqueConstraint("provider", "cache_key", name="uq_sec_provider_cache_provider_key"),
    )
    op.create_index("ix_sec_provider_cache_expires", "sec_provider_cache", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_sec_provider_cache_expires", table_name="sec_provider_cache")
    op.drop_table("sec_provider_cache")
