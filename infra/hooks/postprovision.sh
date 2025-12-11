#!/bin/bash

# Azure Developer CLI Post-Provision Hook
# Creates a service principal for database migrations with proper PostgreSQL AAD access
# This script runs automatically after 'azd provision'

set -e

echo ""
echo "=========================================="
echo "Post-Provision Hook: Migration Service Principal Setup"
echo "=========================================="

# Get environment variables from azd
ENV_NAME="${AZURE_ENV_NAME}"
RESOURCE_GROUP=$(azd env get-values --output json | jq -r '.AZURE_RESOURCE_GROUP')
POSTGRES_FQDN=$(azd env get-values --output json | jq -r '.POSTGRES_FQDN')
POSTGRES_DB=$(azd env get-values --output json | jq -r '.POSTGRES_DB // "postgres"')
MANAGED_IDENTITY_CLIENT_ID=$(azd env get-values --output json | jq -r '.MANAGED_IDENTITY_CLIENT_ID')
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

if [ -z "$ENV_NAME" ] || [ -z "$RESOURCE_GROUP" ] || [ -z "$POSTGRES_FQDN" ]; then
  echo "Error: Required environment variables not found"
  exit 1
fi

echo "Environment: $ENV_NAME"
echo "Resource Group: $RESOURCE_GROUP"
echo "PostgreSQL FQDN: $POSTGRES_FQDN"
echo "Database: $POSTGRES_DB"

SP_NAME="sp-${ENV_NAME}-migration"
EXISTING_SP=$(az ad sp list --display-name "$SP_NAME" --query "[0].appId" -o tsv)

if [ -n "$EXISTING_SP" ]; then
  echo ""
  echo "Migration service principal already exists: $SP_NAME"
  echo "Using existing credentials from azd environment"
  APP_ID="$EXISTING_SP"
  SP_PASSWORD=$(azd env get-value MIGRATION_SP_PASSWORD)
  TENANT_ID=$(azd env get-value MIGRATION_SP_TENANT_ID)
  
  if [ -z "$SP_PASSWORD" ] || [ -z "$TENANT_ID" ]; then
    echo "Error: Existing SP found but credentials not in azd env. Please set MIGRATION_SP_PASSWORD and MIGRATION_SP_TENANT_ID manually."
    exit 1
  fi
else
  echo ""
  echo "Creating migration service principal: $SP_NAME"
  SP_OUTPUT=$(az ad sp create-for-rbac \
    --name "$SP_NAME" \
    --role "Contributor" \
    --scopes "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP" \
    --query "{appId: appId, password: password, tenant: tenant}" \
    -o json)
  APP_ID=$(echo "$SP_OUTPUT" | jq -r '.appId')
  SP_PASSWORD=$(echo "$SP_OUTPUT" | jq -r '.password')
  TENANT_ID=$(echo "$SP_OUTPUT" | jq -r '.tenant')
  echo "Service Principal created successfully"
  echo "  App ID: $APP_ID"
  
  # Store new SP credentials in azd environment
  azd env set MIGRATION_SP_APP_ID "$APP_ID" --no-prompt
  azd env set MIGRATION_SP_PASSWORD "$SP_PASSWORD" --no-prompt
  azd env set MIGRATION_SP_TENANT_ID "$TENANT_ID" --no-prompt
  
  echo ""
  echo "✓ Service principal credentials stored in azd environment"
fi

# Get the service principal object ID
SP_OBJECT_ID=$(az ad sp show --id "$APP_ID" --query id -o tsv)

echo ""
echo "Configuring PostgreSQL AAD access for migration service principal..."

# Grant the service principal AAD admin rights on PostgreSQL
# This allows it to create database roles and manage permissions
POSTGRES_SERVER_NAME=$(echo "$POSTGRES_FQDN" | cut -d'.' -f1)

echo "Adding service principal as PostgreSQL AAD admin..."
az postgres flexible-server microsoft-entra-admin create \
  --resource-group "$RESOURCE_GROUP" \
  --server-name "$POSTGRES_SERVER_NAME" \
  --object-id "$SP_OBJECT_ID" \
  --display-name "$SP_NAME" \
  --type ServicePrincipal \
  || echo "Note: Service principal may already be an AAD admin"

echo ""
echo "Granting UAMI database role for app runtime..."

if ! command -v psql >/dev/null 2>&1; then
  echo "Error: psql is required to grant database roles. Please install psql (PostgreSQL client)."
  exit 1
fi

# Get AAD token for the SP to connect to PostgreSQL
# Using OAuth client credentials flow directly
AAD_TOKEN=$(curl -s -X POST "https://login.microsoftonline.com/$TENANT_ID/oauth2/v2.0/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=$APP_ID" \
  -d "client_secret=$SP_PASSWORD" \
  -d "scope=https://ossrdbms-aad.database.windows.net/.default" \
  -d "grant_type=client_credentials" | jq -r '.access_token')

if [ -z "$AAD_TOKEN" ]; then
  echo "Error: Failed to obtain AAD token for PostgreSQL."
  exit 1
fi

export PGPASSWORD="$AAD_TOKEN"

# Create UAMI role and grant database-level privileges
psql "host=$POSTGRES_FQDN dbname=$POSTGRES_DB user=$SP_NAME sslmode=require" \
  -v ON_ERROR_STOP=1 \
  -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '$MANAGED_IDENTITY_CLIENT_ID') THEN CREATE ROLE \"$MANAGED_IDENTITY_CLIENT_ID\" WITH LOGIN; END IF; ALTER ROLE \"$MANAGED_IDENTITY_CLIENT_ID\" CREATEDB CREATEROLE; GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO \"$MANAGED_IDENTITY_CLIENT_ID\"; END \$\$;"

echo "✓ UAMI granted database-level privileges"

# Grant schema and table-level privileges
echo "Granting schema and table-level privileges to UAMI..."
psql "host=$POSTGRES_FQDN dbname=$POSTGRES_DB user=$SP_NAME sslmode=require" \
  -v ON_ERROR_STOP=1 <<EOF
-- Grant schema usage
GRANT USAGE ON SCHEMA public TO "$MANAGED_IDENTITY_CLIENT_ID";

-- Grant privileges on all existing tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "$MANAGED_IDENTITY_CLIENT_ID";

-- Grant privileges on all sequences (for auto-increment)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "$MANAGED_IDENTITY_CLIENT_ID";

-- Set default privileges for future tables created by the SP
ALTER DEFAULT PRIVILEGES FOR ROLE "$SP_NAME" IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "$MANAGED_IDENTITY_CLIENT_ID";
ALTER DEFAULT PRIVILEGES FOR ROLE "$SP_NAME" IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO "$MANAGED_IDENTITY_CLIENT_ID";
EOF

echo ""
echo "✓ UAMI granted schema and table-level privileges for runtime access"

echo ""
echo "=========================================="
echo "Post-Provision Hook: Complete"
echo "=========================================="
echo ""
echo "Migration service principal configured:"
echo "  - Name: $SP_NAME"
echo "  - App ID: $APP_ID"
echo "  - Object ID: $SP_OBJECT_ID"
echo ""
echo "For GitHub Actions, add these secrets:"
echo "  MIGRATION_SP_APP_ID: $APP_ID"
echo "  MIGRATION_SP_PASSWORD: <stored in azd environment>"
echo "  MIGRATION_SP_TENANT_ID: <stored in azd environment>"
echo ""
echo "To retrieve credentials:"
echo "  azd env get-values --output json | jq -r '.MIGRATION_SP_PASSWORD'"
echo "  azd env get-values --output json | jq -r '.MIGRATION_SP_TENANT_ID'"
echo "=========================================="
echo ""
