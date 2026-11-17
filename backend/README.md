# Market Analytics backend

## Local setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e ".[dev]"
cp .env.example .env
```

Start PostgreSQL from the repository root with `docker compose up -d db`.
Then, from `backend/`, run `alembic upgrade head` and `uvicorn app.main:app --reload`.

Health endpoints:

- `GET /health/live`: process liveness; deliberately does not depend on PostgreSQL.
- `GET /health/ready`: readiness; returns HTTP 503 if PostgreSQL cannot execute `SELECT 1`.

For staging/production, provide a unique `SECRET_KEY` of at least 32 characters,
set `APP_DEBUG=false`, and use externally managed secrets. The example credentials
in `docker-compose.yml` are for local development only.

Install development tools from `backend/` with `python -m pip install -e ".[dev]"`.
This installs Ruff as a development dependency. The Ruff configuration enables the
`I` ruleset so import ordering is checked in addition to the default lint rules.
Run checks from `backend/` with:

```bash
python -m ruff --version
python -m ruff check app tests
python -m compileall -q app tests
pytest -q
```

To apply safe automatic lint fixes (including import sorting) locally, run
`python -m ruff check --fix app tests`, review the diff, and then rerun
`python -m ruff check app tests`. CI only checks; it never rewrites source files.

## Asset identity and SEC endpoints

The identity registry currently exposes company/asset creation and search under `/api/v1`. SEC lookup endpoints resolve ticker candidates and retrieve official CIK submission identity. SEC resolution does not automatically create or verify a database record. Configure `SEC_USER_AGENT` with an identifiable application name and a valid contact email before making SEC requests.

Run migrations from `backend/` with `alembic upgrade head` after PostgreSQL is available.
