from app.api.v1.dependencies import (
    allowed_roles_for_company_write,
    get_current_user,
    require_company_access,
)
from app.api.v1.endpoints.business_quality import router as business_quality_router
from app.api.v1.endpoints.financial_data import router as financial_data_router
from app.api.v1.endpoints.identity import router as identity_router
from app.api.v1.endpoints.metrics import router as metrics_router
from app.main import app


def _router_dependency_calls(router) -> set:
    """Return dependencies declared at router level, independent of app inclusion internals."""
    return {dependency.dependency for dependency in router.dependencies}


def _has_bearer_security(operation: dict) -> bool:
    return any("HTTPBearer" in requirement for requirement in operation.get("security", []))


def test_company_scoped_api_routers_require_company_access():
    # Authorization is deliberately applied at router level to every operation.
    for router in (business_quality_router, financial_data_router, metrics_router):
        assert require_company_access in _router_dependency_calls(router)


def test_identity_api_router_requires_authenticated_user():
    assert get_current_user in _router_dependency_calls(identity_router)


def test_health_endpoints_are_the_only_unauthenticated_operational_routes():
    paths = app.openapi()["paths"]
    public_paths = {"/api/v1/auth/token", "/api/v1/auth/refresh"}
    for path, operations in paths.items():
        if not path.startswith("/api/v1/") or path in public_paths:
            continue
        for method, operation in operations.items():
            if method in {"get", "post", "put", "patch", "delete"}:
                assert _has_bearer_security(operation), (
                    f"{method.upper()} {path} must declare bearer authentication"
                )


def test_company_write_role_policy_separates_analysis_from_review():
    assert allowed_roles_for_company_write("/business-quality/companies/x/assessments") == {"ANALYST", "ADMIN"}
    assert allowed_roles_for_company_write("/business-quality/evidence-candidates/x/review") == {"REVIEWER", "ADMIN"}
    assert allowed_roles_for_company_write("/business-quality/assessments/x/review-events") == {
        "ANALYST", "REVIEWER", "ADMIN"
    }
    assert "REVIEWER" not in allowed_roles_for_company_write("/financial-data/assets/x/import")


def test_session_management_endpoints_are_registered_as_protected_routes():
    paths = app.openapi()["paths"]
    expected = {
        "/api/v1/auth/sessions": {"get"},
        "/api/v1/auth/sessions/{session_id}": {"delete"},
    }
    for path, methods in expected.items():
        assert path in paths
        assert methods.issubset(paths[path])
        for method in methods:
            assert _has_bearer_security(paths[path][method]), (
                f"{method.upper()} {path} must require bearer authentication"
            )
