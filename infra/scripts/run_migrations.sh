#!/usr/bin/env bash
set -euo pipefail

# Remember the current default account so we can restore it after SP login
ORIGINAL_SUBSCRIPTION_ID=""
if az account show >/dev/null 2>&1; then
  ORIGINAL_SUBSCRIPTION_ID=$(az account show --query id -o tsv || true)
fi

# Ensure we return to the original account when the script exits
SP_LOGIN_PERFORMED=false
cleanup() {
  if [ "$SP_LOGIN_PERFORMED" = true ]; then
    az logout --username "$MIGRATION_SP_APP_ID" >/dev/null 2>&1 || true
    if [ -n "$ORIGINAL_SUBSCRIPTION_ID" ]; then
      az account set --subscription "$ORIGINAL_SUBSCRIPTION_ID" >/dev/null 2>&1 || true
    fi
  fi
}
trap cleanup EXIT

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
  SP_LOGIN_PERFORMED=true
  
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

# For service principals, use the SP name instead of app ID as username
# Azure PostgreSQL AAD auth requires the service principal display name
SP_NAME="sp-${AZURE_ENV_NAME}-migration"

# Build the connection URL directly with SSL
export DATABASE_URL="postgresql+psycopg2://${SP_NAME}:${PGPASSWORD}@${POSTGRES_FQDN}:5432/${POSTGRES_DB}?sslmode=require"

alembic upgrade head

echo "✓ Migrations completed successfully"
