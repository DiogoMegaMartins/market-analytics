# Market Analytics

Plataforma de análise fundamentalista, inteligência de mercado e apoio à investigação de investimentos de longo prazo.

## Estado deste repositório

Este repositório é um **monólito modular em desenvolvimento**. Já contém implementações parciais e testadas de identidade SEC, importação Company Facts, normalização e métricas financeiras, Business Quality, evidências documentais, autenticação/RBAC, segurança operacional e observabilidade. Outros domínios continuam apenas especificados ou parcialmente implementados. Não representa uma plataforma completa nem pronta para produção.

Estados usados na documentação:
- `IMPLEMENTED + TESTED`: implementado e validado por testes.
- `IMPLEMENTED`: código existente, validação incompleta.
- `PARTIAL`: implementação parcial.
- `NOT IMPLEMENTED`: especificado, ainda sem implementação.
- `UNKNOWN`: ainda não auditado.

O estado de cada componente deve ser confirmado nos relatórios de sprint e nos testes; uma especificação documentada não equivale a uma funcionalidade implementada.

## Princípios fundamentais

1. Não inventar dados nem preencher ausências com zero.
2. Distinguir factos, métricas, evidências, interpretações e hipóteses.
3. Preservar proveniência, temporalidade, versões e lineage.
4. Separar qualidade do negócio, valuation, risco e qualidade dos dados.
5. Os motores determinísticos são a autoridade para cálculos e scores.
6. A IA pode pesquisar e interpretar, mas não alterar silenciosamente factos, cálculos ou avaliações.
7. Preservar políticas `LATEST_RESTATED` e `AS_KNOWN_AT`.
8. Construir inicialmente como monólito modular.

## Stack proposta

- Frontend: Next.js, TypeScript, Tailwind CSS e shadcn/ui.
- Backend: Python 3.12, FastAPI, Pydantic e SQLAlchemy async.
- Dados: PostgreSQL; Redis e workers assíncronos numa fase posterior.
- Armazenamento de documentos/raw: storage compatível com S3.
- Qualidade operacional: pytest, Ruff, OpenTelemetry e Sentry.

## Estrutura

- `frontend/`: aplicação web e funcionalidades por domínio.
- `backend/`: API, domínio, modelos, fornecedores, serviços e testes.
- `docs/`: arquitetura, metodologia, regras, diagramas, decisões e plano de implementação.
- `scripts/`: ferramentas de desenvolvimento e manutenção.

## Arranque

Consultar `docs/implementation/LOCAL_DEVELOPMENT.md`. Não configurar credenciais reais antes de rever `backend/.env.example` e as políticas de segurança.

## Sprint 4.0.4 — Financial Data Pipeline

The backend now includes an initial SEC Company Facts import pipeline. See `docs/implementation/sprint-4.0.4.md` for endpoints, data model, validation results and known limitations.


## Sprint 4.0.8 — SEC integration & reconciliation

- Added a runtime filing-reference catalog for FY2024 Microsoft, Apple and Coca-Cola.
- Added reconciliation of persisted normalized facts against the curated references.
- Added `GET /api/v1/financial-data/companies/{company_id}/reconcile-reference?ticker=...`.
- Added explicit handling for missing values, mismatches, incompatible units/periods and ambiguous source contexts.
- The reconciliation endpoint is a validation tool; it does not claim to perform a live SEC fetch.
- See `docs/implementation/sprint-4.0.8-sec-reconciliation.md`.


## Sprint 4.0.9 — Financial Data Pipeline Hardening

The SEC connector now supports bounded retries, `Retry-After`, fail-fast HTTP 403 handling, persistent Company Facts caching and database-backed idempotent inserts. Configuration is available through `SEC_MAX_ATTEMPTS`, `SEC_RETRY_BASE_SECONDS`, `SEC_RETRY_MAX_SECONDS`, and `SEC_COMPANY_FACTS_CACHE_TTL_SECONDS`.

See `backend/docs/implementation/sprint-4.0.9-pipeline-hardening.md` for validation results, known limitations and the operational runbook.

### Business Quality Engine v1

O motor determinístico e a rubrica inicial encontram-se em `backend/app/services/business_quality/engine.py`. A metodologia e limitações estão documentadas em `docs/implementation/sprint-4.1.0-business-quality-engine.md`.

### Sprint 4.1.1 — Business Quality persistence and API

The Business Quality Engine now has persistence for versioned assessments and endpoints to create, list and retrieve assessments. Inputs remain analyst-supplied and evidence-backed; the API does not infer scores. See `backend/docs/implementation/sprint-4.1.1-business-quality-persistence-api.md`.

### Sprint 4.1.2 — Business Quality calibration harness

Added an offline sensitivity-analysis utility for comparing explicitly defined alternative weights across the five Business Quality dimensions. It reports score/rank ranges without changing production assessments or claiming empirical validation. See `docs/SPRINT-4.1.2-REPORT.md`.

### Sprint 4.1.3 — Analyst Review Workflow

Introduces append-only review events and a deterministic Draft → Submitted → Reviewed → Approved/Rejected workflow for Business Quality assessments. See `docs/implementation/sprint-4.1.3-analyst-review-workflow.md`. Actor IDs are not yet authenticated; do not expose these endpoints publicly before RBAC/tenant authorization is implemented.

### Sprint 4.1.4 — Business Quality Historical Validation

Added an offline descriptive validation harness for approved historical assessments. It reports period coverage, within-company score changes and cross-sectional Spearman rank consistency, while excluding unapproved/incomplete observations and preventing comparisons across methodology versions. It does not claim predictive validity or include fabricated historical company scores. See `docs/implementation/sprint-4.1.4-business-quality-historical-validation.md`.

### Sprint 4.1.5 — Point-in-Time Evidence

Introduces a deterministic evidence eligibility policy and reproducible manifest for historical Business Quality assessments. Evidence without verifiable publication and availability timestamps is excluded rather than assumed to have been known at the cutoff. See `backend/docs/implementation/sprint-4.1.5-point-in-time-evidence.md`.

### Sprint 4.1.6 — SEC Historical Filing Catalogue

Added a reusable SEC EDGAR submissions catalogue for recent and historical filing metadata (10-K, 10-Q, 20-F, 6-K), including accession identifiers, report/filing dates, archive URLs and deterministic record hashes. This is metadata indexing only; filing bodies are not yet downloaded or parsed into evidence. See `backend/docs/implementation/sprint-4.1.6-sec-filing-catalogue.md`.

### Sprint 4.1.7 — SEC filing document ingestion

Added bounded SEC EDGAR document download, original-byte SHA-256, deterministic HTML/plain-text extraction, and candidate section segmentation. This does not yet persist documents or extracted passages, and it does not produce approved evidence or scores. See `docs/implementation/sprint-4.1.7-sec-filing-document-ingestion.md`.

## Sprint 4.1.8 — Evidence persistence & traceability

Persists original SEC source bytes, extracted document sections and reviewable Business Quality evidence candidates. Every stored document and section/passage has a SHA-256 digest. Candidate evidence is not treated as verified until a distinct reviewer approves it. Original bytes are stored in PostgreSQL BYTEA for this MVP (20 MB API limit); production should move blobs to versioned object storage while retaining hashes and immutable metadata. The API currently trusts caller-supplied actor IDs and requires authentication/RBAC before public exposure.

### Sprint 4.1.9 — Evidence audit and point-in-time linking

Added append-only, hash-linked evidence review events and immutable assessment-to-evidence eligibility snapshots. Only verified evidence with verifiable publication timing at or before the assessment cutoff can be eligible. Client-supplied actor IDs remain a pre-production limitation; see `docs/implementation/sprint-4.1.9-evidence-audit-pit.md`.

### Sprint 4.2.0 — Evidence extraction

The Business Quality evidence pipeline now exposes a versioned criterion catalogue and deterministic, review-only passage extraction for stored SEC filing sections. See `docs/SPRINT-4.2.0-REPORT.md` for endpoints, validation and limitations. Keyword matches remain unverified candidates and never generate scores.

### Sprint 4.2.1 — Evidence Review Workspace

Added a first Next.js review workspace at `/research/evidence` to browse persisted SEC filings/sections, preview extracted candidate passages, persist selected candidates, filter review queues and inspect source provenance plus append-only review history. The workspace reuses the existing deterministic extraction and evidence-review APIs; it does not verify facts or score criteria. Configure `NEXT_PUBLIC_API_BASE_URL` in the frontend and `CORS_ALLOWED_ORIGINS` in the backend. Authentication/RBAC and tenant authorization are still missing, so this remains an internal development surface. See `docs/SPRINT-4.2.1-REPORT.md`.

## Sprint 4.2.2 — Authentication & RBAC

Introduced administratively provisioned users and company-scoped roles (`ANALYST`, `REVIEWER`, `ADMIN`). There is deliberately no public self-registration endpoint. The initial bearer-token implementation was hardened in Sprint 4.2.3 to use HttpOnly session cookies, rotating refresh tokens and CSRF protection. Provision users administratively from `backend/` after applying migrations:

```bash
python scripts_provision_user.py --email analyst@example.com --display-name "Research Analyst" --company-id <COMPANY_UUID> --role ANALYST
```

The browser login is available at `/login`; it stores only the CSRF token client-side, not access or refresh credentials.

## Sprint 4.2.3 — Security hardening & authorization coverage

Introduces server-side revocable sessions, 15-minute session-bound access cookies, rotating opaque refresh tokens with replay detection, CSRF protection for cookie-authenticated writes, database-backed login throttling, append-only authentication audit events, company-scoped authorization for identity/financial-data/metrics/Business Quality APIs, and company-admin membership management. Frontend authentication now uses HttpOnly cookies rather than storing bearer credentials in `sessionStorage`; only the CSRF token is retained client-side. See `docs/implementation/sprint-4.2.3-security-hardening.md` for validation and remaining production work.

## Deployment verification

A repeatable local verification script is available at `scripts/verify-deployment.sh`. It applies migrations to the configured database, runs backend tests, then type-checks and builds the frontend. The GitHub Actions pipeline `.github/workflows/ci.yml` runs the same checks against PostgreSQL 16. See `docs/implementation/sprint-4.2.4-security-integration-deployment.md` for execution status and remaining limitations.

### Sprint 4.2.5 — Multi-Tenant Security & Session Reliability

- Refresh-token concurrency grace, without reissuing credentials to a consumed token.
- Per-user session listing and revocation endpoints.
- Protection against demoting the final company administrator.
- Single-flight refresh in the Evidence Review Workspace.
- Validation: 128 tests passed; 2 PostgreSQL integration tests skipped without `TEST_DATABASE_URL`.


### Sprint 4.2.6 — Production security verification coverage

Adds real-PostgreSQL integration tests for company tenant isolation, resource-ID access checks, and Analyst/Reviewer write boundaries. Staging/production configuration now rejects wildcard, non-HTTPS, path-bearing, or credential-bearing CORS origins. The PostgreSQL integration tests run in CI after applying Alembic migrations; local runs without `TEST_DATABASE_URL` skip those checks explicitly. See `docs/implementation/sprint-4.2.6-production-security-verification.md`.

## Operational monitoring (Sprint 4.2.8)

The API exposes Prometheus metrics at `/metrics` (protected by `METRICS_TOKEN` in staging/production). Example Prometheus alert rules and a Grafana dashboard are provided under `ops/`. An optional monitoring stack can be started with `docker-compose.observability.yml`; see `docs/operations/observability-monitoring.md` before enabling it. PostgreSQL backup scripts are available under `scripts/` and can emit node_exporter textfile metrics when `BACKUP_METRICS_DIR` is configured.

### Sprint 4.2.8 — Observability, Monitoring & Operational Resilience

Added a Prometheus-compatible `/metrics` endpoint, low-cardinality HTTP metrics, PostgreSQL pool snapshots, SEC provider retry counters, server-generated request IDs with JSON request logs, Prometheus alert rules, a Grafana operations dashboard and optional node_exporter textfile metrics from PostgreSQL backup jobs. See `docs/operations/observability-monitoring.md`. Metrics are process-local and are not aggregated across workers.

## Integrated local deployment (Sprint 4.2.9)

For a containerized local integration environment, copy `.env.compose.example` to `.env`, replace the development secrets, and run:

```bash
docker compose -f docker-compose.app.yml up --build -d
./scripts/smoke-test.sh
./scripts/acceptance-test.sh
```

The Compose profile starts PostgreSQL, applies Alembic migrations as a one-shot release step, then starts the API and frontend. The acceptance script also checks request IDs, unauthenticated access, CORS and, when disposable credentials are supplied, login and optional cross-tenant denial. See `docs/operations/deployment-packaging.md` and `docs/testing/acceptance-testing.md`. This package is not, by itself, a production-readiness certification.


### Sprint 4.3.0 — Integration & Acceptance Test Harness

Added `scripts/acceptance-test.sh` for API liveness/readiness, database connectivity, request IDs, unauthenticated access rejection, local CORS preflight and frontend response. Optional disposable test credentials exercise login/profile; an optional foreign company UUID verifies cross-tenant requests are hidden with HTTP 404. See `docs/testing/acceptance-testing.md`. PostgreSQL integration tests remain enabled in CI through `TEST_DATABASE_URL`; local execution in this environment had no PostgreSQL server or Docker, so live Compose, HTTP acceptance, backup/restore and alert-delivery exercises remain unverified.

## Sprint 4.3.1 — Research Intelligence Foundation

Added a deterministic, citation-first research brief over SEC filing documents and sections already ingested into the evidence store. The company-scoped endpoint `GET /api/v1/research/companies/{company_id}/brief` groups candidate passages into risk disclosures, management assertions and quantitative claims, and flags heuristic potential conflicts. Every passage retains filing metadata, SEC URL, document hash, section locator and an explicit unverified status. This increment does not call an LLM, fetch filings live, verify claims, score Business Quality, calculate fair value or issue investment recommendations. See `docs/research/ai-research-intelligence-v1.md`.

## AI Research Copilot

The optional OpenAI Responses API integration is disabled by default. See [AI Research Copilot setup and security](docs/implementation/AI_RESEARCH_COPILOT.md) and [Sprint 4.3.3 report](docs/SPRINT-4.3.3-REPORT.md).


## Latest increment — Sprint 4.3.4

Deterministic `What Changed?` comparison endpoint for filing evidence and historical Business Quality assessment snapshots. See `docs/implementation/SPRINT-4.3.4-WHAT-CHANGED.md`.


## Latest increment — Sprint 4.3.5

Financial Evolution endpoint compares persisted annual metric runs and applies configurable, explicitly heuristic materiality classification. Thesis monitoring remains deferred pending a versioned thesis data model. See `docs/implementation/SPRINT-4.3.5-FINANCIAL-EVOLUTION.md`.


## Latest increment — Sprint 4.3.6

Versioned Investment Thesis Engine with explicit assumptions, deterministic breach candidates, and append-only analyst decisions. See `docs/implementation/SPRINT-4.3.6-INVESTMENT-THESIS.md`.

### Sprint 4.3.7 — Thesis evidence linking

Investment theses can now link individual assumptions to persisted Business Quality evidence candidates or financial metric results. Each link records whether the evidence supports, contradicts, or qualifies the assumption, plus analyst rationale. Cross-company references are rejected; links are immutable and tied to a specific thesis version. The intelligence endpoint reports counts and source review/calculation status only — it does not infer causality, score the thesis, or invalidate it automatically.

## Thesis Intelligence Dashboard (Sprint 4.3.8)

A primeira interface para consultar teses, pressupostos, cobertura de evidência, avaliações determinísticas e decisões do analista está disponível em `/thesis`. Ver `docs/implementation/SPRINT-4.3.8-THESIS-INTELLIGENCE-DASHBOARD.md` para funcionalidades, limites e validação.


## Sprint 4.3.9 — Thesis Versioning & Research Workflow

- Editor para preparar uma nova versão a partir da atual, mantendo o histórico imutável.
- Comparação de campos entre versões e histórico cronológico.
- Ligações de evidência não são copiadas automaticamente entre versões.
- Ver `docs/implementation/SPRINT-4.3.9-THESIS-VERSIONING.md`.

## Sprint 4.4.0 — Thesis Monitoring & Alerts

Added deterministic on-demand monitoring of explicit thesis assumptions and persisted `PENDING` / `REVIEWED` / `RESOLVED` alerts with append-only audit events. Threshold breaches and material metric changes are review triggers only; no thesis, investment decision, or valuation is changed automatically. Material change uses a fixed 20% comparison against the prior calculated run for the same fiscal year. See `docs/implementation/SPRINT-4.4.0-THESIS-MONITORING-ALERTS.md` for endpoints, migration, validation and limitations.
