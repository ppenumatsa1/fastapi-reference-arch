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

See [`docs/design/projectstructure.md`](docs/design/projectstructure.md) for the full directory tree and naming conventions. Additional documentation (PRD, architecture notes, tech stack, user flows) lives under [`docs/design/`](docs/design/).

## Azure Deployment

Deploy to Azure Container Apps with PostgreSQL using Azure Developer CLI (azd):

```bash
# One-command deployment (infrastructure + code)
azd up

# Or provision infrastructure only
azd provision

# Deploy application updates
azd deploy
```

The `azd` hooks automatically handle:

- Service Principal creation for PostgreSQL AAD authentication
- Secure password generation
- Environment variable configuration
- Resource group and Azure resource provisioning

See [`infra/bicep/README.md`](infra/bicep/README.md) for detailed infrastructure documentation and customization options.

### Prerequisites for Azure Deployment

- Azure CLI: `az login` with appropriate subscription permissions
- Azure Developer CLI: install from [aka.ms/azd](https://aka.ms/azd)
- Permissions to create Service Principals and assign RBAC roles
