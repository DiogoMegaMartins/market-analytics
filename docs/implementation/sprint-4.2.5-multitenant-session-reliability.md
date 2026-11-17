# Sprint 4.2.5 — Multi-Tenant Security & Session Reliability

## Scope

This sprint hardens refresh-token rotation under concurrent browser requests, adds user-visible session management, and protects the final company administrator from accidental demotion.

## Changes

- Added a 10-second refresh-rotation concurrency grace period. A previously consumed refresh token presented inside this window returns HTTP 409 without issuing credentials or revoking the session. Reuse outside the window continues to revoke the session and creates a security audit event.
- Added `GET /api/v1/auth/sessions` to list the authenticated user's sessions without exposing token hashes.
- Added `DELETE /api/v1/auth/sessions/{session_id}` to revoke only a session owned by the authenticated user. Unknown or foreign sessions return 404. Revoking the current session also clears its cookies.
- Serialized company membership role changes by locking the company row and prevented demotion of the final administrator.
- Added a single-flight refresh request in the Evidence Review Workspace so simultaneous 401 responses share one refresh operation.
- Added unit and route-registration tests for refresh grace and session management.

## Security semantics

The grace period is a concurrency accommodation, not a second-use token. A duplicate request receives no replacement cookie and cannot authenticate with the consumed token. The client should retry its original request using the newly rotated cookie. A replay after the grace period revokes the session.

Session metadata includes user agent and IP address; these values are informational and should not be treated as reliable device identity. Session listing and revocation are scoped to the authenticated user.

## Validation

- `pytest -q`: 128 passed, 2 skipped (the PostgreSQL integration tests require `TEST_DATABASE_URL`).
- Python compilation: application modules compile successfully.
- FastAPI import: successful; 43 routes registered.
- Alembic offline SQL generation: successful through `0011_auth_security`.
- A live PostgreSQL migration and full frontend build were not run in this environment.

## Remaining production work

- Execute CI against real PostgreSQL and validate row-lock behavior under concurrent refresh requests.
- Consider a distributed rate limiter (Redis) for multi-worker deployments; login limits currently use PostgreSQL.
- Add MFA, account recovery, device trust policy and security notifications in a later security phase.
- Ensure the production deployment uses HTTPS, a unique high-entropy `SECRET_KEY`, strict CORS origins and secure cookies.
