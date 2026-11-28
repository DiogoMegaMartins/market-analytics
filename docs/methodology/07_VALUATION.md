# Valuation Engine

## Métodos
- Empresas industriais: FCFF DCF e FCFE quando apropriado.
- Bancos/seguradoras: Residual Income, P/TBV e DDM; Embedded Value para Life quando dados actuariais suportam.
- Equity REIT: AFFO multiple e NAV.
- mREIT: métodos específicos de book value, spreads, duration e risco de crédito.
- Cíclicas: earnings e margens normalizados de meio de ciclo.
- Growth: DCF multi-stage com convergência gradual.

## FCFF
FCFF = EBIT × (1 − Tax Rate) + D&A − CAPEX − ΔNWC.
Descontar a WACC; EV = PV dos fluxos + PV do terminal value. Equity Value = EV − Net Debt ± outros ajustamentos. FV/share = Equity Value / diluted shares.

## Controlo
Moeda e inflação consistentes; WACC superior ao terminal growth; pressupostos explícitos; cenários Bear/Base/Bull; sensibilidades; lineage. Terminal value acima de 80% do EV gera aviso, não invalidação automática. Não fazer média cega de métodos.


## Suitability guard (SEC SIC)

The API uses the SIC code verified from the SEC submissions record when registering a SEC ticker. Current narrow safeguards reject FCFF DCF for SIC 6000–6299 (banks, credit and other financial institutions), SIC 6311–6399 (insurance issuers), and SIC 6798 (REITs). An active asset classified as REIT remains a fallback safeguard regardless of issuer SIC. SIC is source-derived and is not accepted from company-create input.

A missing or unrecognized SIC is not interpreted as a sector classification; analysts must verify the issuer's business model and choose an appropriate method. SIC mapping is a conservative guard, not a complete sector taxonomy. In particular, classifications based on SEC SIC can be imperfect for diversified issuers and do not replace analyst review.
