from app.main import app


def test_evidence_review_workspace_routes_are_registered():
    # OpenAPI is the stable public route registry; app.routes may contain lazy
    # _IncludedRouter wrappers in newer FastAPI versions.
    paths = app.openapi()["paths"]
    expected = {
        "/api/v1/business-quality/companies/{company_id}/source-documents",
        "/api/v1/business-quality/source-documents/{document_id}/sections",
        "/api/v1/business-quality/companies/{company_id}/evidence-candidates",
        "/api/v1/business-quality/evidence-candidates/{candidate_id}",
    }
    assert expected.issubset(paths)
    for path in expected:
        assert "get" in paths[path]
        assert any("HTTPBearer" in item for item in paths[path]["get"].get("security", []))


def test_cors_middleware_is_registered_for_web_workspace():
    assert any(item.cls.__name__ == "CORSMiddleware" for item in app.user_middleware)
