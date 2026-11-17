"""Persist deterministic thesis monitoring alerts and audit events.

Revision ID: 0014_thesis_monitoring_alerts
Revises: 0013_thesis_evidence_links
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0014_thesis_monitoring_alerts"
down_revision = "0013_thesis_evidence_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "investment_thesis_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("thesis_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("investment_theses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("investment_thesis_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assumption_id", sa.String(80), nullable=False),
        sa.Column("metric_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("financial_metric_runs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("alert_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("thesis_id", "version_id", "assumption_id", "metric_run_id", "alert_type", name="uq_thesis_alert_detection"),
        sa.CheckConstraint("status IN ('PENDING','REVIEWED','RESOLVED')", name="ck_thesis_alert_status"),
        sa.CheckConstraint("alert_type IN ('THRESHOLD_BREACH','MATERIAL_CHANGE')", name="ck_thesis_alert_type"),
    )
    op.create_index("ix_thesis_alerts_thesis_status_created", "investment_thesis_alerts", ["thesis_id", "status", "created_at"])
    op.create_table(
        "investment_thesis_alert_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("investment_thesis_alerts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("from_status", sa.String(20)), sa.Column("to_status", sa.String(20), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("comment", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("to_status IN ('PENDING','REVIEWED','RESOLVED')", name="ck_thesis_alert_event_to_status"),
    )
    op.create_index("ix_thesis_alert_events_alert_created", "investment_thesis_alert_events", ["alert_id", "created_at"])
    op.execute("CREATE TRIGGER trg_thesis_alert_events_immutable BEFORE UPDATE OR DELETE ON investment_thesis_alert_events FOR EACH ROW EXECUTE FUNCTION reject_thesis_history_mutation()")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_thesis_alert_events_immutable ON investment_thesis_alert_events")
    op.drop_index("ix_thesis_alert_events_alert_created", table_name="investment_thesis_alert_events")
    op.drop_table("investment_thesis_alert_events")
    op.drop_index("ix_thesis_alerts_thesis_status_created", table_name="investment_thesis_alerts")
    op.drop_table("investment_thesis_alerts")
