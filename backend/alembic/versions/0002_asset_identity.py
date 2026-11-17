"""Add company, asset and temporal identifier registry.

Revision ID: 0002_asset_identity
Revises: 0001_initial_schema
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_asset_identity"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("legal_name", sa.String(300), nullable=False),
        sa.Column("display_name", sa.String(300)),
        sa.Column("country_code", sa.String(2)),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    )
    op.create_index("ix_companies_name", "companies", ["legal_name"])
    op.create_table(
        "assets",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("asset_type", sa.String(30), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    )
    op.create_index("ix_assets_company_type", "assets", ["company_id", "asset_type"])
    op.create_table(
        "asset_identifiers",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="RESTRICT")),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assets.id", ondelete="RESTRICT")),
        sa.Column("identifier_type", sa.String(30), nullable=False),
        sa.Column("value", sa.String(160), nullable=False),
        sa.Column("exchange_mic", sa.String(4)),
        sa.Column("exchange_name", sa.String(120)),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_to", sa.Date()),
        sa.Column("verification_status", sa.String(30), nullable=False, server_default="UNVERIFIED"),
        sa.Column("source_name", sa.String(100)),
        sa.Column("source_url", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.CheckConstraint("(company_id IS NOT NULL AND asset_id IS NULL) OR (company_id IS NULL AND asset_id IS NOT NULL)", name="ck_asset_identifiers_exactly_one_owner"),
        sa.CheckConstraint("valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from", name="ck_asset_identifiers_valid_date_order"),
        sa.UniqueConstraint("identifier_type", "value", "valid_from", name="uq_asset_identifiers_type_value_from"),
    )
    op.create_index("ix_asset_identifiers_lookup", "asset_identifiers", ["identifier_type", "value"])


def downgrade() -> None:
    op.drop_index("ix_asset_identifiers_lookup", table_name="asset_identifiers")
    op.drop_table("asset_identifiers")
    op.drop_index("ix_assets_company_type", table_name="assets")
    op.drop_table("assets")
    op.drop_index("ix_companies_name", table_name="companies")
    op.drop_table("companies")
