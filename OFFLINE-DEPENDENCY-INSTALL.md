# Instalação offline de asyncpg e Ruff

## Estado da configuração CI

O projeto já declara `asyncpg` como dependência de execução e `ruff` como dependência de desenvolvimento em `backend/pyproject.toml`. O workflow `.github/workflows/ci.yml` já instala `.[dev]`, verifica a instalação do Ruff, executa `ruff check` e confirma a importação de `asyncpg` no job PostgreSQL. Assim, não é necessária uma alteração adicional ao workflow para estes dois pacotes.

## 1. Preparar os wheels num computador com Internet

O ambiente do ChatGPT usado para executar o projeto não consegue descarregar pacotes diretamente. Num computador com Internet, executa o comando abaixo. Ele descarrega wheels binários para Linux x86_64 e Python 3.13, que correspondem ao ambiente de execução atual do projeto neste chat.

```bash
python -m pip download \
  --dest market-analytics-wheelhouse \
  --only-binary=:all: \
  --no-deps \
  --python-version 3.13 \
  --implementation cp \
  --abi cp313 \
  --abi abi3 \
  --abi none \
  --platform manylinux2014_x86_64 \
  "asyncpg>=0.29" \
  "ruff>=0.6,<1.0"
```

Compacta a pasta `market-analytics-wheelhouse` num ficheiro ZIP e anexa-o à conversa do ChatGPT.

## 2. Instalação neste ambiente

Depois de receber o ZIP, extrair os ficheiros e instalar sem acesso à Internet:

```bash
python -m pip install --no-index --find-links ./market-analytics-wheelhouse "asyncpg>=0.29" "ruff>=0.6,<1.0"
```

## 3. Verificação

A partir da pasta `backend`:

```bash
python -m ruff --version
python -c "import asyncpg; print(asyncpg.__version__)"
python -m ruff check --output-format=github app tests
python -m compileall -q app tests
pytest -q
```

A suite completa só será considerada validada depois de todos os comandos terminarem e o resultado integral do `pytest` ser analisado. A instalação offline não executa migrações nem estabelece ligações à Neon.
