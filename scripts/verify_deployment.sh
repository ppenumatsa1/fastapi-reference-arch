#!/bin/bash
set -euo pipefail

# Usage: ./scripts/verify_deployment.sh [--env local|azure] [--base-url URL]
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
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

# Detect deployment environment and set base URL
if [ -n "$BASE_URL" ]; then
  : # honor explicit override
elif [ "$ENVIRONMENT" = "azure" ]; then
  if [ -n "${CONTAINER_APP_FQDN:-}" ]; then
    BASE_URL="https://$CONTAINER_APP_FQDN"
  elif command -v azd >/dev/null 2>&1 && azd env get-values >/dev/null 2>&1; then
    FQDN=$(azd env get-values | grep -E '^CONTAINER_APP_FQDN=' | cut -d'=' -f2- | tr -d '"')
    [ -n "$FQDN" ] && BASE_URL="https://$FQDN"
  fi

  if [ -z "$BASE_URL" ]; then
    echo "Error: Azure mode requested but CONTAINER_APP_FQDN not found." >&2
    echo "Pass --base-url or set CONTAINER_APP_FQDN (or ensure azd env has it)." >&2
    exit 1
  fi
else
  BASE_URL="http://localhost:8000"
fi

echo "Environment: $ENVIRONMENT"
echo "Target: $BASE_URL"

echo ""

if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required for this script." >&2
  exit 1
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

# Test 2: List todos (verify seeded data)
echo "✓ Test 2/4: List todos (verify seeding)"
TODOS_RESPONSE=$(curl -s "$BASE_URL/api/v1/todos/?limit=3&offset=0")
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

CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/todos/" \
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
RETRIEVE_RESPONSE=$(curl -s "$BASE_URL/api/v1/todos/$CREATED_ID")
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
