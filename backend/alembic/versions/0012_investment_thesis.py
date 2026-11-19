"""Create versioned investment thesis and append-only events.

Revision ID: 0012_investment_thesis
Revises: 0011_auth_security
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012_investment_thesis"
down_revision = "0011_auth_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "investment_theses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("current_version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_investment_theses_company_owner", "investment_theses", ["company_id", "owner_user_id", "updated_at"])
    op.create_table(
        "investment_thesis_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("thesis_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("investment_theses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("assumptions", postgresql.JSONB(), nullable=False),
        sa.Column("risks", postgresql.JSONB(), nullable=False),
        sa.Column("evidence_references", postgresql.JSONB(), nullable=False),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("thesis_id", "version_number", name="uq_thesis_version_number"),
    )
    op.create_index("ix_thesis_versions_created", "investment_thesis_versions", ["thesis_id", "created_at"])
    op.create_table(
        "investment_thesis_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("thesis_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("investment_theses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("investment_thesis_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("decision", sa.String(40), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_thesis_events_thesis_created", "investment_thesis_events", ["thesis_id", "created_at"])
    op.execute("""
    CREATE FUNCTION reject_thesis_history_mutation() RETURNS trigger AS $$
    BEGIN
      RAISE EXCEPTION 'investment thesis versions and events are append-only';
    END;
    $$ LANGUAGE plpgsql;
    """)
    op.execute("""
    CREATE TRIGGER trg_thesis_versions_immutable
    BEFORE UPDATE OR DELETE ON investment_thesis_versions
    FOR EACH ROW EXECUTE FUNCTION reject_thesis_history_mutation();
    """)
    op.execute("""
    CREATE TRIGGER trg_thesis_events_immutable
    BEFORE UPDATE OR DELETE ON investment_thesis_events
    FOR EACH ROW EXECUTE FUNCTION reject_thesis_history_mutation();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_thesis_events_immutable ON investment_thesis_events")
    op.execute("DROP TRIGGER IF EXISTS trg_thesis_versions_immutable ON investment_thesis_versions")
    op.execute("DROP FUNCTION IF EXISTS reject_thesis_history_mutation()")
    op.drop_index("ix_thesis_events_thesis_created", table_name="investment_thesis_events")
    op.drop_table("investment_thesis_events")
    op.drop_index("ix_thesis_versions_created", table_name="investment_thesis_versions")
    op.drop_table("investment_thesis_versions")
    op.drop_index("ix_investment_theses_company_owner", table_name="investment_theses")
    op.drop_table("investment_theses")
