#!/bin/bash

# Azure Bicep Provisioning Script
# This script automates the creation of Azure resources for the FastAPI app
# Usage: ./provision.sh <environment-name> [location]

set -e

# Default values
DEFAULT_LOCATION="canadacentral"

# Parse arguments
ENV_NAME="${1}"
LOCATION="${2:-$DEFAULT_LOCATION}"

# Validate required arguments
if [ -z "$ENV_NAME" ]; then
  echo "Error: Environment name is required."
  echo "Usage: ./provision.sh <environment-name> [location]"
  echo "Example: ./provision.sh dev canadacentral"
  exit 1
fi

echo "=========================================="
echo "Azure Bicep Provisioning Script"
echo "=========================================="
echo "Environment: $ENV_NAME"
echo "Location: $LOCATION"
echo "=========================================="

# Step 1: Create or reuse azd environment
echo ""
echo "[Step 1/8] Creating azd environment..."
if azd env list 2>&1 | grep -q "$ENV_NAME"; then
  echo "Environment '$ENV_NAME' already exists. Selecting it..."
  azd env select "$ENV_NAME"
else
  echo "Creating new environment '$ENV_NAME'..."
  azd env new "$ENV_NAME"
fi

# Set location in azd environment
echo "Setting location to $LOCATION..."
azd env set AZURE_LOCATION "$LOCATION"

# Step 2: Create Resource Group
echo ""
echo "[Step 2/8] Creating Resource Group..."
RESOURCE_GROUP="rg-$ENV_NAME"
echo "Resource Group: $RESOURCE_GROUP"

if az group exists -n "$RESOURCE_GROUP" | grep -q "true"; then
  echo "Resource Group '$RESOURCE_GROUP' already exists."
else
  echo "Creating Resource Group '$RESOURCE_GROUP' in $LOCATION..."
  az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
fi

# Store in azd environment
azd env set AZURE_RESOURCE_GROUP "$RESOURCE_GROUP"

# Step 3: Create Service Principal for AAD Administrator
echo ""
echo "[Step 3/8] Creating Service Principal for PostgreSQL AAD Admin..."
SP_NAME="sp-postgres-admin-$ENV_NAME"
echo "Service Principal: $SP_NAME"

# Check if SP already exists
EXISTING_SP=$(az ad sp list --display-name "$SP_NAME" --query "[0].id" -o tsv 2>/dev/null || echo "")

if [ -n "$EXISTING_SP" ]; then
  echo "Service Principal '$SP_NAME' already exists."
  SP_OBJECT_ID=$(az ad sp show --id "$EXISTING_SP" --query "id" -o tsv)
  SP_APP_ID=$(az ad sp show --id "$EXISTING_SP" --query "appId" -o tsv)
else
  echo "Creating new Service Principal '$SP_NAME'..."
  SP_JSON=$(az ad sp create-for-rbac --name "$SP_NAME" --skip-assignment --output json)
  SP_APP_ID=$(echo "$SP_JSON" | jq -r '.appId')
  
  # Wait for SP propagation
  echo "Waiting for Service Principal to propagate..."
  sleep 30
  
  SP_OBJECT_ID=$(az ad sp show --id "$SP_APP_ID" --query "id" -o tsv)
fi

TENANT_ID=$(az account show --query "tenantId" -o tsv)

echo "Service Principal Object ID: $SP_OBJECT_ID"
echo "Service Principal App ID: $SP_APP_ID"
echo "Tenant ID: $TENANT_ID"

# Store in azd environment
azd env set AAD_ADMIN_OBJECT_ID "$SP_OBJECT_ID"
azd env set AAD_ADMIN_TENANT_ID "$TENANT_ID"

# Step 4: Update main.parameters.json
echo ""
echo "[Step 4/6] Updating main.parameters.json with AAD administrator details..."
PARAMS_FILE="./infra/bicep/main.parameters.json"

# Update aadAdministrator object
jq --arg principalName "$SP_NAME" \
   --arg objectId "$SP_OBJECT_ID" \
   --arg tenantId "$TENANT_ID" \
   '.parameters.aadAdministrator.value.principalName = $principalName |
    .parameters.aadAdministrator.value.principalType = "ServicePrincipal" |
    .parameters.aadAdministrator.value.principalId = $objectId |
    .parameters.aadAdministrator.value.objectId = $objectId | 
    .parameters.aadAdministrator.value.tenantId = $tenantId' \
   "$PARAMS_FILE" > "$PARAMS_FILE.tmp" && mv "$PARAMS_FILE.tmp" "$PARAMS_FILE"

# Update location
jq --arg location "$LOCATION" \
   '.parameters.location.value = $location' \
   "$PARAMS_FILE" > "$PARAMS_FILE.tmp" && mv "$PARAMS_FILE.tmp" "$PARAMS_FILE"

# Update environmentName
jq --arg envName "$ENV_NAME" \
   '.parameters.environmentName.value = $envName' \
   "$PARAMS_FILE" > "$PARAMS_FILE.tmp" && mv "$PARAMS_FILE.tmp" "$PARAMS_FILE"

echo "Updated main.parameters.json successfully."

# Step 5: Generate secure password for PostgreSQL
echo ""
echo "[Step 5/6] Generating secure PostgreSQL admin password..."
POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
echo "PostgreSQL password generated and will be stored securely in azd environment."
azd env set POSTGRES_ADMIN_PASSWORD "$POSTGRES_PASSWORD"

# Step 6: Run Provisioning with VNet Integration
echo ""
echo "[Step 6/6] Running azd provision with PostgreSQL VNet integration..."
echo "This will create all Azure resources. This may take 5-10 minutes..."
echo "PostgreSQL will be deployed with private access (VNet integration) - no public IPs needed!"

# Run azd provision
azd provision --no-prompt

# Display final outputs
echo ""
echo "=========================================="
echo "Provisioning Complete!"
echo "=========================================="
echo ""
echo "Azure Resources:"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Location: $LOCATION"
echo ""

# Retrieve outputs from azd
REGISTRY_ENDPOINT=$(azd env get-value AZURE_CONTAINER_REGISTRY_ENDPOINT 2>/dev/null || echo "N/A")
CONTAINER_APP_FQDN=$(azd env get-value CONTAINER_APP_FQDN 2>/dev/null || echo "N/A")
POSTGRES_FQDN=$(azd env get-value POSTGRES_FQDN 2>/dev/null || echo "N/A")

echo "Service Endpoints:"
echo "  Container Registry: $REGISTRY_ENDPOINT"
echo "  Container App: https://$CONTAINER_APP_FQDN"
echo "  PostgreSQL Server: $POSTGRES_FQDN"
echo ""
echo "Environment variables stored in azd environment '$ENV_NAME':"
echo "  AZURE_LOCATION"
echo "  AZURE_RESOURCE_GROUP"
echo "  AAD_ADMIN_OBJECT_ID"
echo "  AAD_ADMIN_TENANT_ID"
echo "  POSTGRES_ADMIN_PASSWORD (secret)"
echo "  AZURE_CONTAINER_REGISTRY_ENDPOINT"
echo "  CONTAINER_APP_FQDN"
echo "  POSTGRES_FQDN"
echo ""
echo "Network Configuration:"
echo "  ✓ PostgreSQL uses VNet Integration (Private Access)"
echo "  ✓ Container Apps can access PostgreSQL directly via private IP"
echo "  ✓ No public IP addresses or firewall rules needed!"
echo ""
echo "Next Steps:"
echo "  1. Build and push your container image:"
echo "     az acr build --registry <registry-name> --image fastapi-app:latest ."
echo "  2. Update Container App to use your image:"
echo "     az containerapp update --name <app-name> --resource-group $RESOURCE_GROUP --image <registry-name>.azurecr.io/fastapi-app:latest"
echo "  3. Run database migrations:"
echo "     ./infra/scripts/run_migrations.sh"
echo ""
echo "=========================================="
