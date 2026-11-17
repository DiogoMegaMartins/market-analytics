from sqlalchemy import DateTime

from app.platform.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


def test_base_has_naming_convention() -> None:
    assert Base.metadata.naming_convention["pk"] == "pk_%(table_name)s"


def test_timestamp_mixin_uses_timezone_aware_columns() -> None:
    created = TimestampMixin.__annotations__["created_at"]
    assert "datetime" in str(created)
    assert DateTime(timezone=True).timezone is True


def test_uuid_primary_key_mixin_uses_postgres_generated_uuid() -> None:
    column = UUIDPrimaryKeyMixin.__dict__["id"].column
    assert column.primary_key is True
    assert column.server_default is not None
