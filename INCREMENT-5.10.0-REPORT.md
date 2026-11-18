# Incremento 5.10.0 — Comparação reprodutível de valuation runs

## Objetivo
Comparar duas avaliações persistidas e imutáveis, sem recalcular cenários ou alterar o histórico.

## Alterações
- Serviço puro para comparar snapshots Bear, Base e Bull.
- Diferenças absolutas e percentuais para enterprise value, equity value, valor por ação e componentes de valor presente.
- Lista dos campos de premissas alterados, sem inferir qual versão é melhor.
- Exige método, versão do motor, ano-base e moeda compatíveis.
- Baseline zero produz percentagem `null`, evitando divisão por zero.
- Endpoint filtra ambos os IDs pela mesma empresa e responde 404 para avaliações não acessíveis.

## Endpoint
`GET /api/v1/valuation/companies/{company_id}/runs/{baseline_run_id}/compare/{comparison_run_id}`

## Limites
- Compara snapshots; não recalcula avaliações.
- Não altera schema, histórico, Neon ou produção.
- Não emite recomendações de investimento; exige revisão do analista.

## Validação
Testes unitários cobrem deltas, baseline zero, incompatibilidades e dados inválidos. Teste PostgreSQL cobre endpoint, read-only e isolamento multiempresa.
