"""Enforce append-only valuation run history.

Revision ID: 0021_valuation_run_immutability
Revises: 0020_valuation_runs
"""
from alembic import op

revision = "0021_valuation_run_immutability"
down_revision = "0020_valuation_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION prevent_valuation_run_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION
                'valuation_runs is append-only; % is not permitted', TG_OP
                USING ERRCODE = '55000';
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_valuation_runs_immutable
        BEFORE UPDATE OR DELETE ON valuation_runs
        FOR EACH ROW
        EXECUTE FUNCTION prevent_valuation_run_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_valuation_runs_immutable ON valuation_runs")
    op.execute("DROP FUNCTION IF EXISTS prevent_valuation_run_mutation()")
