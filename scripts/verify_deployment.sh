#!/bin/bash
set -euo pipefail

# Usage: ./scripts/verify_deployment.sh [--env local|azure] [--base-url URL]
#                                     [--check-telemetry|--skip-telemetry-check]
# Defaults to local (http://localhost:8000). Azure mode expects CONTAINER_APP_FQDN
# or an azd environment with CONTAINER_APP_FQDN set.

# Post-deployment verification script
# Tests API health, reads, and writes to ensure full stack is operational

echo ""
echo "=========================================="
echo "Post-Deployment Verification"
echo "=========================================="
echo ""

ENVIRONMENT="local"
BASE_URL=""
CHECK_TELEMETRY="false"
CHECK_TELEMETRY_SET="false"
AZD_VALUES_JSON=""

get_from_azd_env() {
  local key="$1"

  if [ -z "$AZD_VALUES_JSON" ]; then
    if command -v azd >/dev/null 2>&1 && azd env get-values --output json >/dev/null 2>&1; then
      AZD_VALUES_JSON=$(azd env get-values --output json)
    else
      AZD_VALUES_JSON='{}'
    fi
  fi

  echo "$AZD_VALUES_JSON" | jq -r --arg key "$key" '.[$key] // empty'
}

resolve_base_url() {
  if [ -n "$BASE_URL" ]; then
    return
  fi

  if [ "$ENVIRONMENT" = "azure" ]; then
    if [ -n "${CONTAINER_APP_FQDN:-}" ]; then
      BASE_URL="https://$CONTAINER_APP_FQDN"
      return
    fi

    local fqdn
    fqdn=$(get_from_azd_env "CONTAINER_APP_FQDN")
    if [ -n "$fqdn" ]; then
      BASE_URL="https://$fqdn"
      return
    fi

    echo "Error: Azure mode requested but CONTAINER_APP_FQDN not found." >&2
    echo "Pass --base-url or set CONTAINER_APP_FQDN (or ensure azd env has it)." >&2
    exit 1
  fi

  BASE_URL="http://localhost:8000"
}

apply_target_defaults() {
  local is_non_local=false
  if [ -n "$BASE_URL" ] && [ "$BASE_URL" != "http://localhost:8000" ]; then
    is_non_local=true
  fi

  if [ "$CHECK_TELEMETRY_SET" = "false" ]; then
    if [ "$is_non_local" = "true" ]; then
      CHECK_TELEMETRY="true"
    else
      CHECK_TELEMETRY="false"
    fi
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --base-url)
      BASE_URL="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [--env local|azure] [--base-url URL]"
      echo "          [--check-telemetry|--skip-telemetry-check]"
      exit 0
      ;;
    --check-telemetry)
      CHECK_TELEMETRY="true"
      CHECK_TELEMETRY_SET="true"
      shift
      ;;
    --skip-telemetry-check)
      CHECK_TELEMETRY="false"
      CHECK_TELEMETRY_SET="true"
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

resolve_base_url
apply_target_defaults

echo "Environment: $ENVIRONMENT"
echo "Target: $BASE_URL"
echo "Telemetry check mode: $CHECK_TELEMETRY"

echo ""

if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required for this script." >&2
  exit 1
fi

if [ "$CHECK_TELEMETRY" = "true" ]; then
  echo "ℹ️  Telemetry check mode is enabled for this run."
  echo "    (Deep telemetry validation remains in scripts/kusto/run-observability-suite.sh)"
  echo ""
fi

# Test 1: Health check
echo "✓ Test 1/4: Health endpoint"
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health" || echo "000")
if [ "$HEALTH_STATUS" = "200" ]; then
  echo "  ✅ Health check passed (HTTP 200)"
else
  echo "  ❌ Health check failed (HTTP $HEALTH_STATUS)"
  exit 1
fi
echo ""

# Test 2: List users (verify seeded data)
echo "✓ Test 2/4: List users (verify seeding)"
USERS_RESPONSE=$(curl -s "$BASE_URL/api/v1/users/?limit=3&offset=0")
USER_COUNT=$(echo "$USERS_RESPONSE" | jq '.items | length' 2>/dev/null || echo "0")
TOTAL_COUNT=$(echo "$USERS_RESPONSE" | jq '.total' 2>/dev/null || echo "0")
if [ "$USER_COUNT" -ge 1 ] || [ "$TOTAL_COUNT" -ge 1 ]; then
  echo "  ✅ Found $TOTAL_COUNT total users (showing $USER_COUNT)"
  echo "$USERS_RESPONSE" | jq -r '.items[] | "     - [\(.id)] \(.first_name) \(.last_name) <\(.email)>"' 2>/dev/null | head -3
else
  echo "  ⚠️  No users found (expected seeded data)"
fi
echo ""

# Test 3: Create a new user
echo "✓ Test 3/4: Create new user (verify write)"
VERIFY_FIRST_NAME="Deploy$(date -u +%s)"
NEW_USER=$(cat <<EOF
{
  "first_name": "${VERIFY_FIRST_NAME}",
  "last_name": "Check",
  "email": "deploy.check.$(date -u +%Y%m%d%H%M%S)@example.com",
  "is_active": true
}
EOF
)

CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d "$NEW_USER")

CREATED_ID=$(echo "$CREATE_RESPONSE" | jq -r '.id' 2>/dev/null || echo "null")
if [ "$CREATED_ID" != "null" ] && [ -n "$CREATED_ID" ]; then
  echo "  ✅ Created user with ID: $CREATED_ID"
else
  echo "  ❌ Failed to create user"
  echo "  Response: $CREATE_RESPONSE"
  exit 1
fi
echo ""

# Test 4: Search for the created user by unique first name
echo "✓ Test 4/4: Search created user (verify read after write)"
RETRIEVE_RESPONSE=$(curl -s "$BASE_URL/api/v1/users/search?q=$VERIFY_FIRST_NAME")
RETRIEVED_ID=$(echo "$RETRIEVE_RESPONSE" | jq -r --arg id "$CREATED_ID" '.items[]? | select((.id|tostring) == $id) | .id' | head -n1)
if [ "$RETRIEVED_ID" = "$CREATED_ID" ]; then
  echo "  ✅ Successfully found created user $CREATED_ID via search"
  echo "$RETRIEVE_RESPONSE" | jq -r --arg id "$CREATED_ID" '.items[] | select((.id|tostring) == $id) | "     Name: \(.first_name) \(.last_name)\n     Email: \(.email)\n     Created: \(.created_at)"' 2>/dev/null
else
  echo "  ❌ Failed to find created user $CREATED_ID via search"
  exit 1
fi
echo ""

echo "=========================================="
echo "✅ All verification tests passed!"
echo "=========================================="
echo ""
echo "API is fully operational:"
echo "  - Health checks responding"
echo "  - Database connectivity confirmed"
echo "  - Read operations working"
echo "  - Write operations working"
echo ""
