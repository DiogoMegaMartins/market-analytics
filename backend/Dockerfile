FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --home-dir /app app
COPY pyproject.toml ./
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
RUN python -m pip install --upgrade pip \
    && python -m pip install . \
    && python -m pip install --upgrade 'setuptools>=78.1.1' \
    && echo "=== SETUPTOOLS: PIP METADATA ===" \
    && python -m pip show setuptools \
    && echo "=== SETUPTOOLS: PYTHON DISTRIBUTIONS ===" \
    && python -c 'from importlib.metadata import distributions; [print("{}=={} | {}".format(d.metadata.get("Name"), d.version, d._path)) for d in distributions() if (d.metadata.get("Name") or "").lower() == "setuptools"]' \
    && echo "=== SETUPTOOLS: METADATA FILES ===" \
    && for dir in /usr/local/lib/python3.12/site-packages /usr/lib/python3/dist-packages; do if [ -d "$dir" ]; then find "$dir" -type f \( -path '*/setuptools-*.dist-info/METADATA' -o -path '*/setuptools-*.egg-info/PKG-INFO' \) -print -exec grep -m1 -i '^Version:' {} \;; fi; done \
    && echo "=== SETUPTOOLS: DEBIAN PACKAGES ===" \
    && (dpkg-query -W -f='${Package} ${Version}\n' '*setuptools*' 2>/dev/null || true)

USER app
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
