# ADR-002 — Dados temporais e snapshots

Estado: Proposto

Decisão: preservar raw e resultados imutáveis; distinguir período económico, publicação, disponibilidade e recolha. Suportar `LATEST_RESTATED` e `AS_KNOWN_AT`.

Consequência: mais armazenamento e complexidade, mas permite reproduzir análises históricas e backtests sem look-ahead.
