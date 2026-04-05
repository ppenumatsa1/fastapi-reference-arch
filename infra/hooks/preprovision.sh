#!/bin/bash

# Azure Developer CLI Pre-Provision Hook
# Sets required environment variables before `azd provision`

set -euo pipefail

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Error: required command '$1' not found" >&2
    exit 1
  fi
}

require_command az
require_command azd
require_command jq

get_azd_env_json() {
  azd env get-values --output json 2>/dev/null || echo '{}'
}

get_azd_env_value() {
  local json="$1"
  local key="$2"
  echo "$json" | jq -r --arg key "$key" '.[$key] // empty'
}

echo ""
echo "=========================================="
echo "Pre-Provision Hook: Environment Setup"
echo "=========================================="

ENV_NAME="${AZURE_ENV_NAME:-}"
if [ -z "$ENV_NAME" ]; then
  echo "Error: AZURE_ENV_NAME is not set. Run via azd." >&2
  exit 1
fi

RESOURCE_GROUP="rg-$ENV_NAME"
echo "Resource Group: $RESOURCE_GROUP"
azd env set AZURE_RESOURCE_GROUP "$RESOURCE_GROUP" --no-prompt

POSTGRES_ADMIN_USER="${POSTGRES_ADMIN_USER:-pgadmin}"
azd env set POSTGRES_ADMIN_USER "$POSTGRES_ADMIN_USER" --no-prompt

POSTGRES_ENTRA_ADMIN_OBJECT_ID="${POSTGRES_ENTRA_ADMIN_OBJECT_ID:-}"
POSTGRES_ENTRA_ADMIN_NAME="${POSTGRES_ENTRA_ADMIN_NAME:-}"
POSTGRES_ENTRA_ADMIN_TYPE="${POSTGRES_ENTRA_ADMIN_TYPE:-User}"
AZD_ENV_JSON=$(get_azd_env_json)

if [ -z "$POSTGRES_ENTRA_ADMIN_OBJECT_ID" ]; then
  POSTGRES_ENTRA_ADMIN_OBJECT_ID=$(get_azd_env_value "$AZD_ENV_JSON" "POSTGRES_ENTRA_ADMIN_OBJECT_ID")
fi
if [ -z "$POSTGRES_ENTRA_ADMIN_NAME" ]; then
  POSTGRES_ENTRA_ADMIN_NAME=$(get_azd_env_value "$AZD_ENV_JSON" "POSTGRES_ENTRA_ADMIN_NAME")
fi
if [ -z "$POSTGRES_ENTRA_ADMIN_TYPE" ]; then
  POSTGRES_ENTRA_ADMIN_TYPE=$(get_azd_env_value "$AZD_ENV_JSON" "POSTGRES_ENTRA_ADMIN_TYPE")
fi

if [ -z "$POSTGRES_ENTRA_ADMIN_OBJECT_ID" ] || [ -z "$POSTGRES_ENTRA_ADMIN_NAME" ]; then
  echo "Error: PostgreSQL Entra admin identity is required." >&2
  echo "Set POSTGRES_ENTRA_ADMIN_OBJECT_ID and POSTGRES_ENTRA_ADMIN_NAME before azd provision/up." >&2
  exit 1
fi

azd env set POSTGRES_ENTRA_ADMIN_OBJECT_ID "$POSTGRES_ENTRA_ADMIN_OBJECT_ID" --no-prompt
azd env set POSTGRES_ENTRA_ADMIN_NAME "$POSTGRES_ENTRA_ADMIN_NAME" --no-prompt
azd env set POSTGRES_ENTRA_ADMIN_TYPE "$POSTGRES_ENTRA_ADMIN_TYPE" --no-prompt

azd env set DB_AUTH_MODE "aad" --no-prompt
azd env set ENABLE_TELEMETRY "true" --no-prompt

echo ""
echo "=========================================="
echo "Pre-Provision Hook: Complete"
echo "=========================================="
echo "Environment variables set:"
echo "  - AZURE_LOCATION: ${AZURE_LOCATION:-}"
echo "  - AZURE_RESOURCE_GROUP: $RESOURCE_GROUP"
echo "  - POSTGRES_ENTRA_ADMIN_NAME: $POSTGRES_ENTRA_ADMIN_NAME"
echo "=========================================="
echo ""
