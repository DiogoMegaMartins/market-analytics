# Market Analytics — Increment 5.7.10

## Objetivo
Corrigir os três diagnósticos Ruff `I001` reportados após a versão 5.7.9.

## Alterações
- `backend/app/services/financial_data/sec_company_facts.py`: normalizado o espaçamento no final do bloco de imports antes do comentário de módulo.
- `backend/app/services/metrics/historical.py`: removido o excesso de linhas em branco entre imports e a primeira definição.
- `backend/tests/unit/test_observability.py`: ordenados os imports de terceiros e de primeira parte, mantendo `app.main` e `app.core` no mesmo grupo.

## Validação executada
- `python -m compileall -q app tests`: concluído sem erros.
- `pytest -q --ignore=tests/unit/test_dependencies.py`: **191 passed, 9 skipped**.
- Ruff não foi executado neste ambiente; portanto, esta versão não é certificada como Ruff-clean até confirmação do GitHub Actions.

## Limites
Não foram alterados cálculos financeiros, dados SEC, modelos, migrações, esquema da base de dados ou configuração de Neon. Não foram efetuadas ligações nem escritas em bases de dados.
