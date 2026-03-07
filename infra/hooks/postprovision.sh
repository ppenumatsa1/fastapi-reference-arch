#!/bin/bash

# Azure Developer CLI Post-Provision Hook
# Configures PostgreSQL Entra admin and grants runtime UAMI database privileges.

set -euo pipefail

echo ""
echo "=========================================="
echo "Post-Provision Hook: Database Principal Setup"
echo "=========================================="

ENV_NAME="${AZURE_ENV_NAME}"
VALUES=$(azd env get-values --output json)

RESOURCE_GROUP=$(echo "$VALUES" | jq -r '.AZURE_RESOURCE_GROUP')
POSTGRES_FQDN=$(echo "$VALUES" | jq -r '.POSTGRES_FQDN')
POSTGRES_SERVER_NAME=$(echo "$VALUES" | jq -r '.POSTGRES_SERVER_NAME')
POSTGRES_DB=$(echo "$VALUES" | jq -r '.POSTGRES_DB // "postgres"')
POSTGRES_ENTRA_ADMIN_OBJECT_ID=$(echo "$VALUES" | jq -r '.POSTGRES_ENTRA_ADMIN_OBJECT_ID // empty')
POSTGRES_ENTRA_ADMIN_NAME=$(echo "$VALUES" | jq -r '.POSTGRES_ENTRA_ADMIN_NAME // empty')
POSTGRES_ENTRA_ADMIN_TYPE=$(echo "$VALUES" | jq -r '.POSTGRES_ENTRA_ADMIN_TYPE // "User"')
MANAGED_IDENTITY_NAME=$(echo "$VALUES" | jq -r '.MANAGED_IDENTITY_NAME // empty')

if [ -z "$ENV_NAME" ] || [ -z "$RESOURCE_GROUP" ] || [ -z "$POSTGRES_FQDN" ] || [ -z "$POSTGRES_SERVER_NAME" ]; then
  echo "Error: Required environment variables not found"
  exit 1
fi

if [ -z "$POSTGRES_ENTRA_ADMIN_OBJECT_ID" ] || [ -z "$POSTGRES_ENTRA_ADMIN_NAME" ] || [ -z "$MANAGED_IDENTITY_NAME" ]; then
  echo "Error: Missing PostgreSQL Entra admin or managed identity metadata in azd env."
  exit 1
fi

echo "Environment: $ENV_NAME"
echo "Resource Group: $RESOURCE_GROUP"
echo "PostgreSQL Server: $POSTGRES_SERVER_NAME"
echo "PostgreSQL FQDN: $POSTGRES_FQDN"
echo "Database: $POSTGRES_DB"
echo "Entra Admin: $POSTGRES_ENTRA_ADMIN_NAME ($POSTGRES_ENTRA_ADMIN_TYPE)"
echo "Runtime Principal: $MANAGED_IDENTITY_NAME"

echo ""
echo "Ensuring psql is available..."
if ! command -v psql >/dev/null 2>&1; then
  echo "Error: psql is required to grant database roles. Please install psql (PostgreSQL client)."
  exit 1
fi

echo "Ensuring PostgreSQL Entra admin is configured..."
EXISTING_ADMIN=$(az postgres flexible-server microsoft-entra-admin list \
  --resource-group "$RESOURCE_GROUP" \
  --server-name "$POSTGRES_SERVER_NAME" \
  --query "[?objectId=='$POSTGRES_ENTRA_ADMIN_OBJECT_ID'] | [0].objectId" \
  -o tsv 2>/dev/null || true)

if [ -z "$EXISTING_ADMIN" ]; then
  az postgres flexible-server microsoft-entra-admin create \
    --resource-group "$RESOURCE_GROUP" \
    --server-name "$POSTGRES_SERVER_NAME" \
    --display-name "$POSTGRES_ENTRA_ADMIN_NAME" \
    --object-id "$POSTGRES_ENTRA_ADMIN_OBJECT_ID" \
    --type "$POSTGRES_ENTRA_ADMIN_TYPE" \
    >/dev/null
fi

POSTGRES_AAD_TOKEN=$(az account get-access-token --resource-type oss-rdbms --query accessToken -o tsv)
export PGPASSWORD="$POSTGRES_AAD_TOKEN"

echo "Creating or updating runtime principal grants..."
psql "host=$POSTGRES_FQDN dbname=$POSTGRES_DB user=$POSTGRES_ENTRA_ADMIN_NAME sslmode=require" \
  -v ON_ERROR_STOP=1 <<EOF
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '$MANAGED_IDENTITY_NAME') THEN
    PERFORM pgaadauth_create_principal('$MANAGED_IDENTITY_NAME', false, false);
  END IF;
END
\$\$;

GRANT CONNECT ON DATABASE $POSTGRES_DB TO "$MANAGED_IDENTITY_NAME";
GRANT USAGE ON SCHEMA public TO "$MANAGED_IDENTITY_NAME";
GRANT CREATE ON SCHEMA public TO "$MANAGED_IDENTITY_NAME";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "$MANAGED_IDENTITY_NAME";
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "$MANAGED_IDENTITY_NAME";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "$MANAGED_IDENTITY_NAME";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO "$MANAGED_IDENTITY_NAME";
EOF

echo ""
echo "✓ Runtime Entra principal configured"
echo "=========================================="
echo "Post-Provision Hook: Complete"
echo "=========================================="
echo ""
