# Baseline de segurança

- Não guardar segredos no Git; `.env` ignorado.
- Separar autenticação, autorização e entitlements.
- Verificar ownership e workspace em todas as operações.
- Cookies Secure/HttpOnly/SameSite e CSRF quando aplicável.
- Rate limiting em endpoints sensíveis e conectores.
- Validar assinaturas de webhooks.
- Logs sem passwords, tokens ou dados financeiros sensíveis desnecessários.
- Encriptação em trânsito e em repouso conforme ambiente.
- Backups testados e política de retenção.
- Revisão legal de privacidade, licenças de dados e eventual aconselhamento de investimento antes de disponibilização pública.

## Sprint 4.2.3 implementation notes

- Browser access/refresh credentials are HttpOnly cookies; access TTL is 15 minutes and refresh-session lifetime is 30 days.
- Cookie-authenticated unsafe methods require a session-bound CSRF token in `X-CSRF-Token`.
- Refresh tokens rotate; replay of a consumed refresh token revokes the associated session.
- Login throttling and append-only auth audit events are persisted in PostgreSQL.
- Identity, financial data, metrics and Business Quality APIs are authenticated; company data requires a matching membership.
- Cookie `Secure` is enabled in staging/production. Frontend/API should be deployed same-site and CORS origins must remain explicit.
- This is not production sign-off: PostgreSQL concurrency/migration tests, MFA/recovery, proxy-aware distributed rate limits, penetration testing and deployment-specific cookie validation remain outstanding.
