# Increment 5.16.0 — Portfolio Transaction Ledger

## Objetivo

Introduzir o primeiro alicerce persistente de Portfolio & Backtesting: carteiras por empresa e registo append-only de transações, com isolamento multi-tenant e idempotência.

## Implementação

- Novo modelo `Portfolio` com empresa, nome, moeda base, estado e autoria.
- Novo modelo `PortfolioTransaction` com tipo, activo, trade/settlement dates, quantidade, preço, montante bruto, moeda, fees, taxes, referência externa e idempotency key.
- Migração Alembic (revision `0022_portfolio_ledger`), com chaves estrangeiras, constraints de forma e valores, índices e trigger PostgreSQL que bloqueia UPDATE/DELETE das transações.
- API autenticada:
  - `POST /api/v1/portfolio/companies/{company_id}/portfolios`
  - `GET /api/v1/portfolio/companies/{company_id}/portfolios`
  - `GET /api/v1/portfolio/companies/{company_id}/portfolios/{portfolio_id}`
  - `POST /api/v1/portfolio/companies/{company_id}/portfolios/{portfolio_id}/transactions`
  - `GET /api/v1/portfolio/companies/{company_id}/portfolios/{portfolio_id}/transactions`
- Tipos iniciais: BUY, SELL, DIVIDEND, DEPOSIT, WITHDRAWAL, FEE, TAX e INTEREST.
- Chaves idempotentes por carteira: repetição idêntica devolve o registo existente; reutilização com conteúdo diferente devolve 409.
- Moeda de cada transação tem de coincidir com a moeda base da carteira. FX fica explicitamente fora do âmbito.
- Testes unitários de validação e teste de integração PostgreSQL para persistência e imutabilidade.
- Sem cálculos de posições, lotes, performance ou recomendações.

## Segurança e âmbito operacional

- Rotas usam `require_company_access` ao nível do router e confirmam a relação carteira/empresa em cada operação.
- Sem operações em Neon ou produção. Migração apenas exercitada pelo CI PostgreSQL isolado.
- O PR #16 foi integrado na `main` em 2026-11-18 (merge commit `4b4167b715f07a26f22492877249c6ae8d3ba447`). O CI pós-merge na `main` concluiu com sucesso; o workflow Neon permaneceu ignorado por ser manual.
