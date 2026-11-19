"""User authentication and company-scoped RBAC.

Revision ID: 0010_auth_rbac
Revises: 0009_bq_evidence_audit_pit
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = "0010_auth_rbac"
down_revision = "0009_bq_evidence_audit_pit"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "company_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "company_id", name="uq_company_membership_user_company"),
        sa.CheckConstraint("role IN ('ANALYST','REVIEWER','ADMIN')", name="company_membership_role_valid"),
    )
    op.create_index("ix_company_memberships_company", "company_memberships", ["company_id"])

def downgrade() -> None:
    op.drop_table("company_memberships")
    op.drop_table("users")
