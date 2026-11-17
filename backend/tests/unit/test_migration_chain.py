import ast
from pathlib import Path


def _migration_metadata() -> dict[str, str | None]:
    versions = Path(__file__).parents[2] / "alembic" / "versions"
    metadata: dict[str, str | None] = {}
    for path in versions.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        values: dict[str, object] = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name) and target.id in {"revision", "down_revision"}:
                    values[target.id] = ast.literal_eval(node.value)
            elif (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id in {"revision", "down_revision"}
                and node.value is not None
            ):
                values[node.target.id] = ast.literal_eval(node.value)
        revision = values.get("revision")
        parent = values.get("down_revision")
        assert isinstance(revision, str), f"Missing revision in {path.name}"
        assert parent is None or isinstance(parent, str), f"Invalid down_revision in {path.name}"
        assert revision not in metadata, f"Duplicate revision: {revision}"
        metadata[revision] = parent
    return metadata


def test_alembic_has_single_increment_4_1_head() -> None:
    metadata = _migration_metadata()
    assert "0019_neon_operational_indexes" in metadata
    assert metadata["0019_neon_operational_indexes"] == "0018_point_in_time_contract"
    assert len(metadata) == len(set(metadata))
    assert all(len(revision) <= 32 for revision in metadata)
    assert all(parent is None or parent in metadata for parent in metadata.values())
    parents = {parent for parent in metadata.values() if parent is not None}
    heads = set(metadata) - parents
    assert heads == {"0019_neon_operational_indexes"}


def test_thesis_history_triggers_follow_table_creation() -> None:
    migration = Path(__file__).parents[2] / "alembic" / "versions" / "0012_investment_thesis.py"
    source = migration.read_text(encoding="utf-8")
    assert source.index('op.create_table(\n        "investment_thesis_versions"') < source.index(
        "CREATE TRIGGER trg_thesis_versions_immutable"
    )
    assert source.index('op.create_table(\n        "investment_thesis_events"') < source.index(
        "CREATE TRIGGER trg_thesis_events_immutable"
    )
    assert source.count("op.execute(") == 6  # 3 trigger/function statements + 3 downgrade statements


def test_postgres_integration_suite_is_opt_in() -> None:
    integration = Path(__file__).parents[1] / "integration"
    assert any("TEST_DATABASE_URL" in path.read_text(encoding="utf-8") for path in integration.glob("*.py"))
