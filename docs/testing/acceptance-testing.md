# Integration and acceptance testing

The acceptance script checks the running API, database readiness, request IDs, unauthenticated access, local CORS, and the frontend. It is intentionally read-only apart from creating an authentication session when optional test credentials are supplied.

## Run against the local Compose profile

```bash
cp .env.compose.example .env
# Replace POSTGRES_PASSWORD and SECRET_KEY with unique 64-character hex values.
# Example: openssl rand -hex 32

docker compose -f docker-compose.app.yml up --build -d
docker compose -f docker-compose.app.yml ps
./scripts/acceptance-test.sh
```

The Compose profile binds API and frontend ports to loopback. It is a local integration profile, not a production ingress, TLS, secrets-management, or high-availability deployment.

## Authenticated and tenant-isolation checks

Create dedicated disposable test users and provision a company that is deliberately **not** a member of the test user. Do not use a real account or production data.

```bash
export MA_ACCEPTANCE_EMAIL='acceptance-user@example.test'
export MA_ACCEPTANCE_PASSWORD='use-a-disposable-test-password'
export MA_ACCEPTANCE_FOREIGN_COMPANY_ID='00000000-0000-0000-0000-000000000000'
./scripts/acceptance-test.sh
```

The optional cross-tenant check requests the company financial-facts endpoint and requires HTTP 404, matching the application's tenant-hiding policy. Use a real company UUID belonging exclusively to a different test user; the example UUID is only a placeholder.

## CI coverage

The GitHub Actions workflow provisions PostgreSQL 16, applies Alembic migrations, runs the backend suite with `TEST_DATABASE_URL`, checks the migration revision, performs API health smoke tests, and builds the frontend and both container images. The PostgreSQL integration tests include membership isolation, role authorization, and immutable audit-event constraints.

A successful CI run is not a substitute for a restore drill, external alert-delivery test, load test, or deployment review in the target hosting environment. Record the tested commit, database version, migration revision, test-account identifiers (never passwords), backup/restore duration, and observed RTO/RPO for each operational exercise.
