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

echo ""
echo "Note: Migration service principal will be created by postprovision hook"

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
echo "  - POSTGRES_ADMIN_PASSWORD: *** (hidden)"
echo "=========================================="
echo ""
