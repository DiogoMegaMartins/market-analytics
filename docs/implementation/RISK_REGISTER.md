# Risk register inicial

| ID | Risco | Prioridade proposta | Evidência a recolher |
|---|---|---:|---|
| R1 | Normalized facts não integrados no Metrics Engine | P0 | Fluxo ponta-a-ponta e testes |
| R2 | Lineage incompleto / mistura de MetricRuns | P0 | IDs de origem e coerência de run |
| R3 | Períodos fiscais e YTD heurísticos | P1 | Casos 10-Q/10-K e fiscal calendars |
| R4 | CAPEX, unidade e moeda inconsistentes | P1 | Regras de normalização e golden tests |
| R5 | SEC rate limit apenas por processo | P1 | Estratégia distribuída e quotas |
| R6 | Modelo de listing/asset demasiado simplificado | P1 | Múltiplas classes e listings |
| R7 | AS_KNOWN_AT com timestamps insuficientes | P1 | available_at e precisão temporal |
| R8 | Motores sectoriais misturam bases | P1 | Scope, período, norma e lineage |
| R9 | Backtesting com look-ahead/survivorship | P1 | Universo point-in-time e delisted |
| R10 | AI claims sem grounding/citação verificável | P1 | Avaliações e rastreabilidade |
| R11 | Autorização/entitlements apenas conceptuais | P1 | Testes de acesso backend |
| R12 | Licenças e direitos de redistribuição de dados | P1 | Inventário contratual por fornecedor |

Prioridades são hipóteses de triagem e devem ser confirmadas pela auditoria.
