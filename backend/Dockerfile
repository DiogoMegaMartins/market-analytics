FROM python:3.12.16-slim-trixie AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --home-dir /app app
COPY pyproject.toml ./
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
RUN python -m pip install --upgrade pip 'setuptools>=78.1.1' \
    && python -m pip install . \
    && find /usr/local/lib/python3.12/ensurepip/_bundled -maxdepth 1 -type f -name 'setuptools-*.whl' -delete \
    && test -z "$(find /usr/local/lib/python3.12/ensurepip/_bundled -maxdepth 1 -type f -name 'setuptools-*.whl' -print -quit)" \
    && python -c 'from importlib.metadata import version, distributions; v=version("setuptools"); parts=tuple(int(p) for p in v.split(".")[:3]); assert parts >= (78, 1, 1), f"Vulnerable setuptools version: {v}"; old=[(d.version, str(d._path)) for d in distributions() if (d.metadata.get("Name") or "").lower() == "setuptools" and tuple(int(p) for p in d.version.split(".")[:3]) < (78, 1, 1)]; assert not old, f"Old setuptools distributions remain: {old}"; print(f"setuptools={v}; no vulnerable distribution remains")'

USER app
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
