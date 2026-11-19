# Sprint 4.3.8 — Thesis Intelligence Dashboard

## Objetivo
Disponibilizar uma primeira interface web funcional para o motor de teses introduzido nos sprints 4.3.6 e 4.3.7, sem deslocar regras de autorização ou lógica financeira para o cliente.

## Implementado
- Nova rota frontend `/thesis` e componente `features/thesis/thesis-dashboard.tsx`.
- Lista teses do utilizador para uma empresa e consulta a versão atual, pressupostos, riscos e racional.
- Criação de teses com pressupostos quantitativos em JSON validado no cliente e novamente no backend.
- Associação de fontes existentes a pressupostos através dos endpoints de evidência: métricas financeiras ou candidatos documentais, com relação SUPPORTS / CONTRADICTS / QUALIFIES e racional explícito.
- Painel de cobertura de evidência com contagens por relação e por estado da fonte.
- Execução e apresentação da última avaliação determinística por ano fiscal.
- Registo de decisões explícitas KEEP / REVISE / ON_HOLD / INVALIDATE e consulta de eventos de auditoria.
- Integração da rota no ecrã inicial e redirecionamento pós-login para `/thesis`.
- Padrão de sessão, refresh e CSRF alinhado com o Evidence Review Workspace existente.

## Decisões e limites
- O frontend não faz scoring nem altera a tese sem decisão explícita do analista.
- As fontes são identificadas por UUID; o backend valida existência, pertença à empresa e associação ao pressuposto.
- O dashboard não pesquisa automaticamente o catálogo de métricas nem candidatos documentais. Essa descoberta permanece manual nesta versão.
- Não foi implementado editor de versões históricas nem fluxo visual de criação de nova versão. A ação REVISE continua a exigir uma nova versão através do endpoint existente, ainda sem formulário dedicado no dashboard.
- O dashboard mostra ligações e respetivas referências/justificações, mas a leitura integral de um candidato documental continua no Evidence Review Workspace.
- A avaliação mantém a limitação anterior: usa o último conjunto de métricas persistido para o ano fiscal e não uma fotografia AS-KNOWN-AT.

## Validação
- Backend: `pytest -q` — 178 aprovados, 5 ignorados (testes que exigem PostgreSQL real).
- Frontend: não foi possível executar `npm run typecheck` nem `npm run build`, porque `frontend/node_modules` não existe neste ambiente. A tentativa de `tsc --noEmit` falhou por ausência de React, Next.js e respetivos tipos, não sendo uma validação conclusiva do código TSX.
- Não foram executados testes HTTP autenticados, migração PostgreSQL real, nem testes E2E do browser.
