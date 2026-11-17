# Estratégia de testes

1. Unitários: cálculos puros, period classifier, resolver, scoring e regras.
2. Golden tests: casos financeiros conhecidos, fórmulas e cenários.
3. Integração: DB, repositories, providers simulados e APIs.
4. Contract tests: schemas e conectores.
5. Temporal tests: AS_KNOWN_AT, restatements, available_at.
6. Security tests: ownership, RBAC, IDOR, injection, webhook signatures.
7. E2E: fluxos principais frontend/backend.
8. Backtesting validation: point-in-time universe, delisted assets, costs, corporate actions e ausência de look-ahead.

Testes devem cobrir inputs inválidos, dados em falta, moedas/unidades incompatíveis e lineage.
