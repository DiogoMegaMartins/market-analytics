def test_database_dependencies_are_importable() -> None:
    import asyncpg
    import sqlalchemy

    assert asyncpg.__version__
    assert sqlalchemy.__version__
