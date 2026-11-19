# Database migrations

Alembic is configured for asynchronous PostgreSQL connections. Run commands from
`backend/` after installing the project dependencies and setting `DATABASE_URL`:

```bash
alembic upgrade head
alembic current
alembic revision --autogenerate -m "describe change"
```

The initial revision is intentionally empty. Domain tables must be introduced by
reviewed, version-controlled migrations; do not create production tables with
`Base.metadata.create_all()`.
