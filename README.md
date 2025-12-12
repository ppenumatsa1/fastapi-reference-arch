# fastapi-reference-arch

Production-ready FastAPI reference implementing a TODO CRUD service backed by PostgreSQL and SQLAlchemy. The template (root folder name `fastapi-reference-arch`) showcases layered architecture (routes → services → repositories → core) plus automation hooks for Azure Bicep deployments.

## Goal

Provide a reference-grade TODO management API that demonstrates FastAPI best practices, CRUD workflows, and operational readiness for Azure deployments—so new greenfield projects can start from a minimal yet well-structured baseline and layer additional features on top. This README is meant to be enough for a new developer to clone, run locally with Docker Compose, and deploy to Azure with `azd`.

## Features

- Consistent naming conventions plus linting/formatting enforcement (Ruff, Black, isort) keep the codebase uniform.
- FastAPI application using async/await end-to-end with a layered folder structure (routes → services → repositories) that isolates the data access layer.
- Async SQLAlchemy ORM stack (`asyncpg`) with Alembic migrations to manage schema changes safely.
- Pydantic-powered request/response models that validate inputs and outputs.
- Centralized exception handling so API errors map cleanly to HTTP responses.
- Built-in observability via structured logs plus Application Insights/OpenTelemetry wiring.
- Configurable via `.env`, adhering to `pydantic-settings` and Twelve-Factor conventions.
- Docker Compose stack (FastAPI + PostgreSQL) for local development.
- Pytest-based async test suites exercising the full stack through HTTPX clients.

## Local Development (Docker Compose)

Prerequisites: Docker, Python 3.12+, `make`.

1. Clone the repository:

```bash
git clone https://github.com/ppenumatsa1/fastapi-reference-arch.git
cd fastapi-reference-arch
```

2. Create Python virtual environment and configure:

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1
cp .env.example .env
```

3. Bring up everything, install deps, run migrations, seed data (idempotent):

```bash
make setup
```

This starts the Docker Compose stack, runs Alembic migrations, and seeds sample TODOs automatically. Logs: `docker compose logs -f api`. Stop: `make down`. Optional direct app run while DB is up: `uvicorn app.main:app --reload`. To verify the local stack: `./scripts/verify_deployment.sh --env local` (defaults to `http://localhost:8000`).

Environment flags worth tweaking while developing:

- `APP_DEBUG=true` keeps FastAPI in debug mode.
- `LOG_LEVEL=DEBUG` turns on verbose JSON logs.
- `DATABASE_URL` / `ASYNC_DATABASE_URL` (optional) override assembled DSNs if you need a custom connection string.

## Common Make Targets

| Target                  | Purpose                                                                                          |
| ----------------------- | ------------------------------------------------------------------------------------------------ |
| `make setup`            | Installs Python deps, installs `pre-commit`, applies Alembic migrations, seeds sample TODO rows. |
| `make up` / `make down` | Starts or stops the Docker Compose stack (API + PostgreSQL).                                     |
| `make up-build`         | Rebuilds Docker images (e.g., after dependency changes) before starting the stack.               |
| `make lint`             | Runs `ruff check` via `scripts/lint.sh`.                                                         |
| `make format`           | Runs `isort` and `black` through `scripts/format.sh`.                                            |
| `make test`             | Executes `pytest` by delegating to `scripts/test.sh`.                                            |

Run `make help` to see the latest list as new automation hooks are added.

## Azure Deployment (azd)

**Prerequisites:**

Install these tools first:

**Linux (Ubuntu/Debian):**

```bash
# Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Azure Developer CLI
curl -fsSL https://aka.ms/install-azd.sh | bash

# PostgreSQL client
sudo apt-get update && sudo apt-get install -y postgresql-client

# Python venv + dependencies (pyproject is the source of truth; requirements.txt points to it)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # or: pip install '.[dev]'
```

**Windows (PowerShell as Administrator):**

```powershell
# Azure CLI
winget install Microsoft.AzureCLI

# Azure Developer CLI
winget install Microsoft.Azd

# PostgreSQL client
winget install PostgreSQL.PostgreSQL

# Python venv + dependencies (pyproject is the source of truth; requirements.txt points to it)
py -3 -m venv .venv
\.venv\Scripts\Activate.ps1
pip install -r requirements.txt   # or: pip install .[dev]
```

**Deploy to Azure:**

```bash
az login                # azd reuses these credentials
python3 -m venv .venv   # or: py -3 -m venv .venv (Windows)
source .venv/bin/activate  # or: .\.venv\Scripts\Activate.ps1 (Windows)
pip install -r requirements.txt   # or: pip install .[dev]
azd env new <env-name>
azd up                  # provision + deploy + run migrations + seed
# subsequent deploys
azd deploy
```

**Note:** Python venv must be activated for `azd up` and `azd deploy` - the postdeploy hook runs Alembic migrations which requires Python dependencies.

**Verify deployment:**

```bash
# Azure (uses CONTAINER_APP_FQDN or azd env)
./scripts/verify_deployment.sh --env azure

# Local (defaults to localhost:8000)
./scripts/verify_deployment.sh --env local

# Explicit URL override (any environment)
./scripts/verify_deployment.sh --base-url https://my-app.azurecontainerapps.io
```

Runs automated tests to verify health, DB reads, and writes. The script defaults to local mode; Azure mode requires `CONTAINER_APP_FQDN` (or an azd env with that value) unless `--base-url` is provided.

**Note:** On first run, `azd up` will interactively prompt you to:

- Select an Azure subscription
- Choose an existing resource group or create a new one
- Pick an Azure region (e.g., Central US)

What azd hooks do (summary):

- Pre-provision ([infra/hooks/preprovision.sh](infra/hooks/preprovision.sh)): sets location/resource group defaults; generates Postgres admin and `todo_user` passwords into the azd env.
- Bicep ([infra/bicep](infra/bicep)): provisions Container Apps, PostgreSQL Flexible Server, ACR, identities, and wiring.
- Post-provision ([infra/hooks/postprovision.sh](infra/hooks/postprovision.sh)): creates `todo_user`, grants CONNECT/USAGE/CREATE and DML/sequence rights on `public`.
- Post-deploy ([infra/scripts/run_migrations.sh](infra/scripts/run_migrations.sh)): builds DSNs from env/Key Vault, runs `alembic upgrade head`, then seeds sample todos (idempotent).

Each deployment uses a unique image tag (`azd-deploy-<timestamp>`) for traceability and rollback capability.

Network/firewall: PostgreSQL firewall allows all IPv4 by default for development. Lock down in production via [infra/bicep/modules/postgres.bicep](infra/bicep/modules/postgres.bicep). For deeper details, see [infra/bicep/README.md](infra/bicep/README.md).

## Project Structure

See [docs/design/projectstructure.md](docs/design/projectstructure.md) for the full directory tree and naming conventions. Additional documentation (PRD, architecture notes, tech stack, user flows) lives under [docs/design/](docs/design/).

## Database Authentication Modes

- **Local (password mode)**: Docker Compose supplies `todo_user` / `todo_pass` for the bundled PostgreSQL container. Override via `.env` if needed.
- **Azure (password mode)**: The app uses a dedicated `todo_user` whose password lives in Key Vault as `todo-db-password`; Container Apps injects it via secret reference. The azd hooks create/rotate the user and grant the required privileges.

## Migrations + Config

- Azure: postdeploy hook runs migrations and seeds on every `azd deploy`.
- Local/CI: `bash ./infra/scripts/run_migrations.sh` (honors `DATABASE_*` / `TODO_DB_*`; can pull password from Key Vault when `AZURE_KEY_VAULT_NAME`/`KEYVAULT_NAME` are set).
- Local defaults: host `postgres`, port `5432`, user `todo_user`, password `todo_pass`, db `todo_db`, `APP_ENV=development`, `LOG_LEVEL=INFO`.
- Azure env (password mode): see the app variables listed in [infra/bicep/README.md](infra/bicep/README.md#app-configuration-azure-password-mode).

## Telemetry

Application Insights is wired for the API; it activates when `APPLICATIONINSIGHTS_CONNECTION_STRING` is set. OpenTelemetry captures FastAPI, SQLAlchemy, and logging spans.
