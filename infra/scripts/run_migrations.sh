#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$ROOT_DIR"

export PYTHONPATH="$ROOT_DIR${PYTHONPATH:+:$PYTHONPATH}"

echo "Running database migrations..."

# Check if we have migration service principal credentials
if [ -n "${MIGRATION_SP_APP_ID:-}" ] && [ -n "${MIGRATION_SP_PASSWORD:-}" ] && [ -n "${MIGRATION_SP_TENANT_ID:-}" ]; then
  echo "Authenticating with migration service principal..."
  
  # Login with service principal
  az login --service-principal \
    --username "$MIGRATION_SP_APP_ID" \
    --password "$MIGRATION_SP_PASSWORD" \
    --tenant "$MIGRATION_SP_TENANT_ID" \
    --allow-no-subscriptions > /dev/null 2>&1
  
  # Get AAD token for PostgreSQL using the service principal
  echo "Getting AAD token for PostgreSQL..."
  AAD_TOKEN=$(az account get-access-token \
    --resource-type oss-rdbms \
    --query accessToken \
    --output tsv)
  
  if [ -z "$AAD_TOKEN" ]; then
    echo "Error: Failed to get AAD token"
    exit 1
  fi
  
  # Set password to AAD token for psycopg2
  export PGPASSWORD="$AAD_TOKEN"
  
  echo "✓ Authentication successful"
else
  echo "Using default authentication (password or managed identity)"
fi

echo "Running Alembic migrations..."

# Set environment variables for the app config
export DB_AUTH_MODE="password"
export DATABASE_HOST="$POSTGRES_FQDN"
export DATABASE_PORT="5432"
export DATABASE_NAME="$POSTGRES_DB"
export DATABASE_USER="$MIGRATION_SP_APP_ID"
export DATABASE_PASSWORD="$PGPASSWORD"

alembic upgrade head

echo "✓ Migrations completed successfully"
