# Sprint 4.2.1 — Evidence Review Workspace

## Objetivo

Criar uma primeira interface de investigação para navegar por documentos SEC persistidos, consultar secções extraídas, executar a extração determinística de passagens candidatas, guardar candidatos e submeter decisões de revisão humana.

## Implementação

### API

Foram acrescentados endpoints de leitura sobre os modelos de evidência existentes:

- `GET /api/v1/business-quality/companies/{company_id}/source-documents`
- `GET /api/v1/business-quality/source-documents/{document_id}/sections`
- `GET /api/v1/business-quality/companies/{company_id}/evidence-candidates`
- `GET /api/v1/business-quality/evidence-candidates/{candidate_id}`

Os endpoints de criação, extração e revisão existentes são reutilizados. A API de listagem nunca devolve os bytes originais do documento. O detalhe apresenta documento, secção, passagem, hashes e histórico de revisão.

### Frontend

Nova rota Next.js: `/research/evidence`.

Funcionalidades:

1. Carregar documentos SEC através do UUID da empresa.
2. Selecionar documento e secção persistida.
3. Consultar um excerto do contexto original.
4. Executar extração de passagens candidatas.
5. Consultar avisos heurísticos de possíveis contradições.
6. Guardar passagens para revisão independente.
7. Filtrar candidatos por estado.
8. Consultar detalhe, fonte SEC, secção e cadeia de eventos.
9. Verificar, rejeitar ou marcar como substituída, com comentário obrigatório.

A interface mostra explicitamente que `VERIFIED` representa uma decisão do fluxo de revisão e não uma garantia de verdade nem uma pontuação de investimento.

### Configuração de ligação

- `NEXT_PUBLIC_API_BASE_URL` define a base URL da API no frontend.
- `CORS_ALLOWED_ORIGINS` configura origens autorizadas no backend; por omissão permite os dois hosts locais do Next.js.

## Regras metodológicas

- A extração não verifica afirmações nem atribui pontuações.
- O candidato é persistido com estado inicial `CANDIDATE`.
- O criador não pode rever o próprio candidato.
- Uma decisão requer comentário e fica registada no histórico hash-linked existente.
- A interface expõe a fonte e as datas disponíveis para permitir revisão contextual.
- A UI não recalcula nem altera avaliações Business Quality.

## Validação

- `pytest -q`: 107 testes passaram.
- `compileall`: passou.
- Importação FastAPI: passou; 38 rotas registadas (incluindo documentação e health checks).
- Verificação dos quatro novos endpoints: passou.
- `alembic upgrade head --sql`: gerado com sucesso até `0009_bq_evidence_audit_pit`.
- A sintaxe TSX foi verificada com transpilation do compilador TypeScript. A instalação de dependências npm excedeu o tempo limite; não foi possível executar `next build` nem uma verificação completa de tipos com as dependências React/Next.js.
- Não foi executada uma migração numa instância PostgreSQL real nem um fluxo end-to-end com SEC live.

## Limitações e segurança

- Os UUIDs da empresa e IDs de intervenientes são introduzidos manualmente.
- Ainda não existe autenticação, RBAC, autorização por tenant ou proteção IDOR; não expor a API/UI publicamente.
- O CORS local é configurável, mas as origens de produção devem ser explicitamente definidas.
- Os documentos continuam armazenados em PostgreSQL `BYTEA` no MVP.
- A extração e deteção de contradições continuam heurísticas.
- A interface requer documentos e secções previamente persistidos; não faz download live da SEC.

## Próximos passos

1. Autenticação e RBAC com identidade real de analistas/revisores.
2. Pesquisa de empresas por ticker/nome em vez de UUID manual.
3. Visualização documental paginada e PDF/HTML original com localização precisa.
4. Integração com object storage versionado.
5. Testes end-to-end com PostgreSQL e documentos reais SEC.
