"""Add revocable sessions, immutable auth audit events and login rate limits.

Revision ID: 0011_auth_security
Revises: 0010_auth_rbac
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0011_auth_security"
down_revision = "0010_auth_rbac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("refresh_token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("csrf_token_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("user_agent", sa.String(500)),
        sa.Column("ip_address", sa.String(64)),
    )
    op.create_index("ix_auth_sessions_user_active", "auth_sessions", ["user_id", "revoked_at", "expires_at"])
    op.create_table(
        "auth_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("ip_address", sa.String(64)),
        sa.Column("user_agent", sa.String(500)),
        sa.Column("details", sa.String(1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_audit_user_created", "auth_audit_events", ["user_id", "created_at"])
    op.create_table(
        "auth_refresh_token_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("auth_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_auth_refresh_history_session", "auth_refresh_token_history", ["session_id", "consumed_at"])
    op.create_table(
        "login_rate_limits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocked_until", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("key_hash", name="uq_login_rate_limits_key_hash"),
        sa.CheckConstraint("attempts >= 0", name="login_rate_limit_attempts_nonnegative"),
    )
    op.execute("""
    CREATE FUNCTION reject_auth_audit_mutation() RETURNS trigger AS $$
    BEGIN
      RAISE EXCEPTION 'auth_audit_events is append-only';
    END;
    $$ LANGUAGE plpgsql;
    """)
    op.execute("""
    CREATE TRIGGER trg_auth_audit_events_immutable
    BEFORE UPDATE OR DELETE ON auth_audit_events
    FOR EACH ROW EXECUTE FUNCTION reject_auth_audit_mutation();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_auth_audit_events_immutable ON auth_audit_events")
    op.execute("DROP FUNCTION IF EXISTS reject_auth_audit_mutation()")
    op.drop_table("login_rate_limits")
    op.drop_index("ix_auth_refresh_history_session", table_name="auth_refresh_token_history")
    op.drop_table("auth_refresh_token_history")
    op.drop_index("ix_auth_audit_user_created", table_name="auth_audit_events")
    op.drop_table("auth_audit_events")
    op.drop_index("ix_auth_sessions_user_active", table_name="auth_sessions")
    op.drop_table("auth_sessions")
