# Incremento 5.9.0 — Consulta reprodutível de valuation runs

## Objetivo

Disponibilizar uma consulta de detalhe para recuperar as premissas originais e o resultado imutável de uma avaliação DCF previamente persistida.

## Alterações

- Novo endpoint `GET /api/v1/valuation/companies/{company_id}/runs/{run_id}`.
- A consulta filtra simultaneamente por `company_id` e `run_id`; um identificador de outra empresa devolve 404 sem revelar a existência do registo.
- A resposta inclui identificador da avaliação, empresa, instante de criação, autor, versão do motor, método, ano-base, moeda, premissas originais e resultado calculado.
- O endpoint herda a dependência de autenticação e autorização company-scoped do router de valuation.
- O histórico existente mantém o seu formato resumido.

## Validação adicionada

- Teste unitário confirma o registo da nova rota e a proteção company-scoped do router.
- Contrato PostgreSQL verifica que as premissas e resultado devolvidos correspondem aos dados persistidos.
- Contrato PostgreSQL verifica que um run pertencente a outra empresa não pode ser consultado através do identificador da empresa autorizada.
- Os testes existentes de imutabilidade UPDATE/DELETE permanecem aplicáveis.

## Limites

- Não altera o motor FCFF DCF nem recalcula avaliações históricas.
- Não altera o schema nem requer migração.
- Não aplica migrações a Neon ou produção.
- O endpoint não constitui recomendação de investimento; as premissas e resultados continuam sujeitos a revisão do analista.

## Estado da validação

A validação CI será executada no pull request. Os testes de integração dependem da job PostgreSQL do GitHub Actions.
