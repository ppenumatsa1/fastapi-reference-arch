#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$ROOT_DIR"

export PYTHONPATH="$ROOT_DIR${PYTHONPATH:+:$PYTHONPATH}"

# Prefer project virtual environment for hook execution when available.
if [ -z "${VIRTUAL_ENV:-}" ] && [ -f "$ROOT_DIR/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.venv/bin/activate"
fi

PYTHON_BIN="${PYTHON:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

echo "Running database migrations..."

DB_AUTH_MODE="${DB_AUTH_MODE:-password}"
DATABASE_USER="${DATABASE_USER:-${USER_DB_USER:-user_user}}"
DATABASE_PASSWORD="${DATABASE_PASSWORD:-${USER_DB_PASSWORD:-}}"
DATABASE_HOST="${DATABASE_HOST:-${POSTGRES_FQDN:-localhost}}"
DATABASE_PORT="${DATABASE_PORT:-5432}"
DATABASE_NAME="${DATABASE_NAME:-${POSTGRES_DB:-user_db}}"
POSTGRES_ENTRA_ADMIN_NAME="${POSTGRES_ENTRA_ADMIN_NAME:-}"

AZD_VALUES_JSON='{}'
if command -v azd >/dev/null 2>&1 && [ -n "${AZURE_ENV_NAME:-}" ]; then
  AZD_VALUES_JSON=$(azd env get-values --output json 2>/dev/null || echo '{}')
  if [ "$DB_AUTH_MODE" = "password" ]; then
    DB_AUTH_MODE=$(echo "$AZD_VALUES_JSON" | jq -r '.DB_AUTH_MODE // "password"')
  fi
  if [ -z "$POSTGRES_ENTRA_ADMIN_NAME" ]; then
    POSTGRES_ENTRA_ADMIN_NAME=$(echo "$AZD_VALUES_JSON" | jq -r '.POSTGRES_ENTRA_ADMIN_NAME // empty')
  fi
fi

if [ "$DB_AUTH_MODE" = "aad" ] || [ "$DB_AUTH_MODE" = "entra" ]; then
  if [ "$DATABASE_HOST" = "postgres" ] || [ "$DATABASE_HOST" = "localhost" ]; then
    DB_AUTH_MODE="password"
  else
    if [ -z "$POSTGRES_ENTRA_ADMIN_NAME" ] && command -v azd >/dev/null 2>&1; then
      POSTGRES_ENTRA_ADMIN_NAME=$(azd env get-values --output json 2>/dev/null | jq -r '.POSTGRES_ENTRA_ADMIN_NAME // empty')
    fi

    if [ -n "$POSTGRES_ENTRA_ADMIN_NAME" ]; then
      DATABASE_USER="$POSTGRES_ENTRA_ADMIN_NAME"
    fi

    if ! command -v az >/dev/null 2>&1; then
      echo "Error: az CLI is required for Entra database token acquisition."
      exit 1
    fi

    DATABASE_PASSWORD=$(az account get-access-token --resource-type oss-rdbms --query accessToken -o tsv)
  fi
fi

# Attempt to pull password from Key Vault only for password mode
if [ "$DB_AUTH_MODE" = "password" ] && [ -z "$DATABASE_PASSWORD" ]; then
  VAULT_NAME="${AZURE_KEY_VAULT_NAME:-${KEYVAULT_NAME:-}}"
  if [ -n "$VAULT_NAME" ]; then
    echo "Fetching database password from Key Vault $VAULT_NAME..."
    DATABASE_PASSWORD=$(az keyvault secret show \
      --vault-name "$VAULT_NAME" \
      --name "user-db-password" \
      --query value \
      -o tsv 2>/dev/null || true)
  fi
fi

# Local dev fallback: use compose defaults when pointing at the bundled postgres service
if [ "$DB_AUTH_MODE" = "password" ] && [ -z "$DATABASE_PASSWORD" ] && { [ "$DATABASE_HOST" = "postgres" ] || [ "$DATABASE_HOST" = "localhost" ]; }; then
  DATABASE_PASSWORD="user_pass"
fi

if [ -z "$DATABASE_PASSWORD" ]; then
  echo "Error: database credential token/password could not be resolved for auth mode '$DB_AUTH_MODE'."
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

"$PYTHON_BIN" -m alembic upgrade head

echo "Seeding sample data..."
"$PYTHON_BIN" scripts/seed_data.py

echo "✓ Migrations completed successfully"
