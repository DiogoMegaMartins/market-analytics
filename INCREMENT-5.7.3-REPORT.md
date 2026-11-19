# Incremento 5.7.3 — correções Ruff

## Alterações
- `backend/tests/unit/test_sec_resilience.py`: removido o import não utilizado `asyncio`.
- `FakeAsyncClient.responses` e `FakeAsyncClient.calls` passaram a ter anotações `ClassVar`, explicitando que são estado partilhado intencionalmente pela classe e resolvendo a regra Ruff `RUF012`.
- `backend/tests/unit/test_thesis_engine.py`: removido o import não utilizado `Decimal`.

## Validação executada
- `py_compile` nos dois ficheiros alterados: passou.
- `pytest tests/unit/test_sec_resilience.py tests/unit/test_thesis_engine.py -q`: 18 passaram.
- Ruff não foi executado neste ambiente porque o módulo `ruff` não está instalado. A validação final do Ruff deve ser feita no ambiente local do projeto.
- Nenhuma migração ou base de dados foi alterada.
