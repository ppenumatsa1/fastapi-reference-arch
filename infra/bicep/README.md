# Azure IaC (Bicep)

This folder hosts the azd-compatible Bicep templates that provision the FastAPI reference stack on Azure Container Apps plus Azure Database for PostgreSQL.

## Layout

```
infra/bicep/
├── README.md                # You are here
├── main.bicep               # Root template orchestrating all modules
├── main.parameters.json     # Parameter file for azd/automation
└── modules/
    ├── aca.bicep            # Container Apps environment + app
    ├── identity.bicep       # Managed identities
    ├── monitoring.bicep     # Log Analytics + App Insights
    ├── network.bicep        # Single VNet + subnets
    ├── postgres.bicep       # Azure Database for PostgreSQL flexible server
    ├── registry.bicep       # Azure Container Registry
    └── rbac.bicep           # Role assignments (ACR + PostgreSQL)
```

Each module follows the `az{prefix}{token}` naming rule required by the deployment policy and emits IDs needed by downstream modules. Sensitive values are never committed; use azd environment secrets or pipeline variables to populate secure parameters at deploy time.

## Prerequisites

Before provisioning, ensure you have:

- **Azure CLI** (≥ 2.60): `az --version`
- **Bicep CLI**: bundled with Azure CLI or standalone via `az bicep install`
- **Azure Developer CLI (azd)**: install from [aka.ms/azd](https://aka.ms/azd)
- An active Azure subscription with permissions to create resources and assign RBAC roles

Sign in and set your default subscription:

```bash
az login
az account set --subscription <subscription-id>
```

## Parameters & Conventions

- `environmentName` and `location` are mandatory; azd injects them as `AZURE_ENV_NAME` and `AZURE_LOCATION`.
- `postgresAdminPassword` is marked `@secure()`. Store it as an azd secret: `azd env set POSTGRES_ADMIN_PASSWORD '<strong-password>' --secret`.
- `aadAdministrator` must describe the Entra ID principal (user, group, or service principal) that manages PostgreSQL. Provide `principalName`, `principalType`, `principalId` (object ID), and `tenantId`. This enables the user-assigned managed identity to gain database roles via RBAC.
- `postgresFirewallRules` must list IPv4 ranges allowed to reach PostgreSQL's public endpoint. Initially provision without ACA IPs, then update after deployment (see steps below).
- `serviceName` defaults to `api` and tags the Container App with `azd-service-name`.
- Container Apps uses the required base image `mcr.microsoft.com/azuredocs/containerapps-helloworld:latest` initially. Swap to your FastAPI image during CI/CD.

## Streamlined Provisioning with azd

The infrastructure setup uses **azd hooks** to automate AAD Service Principal creation and environment configuration. Everything runs with a single command.

### Quick Start

From the repo root:

```bash
# Create environment and provision all resources
azd up

# Or provision infrastructure only (without deployment)
azd provision
```

That's it! The preprovision hook automatically:

- Creates/reuses a Service Principal for PostgreSQL AAD admin
- Generates a secure PostgreSQL password
- Sets all required environment variables
- Configures Bicep parameters

### What Happens Behind the Scenes

1. **Pre-provision Hook** (`infra/hooks/preprovision.sh`):

   - Creates Service Principal: `sp-postgres-admin-<env-name>`
   - Sets environment variables:
     - `AZURE_LOCATION` (default: canadacentral)
     - `AZURE_RESOURCE_GROUP` (rg-<env-name>)
     - `AAD_ADMIN_PRINCIPAL_NAME`
     - `AAD_ADMIN_PRINCIPAL_ID`
     - `AAD_ADMIN_TENANT_ID`
     - `POSTGRES_ADMIN_PASSWORD` (auto-generated if not set)

2. **Bicep Deployment**:
   - Reads values from azd environment variables
   - Deploys all modules in dependency order
   - Creates resources with proper RBAC assignments

### Manual Configuration (Optional)

If you want to customize settings before provisioning:

```bash
# Create environment
azd env new <env-name>

# Set custom location (optional, defaults to canadacentral)
azd env set AZURE_LOCATION eastus

# Set custom password (optional, auto-generated if not provided)
azd env set POSTGRES_ADMIN_PASSWORD '<strong-password>' --no-prompt

# Now provision
azd provision
```

### Parameters

All parameters are now managed through `azd env` variables or defaults:

- `environmentName`: automatically from `AZURE_ENV_NAME`
- `location`: from `AZURE_LOCATION` (default: canadacentral)
- `serviceName`: defaults to `api`
- `aadAdministrator`: auto-populated from preprovision hook
- `postgresAdminPassword`: auto-generated or from environment

The `main.parameters.json` file uses variable substitution - no manual editing required

### 5. Capture ACA Outbound IPs

Once the Container App environment is deployed, retrieve its outbound IP addresses:

```bash
MANAGED_ENV_NAME=$(az containerapp env list -g <resource-group> --query "[0].name" -o tsv)
az containerapp env show -n $MANAGED_ENV_NAME -g <resource-group> \
  --query "properties.staticIp" -o tsv
```

Or get all outbound IPs if available in your API version:

```bash
az containerapp env show -n $MANAGED_ENV_NAME -g <resource-group> \
  --query "properties.outboundIpAddresses[]" -o tsv
```

### 6. Update Firewall Rules

Add the ACA IPs to `postgresFirewallRules` in `main.parameters.json`:

```json
"postgresFirewallRules": {
  "value": [
    {
      "name": "aca-egress-1",
      "startIpAddress": "20.51.x.x",
      "endIpAddress": "20.51.x.x"
    }
  ]
}
```

Re-run provisioning to apply the firewall updates:

```bash
azd provision \
  --template-file infra/bicep/main.bicep \
  --parameters @infra/bicep/main.parameters.json \
  --parameters postgresAdminPassword=$POSTGRES_ADMIN_PASSWORD
```

### 7. Verify Role Assignments

Confirm the user-assigned managed identity has the required roles:

```bash
UAMI_PRINCIPAL_ID=$(az identity show -n <identity-name> -g <resource-group> --query principalId -o tsv)
az role assignment list --assignee $UAMI_PRINCIPAL_ID --all -o table
```

You should see:

- `AcrPull` scoped to the Container Registry
- `PostgreSQL Flexible Server Contributor` scoped to the PostgreSQL server

### 8. Validate Database Access

Connect to PostgreSQL using the AAD admin credentials and verify the managed identity principal appears:

```bash
psql "host=<postgres-fqdn> dbname=postgres user=<aad-admin-email> sslmode=require"
```

Inside psql:

```sql
SELECT * FROM pgaadauth_list_principals();
```

The user-assigned managed identity should be listed once it connects.

## Outputs

After successful provisioning, azd stores these outputs (view with `azd env get-values`):

- `RESOURCE_GROUP_ID`: Full resource ID of the resource group
- `AZURE_CONTAINER_REGISTRY_ENDPOINT`: ACR login server for image pushes
- `CONTAINER_APP_FQDN`: Public FQDN of the Container App
- `POSTGRES_FQDN`: Fully qualified domain name of the PostgreSQL server

Use these in subsequent deployment steps or CI/CD pipelines.

## Next Steps (CI/CD with GitHub Actions)

Once azd provisioning works locally, create a deployment pipeline:

1. **Store secrets in GitHub**: Add `AZURE_CREDENTIALS`, `POSTGRES_ADMIN_PASSWORD`, and AAD details as repository secrets.
2. **Build and push image**: Use `docker build` to create the FastAPI image, then push to ACR using the managed identity (via `az acr login` with service principal or federated credentials).
3. **Update Container App**: Run `az containerapp revision create` to deploy the new image revision, referencing the ACR image. The user-assigned managed identity automatically pulls the image (no Docker credentials needed).
4. **Run migrations**: Execute Alembic migrations from a job/init container using the same managed identity to authenticate to PostgreSQL via AAD.

Because the user-assigned managed identity holds both `AcrPull` and `PostgreSQL Flexible Server Contributor`, runtime operations require zero secrets.
