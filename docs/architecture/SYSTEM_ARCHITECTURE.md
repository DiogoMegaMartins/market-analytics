# Arquitectura do sistema

## Estilo
Monólito modular com fronteiras de domínio explícitas. Não introduzir microserviços ou Kafka antes de existir necessidade operacional comprovada.

## Componentes
- Next.js frontend
- FastAPI API
- Domain services e calculation engines
- PostgreSQL como fonte de verdade transaccional
- Redis/workers para jobs assíncronos numa fase posterior
- Object storage para documentos e payloads volumosos
- Providers externos isolados por adaptadores
- Observabilidade via logs estruturados, métricas e tracing

## Regras
- Routers finos; regras de negócio nos serviços/domínio.
- Cálculos puros e determinísticos sempre que possível.
- Repositories encapsulam persistência.
- Providers nunca definem regras de investimento.
- AI orchestration não altera resultados determinísticos.
- Snapshots e resultados publicados são versionados e auditáveis.
