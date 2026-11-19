# Incremento 5.7.8 — Ruff import remediation

## Origem

Baseado no pacote `market-analytics-increment-5.7.7-ruff-ci.zip` e no relatório de diagnóstico fornecido após a execução do CI. O relatório apresentado contém ocorrências `I001` (ordenação/formatação de imports).

## Alterações

- Reorganizados imports nos módulos da API, serviços, modelos e testes indicados pelo diagnóstico.
- Normalizada a ordenação dos nomes importados e a separação entre imports standard library, terceiros e internos.
- Movidos para o bloco de imports do módulo os imports tardios em `app/api/v1/endpoints/business_quality.py` que originavam ocorrências `I001` em blocos no meio do ficheiro.
- Mantida a configuração Ruff existente e o job `backend-quality` do GitHub Actions introduzidos no incremento 5.7.7.
- Não foram alteradas regras financeiras, cálculos, modelos de dados, migrações ou configuração Neon.

## Validação executada neste ambiente

- `python -m compileall -q app tests`: passou.
- `pytest -q --ignore=tests/unit/test_dependencies.py`: **191 passed, 9 skipped**.
- A suite completa não foi executada nesta validação; a exclusão é apenas do teste de dependências que anteriormente falhou por ausência de `asyncpg` neste ambiente.
- Ruff não pôde ser executado localmente porque o executável/pacote não está instalado e este ambiente não conseguiu aceder ao PyPI (falha de resolução DNS).

## Estado

Esta versão corrige os blocos de imports indicados no relatório e mantém Ruff obrigatório no CI. **Não é declarada como Ruff-clean** até o job `backend-quality` ser executado com sucesso no GitHub Actions.

## Segurança e dados

Nenhuma ligação ou escrita à Neon foi efetuada. Nenhuma migração foi aplicada. Nenhum dado financeiro ou registo SEC foi alterado.
