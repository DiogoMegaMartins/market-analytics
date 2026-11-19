#!/usr/bin/env python3
"""Parse a PostgreSQL URL into libpq environment values and a private pgpass file."""
import os
import sys
from urllib.parse import parse_qs, unquote, urlsplit

if len(sys.argv) != 3:
    raise SystemExit("usage: pg-uri-to-env.py POSTGRES_URL PGPASS_FILE")
url, passfile = sys.argv[1:]
parsed = urlsplit(url)
if parsed.scheme not in {"postgresql", "postgresql+asyncpg"}:
    raise SystemExit("DATABASE URL must use PostgreSQL")
if not parsed.hostname or not parsed.path.strip("/"):
    raise SystemExit("DATABASE URL must include host and database name")
user = unquote(parsed.username or "")
password = unquote(parsed.password or "")
database = unquote(parsed.path.lstrip("/"))
host = parsed.hostname
port = str(parsed.port or 5432)
query = parse_qs(parsed.query)
sslmode = query.get("sslmode", [""])[0]
if sslmode and sslmode not in {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}:
    raise SystemExit("Unsupported PostgreSQL sslmode")

def pgpass_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(":", "\\:").replace("\n", "")

with open(passfile, "w", encoding="utf-8") as handle:
    handle.write(":".join(pgpass_escape(v) for v in (host, port, database, user, password)) + "\n")
os.chmod(passfile, 0o600)
for value in (host, port, user, database, sslmode):
    sys.stdout.buffer.write(value.encode() + b"\0")
