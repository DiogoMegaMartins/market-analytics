# Incremento 5.13.0 — Diferenças detalhadas de pressupostos de valuation

## Objetivo

Tornar a comparação entre duas avaliações persistidas mais explicável, mostrando precisamente quais os pressupostos alterados, incluindo campos aninhados nos cenários e períodos de previsão.

## Implementação

- O serviço de comparação percorre recursivamente objetos e listas JSON de pressupostos.
- Devolve `changed_assumption_paths` com caminhos determinísticos em notação pontuada, incluindo índices de listas.
- Devolve `assumption_differences` com o valor anterior, o valor novo e indicadores de presença para cada lado.
- Os indicadores de presença distinguem um campo removido/adicionado de um campo cujo valor é explicitamente JSON `null`.
- Mantém `changed_assumption_fields` para compatibilidade com os consumidores existentes.
- O workspace mostra uma tabela com caminho, valor de referência e valor de comparação.
- A comparação dos resultados Bear/Base/Bull, deltas financeiros e limitações mantém-se inalterada.

## Segurança e integridade

- Apenas lê snapshots imutáveis já persistidos.
- Não recalcula avaliações nem modifica histórico.
- Mantém os controlos de acesso por empresa e a resposta 404 para runs fora do âmbito da empresa.
- Continua a exigir revisão do analista e não emite recomendações de investimento.
- Sem alterações ao schema, migrações, Neon ou produção.

## Validação

GitHub Actions — run [44380715432](https://github.com/DiogoMegaMartins/market-analytics/actions/runs/44380715432): **completed / success**.

- `backend-quality`: success (Ruff, import ordering e sintaxe Python).
- `backend-postgres`: success (migrações, downgrade/upgrade, testes backend/PostgreSQL, confirmação de que os testes de integração não foram ignorados e API health smoke test).
- `frontend-build`: success (type-check e build).
- `container-images`: success (imagens API e frontend).
- `neon-integration-migrations`: skipped, conforme configuração manual-only.

Não foram observadas falhas nos jobs obrigatórios.
