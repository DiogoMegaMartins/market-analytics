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
A validação automatizada será reportada após a execução do GitHub Actions para este pull request.
