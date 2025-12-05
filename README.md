# fastapi-reference-arch

Production-ready FastAPI reference implementing a TODO CRUD service backed by PostgreSQL and SQLAlchemy. The template (root folder name `fastapi-reference-arch`) showcases layered architecture (routes → services → repositories → core) plus automation hooks for future Azure Bicep deployments.

## Goal

Provide a reference-grade TODO management API that demonstrates FastAPI best practices, CRUD workflows, and operational readiness for Azure deployments—so new greenfield projects can start from a minimal yet well-structured baseline and layer additional features on top.

## Features

- FastAPI application with structured routing and dependency injection.
- SQLAlchemy ORM models + Alembic migrations targeting PostgreSQL.
- Configurable via `.env`, adhering to `pydantic-settings` and Twelve-Factor conventions.
- Docker Compose stack (FastAPI + PostgreSQL) for local development.
- Ruff linting, Black formatting, and isort import management wired through `pyproject.toml`.
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
| `make lint`             | Runs `ruff check` via `scripts/lint.sh`.                                                         |
| `make format`           | Runs `isort` and `black` through `scripts/format.sh`.                                            |
| `make test`             | Executes `pytest` by delegating to `scripts/test.sh`.                                            |

Run `make help` to see the latest list as new automation hooks are added.

## Project Structure

docs/design/

```
fastapi-reference-arch/
├── app/
│   ├── core/
│   ├── routes/
│   ├── services/
│   └── repo/
├── infra/
├── docs/design/
├── scripts/
├── tests/
├── docker-compose.yml
├── Dockerfile
└── README.md
```

Detailed documentation lives under [`docs/design/`](docs/design/) (PRD, architecture, tech stack, and user flows).
