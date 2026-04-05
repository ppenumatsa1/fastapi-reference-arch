#!/bin/bash
set -euo pipefail

# Usage: ./scripts/verify_deployment.sh [--env local|azure] [--base-url URL] [--require-auth]
#                                     [--tenant-id ID] [--client-id ID]
#                                     [--client-secret SECRET] [--scope SCOPE]
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
REQUIRE_AUTH="false"
REQUIRE_AUTH_SET="false"
CHECK_TELEMETRY="false"
CHECK_TELEMETRY_SET="false"
TENANT_ID="${ENTRA_TENANT_ID:-}"
CLIENT_ID="${ENTRA_CLIENT_ID:-}"
CLIENT_SECRET="${ENTRA_CLIENT_SECRET:-}"
SCOPE="${ENTRA_SCOPE:-}"
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

  if [ "$REQUIRE_AUTH_SET" = "false" ]; then
    if [ "$is_non_local" = "true" ]; then
      REQUIRE_AUTH="true"
    else
      REQUIRE_AUTH="false"
    fi
  fi

  if [ "$CHECK_TELEMETRY_SET" = "false" ]; then
    if [ "$is_non_local" = "true" ]; then
      CHECK_TELEMETRY="true"
    else
      CHECK_TELEMETRY="false"
    fi
  fi
}

resolve_auth_inputs() {
  if [ "$REQUIRE_AUTH" != "true" ]; then
    return
  fi

  [ -z "$TENANT_ID" ] && TENANT_ID=$(get_from_azd_env "ENTRA_TENANT_ID")
  [ -z "$CLIENT_ID" ] && CLIENT_ID=$(get_from_azd_env "ENTRA_CLIENT_ID")
  [ -z "$CLIENT_SECRET" ] && CLIENT_SECRET=$(get_from_azd_env "ENTRA_CLIENT_SECRET")
  [ -z "$SCOPE" ] && SCOPE=$(get_from_azd_env "ENTRA_SCOPE")
}

validate_auth_inputs() {
  if [ "$REQUIRE_AUTH" != "true" ]; then
    return
  fi

  if [ -z "$TENANT_ID" ] || [ -z "$CLIENT_ID" ] || [ -z "$CLIENT_SECRET" ]; then
    echo "Error: --require-auth requires tenant/client credentials." >&2
    echo "Set ENTRA_TENANT_ID, ENTRA_CLIENT_ID, ENTRA_CLIENT_SECRET or pass flags." >&2
    exit 1
  fi

  if [ -z "$SCOPE" ]; then
    echo "Error: missing scope. Provide --scope or ENTRA_SCOPE." >&2
    exit 1
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
      echo "Usage: $0 [--env local|azure] [--base-url URL] [--require-auth]"
      echo "          [--tenant-id ID] [--client-id ID] [--client-secret SECRET]"
      echo "          [--scope SCOPE] [--check-telemetry|--skip-telemetry-check]"
      exit 0
      ;;
    --require-auth)
      REQUIRE_AUTH="true"
      REQUIRE_AUTH_SET="true"
      shift
      ;;
    --no-require-auth)
      REQUIRE_AUTH="false"
      REQUIRE_AUTH_SET="true"
      shift
      ;;
    --tenant-id)
      TENANT_ID="$2"
      shift 2
      ;;
    --client-id)
      CLIENT_ID="$2"
      shift 2
      ;;
    --client-secret)
      CLIENT_SECRET="$2"
      shift 2
      ;;
    --scope)
      SCOPE="$2"
      shift 2
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
resolve_auth_inputs
validate_auth_inputs

echo "Environment: $ENVIRONMENT"
echo "Target: $BASE_URL"
echo "Auth mode: $REQUIRE_AUTH"
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

AUTHORIZATION_HEADER=""
if [ "$REQUIRE_AUTH" = "true" ]; then
  TOKEN_RESPONSE=$(curl -s -X POST \
    "https://login.microsoftonline.com/$TENANT_ID/oauth2/v2.0/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "client_id=$CLIENT_ID" \
    --data-urlencode "client_secret=$CLIENT_SECRET" \
    --data-urlencode "scope=$SCOPE" \
    --data-urlencode "grant_type=client_credentials")

  ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token // empty')
  if [ -z "$ACCESS_TOKEN" ]; then
    echo "Error: failed to acquire access token." >&2
    echo "Token response: $TOKEN_RESPONSE" >&2
    exit 1
  fi

  AUTHORIZATION_HEADER="Authorization: Bearer $ACCESS_TOKEN"
fi

curl_with_auth() {
  if [ -n "$AUTHORIZATION_HEADER" ]; then
    curl "$@" -H "$AUTHORIZATION_HEADER"
  else
    curl "$@"
  fi
}

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

# Test 2: List todos (verify seeded data)
echo "✓ Test 2/4: List todos (verify seeding)"
TODOS_RESPONSE=$(curl_with_auth -s "$BASE_URL/api/v1/todos/?limit=3&offset=0")
TODO_COUNT=$(echo "$TODOS_RESPONSE" | jq '.items | length' 2>/dev/null || echo "0")
TOTAL_COUNT=$(echo "$TODOS_RESPONSE" | jq '.total' 2>/dev/null || echo "0")
if [ "$TODO_COUNT" -ge 1 ] || [ "$TOTAL_COUNT" -ge 1 ]; then
  echo "  ✅ Found $TOTAL_COUNT total todos (showing $TODO_COUNT)"
  echo "$TODOS_RESPONSE" | jq -r '.items[] | "     - [\(.id)] \(.title)"' 2>/dev/null | head -3
else
  echo "  ⚠️  No todos found (expected seeded data)"
fi
echo ""

# Test 3: Create a new todo
echo "✓ Test 3/4: Create new todo (verify write)"
NEW_TODO=$(cat <<EOF
{
  "title": "Deployment verification test",
  "description": "Created by verify_deployment.sh at $(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "is_completed": false
}
EOF
)

CREATE_RESPONSE=$(curl_with_auth -s -X POST "$BASE_URL/api/v1/todos/" \
  -H "Content-Type: application/json" \
  -d "$NEW_TODO")

CREATED_ID=$(echo "$CREATE_RESPONSE" | jq -r '.id' 2>/dev/null || echo "null")
if [ "$CREATED_ID" != "null" ] && [ -n "$CREATED_ID" ]; then
  echo "  ✅ Created todo with ID: $CREATED_ID"
else
  echo "  ❌ Failed to create todo"
  echo "  Response: $CREATE_RESPONSE"
  exit 1
fi
echo ""

# Test 4: Retrieve the created todo
echo "✓ Test 4/4: Retrieve created todo (verify read after write)"
RETRIEVE_RESPONSE=$(curl_with_auth -s "$BASE_URL/api/v1/todos/$CREATED_ID")
RETRIEVED_ID=$(echo "$RETRIEVE_RESPONSE" | jq -r '.id' 2>/dev/null || echo "null")
if [ "$RETRIEVED_ID" = "$CREATED_ID" ]; then
  echo "  ✅ Successfully retrieved todo $CREATED_ID"
  echo "$RETRIEVE_RESPONSE" | jq -r '"     Title: \(.title)\n     Created: \(.created_at)"' 2>/dev/null
else
  echo "  ❌ Failed to retrieve todo $CREATED_ID"
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
