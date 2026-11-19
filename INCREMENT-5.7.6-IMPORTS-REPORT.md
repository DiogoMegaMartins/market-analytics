# Incremento 5.7.6 — correção de imports (I001)

## Origem
Relatório `Texto colado(3).txt`, com 71 ocorrências Ruff `I001` distribuídas por 57 caminhos de ficheiro.

## Alterações
- Reorganização dos blocos de imports nos ficheiros identificados no relatório.
- Separação dos grupos standard library, dependências externas e módulos `app`.
- Ordenação dos nomes importados e formatação multiline quando necessário.
- Imports locais dentro de funções mantidos no respetivo âmbito e indentação.
- Sem alterações intencionais à lógica de negócio, cálculos financeiros, regras de investimento ou persistência SEC.

## Validação executada
- `python -m compileall -q app tests`: passou.
- `pytest -q --ignore=tests/unit/test_dependencies.py`: **191 passed, 9 skipped**.

## Limitações
- Ruff não está instalado neste ambiente e não foi possível executá-lo; por isso, esta entrega não é certificada como `ruff check` limpo. A correção foi aplicada com base nos diagnósticos e sugestões I001 do relatório fornecido.
- O teste completo continua condicionado pela dependência `asyncpg` ausente no ambiente. O teste excluído foi `tests/unit/test_dependencies.py`; no histórico da versão 5.7.5, o erro identificado era `ModuleNotFoundError: asyncpg`.
- Os 9 testes ignorados pelo pytest mantêm-se; não foram apresentados como testes aprovados.
- Não foi efetuada qualquer ligação ou escrita na Neon.
