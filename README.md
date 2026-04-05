# fastapi-reference-arch

Production-ready FastAPI reference implementing a TODO CRUD service backed by PostgreSQL and SQLAlchemy. The template (root folder name `fastapi-reference-arch`) showcases a versioned API boundary plus feature modules (`api/v1` + `modules`) and automation hooks for Azure Bicep deployments.

## Goal

Provide a reference-grade TODO management API that demonstrates FastAPI best practices, CRUD workflows, and operational readiness for Azure deployments—so new greenfield projects can start from a minimal yet well-structured baseline and layer additional features on top. This README is meant to be enough for a new developer to clone, run locally with Docker Compose, and deploy to Azure with `azd`.

## Features

- Consistent naming conventions plus linting/formatting enforcement (Ruff, Black, isort) keep the codebase uniform.
- FastAPI application using async/await end-to-end with clear boundaries between versioned HTTP contracts (`app/api/v1`) and reusable feature internals (`app/modules`).
- Async SQLAlchemy ORM stack (`asyncpg`) with Alembic migrations to manage schema changes safely.
- Pydantic-powered request/response models that validate inputs and outputs.
- Centralized exception handling maps domain/app faults to consistent HTTP error responses.
- Built-in observability via structured logs plus Application Insights/OpenTelemetry wiring.
- Configurable via `.env`, adhering to `pydantic-settings` and Twelve-Factor conventions.
- Docker Compose stack (FastAPI + PostgreSQL) for local development.
- Pytest-based async test suites exercising the full stack through HTTPX clients.

## Local Development (Docker Compose)

Prerequisites: Docker, Python 3.11+, `make`.

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

## Reference Guides

- Template implementation rules: [docs/guides/template-playbook.md](docs/guides/template-playbook.md)
- Error response envelope and examples: [docs/guides/error-contract.md](docs/guides/error-contract.md)
- Entra auth setup and verification modes: [docs/guides/auth-setup.md](docs/guides/auth-setup.md)
- Observability validation and KQL workflow: [docs/guides/observability-validation.md](docs/guides/observability-validation.md)

## Azure Deployment (azd)

**Prerequisites:**

Install these tools first:

**Linux (Ubuntu/Debian):**

```bash
# Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Azure Developer CLI
curl -fsSL https://aka.ms/install-azd.sh | bash

# Docker (required by azd package/provision preview for this template)
sudo apt-get update && sudo apt-get install -y docker.io

# PostgreSQL client
sudo apt-get update && sudo apt-get install -y postgresql-client

# Python venv + dependencies (pyproject.toml is the source of truth)
python3 -m venv .venv
source .venv/bin/activate
pip install '.[dev]'
```

**Deploy to Azure:**

```bash
az login                # azd reuses these credentials
python3 -m venv .venv   # or: py -3 -m venv .venv (Windows)
source .venv/bin/activate  # or: .\.venv\Scripts\Activate.ps1 (Windows)
pip install .[dev]
azd env new <env-name>

azd env new <env-name>

azd provision --preview

azd provision --preview
azd up                  # provision + deploy + run migrations + seed
# subsequent deploys
azd deploy
```

**Note:** Python venv must be activated for `azd up` and `azd deploy` - the postdeploy hook runs Alembic migrations which requires Python dependencies.
Also ensure Docker is installed/running before `azd provision --preview` or `azd up`.

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

Config resolution behavior:

- `--base-url` or `--env azure` defaults to auth on and telemetry-check mode on.
- Local target defaults to auth off and telemetry-check mode off.
- For auth inputs, precedence is: CLI args -> environment vars -> `azd env` values.

**Note:** On first run, `azd up` will interactively prompt you to:

- Select an Azure subscription
- Choose an existing resource group or create a new one
- Pick an Azure region (e.g., Central US)

For infrastructure internals (Bicep modules, azd hooks, migration scripts, and hardening notes), see [infra/README.md](infra/README.md) and [infra/bicep/README.md](infra/bicep/README.md).

## Project Structure

See [docs/design/projectstructure.md](docs/design/projectstructure.md) for the full directory tree and naming conventions. Additional documentation (PRD, architecture notes, tech stack, user flows) lives under [docs/design/](docs/design/).

## Database Authentication Modes

- **Local (password mode)**: Docker Compose supplies `todo_user` / `todo_pass` for the bundled PostgreSQL container. Override via `.env` if needed.
- **Azure (Microsoft Entra mode)**: The app uses the Container Apps user-assigned managed identity for PostgreSQL login. Runtime acquires short-lived Entra access tokens and does not rely on `DATABASE_PASSWORD`.

## Migrations + Config

- Azure: postdeploy hook runs migrations and seeds on every `azd deploy`.
- Azure migration hook uses Entra token auth (`DB_AUTH_MODE=aad`) and the configured PostgreSQL Entra admin identity.
- Local/CI: `bash ./infra/scripts/run_migrations.sh` (password mode for local Docker defaults, or Entra token mode when `DB_AUTH_MODE=aad`).
- Local defaults: host `postgres`, port `5432`, user `todo_user`, password `todo_pass`, db `todo_db`, `APP_ENV=development`, `LOG_LEVEL=INFO`.
- Azure env (Entra mode): `DB_AUTH_MODE=aad`, `DATABASE_HOST=<postgres-fqdn>`, `DATABASE_NAME=postgres`, `DATABASE_USER=<managed-identity-name>`, `AZURE_CLIENT_ID=<uami-client-id>`.

## Telemetry

Application Insights is enabled when `APPLICATIONINSIGHTS_CONNECTION_STRING` is set. OpenTelemetry captures request spans, dependency spans, and traces.

Observability references:

- Instrumentation details: [docs/design/instrument-flow.md](docs/design/instrument-flow.md)
- Kusto queries and suite runner: [scripts/kusto](scripts/kusto)

Run all core checks:

```bash
./scripts/kusto/run-observability-suite.sh
```

Run end-to-end timeline query directly:

```bash
az monitor app-insights query \
	--app <application-id> \
	--analytics-query "$(cat scripts/kusto/end-to-end-flow-by-operation.kql)"
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
