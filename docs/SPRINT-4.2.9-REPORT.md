# Sprint 4.2.9 — Deployment Packaging & Operational Validation

## Delivered

- Added a non-root Python 3.12 API container with liveness healthcheck.
- Added a multi-stage Node 22 / Next.js standalone frontend container with healthcheck.
- Added `docker-compose.app.yml` to orchestrate PostgreSQL, one-shot Alembic migration, API and frontend.
- Migration is a distinct one-shot service; API waits for successful migration completion.
- Database and application ports are loopback-bound in the local integration profile; PostgreSQL is not published to the host.
- Added `.env.compose.example`, deployment guide and a live smoke-test script.
- Added standalone Next.js output configuration for a smaller runtime image.

## Not certified / not executed here

Docker Engine/Compose and a local PostgreSQL server are unavailable in this execution environment. Therefore images were not built locally, the Compose stack was not started, and no live migration, authentication, tenant-isolation, backup/restore, Prometheus scrape, alert delivery or load test was performed. These are explicitly not reported as passed.

## Acceptance path

Run the Compose integration profile on a Docker host, verify `migrate` exits with code 0, run `scripts/smoke-test.sh`, exercise authenticated requests across two distinct tenants, perform a real backup and restore into a separate database, then verify Prometheus/Grafana and alert routing. Record outputs and environment versions before declaring operational readiness.
