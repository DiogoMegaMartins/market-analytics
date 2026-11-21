FROM debian:trixie-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv python3-dev build-essential \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml ./
COPY app ./app
RUN python -m pip install --upgrade pip 'setuptools>=78.1.1' \
    && python -m pip install . \
    && python -m pip uninstall -y setuptools \
    && python - <<'PY'
import importlib.util
import shutil
import sysconfig
from pathlib import Path

site_packages = Path(sysconfig.get_paths()["purelib"])
for path in site_packages.glob("pip*"):
    if path.is_dir():
        shutil.rmtree(path)
    elif path.is_file():
        path.unlink()

for path in Path(sysconfig.get_paths()["scripts"]).glob("pip*"):
    path.unlink(missing_ok=True)

assert importlib.util.find_spec("pip") is None, "pip must not be present in the runtime venv"
try:
    from importlib.metadata import version
    version("setuptools")
except Exception as exc:
    from importlib.metadata import PackageNotFoundError
    assert isinstance(exc, PackageNotFoundError), f"Unexpected setuptools metadata error: {exc}"
else:
    raise AssertionError("setuptools must not be present in the runtime venv")
print("Build-only tools removed: pip, setuptools")
PY

FROM debian:trixie-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 ca-certificates zlib1g \
    && apt-get upgrade -y --no-install-recommends \
    && find /usr -type f -name 'setuptools-*.whl' -print -delete \
    && test -z "$(find /usr -type f -name 'setuptools-*.whl' -print -quit)" \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --home-dir /app app

COPY --from=builder /opt/venv /opt/venv
COPY alembic.ini ./
COPY alembic ./alembic

RUN python -c 'from importlib.metadata import version; v=version("setuptools"); parts=tuple(int(p) for p in v.split(".")[:3]); assert parts >= (78, 1, 1), f"Vulnerable setuptools version: {v}"; print(f"Runtime setuptools={v}")'

USER app
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
