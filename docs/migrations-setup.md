# Database Migrations with Service Principal

## Overview

This project uses a **dedicated migration service principal** to run Alembic database migrations. This approach solves the AAD authentication challenge where:

- **Managed identities** can only authenticate from within Azure resources (Container Apps)
- **Regular service principals** cannot generate `AAD_AUTH_TOKENTYPE_APP_USER` tokens required for managed identity impersonation
- **Migration service principal** has direct AAD admin access to PostgreSQL and can run migrations

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  GitHub Actions CI/CD                                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  1. Authenticate with Migration Service Principal     │  │
│  │  2. Get AAD token for PostgreSQL                      │  │
│  │  3. Run Alembic migrations                            │  │
│  │  4. Seed database                                     │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ AAD Token
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Azure PostgreSQL Flexible Server                          │
│  - AAD Authentication Enabled                              │
│  - Migration SP as AAD Admin                               │
│  - Managed Identity (UAMI) as AAD Admin                    │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ AAD Token
                            │
┌─────────────────────────────────────────────────────────────┐
│  Azure Container Apps                                       │
│  - Uses Managed Identity (UAMI)                            │
│  - DefaultAzureCredential for app authentication           │
└─────────────────────────────────────────────────────────────┘
```

## Setup Process

### 1. Automatic Setup (Recommended)

The migration service principal is automatically created during `azd provision`:

```bash
azd provision
```

This runs the **postprovision hook** (`infra/hooks/postprovision.sh`) which:

1. Creates a service principal named `sp-{environment}-migration`
2. Grants it Reader role on the resource group
3. Adds it as PostgreSQL AAD admin
4. Stores credentials in the azd environment

### 2. Manual Setup (If Needed)

If you need to manually create or recreate the service principal:

```bash
# Run the postprovision hook manually
./infra/hooks/postprovision.sh

# Retrieve the credentials
azd env get-values --output json | jq -r '.MIGRATION_SP_APP_ID'
azd env get-values --output json | jq -r '.MIGRATION_SP_PASSWORD'
azd env get-values --output json | jq -r '.MIGRATION_SP_TENANT_ID'
```

## GitHub Actions Setup

### Required Secrets

Add these secrets to your GitHub repository:

1. **MIGRATION_SP_APP_ID** - The application (client) ID of the migration service principal
2. **MIGRATION_SP_PASSWORD** - The password/secret of the migration service principal
3. **MIGRATION_SP_TENANT_ID** - Your Azure AD tenant ID
4. **AZURE_SUBSCRIPTION_ID** - Your Azure subscription ID
5. **AZURE_ENV_NAME** - Your azd environment name (e.g., "dev")

To add secrets:

```bash
# Navigate to: Repository Settings > Secrets and variables > Actions > New repository secret

# Get values from azd environment
azd env get-values --output json | jq -r '.MIGRATION_SP_APP_ID'
azd env get-values --output json | jq -r '.MIGRATION_SP_PASSWORD'
azd env get-values --output json | jq -r '.MIGRATION_SP_TENANT_ID'
az account show --query id -o tsv  # For AZURE_SUBSCRIPTION_ID
```

### How It Works

The CI workflow (`.github/workflows/ci.yml`) has a `migrations` job that:

1. **Authenticates** using the migration service principal
2. **Gets AAD token** for PostgreSQL using `az account get-access-token --resource-type oss-rdbms`
3. **Sets PGPASSWORD** to the AAD token (required by psycopg2/Alembic)
4. **Runs migrations** with `alembic upgrade head`
5. **Seeds database** with initial data using `scripts/seed_data.py`

## Local Development

### Option 1: Run Migrations from GitHub Actions

Push to any of these branches to trigger migrations:

- `main`
- `infra-bicep`
- `dev`

```bash
git push origin infra-bicep
```

### Option 2: Use Migration Script with Service Principal

Export the migration service principal credentials and run the migration script:

```bash
# Get credentials from azd environment
export MIGRATION_SP_APP_ID=$(azd env get-value MIGRATION_SP_APP_ID)
export MIGRATION_SP_PASSWORD=$(azd env get-value MIGRATION_SP_PASSWORD)
export MIGRATION_SP_TENANT_ID=$(azd env get-value MIGRATION_SP_TENANT_ID)

# Export PostgreSQL connection details
export POSTGRES_FQDN=$(azd env get-value POSTGRES_FQDN)
export POSTGRES_DB=$(azd env get-value POSTGRES_DB)

# Run the enhanced migration script
./infra/scripts/run_migrations.sh
```

The script will automatically:

- Login with the service principal
- Get AAD token for PostgreSQL
- Run Alembic migrations

## Why This Approach?

### Problem: AAD Token Types

Azure PostgreSQL AAD authentication supports two token types:

1. **AAD_AUTH_TOKENTYPE_APP_USER** - User-level access (managed identities)
2. **AAD_AUTH_TOKENTYPE_APP** - Application-level access (service principals)

The issue:

- Managed identity tokens (APP_USER) can only be obtained from within Azure
- Service principals authenticating from outside Azure (like GitHub Actions or local dev) cannot generate APP_USER tokens
- Trying to authenticate as a managed identity from outside Azure fails with: _"Service principals cannot generate AAD_AUTH_TOKENTYPE_APP_USER tokens"_

### Solution: Dedicated Migration Service Principal

Create a **separate service principal** specifically for migrations that:

- Has its own AAD admin access to PostgreSQL
- Can authenticate from anywhere (GitHub Actions, local dev)
- Generates its own APP tokens (not impersonating managed identity)
- Runs migrations independently of the application's managed identity

### Advantages

✅ **Works from anywhere** - GitHub Actions, local dev, Azure DevOps  
✅ **No token type conflicts** - Uses service principal's own tokens  
✅ **Secure** - Credentials stored in GitHub Secrets and azd environment  
✅ **Automated** - Runs automatically on push to tracked branches  
✅ **Separate concerns** - Migration auth separate from application auth

## Troubleshooting

### Error: "Service principals cannot generate AAD_AUTH_TOKENTYPE_APP_USER tokens"

This means you're trying to authenticate as a managed identity from outside Azure. Use the migration service principal instead.

### Error: "Failed to get AAD token"

Check that:

1. Service principal credentials are correct
2. Service principal has been added as PostgreSQL AAD admin
3. You're using `--resource-type oss-rdbms` when getting the token

### Error: "password authentication failed"

Check that:

1. You're setting `PGPASSWORD` to the AAD token
2. The username in the connection string is the service principal app ID
3. The connection string includes `?sslmode=require`

### Migrations hanging or timing out

Check that:

1. PostgreSQL server allows connections from GitHub Actions (public access enabled or firewall rules)
2. Network connectivity is working
3. Database exists and is accessible

## Additional Resources

- [Azure PostgreSQL AAD Authentication](https://learn.microsoft.com/azure/postgresql/flexible-server/concepts-azure-ad-authentication)
- [Service Principals vs Managed Identities](https://learn.microsoft.com/azure/active-directory/managed-identities-azure-resources/overview)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
