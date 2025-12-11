#!/bin/bash

# Azure Developer CLI Pre-Provision Hook
# Sets up environment variables for deployment
# This script runs automatically before 'azd provision'

set -e

echo ""
echo "=========================================="
echo "Pre-Provision Hook: Environment Setup"
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

# Set admin user (aligns with bicep default)
POSTGRES_ADMIN_USER="${POSTGRES_ADMIN_USER:-aad_admin}"
azd env set POSTGRES_ADMIN_USER "$POSTGRES_ADMIN_USER"

echo ""
echo "Note: Post-provision will configure the dedicated app DB user with these credentials"

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

# Generate dedicated app DB user credentials if missing
TODO_DB_USER="${TODO_DB_USER:-todo_user}"
azd env set TODO_DB_USER "$TODO_DB_USER"

if [ -z "$TODO_DB_PASSWORD" ]; then
  echo ""
  echo "Generating secure password for $TODO_DB_USER..."
  TODO_DB_PASSWORD_GENERATED=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
  azd env set TODO_DB_PASSWORD "$TODO_DB_PASSWORD_GENERATED" --no-prompt
  echo "Todo DB user password generated and stored securely."
else
  echo ""
  echo "Using existing password for $TODO_DB_USER from environment."
fi

echo ""
echo "=========================================="
echo "Pre-Provision Hook: Complete"
echo "=========================================="
echo "Environment variables set:"
echo "  - AZURE_LOCATION: $AZURE_LOCATION"
echo "  - AZURE_RESOURCE_GROUP: $RESOURCE_GROUP"
echo "  - POSTGRES_ADMIN_PASSWORD: *** (hidden)"
echo "=========================================="
echo ""
