#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$ROOT_DIR"

export PYTHONPATH="$ROOT_DIR${PYTHONPATH:+:$PYTHONPATH}"

echo "Running database migrations..."

DATABASE_USER="${DATABASE_USER:-${TODO_DB_USER:-todo_user}}"
DATABASE_PASSWORD="${DATABASE_PASSWORD:-${TODO_DB_PASSWORD:-}}"
DATABASE_HOST="${DATABASE_HOST:-${POSTGRES_FQDN:-localhost}}"
DATABASE_PORT="${DATABASE_PORT:-5432}"
DATABASE_NAME="${DATABASE_NAME:-${POSTGRES_DB:-todo_db}}"

# Attempt to pull password from Key Vault if not provided
if [ -z "$DATABASE_PASSWORD" ]; then
  VAULT_NAME="${AZURE_KEY_VAULT_NAME:-${KEYVAULT_NAME:-}}"
  if [ -n "$VAULT_NAME" ]; then
    echo "Fetching database password from Key Vault $VAULT_NAME..."
    DATABASE_PASSWORD=$(az keyvault secret show \
      --vault-name "$VAULT_NAME" \
      --name "todo-db-password" \
      --query value \
      -o tsv 2>/dev/null || true)
  fi
fi

# Local dev fallback: use compose defaults when pointing at the bundled postgres service
if [ -z "$DATABASE_PASSWORD" ] && { [ "$DATABASE_HOST" = "postgres" ] || [ "$DATABASE_HOST" = "localhost" ]; }; then
  DATABASE_PASSWORD="todo_pass"
fi

if [ -z "$DATABASE_PASSWORD" ]; then
  echo "Error: DATABASE_PASSWORD (or TODO_DB_PASSWORD) is required."
  exit 1
fi

export PGPASSWORD="$DATABASE_PASSWORD"

SSL_QUERY="sslmode=require"
ASYNC_SSL="ssl=require"
if [ "$DATABASE_HOST" = "postgres" ] || [ "$DATABASE_HOST" = "localhost" ]; then
  SSL_QUERY="sslmode=disable"
  ASYNC_SSL="ssl=disable"
fi

if [ -z "${DATABASE_URL:-}" ]; then
  DATABASE_URL="postgresql+psycopg2://${DATABASE_USER}:${DATABASE_PASSWORD}@${DATABASE_HOST}:${DATABASE_PORT}/${DATABASE_NAME}?${SSL_QUERY}"
fi

export DATABASE_URL
export ASYNC_DATABASE_URL="${ASYNC_DATABASE_URL:-postgresql+asyncpg://${DATABASE_USER}:${DATABASE_PASSWORD}@${DATABASE_HOST}:${DATABASE_PORT}/${DATABASE_NAME}?${ASYNC_SSL}}"
export DATABASE_USER DATABASE_PASSWORD DATABASE_HOST DATABASE_PORT DATABASE_NAME

echo "Using host ${DATABASE_HOST} on port ${DATABASE_PORT} as ${DATABASE_USER} against ${DATABASE_NAME}"

# Wait for database to be reachable (helps local docker-compose workflows)
if command -v pg_isready >/dev/null 2>&1; then
  for _ in {1..30}; do
    if pg_isready -h "$DATABASE_HOST" -p "$DATABASE_PORT" -U "$DATABASE_USER" -d "$DATABASE_NAME" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
else
  for _ in {1..30}; do
    if PGPASSWORD="$DATABASE_PASSWORD" psql "host=$DATABASE_HOST port=$DATABASE_PORT user=$DATABASE_USER dbname=$DATABASE_NAME sslmode=${SSL_QUERY#sslmode=}" -c "select 1" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi

alembic upgrade head

echo "Seeding sample data..."
python scripts/seed_data.py

echo "✓ Migrations completed successfully"
