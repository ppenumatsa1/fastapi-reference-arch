#!/bin/bash

# Azure Developer CLI Pre-Provision Hook
# Sets up environment variables for deployment
# This script runs automatically before 'azd provision'

set -e

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Error: required command '$1' not found" >&2
    exit 1
  fi
}

require_command az
require_command azd
require_command jq
require_command openssl

retry() {
  local attempts="$1"
  local delay_seconds="$2"
  shift 2

  local i
  for ((i = 1; i <= attempts; i++)); do
    if "$@"; then
      return 0
    fi
    if [ "$i" -lt "$attempts" ]; then
      sleep "$delay_seconds"
    fi
  done

  return 1
}

get_azd_env_json() {
  azd env get-values --output json 2>/dev/null || echo '{}'
}

get_azd_env_value() {
  local json="$1"
  local key="$2"
  echo "$json" | jq -r --arg key "$key" '.[$key] // empty'
}

ensure_sp() {
  local app_id="$1"
  local sp_object_id

  sp_object_id=$(az ad sp show --id "$app_id" --query id -o tsv 2>/dev/null || true)
  if [ -z "$sp_object_id" ]; then
    az ad sp create --id "$app_id" >/dev/null
    sp_object_id=$(az ad sp show --id "$app_id" --query id -o tsv)
  fi

  echo "$sp_object_id"
}

assign_app_role_if_missing() {
  local client_sp_object_id="$1"
  local api_sp_object_id="$2"
  local role_id="$3"

  local existing
  existing=$(az rest \
    --method GET \
    --url "https://graph.microsoft.com/v1.0/servicePrincipals/${client_sp_object_id}/appRoleAssignments" \
    --query "value[?resourceId=='${api_sp_object_id}' && appRoleId=='${role_id}'] | length(@)" \
    -o tsv)

  if [ "$existing" = "0" ]; then
    az rest \
      --method POST \
      --url "https://graph.microsoft.com/v1.0/servicePrincipals/${client_sp_object_id}/appRoleAssignments" \
      --headers "Content-Type=application/json" \
      --body "{\"principalId\":\"${client_sp_object_id}\",\"resourceId\":\"${api_sp_object_id}\",\"appRoleId\":\"${role_id}\"}" \
      >/dev/null
  fi
}

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

# Set resource group name convention
RESOURCE_GROUP="rg-$ENV_NAME"
echo "Resource Group: $RESOURCE_GROUP"
azd env set AZURE_RESOURCE_GROUP "$RESOURCE_GROUP"

# Set admin user (aligns with password-only auth)
POSTGRES_ADMIN_USER="${POSTGRES_ADMIN_USER:-pgadmin}"
azd env set POSTGRES_ADMIN_USER "$POSTGRES_ADMIN_USER"

echo ""
echo "Note: Post-provision will configure PostgreSQL Entra principal grants for the runtime managed identity"

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

POSTGRES_ENTRA_ADMIN_OBJECT_ID="${POSTGRES_ENTRA_ADMIN_OBJECT_ID:-}"
POSTGRES_ENTRA_ADMIN_NAME="${POSTGRES_ENTRA_ADMIN_NAME:-}"
POSTGRES_ENTRA_ADMIN_TYPE="${POSTGRES_ENTRA_ADMIN_TYPE:-User}"
AZD_ENV_JSON=$(get_azd_env_json)

if [ -z "$POSTGRES_ENTRA_ADMIN_OBJECT_ID" ] || [ -z "$POSTGRES_ENTRA_ADMIN_NAME" ]; then
  [ -z "$POSTGRES_ENTRA_ADMIN_OBJECT_ID" ] && POSTGRES_ENTRA_ADMIN_OBJECT_ID=$(get_azd_env_value "$AZD_ENV_JSON" "POSTGRES_ENTRA_ADMIN_OBJECT_ID")
  [ -z "$POSTGRES_ENTRA_ADMIN_NAME" ] && POSTGRES_ENTRA_ADMIN_NAME=$(get_azd_env_value "$AZD_ENV_JSON" "POSTGRES_ENTRA_ADMIN_NAME")
  [ -z "$POSTGRES_ENTRA_ADMIN_TYPE" ] && POSTGRES_ENTRA_ADMIN_TYPE=$(get_azd_env_value "$AZD_ENV_JSON" "POSTGRES_ENTRA_ADMIN_TYPE")
fi

if [ -z "$POSTGRES_ENTRA_ADMIN_OBJECT_ID" ] || [ -z "$POSTGRES_ENTRA_ADMIN_NAME" ]; then
  echo "Error: PostgreSQL Entra admin identity is required." >&2
  echo "Set POSTGRES_ENTRA_ADMIN_OBJECT_ID and POSTGRES_ENTRA_ADMIN_NAME before running azd provision/up." >&2
  exit 1
fi

azd env set POSTGRES_ENTRA_ADMIN_OBJECT_ID "$POSTGRES_ENTRA_ADMIN_OBJECT_ID" --no-prompt
azd env set POSTGRES_ENTRA_ADMIN_NAME "$POSTGRES_ENTRA_ADMIN_NAME" --no-prompt
azd env set POSTGRES_ENTRA_ADMIN_TYPE "$POSTGRES_ENTRA_ADMIN_TYPE" --no-prompt

echo ""
echo "Configuring Entra app registrations (API + client)..."

TENANT_ID=$(az account show --query tenantId -o tsv)
API_APP_DISPLAY_NAME="todo-api-${ENV_NAME}"
CLIENT_APP_DISPLAY_NAME="todo-client-${ENV_NAME}"
EXISTING_ENV_CLIENT_ID=$(get_azd_env_value "$AZD_ENV_JSON" "ENTRA_CLIENT_ID")
EXISTING_ENV_CLIENT_SECRET=$(get_azd_env_value "$AZD_ENV_JSON" "ENTRA_CLIENT_SECRET")

API_APP_RAW=$(az ad app list --display-name "$API_APP_DISPLAY_NAME" --query "[0]" -o json)
API_APP_ID=$(echo "$API_APP_RAW" | jq -r '.appId // empty')
API_APP_OBJECT_ID=$(echo "$API_APP_RAW" | jq -r '.id // empty')

if [ -z "$API_APP_ID" ] || [ -z "$API_APP_OBJECT_ID" ]; then
  API_APP_CREATE=$(az ad app create \
    --display-name "$API_APP_DISPLAY_NAME" \
    --sign-in-audience AzureADMyOrg \
    -o json)
  API_APP_ID=$(echo "$API_APP_CREATE" | jq -r '.appId')
  API_APP_OBJECT_ID=$(echo "$API_APP_CREATE" | jq -r '.id')
  echo "Created API app registration: $API_APP_DISPLAY_NAME"
else
  echo "Using existing API app registration: $API_APP_DISPLAY_NAME"
fi

API_AUDIENCE="api://${API_APP_ID}"
az ad app update --id "$API_APP_ID" --identifier-uris "$API_AUDIENCE" >/dev/null

READ_ROLE_ID=$(echo "$AZD_ENV_JSON" | jq -r '.ENTRA_ROLE_TODOS_READ_ID // empty')
WRITE_ROLE_ID=$(echo "$AZD_ENV_JSON" | jq -r '.ENTRA_ROLE_TODOS_WRITE_ID // empty')

CURRENT_APP_ROLES=$(az ad app show --id "$API_APP_ID" --query appRoles -o json)
EXISTING_READ_ROLE_ID=$(echo "$CURRENT_APP_ROLES" | jq -r '.[]? | select(.value=="Todos.Read") | .id // empty')
EXISTING_WRITE_ROLE_ID=$(echo "$CURRENT_APP_ROLES" | jq -r '.[]? | select(.value=="Todos.Write") | .id // empty')
[ -z "$READ_ROLE_ID" ] && READ_ROLE_ID="$EXISTING_READ_ROLE_ID"
[ -z "$WRITE_ROLE_ID" ] && WRITE_ROLE_ID="$EXISTING_WRITE_ROLE_ID"
[ -z "$READ_ROLE_ID" ] && READ_ROLE_ID=$(cat /proc/sys/kernel/random/uuid)
[ -z "$WRITE_ROLE_ID" ] && WRITE_ROLE_ID=$(cat /proc/sys/kernel/random/uuid)
PATCHED_APP_ROLES=$(echo "$CURRENT_APP_ROLES" | jq \
  --arg readRoleId "$READ_ROLE_ID" \
  --arg writeRoleId "$WRITE_ROLE_ID" \
  'def ensure_role($id; $display; $desc; $value):
      if any(.[]?; .value == $value) then .
      else . + [{
        allowedMemberTypes: ["Application"],
        description: $desc,
        displayName: $display,
        id: $id,
        isEnabled: true,
        value: $value
      }] end;
   ensure_role($readRoleId; "Todos.Read"; "Read todos"; "Todos.Read")
   | ensure_role($writeRoleId; "Todos.Write"; "Create and modify todos"; "Todos.Write")')

PATCH_PAYLOAD=$(jq -nc --argjson appRoles "$PATCHED_APP_ROLES" '{appRoles: $appRoles}')
retry 5 3 az rest \
  --method PATCH \
  --url "https://graph.microsoft.com/v1.0/applications/${API_APP_OBJECT_ID}" \
  --headers "Content-Type=application/json" \
  --body "$PATCH_PAYLOAD" \
  >/dev/null

READ_ROLE_ID=$(az ad app show --id "$API_APP_ID" --query "appRoles[?value=='Todos.Read'] | [0].id" -o tsv)
WRITE_ROLE_ID=$(az ad app show --id "$API_APP_ID" --query "appRoles[?value=='Todos.Write'] | [0].id" -o tsv)

CLIENT_APP_RAW=$(az ad app list --display-name "$CLIENT_APP_DISPLAY_NAME" --query "[0]" -o json)
CLIENT_APP_ID=$(echo "$CLIENT_APP_RAW" | jq -r '.appId // empty')

if [ -z "$CLIENT_APP_ID" ]; then
  CLIENT_APP_CREATE=$(az ad app create \
    --display-name "$CLIENT_APP_DISPLAY_NAME" \
    --sign-in-audience AzureADMyOrg \
    -o json)
  CLIENT_APP_ID=$(echo "$CLIENT_APP_CREATE" | jq -r '.appId')
  echo "Created client app registration: $CLIENT_APP_DISPLAY_NAME"
else
  echo "Using existing client app registration: $CLIENT_APP_DISPLAY_NAME"
fi

API_SP_OBJECT_ID=$(ensure_sp "$API_APP_ID")
CLIENT_SP_OBJECT_ID=$(ensure_sp "$CLIENT_APP_ID")

retry 5 3 assign_app_role_if_missing "$CLIENT_SP_OBJECT_ID" "$API_SP_OBJECT_ID" "$READ_ROLE_ID"
retry 5 3 assign_app_role_if_missing "$CLIENT_SP_OBJECT_ID" "$API_SP_OBJECT_ID" "$WRITE_ROLE_ID"

ENTRA_CLIENT_SECRET=""
if [ "$EXISTING_ENV_CLIENT_ID" = "$CLIENT_APP_ID" ] && [ -n "$EXISTING_ENV_CLIENT_SECRET" ]; then
  ENTRA_CLIENT_SECRET="$EXISTING_ENV_CLIENT_SECRET"
fi

if [ -z "$ENTRA_CLIENT_SECRET" ]; then
  ENTRA_CLIENT_SECRET=$(az ad app credential reset \
    --id "$CLIENT_APP_ID" \
    --append \
    --display-name "azd-${ENV_NAME}" \
    --years 2 \
    --query password \
    -o tsv)
  echo "Created client secret for app registration: $CLIENT_APP_DISPLAY_NAME"
else
  echo "Using existing Entra client secret from azd environment"
fi

azd env set ENTRA_TENANT_ID "$TENANT_ID" --no-prompt
azd env set ENTRA_API_AUDIENCE "$API_AUDIENCE" --no-prompt
azd env set ENTRA_SCOPE "${API_AUDIENCE}/.default" --no-prompt
azd env set ENTRA_CLIENT_ID "$CLIENT_APP_ID" --no-prompt
azd env set ENTRA_CLIENT_SECRET "$ENTRA_CLIENT_SECRET" --no-prompt
azd env set ENTRA_API_APP_ID "$API_APP_ID" --no-prompt
azd env set ENTRA_ROLE_TODOS_READ_ID "$READ_ROLE_ID" --no-prompt
azd env set ENTRA_ROLE_TODOS_WRITE_ID "$WRITE_ROLE_ID" --no-prompt
azd env set DB_AUTH_MODE "aad" --no-prompt
azd env set REQUIRE_AUTH "true" --no-prompt
azd env set ENABLE_TELEMETRY "true" --no-prompt

echo ""
echo "=========================================="
echo "Pre-Provision Hook: Complete"
echo "=========================================="
echo "Environment variables set:"
echo "  - AZURE_LOCATION: $AZURE_LOCATION"
echo "  - AZURE_RESOURCE_GROUP: $RESOURCE_GROUP"
echo "  - POSTGRES_ADMIN_PASSWORD: *** (hidden)"
echo "  - POSTGRES_ENTRA_ADMIN_NAME: $POSTGRES_ENTRA_ADMIN_NAME"
echo "  - ENTRA_API_AUDIENCE: $API_AUDIENCE"
echo "  - ENTRA_CLIENT_ID: $CLIENT_APP_ID"
echo "  - ENTRA_CLIENT_SECRET: *** (hidden)"
echo "=========================================="
echo ""
