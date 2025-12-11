# fastapi-reference-arch

Production-ready FastAPI reference implementing a TODO CRUD service backed by PostgreSQL and SQLAlchemy. The template (root folder name `fastapi-reference-arch`) showcases layered architecture (routes → services → repositories → core) plus automation hooks for future Azure Bicep deployments.

## Goal

Provide a reference-grade TODO management API that demonstrates FastAPI best practices, CRUD workflows, and operational readiness for Azure deployments—so new greenfield projects can start from a minimal yet well-structured baseline and layer additional features on top.

## Features

- Consistent naming conventions plus linting/formatting enforcement (Ruff, Black, isort) keep the codebase uniform.
- FastAPI application using async/await end-to-end with a layered folder structure (routes → services → repositories) that isolates the data access layer.
- Async SQLAlchemy ORM stack (`asyncpg`) with Alembic migrations to manage schema changes safely.
- Pydantic-powered request/response models that validate inputs and outputs.
- Centralized exception handling so API errors map cleanly to HTTP responses.
- Built-in observability via structured logs today and ready hooks for metrics/traces.
- Configurable via `.env`, adhering to `pydantic-settings` and Twelve-Factor conventions.
- Docker Compose stack (FastAPI + PostgreSQL) for local development.
- Pytest-based async test suites exercising the full stack through HTTPX clients.
- GitHub Actions workflow (to be added) covering lint, format check, tests, and image build.

## Getting Started

Create and activate a virtual environment, copy the sample env file, then start the Docker stack so PostgreSQL is available:

```bash
python -m venv .venv
source .venv/bin/activate
cp .env.example .env
make up
```

> Ensure Docker Desktop/daemon is running before invoking `make up`.

Once the stack is running, stream FastAPI logs with `docker compose logs -f api`. If you prefer an
all-in-one command that starts the stack and streams immediately, run `docker compose up` (stop
with `Ctrl+C`, which also stops the containers).

`make setup` installs project requirements, wires up `pre-commit`, runs all Alembic migrations, and seeds baseline TODO data:

```bash
make setup
```

Environment flags worth tweaking while developing:

- `APP_DEBUG=true` keeps FastAPI in debug mode so tracebacks surface immediately.
- `LOG_LEVEL=DEBUG` turns on verbose JSON logs (router → service → repository) without code changes.
- `DATABASE_URL` / `ASYNC_DATABASE_URL` (optional) let you override the assembled DSNs if you need a fully custom connection string for sync migrations or the async app runtime.

Stop the containers when you are done:

```bash
make down
```

You can still run FastAPI directly if needed while the database container is up:

```bash
uvicorn app.main:app --reload
```

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

## Project Structure

See [docs/design/projectstructure.md](docs/design/projectstructure.md) for the full directory tree and naming conventions. Additional documentation (PRD, architecture notes, tech stack, user flows) lives under [docs/design/](docs/design/).

## Database Authentication Modes

- **Local (password mode)**: Docker Compose supplies `todo_user` / `todo_pass` for the bundled PostgreSQL container. Override via `.env` if needed.
- **Azure (AAD mode)**: The app uses `DefaultAzureCredential` with the user-assigned managed identity (UAMI). Tokens are scoped to `https://ossrdbms-aad.database.windows.net/.default` and passed as the connection password—no database passwords in Azure. UAMI is not AAD admin; post-provision grants it `db_owner` so it can CRUD without admin rights.

## Azure Deployment (azd)

Prerequisites: Azure CLI (`az login`), Azure Developer CLI (`azd`), rights to create identities/RBAC assignments, and permission to create app registrations. Install `psql` so the hook can grant DB roles. If app registration is blocked, pre-seed `AAD_ADMIN_*` in the azd env.

Identity model for Azure:

- **Your user**: runs `azd up/azd deploy` and has app registration rights.
- **Migration SP (created by hook)**: created/rotated during postprovision, set as PostgreSQL AAD admin, used by postdeploy to run migrations.
- **UAMI (runtime)**: used by Container Apps to pull from ACR and connect to Postgres; postprovision grants it `db_owner` for app CRUD.

Happy-path flow:

```bash
# Log in with your user that can create app registrations
az login

# Provision infra + deploy app
azd up

# Or provision only
azd provision

# Deploy latest code (after changes)
azd deploy
```

What azd hooks do behind the scenes:

- Pre-provision hook generates azd env values and the break-glass Postgres password.
- Bicep deploys Container Apps, PostgreSQL Flexible Server, ACR, identities, and RBAC (UAMI for runtime, ACR pull).
- Post-provision hook creates/rotates the migration SP, sets it as PostgreSQL AAD admin, and grants the UAMI `db_owner` in Postgres.
- Post-deploy hook runs Alembic migrations via the migration SP.

Network/firewall: PostgreSQL firewall is set to allow all IPv4 by default for development. Tighten this for production by editing the firewall rule in [infra/bicep/modules/postgres.bicep](infra/bicep/modules/postgres.bicep) or via the portal.

## Migrations (AAD + Alembic)

How it works:

- The postprovision hook creates/rotates `sp-<env>-migration`, sets it as PostgreSQL AAD admin, and grants the UAMI `db_owner` for runtime CRUD.
- `infra/scripts/run_migrations.sh` uses the migration SP creds from the azd env, fetches an `oss-rdbms` access token, sets `PGPASSWORD` to the token, and runs `alembic upgrade head` (invoked automatically by the postdeploy hook).

Run migrations locally or in CI:

```bash
export MIGRATION_SP_APP_ID=$(azd env get-value MIGRATION_SP_APP_ID)
export MIGRATION_SP_PASSWORD=$(azd env get-value MIGRATION_SP_PASSWORD)
export MIGRATION_SP_TENANT_ID=$(azd env get-value MIGRATION_SP_TENANT_ID)
export POSTGRES_FQDN=$(azd env get-value POSTGRES_FQDN)
export POSTGRES_DB=$(azd env get-value POSTGRES_DB)
export AZURE_ENV_NAME=$(azd env get-value AZURE_ENV_NAME)

make migrate        # or: bash ./infra/scripts/run_migrations.sh
```

Seeding: after migrations, run `make seed` to load baseline TODO data.

Why this model: managed identities cannot emit `AAD_AUTH_TOKENTYPE_APP_USER` tokens outside Azure; a dedicated migration service principal (APP token) works from any runner while the app continues to use its managed identity at runtime.

## Configuration Reference

Local `.env` defaults (password mode):

```env
DATABASE_HOST=postgres
DATABASE_PORT=5432
DATABASE_USER=todo_user
DATABASE_PASSWORD=todo_pass
DATABASE_NAME=todo_db
APP_ENV=development
LOG_LEVEL=INFO
```

Azure environment (AAD mode) variables provided by azd/Bicep:

```env
DB_AUTH_MODE=aad
DATABASE_HOST=<postgres-fqdn>
DATABASE_PORT=5432
DATABASE_NAME=postgres
DATABASE_USER=<managed-identity-client-id>
AZURE_CLIENT_ID=<managed-identity-client-id>
APPLICATIONINSIGHTS_CONNECTION_STRING=<connection-string>
APP_ENV=<environment-name>
LOG_LEVEL=INFO
```

## Telemetry

Application Insights is wired for the API; it activates when `APPLICATIONINSIGHTS_CONNECTION_STRING` is set. OpenTelemetry captures FastAPI, SQLAlchemy, and logging spans.
