# Incremento 5.20.0 — Portfolio Time-Weighted Return Engine

## Objetivo
Calcular TWR determinístico com snapshots datados de valuation e fluxos externos do ledger.

## Metodologia
- NAV por snapshot = market_value + cash_value.
- DEPOSIT é fluxo externo positivo; WITHDRAWAL é negativo.
- BUY, SELL, DIVIDEND, INTEREST, FEE e TAX são atividade interna refletida no NAV.
- Fluxos externos são assumidos no início do respetivo trade_date; a avaliação dessa data é tratada como observação pós-fluxo.
- Exige avaliação nas duas fronteiras do período e em cada data com fluxo externo líquido não nulo.
- Calcula fatores de subperíodo e encadeia-os geometricamente.
- Snapshots duplicados no mesmo dia: maior recorded_at e, em empate, maior id.
- Ausência de cobertura, capital não positivo ou valores não finitos resultam em erro explícito, sem estimativas.

## Limitações
Sem Modified Dietz, interpolação, fluxos intradiários, anualização, MWR/XIRR, FX, benchmarks ou corporate actions. A precisão depende da qualidade e frequência dos snapshots e da premissa temporal de fluxo no início do dia.

## Estado
Implementação proposta para revisão via PR. Nenhuma migração, operação Neon ou acesso a produção.
