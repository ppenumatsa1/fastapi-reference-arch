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

````bash
python -m venv .venv
source .venv/bin/activate
cp .env.example .env
make up
Environment flags worth tweaking while developing:

- `APP_DEBUG=true` keeps FastAPI in debug mode so tracebacks surface immediately.
- `LOG_LEVEL=DEBUG` turns on verbose JSON logs (router → service → repository) without code changes.
- `DATABASE_URL` / `ASYNC_DATABASE_URL` (optional) let you override the assembled DSNs if you need a fully custom connection string for sync migrations or the async app runtime.

Stop the containers when you are done:

```bash
make down
````

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

See [`docs/design/projectstructure.md`](docs/design/projectstructure.md) for the full directory tree and naming conventions. Additional documentation (PRD, architecture notes, tech stack, user flows) lives under [`docs/design/`](docs/design/).

## Azure Deployment

Deploy to Azure Container Apps with PostgreSQL Flexible Server using Azure Developer CLI (azd). The application uses **Managed Identity** for passwordless database authentication and **Application Insights** for telemetry.

### Quick Start

```bash
# Provision infrastructure (one-time or when infra changes)
azd env set MY_IP_ADDRESS <your.ip.addr>
azd provision

# Deploy app + run migrations via CI/CD (see .github/workflows/ci.yml)
azd deploy
```

### Key Features

- **Passwordless Authentication**: Uses User-Assigned Managed Identity (UAMI) for PostgreSQL access
- **Public PG with Firewall**: Postgres is public but locked to ACA outbound IPs + your IP
- **Application Insights**: OpenTelemetry instrumentation with automatic trace/span correlation
- **Environment-aware**: Seamlessly switches between local Docker (password) and Azure (AAD)
- **CI/CD Migrations**: Database schema changes run in GitHub Actions before deployment

### What Gets Created

- Container Registry for Docker images
- Container Apps Environment with VNet integration
- PostgreSQL Flexible Server with AAD authentication
- User-Assigned Managed Identity for app authentication
- Application Insights for telemetry and monitoring
- Firewall rules limiting Postgres access to ACA + developer IPs

### Documentation

- **[Deployment Guide](docs/DEPLOYMENT.md)**: Deployment walkthrough with MI setup
- **[Infrastructure README](infra/bicep/README.md)**: Bicep modules and configuration details

### Prerequisites

- Azure CLI: `az login` with subscription permissions
- Azure Developer CLI: install from [aka.ms/azd](https://aka.ms/azd)
- PostgreSQL client (`psql`) if you want local psql access during troubleshooting
- Permissions to create RBAC assignments
