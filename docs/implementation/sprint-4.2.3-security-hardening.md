# Sprint 4.2.3 — Security hardening & authorization coverage

## Implemented

- Access tokens are bound to a persisted server-side session (`sid`) and expire after 15 minutes.
- Refresh tokens are opaque, high-entropy values; only SHA-256 digests are stored.
- Refresh rotation is persisted in `auth_refresh_token_history`; replay of a consumed token revokes its session.
- Logout revokes the current session; logout-all revokes all active sessions for the user.
- Browser authentication uses `HttpOnly`, `SameSite=Lax` cookies. Cookies are `Secure` in staging/production. The CSRF token is returned once to the browser and retained in `sessionStorage`; unsafe cookie-authenticated requests must send `X-CSRF-Token`.
- Login throttling is database-backed, keyed by normalized email+IP and IP, with separate thresholds (8 and 40 attempts per 15-minute window).
- Authentication and membership changes are written to append-only `auth_audit_events`; a PostgreSQL trigger rejects UPDATE/DELETE.
- Identity, financial-data and metrics APIs require authentication. Company-scoped financial and Business Quality routes additionally require a company membership; writes require ANALYST/ADMIN, evidence review requires REVIEWER/ADMIN, and assessment decisions are checked by action.
- Identity search is scoped to the user's company memberships. Creating a company creates an ADMIN membership for its creator; asset creation and SEC registration enforce membership/role.
- Client-supplied actor/analyst/reviewer identifiers were removed from Business Quality write schemas; actor identity is taken from the authenticated server-side user.
- Company ADMINs can list members and change company-scoped roles.
- Frontend requests use credentialed cookies, CSRF headers, and one refresh-and-retry attempt after access-token expiry.

## New migration

`0011_auth_sessions_audit_rate_limits.py` (revision ID `0011_auth_security`) creates `auth_sessions`, `auth_audit_events`, `auth_refresh_token_history`, and `login_rate_limits`.

## Validation

- Unit/API tests: 119 passed.
- Python compileall: passed.
- FastAPI import: passed; 45 routes registered.
- Alembic offline SQL generation through revision 0011: passed.
- PostgreSQL integration/migration: not run.
- Frontend build/typecheck: not run because frontend dependencies are not installed in this environment.

## Remaining production work

- Deploy frontend and API on the same site (or explicitly configure a compatible cookie domain/SameSite policy); verify cookie behavior behind the actual reverse proxy/TLS termination.
- Add MFA, account recovery, administrator bootstrap controls, invite/deprovision workflows, and security notifications.
- Add distributed edge/WAF rate limits and trusted-proxy configuration; current application login limits use `request.client.host`.
- Add retention/monitoring for auth audit and rate-limit rows, backup/restore testing, and security review/penetration testing.
- Confirm the PostgreSQL trigger and concurrent refresh-rotation behavior with integration tests against a real PostgreSQL instance.
- Apply tenant authorization to any future API routes before exposure; currently all registered data routes are protected, but this must be regression-tested as routes are added.

This sprint materially improves the MVP security baseline but is not a certification or production security sign-off.
