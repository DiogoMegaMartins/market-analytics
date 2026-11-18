# Incremento 5.21.0 — Portfolio Money-Weighted Return (MWR/XIRR)

## Objetivo
Disponibilizar retorno ponderado pelo dinheiro anualizado (XIRR), calculado a partir de snapshots de valuation e fluxos externos datados do ledger.

## Metodologia
- Perspetiva do investidor: NAV inicial é contribuição negativa; DEPOSIT é fluxo negativo; WITHDRAWAL é distribuição positiva; NAV final é distribuição terminal positiva.
- BUY, SELL, DIVIDEND, INTEREST, FEE e TAX são atividade interna e não são tratados como fluxos externos do investidor.
- Convenção ACTUAL/365 com dias reais entre datas.
- Snapshots duplicados na mesma data: maior recorded_at; empate pelo maior id.
- Não exige valuation intermédia em cada data de fluxo; utiliza as datas reais dos fluxos.
- Pesquisa de raízes em espaço log(1 + taxa), limitada a taxas anuais entre -99,99% e 100000%.
- Sem raiz ou múltiplas raízes produzem erro explícito (HTTP 422), sem selecionar arbitrariamente uma solução.
- NAV inicial/final têm de ser positivos; exige fluxos positivos e negativos.

## API
GET `/api/v1/portfolio/companies/{company_id}/portfolios/{portfolio_id}/performance/mwr?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`

Endpoint read-only, tenant-scoped, devolve cash flows usados, taxa XIRR anualizada, convenção de dias, cobertura e limitações.

## Validação
- Testes unitários para retorno simples, sinais de depósitos/levantamentos, múltiplas raízes, ausência de raiz, valores não finitos, NAV inicial inválido e escolha do snapshot canónico.
- Contrato de autorização verifica que o router MWR exige require_company_access.
- CI PostgreSQL deverá executar a suite integral e os testes de integração não podem ser ignorados.

## Limitações
Sem FX, Modified Dietz, benchmark, anualização alternativa, validação externa de NAV, fees attribution fora do NAV, fluxos intradiários ou persistência do resultado. O intervalo de pesquisa é limitado e a qualidade do resultado depende das valuations fornecidas.

## Segurança e operações
Sem alterações de schema/migrações. Nenhuma operação Neon ou produção foi executada. Nenhum merge foi efetuado; PR sujeito a revisão do utilizador.
