# Incremento 5.15.0 — Proveniência e revisão dos alertas de tese

## Objetivo
Tornar os alertas de monitorização rastreáveis à execução de métricas persistida que lhes deu origem e tornar visível o histórico de revisão.

## Implementação
- O endpoint GET de alertas acrescenta metadados da execução financeira: UUID, ano fiscal, instante de criação, versão do motor, política de resolução, data `as_known_at` e estado.
- As execuções são carregadas em lote, evitando uma consulta por alerta.
- O workspace apresenta a proveniência da execução, conserva os detalhes técnicos em área recolhível e mostra o histórico de transições com estado anterior/seguinte, autor, instante e comentário.
- Atualização da documentação do workspace e testes de contrato da rota.

## Segurança e integridade
- Mantém a autorização existente da tese e o acesso à empresa.
- As transições continuam a ser validadas no backend.
- Sem alterações de schema ou migrações; sem operações Neon/produção.
- Alertas permanecem informativos e não provocam alterações automáticas nem invalidação da tese.

## Validação
- GitHub Actions run `44386554265` para o commit `3dca19ae15a2df937b21e7ad811f88114e2a7d24`: backend-quality, backend-postgres, frontend-build e container-images concluídos com sucesso.
- `neon-integration-migrations` foi ignorado por ser manual-only; não foi executado.
- A primeira execução identificou uma asserção demasiado estrita no teste de contrato; a asserção foi corrigida e a execução subsequente passou.
