# Sprint 4.3.9 — Thesis Versioning & Research Workflow

## Objetivo
Fechar o fluxo visual de revisão de teses, permitindo preparar uma nova versão a partir da versão atual, editar o conteúdo e comparar versões sem alterar o histórico anterior.

## Implementação
- Editor no dashboard `/thesis` para resumo, racional, pressupostos estruturados, riscos e referências de evidência.
- O editor pode ser preenchido a partir da versão atual; a gravação usa `POST /thesis/{thesis_id}/versions` já existente.
- Comparação determinística, no cliente, entre a versão atual e uma versão anterior selecionada. Compara resumo, racional, pressupostos, riscos e referências de evidência.
- Histórico cronológico de versões com data, número de pressupostos e riscos.
- As ligações de evidência continuam associadas à versão onde foram criadas; não são copiadas silenciosamente para a versão seguinte.
- IDs de pressupostos podem ser preservados manualmente quando representam a mesma hipótese. Alterações de identidade devem usar novo ID.

## Decisões e limites
- Não foi introduzida migração de base de dados: o backend já suportava versões imutáveis e criação de nova versão.
- A comparação é textual/estrutural e não declara se uma alteração melhora ou enfraquece a tese.
- Uma nova versão não copia automaticamente evidências da versão anterior. O analista deve voltar a associar evidência relevante, mantendo o contexto temporal.
- A decisão `REVISE` continua a ser um evento explícito do analista. A criação posterior de versão não apaga nem altera esse evento.
- Não existe ainda editor visual granular de cada pressuposto; estes continuam a ser editados em JSON validado pelo backend.

## Validação
- Validar sintaxe TSX e TypeScript num ambiente com dependências instaladas.
- Validar backend e migrações existentes sem alterações de schema.
- Testes E2E e autenticação HTTP requerem ambiente de execução completo.
