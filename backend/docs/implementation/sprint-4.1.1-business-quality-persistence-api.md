# Sprint 4.1.1 — Business Quality Persistence & API

## Scope

Persists the deterministic Business Quality v1.0.0 assessment output and analyst-supplied observations. Adds create, list and detail endpoints. The assessment stores the complete input evidence references/rationales and calculated result JSON so that a result can be audited against its engine/rubric version.

## Endpoints

- `POST /api/v1/business-quality/companies/{company_id}/assessments`
- `GET /api/v1/business-quality/companies/{company_id}/assessments?limit=20`
- `GET /api/v1/business-quality/assessments/{assessment_id}`

POST body example:

```json
{
  "analyst_id": "analyst-01",
  "notes": "Annual review based on latest annual report",
  "observations": {
    "BUSINESS_MODEL.clarity": {
      "score": 80,
      "evidence_reference": "https://www.sec.gov/Archives/...",
      "rationale": "Revenue streams and customer proposition are clearly disclosed",
      "confidence": "HIGH"
    }
  }
}
```

Only criteria supplied with score, evidence reference and rationale are assessed. Required missing criteria keep the dimension and overall result insufficient. This API does not automatically extract evidence or generate analyst scores.

## Storage

Migration `0006_business_quality_assessments` creates an append-oriented assessment record with company, engine/rubric versions, status, score, classification, completeness, confidence, input observations and result payload. The API exposes no update/delete operation. Database-level immutability enforcement and tenant authorization are not included yet.

## Important limitations

- Rubric weights/classification thresholds are initial hypotheses, not empirically calibrated.
- Analyst-supplied scores require independent review and evidence verification.
- No sector-specific rubric, evidence registry foreign key, reviewer workflow or AI scoring.
- No live PostgreSQL integration test was run; Alembic offline SQL generation was validated.
- Authentication/authorization is not yet enforced on these endpoints; do not expose publicly until tenant-level access controls are implemented.
