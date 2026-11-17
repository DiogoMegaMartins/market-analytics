from fastapi.testclient import TestClient

import app.main as main_module


def test_liveness_does_not_depend_on_database() -> None:
    with TestClient(main_module.app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readiness_returns_503_when_database_is_unavailable(monkeypatch) -> None:
    async def unavailable() -> None:
        raise OSError("database unavailable")

    monkeypatch.setattr(main_module, "ping_database", unavailable)
    with TestClient(main_module.app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["detail"] == "Database or schema is not ready"


def test_readiness_returns_503_when_schema_is_outdated(monkeypatch) -> None:
    async def available() -> None:
        return None

    async def outdated() -> str:
        raise RuntimeError("schema is outdated")

    monkeypatch.setattr(main_module, "ping_database", available)
    monkeypatch.setattr(main_module, "verify_database_schema", outdated)
    with TestClient(main_module.app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["detail"] == "Database or schema is not ready"


def test_readiness_returns_ready_when_database_is_available(monkeypatch) -> None:
    async def available() -> None:
        return None

    monkeypatch.setattr(main_module, "ping_database", available)
    async def current_schema() -> str:
        return "0019_neon_operational_indexes"

    monkeypatch.setattr(main_module, "verify_database_schema", current_schema)
    with TestClient(main_module.app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready", "database": "connected", "schema": "current",
        "schema_revision": "0019_neon_operational_indexes",
    }
