#!/bin/bash

# Azure Developer CLI Post-Provision Hook
# Configures the dedicated application database user using password authentication

set -e

echo ""
echo "=========================================="
echo "Post-Provision Hook: Database User Setup"
echo "=========================================="

ENV_NAME="${AZURE_ENV_NAME}"
VALUES=$(azd env get-values --output json)

RESOURCE_GROUP=$(echo "$VALUES" | jq -r '.AZURE_RESOURCE_GROUP')
POSTGRES_FQDN=$(echo "$VALUES" | jq -r '.POSTGRES_FQDN')
POSTGRES_DB=$(echo "$VALUES" | jq -r '.POSTGRES_DB // "postgres"')
POSTGRES_ADMIN_USER=$(echo "$VALUES" | jq -r '.POSTGRES_ADMIN_USER // "pgadmin"')
POSTGRES_ADMIN_PASSWORD=$(echo "$VALUES" | jq -r '.POSTGRES_ADMIN_PASSWORD')
TODO_DB_USER=$(echo "$VALUES" | jq -r '.TODO_DB_USER // "todo_user"')
TODO_DB_PASSWORD=$(echo "$VALUES" | jq -r '.TODO_DB_PASSWORD')

if [ -z "$ENV_NAME" ] || [ -z "$RESOURCE_GROUP" ] || [ -z "$POSTGRES_FQDN" ]; then
  echo "Error: Required environment variables not found"
  exit 1
fi

if [ -z "$POSTGRES_ADMIN_PASSWORD" ] || [ -z "$TODO_DB_PASSWORD" ]; then
  echo "Error: Database passwords are missing. Ensure preprovision set POSTGRES_ADMIN_PASSWORD and TODO_DB_PASSWORD."
  exit 1
fi

echo "Environment: $ENV_NAME"
echo "Resource Group: $RESOURCE_GROUP"
echo "PostgreSQL FQDN: $POSTGRES_FQDN"
echo "Database: $POSTGRES_DB"
echo "Admin User: $POSTGRES_ADMIN_USER"
echo "App User: $TODO_DB_USER"

echo ""
echo "Ensuring psql is available..."
if ! command -v psql >/dev/null 2>&1; then
  echo "Error: psql is required to grant database roles. Please install psql (PostgreSQL client)."
  exit 1
fi

export PGPASSWORD="$POSTGRES_ADMIN_PASSWORD"

echo "Creating or updating application user and grants..."
psql "host=$POSTGRES_FQDN dbname=$POSTGRES_DB user=$POSTGRES_ADMIN_USER sslmode=require" \
  -v ON_ERROR_STOP=1 <<EOF
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '$TODO_DB_USER') THEN
    CREATE ROLE "$TODO_DB_USER" WITH LOGIN PASSWORD '$TODO_DB_PASSWORD';
  END IF;
END
\$\$;

GRANT CONNECT ON DATABASE $POSTGRES_DB TO "$TODO_DB_USER";
GRANT USAGE ON SCHEMA public TO "$TODO_DB_USER";
GRANT CREATE ON SCHEMA public TO "$TODO_DB_USER";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "$TODO_DB_USER";
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "$TODO_DB_USER";
ALTER DEFAULT PRIVILEGES FOR ROLE "$POSTGRES_ADMIN_USER" IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "$TODO_DB_USER";
ALTER DEFAULT PRIVILEGES FOR ROLE "$POSTGRES_ADMIN_USER" IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO "$TODO_DB_USER";
EOF

echo ""
echo "✓ Application user configured"
echo "=========================================="
echo "Post-Provision Hook: Complete"
echo "=========================================="
echo ""
