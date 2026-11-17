# Identity, Access, Subscription & Entitlements

Separar autenticação, autorização e entitlements. RBAC combinado com ownership/scope por recurso; autorização validada no backend e protecção contra IDOR. Preferir fornecedor de identidade gerido quando adequado; não inventar criptografia própria. MFA, sessões, rotação de refresh tokens, cookies seguros, CSRF e rate limiting.

Planos e permissões configuráveis. Metering idempotente com reservas e confirmação de consumo. Billing via fornecedor especializado; não armazenar dados de cartões. Webhooks assinados, idempotentes e processados de forma assíncrona. Limites não apagam dados.
