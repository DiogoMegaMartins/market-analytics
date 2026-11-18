# Incremento 5.12.0 — Detalhe reprodutível de valuation run no workspace

## Objetivo

Permitir que o analista abra uma avaliação persistida a partir do histórico e consulte os seus metadados, pressupostos originais e resultado integral, preservando a imutabilidade e sem executar novamente o motor DCF.

## Implementação

- O workspace consulta `GET /api/v1/valuation/companies/{company_id}/runs/{run_id}` ao selecionar uma linha do histórico.
- Apresenta ID, empresa, instante de criação, autor, versão do motor, método, ano-base e moeda.
- Expõe os pressupostos originais e o resultado integral em blocos JSON recolhíveis.
- A avaliação selecionada fica visualmente identificada no histórico.
- Após criar uma nova avaliação, o workspace carrega o respetivo snapshot persistido através do endpoint de detalhe.
- A consulta usa a camada API autenticada existente, com cookies HttpOnly, refresh e proteção CSRF conforme aplicável.

## Segurança e integridade

- A leitura continua company-scoped; o backend devolve 404 para runs inexistentes ou pertencentes a outra empresa.
- O detalhe é read-only e recupera o snapshot persistido.
- Não recalcula avaliações, não altera pressupostos nem resultados, não introduz migrações e não acede a Neon/produção.
- Não emite recomendações de investimento; a revisão do analista continua obrigatória.

## Validação

A validação automatizada será executada no GitHub Actions deste pull request. O resultado final e eventuais correções serão registados após a conclusão da CI.
