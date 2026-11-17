# Financial Metrics Engine

Métricas universais iniciais:
- Revenue Growth e Revenue CAGR
- Gross, Operating e Net Margin
- OCF Margin
- FCF = Operating Cash Flow − CAPEX
- FCF Margin
- CAPEX Intensity

Regras:
- Usar `Decimal` e validar unidades/moedas.
- Não assumir CAPEX positivo nem aplicar `abs()` sem normalização documentada.
- CAGR exige endpoints positivos e intervalo temporal válido.
- Crescimento exige denominador anterior positivo.
- FCF exige OCF e CAPEX compatíveis.
- Gross Profit mapping está pendente de mapeamento XBRL validado.
- Cada resultado deve guardar definição, versão, run e IDs dos factos de origem.
