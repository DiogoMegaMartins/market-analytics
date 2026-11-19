# Sprint 4.2.2 — Authentication, RBAC & Research Permissions

## Delivered
- User accounts with PBKDF2-HMAC-SHA256 password hashes (random 128-bit salt, 310,000 iterations).
- Signed HS256 bearer access tokens with expiry and strict algorithm/header validation.
- Company-scoped memberships and roles: `ANALYST`, `REVIEWER`, `ADMIN`.
- Login (`POST /api/v1/auth/token`) and current-user profile (`GET /api/v1/auth/me`).
- Business Quality routes require authentication and a membership in the company owning the requested resource. Non-members receive 404 to avoid disclosing resource existence.
- Mutating analyst operations require ANALYST or ADMIN; review operations require REVIEWER or ADMIN.
- Actor identities on assessment/evidence creation and review events are taken from the authenticated principal, not trusted from request payloads.
- No public registration endpoint. `backend/scripts_provision_user.py` provisions users and company memberships administratively.
- Frontend login page and session-scoped bearer token for the Evidence Review Workspace.

## Security boundaries and limitations
- This is a first-party MVP authentication implementation, not a completed production identity platform.
- Access tokens expire after one hour; refresh tokens, revocation/rotation, MFA, SSO and account recovery are not implemented.
- Rate limiting, breached-password checks, email verification and central audit/alerting should be added before public deployment.
- Browser token is held in `sessionStorage`; this is more limited than persistent local storage but remains accessible to same-origin JavaScript. Production should move to secure HttpOnly, SameSite cookies and a hardened CSRF strategy.
- Provisioning requires an administrator with database access. Company-level authorization is enforced in the API, but portfolio/workspace tenancy is not yet modelled.
- All API routes outside Business Quality (e.g. identity/financial-data/metrics) are not yet covered by this RBAC policy and must not be treated as public-ready.

## Migration
- Alembic revision `0010_auth_rbac` creates `users` and `company_memberships` with role constraints and indexes.

## Validation
- Password hashing/token unit tests added.
- Python compile/import, API route registration, pytest and Alembic offline SQL generation performed in this sprint.
- No live PostgreSQL migration or end-to-end browser test was performed.
