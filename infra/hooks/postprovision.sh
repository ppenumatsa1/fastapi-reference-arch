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
POSTGRES_DB=$(azd env get-values --output json | jq -r '.POSTGRES_DB')
MANAGED_IDENTITY_CLIENT_ID=$(azd env get-values --output json | jq -r '.MANAGED_IDENTITY_CLIENT_ID')

if [ -z "$ENV_NAME" ] || [ -z "$RESOURCE_GROUP" ] || [ -z "$POSTGRES_FQDN" ]; then
  echo "Error: Required environment variables not found"
  exit 1
fi

echo "Environment: $ENV_NAME"
echo "Resource Group: $RESOURCE_GROUP"
echo "PostgreSQL FQDN: $POSTGRES_FQDN"
echo "Database: $POSTGRES_DB"

# Check if migration SP already exists
SP_NAME="sp-${ENV_NAME}-migration"
EXISTING_SP=$(az ad sp list --display-name "$SP_NAME" --query "[0].appId" -o tsv)

if [ -n "$EXISTING_SP" ]; then
  echo ""
  echo "Migration service principal already exists: $SP_NAME"
  APP_ID="$EXISTING_SP"
else
  echo ""
  echo "Creating migration service principal: $SP_NAME"
  
  # Create service principal with password
  SP_OUTPUT=$(az ad sp create-for-rbac \
    --name "$SP_NAME" \
    --role "Reader" \
    --scopes "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP" \
    --query "{appId: appId, password: password, tenant: tenant}" \
    -o json)
  
  APP_ID=$(echo "$SP_OUTPUT" | jq -r '.appId')
  SP_PASSWORD=$(echo "$SP_OUTPUT" | jq -r '.password')
  TENANT_ID=$(echo "$SP_OUTPUT" | jq -r '.tenant')
  
  echo "Service Principal created successfully"
  echo "  App ID: $APP_ID"
  
  # Store credentials in azd environment
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
az postgres flexible-server ad-admin create \
  --resource-group "$RESOURCE_GROUP" \
  --server-name "$POSTGRES_SERVER_NAME" \
  --object-id "$SP_OBJECT_ID" \
  --display-name "$SP_NAME" \
  --type ServicePrincipal \
  || echo "Note: Service principal may already be an AAD admin"

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
