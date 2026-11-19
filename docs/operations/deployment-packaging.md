# Deployment packaging — Sprint 4.2.9

## Scope and status

This sprint adds reproducible container packaging for the API and Next.js frontend, plus a Compose integration profile. It is a **local integration / pre-production package**, not a production deployment certification. TLS termination, secret management, backups to off-host storage, alert delivery, horizontal scaling, and provider licensing remain deployment-owner responsibilities.

## Local integrated run

1. Install Docker Engine/Desktop with the Compose plugin.
2. Copy `.env.compose.example` to `.env` in the repository root.
3. Replace `POSTGRES_PASSWORD` and `SECRET_KEY` with unique random hexadecimal values (for example, `openssl rand -hex 32`; hexadecimal avoids URL-encoding problems in the Compose database URL). Set a valid SEC contact in `SEC_USER_AGENT`.
4. Start the stack:

   ```bash
   docker compose -f docker-compose.app.yml up --build -d
   ```

   The `migrate` one-shot service runs `alembic upgrade head` after PostgreSQL becomes healthy. API startup is gated on successful migration completion. Migrations are deliberately not run inside the API process.

5. Verify:

   ```bash
   ./scripts/smoke-test.sh
   ./scripts/acceptance-test.sh
   docker compose -f docker-compose.app.yml ps
   docker compose -f docker-compose.app.yml logs --tail=100 api migrate frontend
   ```

6. Stop services while retaining the database volume:

   ```bash
   docker compose -f docker-compose.app.yml down
   ```

   To destroy local database data as well (irreversible): `docker compose -f docker-compose.app.yml down -v`.

The frontend calls the API at `NEXT_PUBLIC_API_BASE_URL`, which is embedded at build time. The default is `http://localhost:8000/api/v1`; change it and rebuild if the browser reaches the API through another origin. The API port and frontend port bind to loopback by default.

## Migration and rollback discipline

- Review migration SQL and take a verified database backup before applying schema changes to a persistent environment.
- Deploy the migration task as a separate release step and wait for successful exit before routing traffic to the new API.
- Do not assume downgrade is safe. Prefer a forward-fix migration and a tested restore plan for destructive changes.
- The Compose profile uses a one-shot migration dependency for convenience; production orchestrators should model this as a release job, not as a permanently running service.

## Container design

- API image uses Python 3.12 slim, installs the backend package, runs as an unprivileged user and exposes `/health/live`.
- Frontend uses a multi-stage Node 22 build and Next.js standalone output, runs as an unprivileged user.
- PostgreSQL data is persisted in a named volume and is not published on a host port in the integrated profile.
- No Redis service is included because the current application does not require Redis for this integration profile.

## Validation boundaries

The repository CI is configured to validate backend migrations/tests against a real PostgreSQL service and build the frontend and container images. Confirm the actual workflow result in GitHub Actions for the commit being deployed. The basic smoke test checks API liveness, API readiness (including database connectivity), and the frontend root. The extended acceptance test also checks request IDs, unauthenticated access rejection and local CORS. With disposable test credentials it can verify login/profile and denial of access to a company owned by another test user. Neither script proves backup/restore correctness, alert delivery, load capacity, or production security. Those require a running deployment and explicit operational exercises.
