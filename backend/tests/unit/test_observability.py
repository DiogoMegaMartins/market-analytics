from fastapi.testclient import TestClient

import app.main as main_module
from app.core.observability import MetricsRegistry


def test_metrics_registry_renders_counter_and_bounded_histogram() -> None:
    registry = MetricsRegistry()
    registry.increment("sample_total", {"kind": "ok"})
    registry.observe("sample_duration_seconds", 0.02, {"route": "/health/live"})
    registry.observe("sample_duration_seconds", 0.2, {"route": "/health/live"})

    rendered = registry.render(pool={"checked_out": 2})
    assert 'sample_total{kind="ok"} 1' in rendered
    assert 'sample_duration_seconds_bucket{route="/health/live",le="0.025"} 1' in rendered
    assert 'sample_duration_seconds_count{route="/health/live"} 2' in rendered
    assert "market_analytics_db_pool_checked_out 2" in rendered


def test_request_metrics_endpoint_exposes_prometheus_format() -> None:
    with TestClient(main_module.app) as client:
        live = client.get("/health/live")
        response = client.get("/metrics")

    assert live.status_code == 200
    assert live.headers.get("x-request-id")
    assert response.headers.get("x-request-id")
    assert response.status_code == 200
    assert "market_analytics_http_requests_total" in response.text
    assert "market_analytics_http_request_duration_seconds_bucket" in response.text


def test_metrics_endpoint_is_hidden_in_production_without_token(monkeypatch) -> None:
    monkeypatch.setattr(main_module.settings, "app_env", "production")
    from pydantic import SecretStr
    monkeypatch.setattr(main_module.settings, "metrics_token", SecretStr(""))
    with TestClient(main_module.app) as client:
        response = client.get("/metrics")
    assert response.status_code == 404


def test_metrics_endpoint_requires_bearer_token_in_production(monkeypatch) -> None:
    monkeypatch.setattr(main_module.settings, "app_env", "production")
    from pydantic import SecretStr
    monkeypatch.setattr(main_module.settings, "metrics_token", SecretStr("a-long-monitoring-secret"))
    with TestClient(main_module.app) as client:
        denied = client.get("/metrics")
        allowed = client.get("/metrics", headers={"Authorization": "Bearer a-long-monitoring-secret"})
    assert denied.status_code == 401
    assert allowed.status_code == 200
