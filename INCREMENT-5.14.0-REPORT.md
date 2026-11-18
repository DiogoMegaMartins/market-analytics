# Incremento 5.14.0 — Caminhos inequívocos para diferenças de pressupostos

## Objetivo

Eliminar ambiguidades nos caminhos de diferenças de pressupostos quando as chaves JSON contêm pontos, barras ou til.

## Implementação

- O serviço de comparação passa a emitir `json_pointer` em conformidade com RFC 6901 para cada diferença.
- Os caracteres especiais são escapados (`~` para `~0` e `/` para `~1`), preservando a distinção entre segmentos de chaves e índices de arrays.
- O campo legado `path` mantém-se para compatibilidade com consumidores existentes.
- O workspace mostra o JSON Pointer canónico e o caminho legível legado.
- Testes unitários cobrem chaves com pontos, barras e til, incluindo casos em que caminhos pontuados poderiam colidir.
- O contrato de integração PostgreSQL valida a nova propriedade na resposta HTTP.

## Segurança e integridade

- Comparação continua read-only sobre snapshots imutáveis.
- Sem alterações de schema, migrações, Neon ou produção.
- Tenant isolation e compatibilidade entre versões/métodos mantidas.
- Revisão do analista continua obrigatória; nenhuma recomendação de investimento é emitida.

## Validação

A aguardar conclusão do GitHub Actions para este PR.
