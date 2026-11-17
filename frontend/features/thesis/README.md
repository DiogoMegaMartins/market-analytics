# Thesis Intelligence Dashboard — Sprint 4.3.8

Rota: `/thesis`.

## Funcionalidades
- Lista teses privadas por empresa (UUID) e abre os detalhes da tese selecionada.
- Cria uma tese e os seus pressupostos quantitativos estruturados.
- Apresenta cobertura de evidência por pressuposto, separando relações SUPPORTS / CONTRADICTS / QUALIFIES e estado da fonte.
- Regista ligações a `FinancialMetricResult` ou `BQEvidenceCandidate` existentes, com justificação do analista.
- Executa avaliação determinística por ano fiscal e apresenta a avaliação mais recente.
- Regista decisões KEEP / REVISE / ON_HOLD / INVALIDATE e consulta o histórico de eventos.

## Segurança e limites
- A autenticação usa cookie de sessão, refresh e token CSRF, seguindo o padrão do Evidence Review Workspace.
- O backend continua responsável por autorização, propriedade da tese, associação da fonte à empresa e validação do tipo de evidência.
- O frontend pede UUIDs existentes; não faz pesquisa nem cria fontes de evidência.
- A interface não atribui pontuações, não declara uma fonte como verdadeira e não invalida automaticamente uma tese.
- A avaliação utiliza o último `FinancialMetricRun` persistido para o ano selecionado; não é uma avaliação point-in-time.

## Validação
A validação Python do backend permanece independente do frontend. O typecheck/build Next.js deve ser executado num ambiente com as dependências declaradas em `package.json` instaladas (`npm install` e `npm run typecheck`, `npm run build`).

## Sprint 4.3.9 — Versionamento e revisão
- Prepara o editor copiando o conteúdo da versão atual para novos campos de edição.
- Cria uma nova versão através do endpoint existente; não atualiza versões anteriores.
- Compara a versão atual com uma versão anterior, campo a campo, sem inferir impacto qualitativo.
- Mostra histórico de versões e assinala uma decisão REVISE ainda associada à versão atual.
- As evidências permanecem ligadas à versão original e têm de ser novamente associadas quando aplicável.
