# Deployment verification

Use `scripts/verify-deployment.sh` for a local verification run. It applies database migrations and therefore must target a disposable development/test database.

The GitHub Actions workflow `.github/workflows/ci.yml` is the authoritative repeatable check:

1. Start PostgreSQL 16.
2. Install the backend and development dependencies.
3. Apply all Alembic migrations.
4. Run unit and integration tests, including append-only audit trigger checks.
5. Start FastAPI and check liveness/readiness.
6. Install frontend dependencies, run TypeScript checking and build Next.js.

Required production configuration must be supplied by the deployment platform, not committed to the repository. Never use the example database password or example secret in staging/production.
