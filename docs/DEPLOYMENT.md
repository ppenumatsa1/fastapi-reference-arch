# Deployment Guide: Environment-Aware Configuration with Managed Identity

This guide explains how the application handles different database configurations for local development vs Azure deployment. Azure uses Managed Identity authentication against a public PostgreSQL instance locked down by firewall rules (ACA outbound IPs + your IP). Database migrations run in CI/CD pipelines before deployment.

## Overview

The application supports two database authentication modes:

- **Password mode**: For local development with Docker Compose
- **AAD mode**: For Azure deployment using Managed Identity (no passwords stored)

## Architecture

### Local Development

- Docker Compose with PostgreSQL container
- Password-based authentication
- Environment variables from `.env` or docker-compose defaults
- No Azure dependencies required

### Azure Deployment

- Azure Container Apps with User-Assigned Managed Identity (UAMI)
- PostgreSQL Flexible Server with AAD authentication (UAMI set as admin)
- Public network access restricted by firewall (ACA outbound IPs + your IP)
- Application Insights telemetry
- No database passwords in environment variables

## Configuration

### Environment Variables

#### Local Development (docker-compose)

```env
# Database connection (password mode - default)
DATABASE_HOST=postgres
DATABASE_PORT=5432
DATABASE_USER=todo_user
DATABASE_PASSWORD=todo_pass
DATABASE_NAME=todo_db

# Application
APP_ENV=development
LOG_LEVEL=INFO
```

#### Azure Deployment (automatically set by Bicep)

```env
# Database authentication mode
DB_AUTH_MODE=aad

# Database connection (AAD mode)
DATABASE_HOST=<postgres-fqdn>
DATABASE_PORT=5432
DATABASE_NAME=postgres
DATABASE_USER=<managed-identity-client-id>

# Azure Managed Identity
AZURE_CLIENT_ID=<managed-identity-client-id>

# Application Insights
APPLICATIONINSIGHTS_CONNECTION_STRING=<connection-string>

# Application
APP_ENV=<environment-name>
LOG_LEVEL=INFO
```

## Deployment Steps

### 1. Provision Infrastructure

```bash
# Set your IP for firewall access and provision Azure resources
azd env set MY_IP_ADDRESS <your.ip.addr>
azd provision
```

What happens:
- Azure resources created (Container App, Postgres, UAMI, App Insights, ACR)
- UAMI is set as Postgres AAD admin
- Firewall allow-list includes ACA outbound IPs plus `MY_IP_ADDRESS`

### 2. Deploy via CI/CD

Push to `main` branch to trigger `.github/workflows/ci.yml`:
- Runs lint/format/tests
- Executes database migrations using UAMI token
- Builds and deploys container to Azure Container Apps

Or manually:
```bash
# Run migrations locally (requires psql + your IP in firewall)
TOKEN=$(az account get-access-token --resource https://ossrdbms-aad.database.windows.net --query accessToken -o tsv)
export PGPASSWORD="$TOKEN"
export DATABASE_URL="postgresql+psycopg2://$(azd env get-value MANAGED_IDENTITY_CLIENT_ID)@$(azd env get-value POSTGRES_FQDN):5432/postgres?sslmode=require"
alembic upgrade head

# Deploy app
azd deploy
```

## How It Works

### Database Authentication Flow

#### Password Mode (Local)

1. App reads `DATABASE_USER` and `DATABASE_PASSWORD` from environment
2. SQLAlchemy connects using these credentials
3. Standard PostgreSQL password authentication

#### AAD Mode (Azure)

1. App detects `DB_AUTH_MODE=aad` in environment
2. On each database connection:
   - Uses `DefaultAzureCredential` to fetch Azure AD token
   - Token scope: `https://ossrdbms-aad.database.windows.net/.default`
   - Injects token as "password" in connection parameters
3. PostgreSQL validates token against AAD (UAMI is the server AAD admin)
4. Connection granted based on role permissions

### Managed Identity Setup

The UAMI is:

- Created in `infra/bicep/modules/identity.bicep`
- Attached to Container App in `infra/bicep/modules/aca.bicep`
- Granted ACR pull permissions in `infra/bicep/modules/rbac.bicep`
- Set as PostgreSQL AAD admin

Client ID is used as:

- `DATABASE_USER` and `AZURE_CLIENT_ID` for token acquisition

### Telemetry

Application Insights integration:

- OpenTelemetry instrumentation for FastAPI, SQLAlchemy, and logging
- Automatic trace/span ID injection into logs
- Connection string provided via `APPLICATIONINSIGHTS_CONNECTION_STRING`
- Disabled if connection string not set (local development)

## Troubleshooting

### "Authentication failed" in Azure

1. Confirm firewall allows ACA outbound IPs (re-provision if needed) and `MY_IP_ADDRESS` for local psql tests.
2. Check Container App logs for token acquisition errors.
3. Verify UAMI is AAD admin in the portal.

### "Cannot connect to database" locally

1. Verify Docker Compose is running: `docker-compose ps`
2. Check database is healthy: `docker-compose logs postgres`
3. Verify `.env` file or environment variables are set correctly
4. Ensure `DB_AUTH_MODE` is not set to `aad` (default is `password`)

### Migration failures

1. Check GitHub Actions logs for Alembic errors.
2. Ensure GitHub Actions runner IP is allowed in Postgres firewall (or use Azure-hosted runners inside VNet).
3. Verify UAMI has DDL permissions (it's set as AAD admin, so it should).
4. For manual migrations, ensure your IP is in `MY_IP_ADDRESS` and you have a valid token.

### Telemetry not appearing in App Insights

1. Verify `APPLICATIONINSIGHTS_CONNECTION_STRING` is set
2. Check application logs for telemetry initialization errors
3. Allow 2-5 minutes for telemetry to appear in Azure Portal
4. Verify dependencies are installed: `pip list | grep opentelemetry`

## Security Best Practices

✅ **Do**:

- Use AAD authentication in production (no passwords in Azure)
- Keep Postgres firewall limited to ACA outbound IPs + your IP
- Rotate the break-glass password periodically
- Monitor access logs in PostgreSQL and App Insights

❌ **Don't**:

- Leave broad firewall ranges open
- Commit `.env` files with secrets to source control

## Next Steps

1. Set up CI/CD pipeline with `azd` integration
2. Add health checks for database connectivity
3. Implement connection pooling optimization
4. Set up alerts in Application Insights
5. Configure autoscaling based on metrics
