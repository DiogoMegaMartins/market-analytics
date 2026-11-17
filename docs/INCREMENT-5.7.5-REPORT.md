# Market Analytics — Increment 5.7.5
## Relatório de correções após o diagnóstico Ruff da versão 5.7.4

### Base
- ZIP de origem: `market-analytics-increment-5.7.4-ruff-remediation.zip`
- Diagnóstico analisado: `Texto colado(2).txt`

### Correções aplicadas
- Corrigida a referência indefinida `reconcile_company_against_reference` no endpoint financeiro, através da importação do serviço de reconciliação existente.
- Corrigida a ausência de `date` em `quarter_derivation.py`.
- Corrigidos imports duplicados e não utilizados em `identity.py`.
- Corrigido o atributo de classe mutável `RETRYABLE_STATUS_CODES` com `ClassVar`.
- Substituídos os aliases `re.I` por `re.IGNORECASE`.
- Removido import não utilizado em `sec_company_facts.py`.
- Alterada a exceção para `TypeError` quando o tipo de `us-gaap` é inválido.
- Reorganizado o registo central de modelos e ordenado `__all__`.
- Corrigidos avisos nos testes: import não utilizado, `dict()` desnecessário, context managers aninhados e condição aninhada.

### Validação executada
- `compileall` em `app` e `tests`: passou.
- `pytest -q --ignore=tests/unit/test_dependencies.py`: **191 passed, 9 skipped**.
- `pytest -q` completo: **191 passed, 9 skipped, 1 failed**. A única falha é `tests/unit/test_dependencies.py`, porque o ambiente de execução não tem o pacote `asyncpg` instalado (`ModuleNotFoundError`). Não foi possível instalar dependências porque o ambiente não tem acesso à Internet.
- Ruff: não executado, porque o executável/pacote Ruff não está instalado e não foi possível instalá-lo sem acesso à Internet.

### Limitações conhecidas
- O diagnóstico contém numerosos avisos `I001` de ordenação/formatação de imports. Algumas áreas foram corrigidas manualmente, mas não é possível certificar que todos os `I001` foram eliminados sem executar Ruff.
- Assim, esta versão não é declarada Ruff-clean.
- Não foram alterados dados financeiros, regras de cálculo, autenticação funcional, proveniência SEC ou migrações da base de dados, salvo as correções explícitas descritas acima.
