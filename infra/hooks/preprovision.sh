#!/bin/bash

# Azure Developer CLI Pre-Provision Hook
# Automates Service Principal creation and environment setup for PostgreSQL AAD Admin
# This script runs automatically before 'azd provision'

set -e

echo ""
echo "=========================================="
echo "Pre-Provision Hook: Setting up AAD Admin"
echo "=========================================="

# Get environment name from azd
ENV_NAME="${AZURE_ENV_NAME}"
if [ -z "$ENV_NAME" ]; then
  echo "Error: AZURE_ENV_NAME is not set. This script should be run via azd."
  exit 1
fi

# Set default location if not already set
if [ -z "$AZURE_LOCATION" ]; then
  DEFAULT_LOCATION="canadacentral"
  echo "Setting default location: $DEFAULT_LOCATION"
  azd env set AZURE_LOCATION "$DEFAULT_LOCATION"
  AZURE_LOCATION="$DEFAULT_LOCATION"
fi

# Set resource group name convention
RESOURCE_GROUP="rg-$ENV_NAME"
echo "Resource Group: $RESOURCE_GROUP"
azd env set AZURE_RESOURCE_GROUP "$RESOURCE_GROUP"

# Create Service Principal for PostgreSQL AAD Administrator
echo ""
echo "Creating/retrieving Service Principal for PostgreSQL AAD Admin..."
SP_NAME="sp-postgres-admin-$ENV_NAME"
echo "Service Principal: $SP_NAME"

# Check if SP already exists
EXISTING_SP=$(az ad sp list --display-name "$SP_NAME" --query "[0].id" -o tsv 2>/dev/null || echo "")

if [ -n "$EXISTING_SP" ]; then
  echo "Service Principal '$SP_NAME' already exists."
  SP_OBJECT_ID="$EXISTING_SP"
  SP_APP_ID=$(az ad sp show --id "$EXISTING_SP" --query "appId" -o tsv)
else
  echo "Creating new Service Principal..."
  SP_APP_ID=$(az ad sp create-for-rbac --name "$SP_NAME" --query "appId" -o tsv)
  echo "Waiting for Service Principal to propagate..."
  sleep 10
  SP_OBJECT_ID=$(az ad sp show --id "$SP_APP_ID" --query "id" -o tsv)
fi

TENANT_ID=$(az account show --query "tenantId" -o tsv)

echo "Service Principal Object ID: $SP_OBJECT_ID"
echo "Service Principal App ID: $SP_APP_ID"
echo "Tenant ID: $TENANT_ID"

# Store AAD admin details in azd environment
azd env set AAD_ADMIN_PRINCIPAL_NAME "$SP_NAME"
azd env set AAD_ADMIN_PRINCIPAL_ID "$SP_OBJECT_ID"
azd env set AAD_ADMIN_TENANT_ID "$TENANT_ID"

# Generate secure PostgreSQL admin password if not already set
if [ -z "$POSTGRES_ADMIN_PASSWORD" ]; then
  echo ""
  echo "Generating secure PostgreSQL admin password..."
  POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
  azd env set POSTGRES_ADMIN_PASSWORD "$POSTGRES_PASSWORD" --no-prompt
  echo "PostgreSQL password generated and stored securely."
else
  echo ""
  echo "Using existing PostgreSQL admin password from environment."
fi

echo ""
echo "=========================================="
echo "Pre-Provision Hook: Complete"
echo "=========================================="
echo "Environment variables set:"
echo "  - AZURE_LOCATION: $AZURE_LOCATION"
echo "  - AZURE_RESOURCE_GROUP: $RESOURCE_GROUP"
echo "  - AAD_ADMIN_PRINCIPAL_NAME: $SP_NAME"
echo "  - AAD_ADMIN_PRINCIPAL_ID: $SP_OBJECT_ID"
echo "  - AAD_ADMIN_TENANT_ID: $TENANT_ID"
echo "  - POSTGRES_ADMIN_PASSWORD: *** (hidden)"
echo "=========================================="
echo ""
