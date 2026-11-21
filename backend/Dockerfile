FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && if dpkg-query -W -f='${Status}' python3-setuptools 2>/dev/null | grep -q 'install ok installed'; then apt-get purge -y python3-setuptools; fi \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --home-dir /app app
COPY pyproject.toml ./
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
RUN python -m pip install --upgrade pip \
    && python -m pip install . \
    && python -m pip uninstall -y setuptools || true
RUN rm -rf /usr/local/lib/python3.12/site-packages/setuptools \
           /usr/local/lib/python3.12/site-packages/setuptools-*.dist-info \
           /usr/local/lib/python3.12/site-packages/setuptools*.egg-info \
           /usr/lib/python3/dist-packages/setuptools \
           /usr/lib/python3/dist-packages/setuptools-*.dist-info \
           /usr/lib/python3/dist-packages/setuptools*.egg-info \
    && python -c 'from importlib.metadata import distributions; found=[(d.metadata.get("Name"), d.version, str(d._path)) for d in distributions() if (d.metadata.get("Name") or "").lower() == "setuptools"]; assert not found, f"setuptools remains in runtime image: {found}"; print("No setuptools distribution remains in runtime image.")'

USER app
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
