# Governação de dados

## Camadas
1. Raw immutable: payload original, hash, fornecedor, URL, retrieved_at.
2. Reported facts: observações extraídas sem sobrescrever o original.
3. Normalized facts: unidade, moeda, período e contexto normalizados.
4. Resolved series: seleção por política temporal e metodologia.
5. Metrics: resultados versionados com lineage.
6. Analysis snapshots: avaliação imutável com versões de regras e motores.

## Temporalidade
- `period_end`: período económico a que o dado respeita.
- `filed_at` / `published_at`: publicação ou submissão.
- `available_at`: momento em que o dado se tornou utilizável.
- `retrieved_at`: momento em que o sistema o obteve.
- `valid_from` / `valid_to`: validade no mundo real.

## Políticas
`LATEST_RESTATED` utiliza a versão mais recente válida. `AS_KNOWN_AT` só utiliza informação disponível até à data/hora de corte. Não misturar resultados de políticas diferentes na mesma série sem identificação explícita.

## Ausências
Usar `UNAVAILABLE`, `INSUFFICIENT_DATA`, `NOT_APPLICABLE` ou `LOW_CONFIDENCE`. Nunca substituir silenciosamente por zero.
