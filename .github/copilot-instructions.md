# Copilot Instructions for `fastapi-reference-arch`

## Build, Test, and Lint Commands

Use the Makefile targets as the primary workflow entrypoints:

- `source .venv/bin/activate && make setup` — install dependencies/hooks, start docker services, run migrations, seed sample data.
- `source .venv/bin/activate && make up` / `make down` — start or stop local API + PostgreSQL containers.
- `source .venv/bin/activate && make lint` — runs `ruff check app tests`.
- `source .venv/bin/activate && make format` — runs `isort app tests` then `black app tests`.
- `source .venv/bin/activate && make test` — runs full pytest suite.

Run a single test with pytest directly:

- `source .venv/bin/activate && pytest tests/test_todos.py::test_create_todo -q`

Database migration command used by local and deployment flows:

- `source .venv/bin/activate && bash ./infra/scripts/run_migrations.sh`

## Using MCP Servers in This Repo

- MCP config is checked in at `.vscode/mcp.json`.
- Azure server uses `npx -y @azure/mcp@latest server start`; authenticate first with `az login` in your shell.
- PostgreSQL server uses `@modelcontextprotocol/server-postgres` and prompts for `postgres_connection_string` at runtime; use the local default only if applicable: `postgresql://todo_user:todo_pass@localhost:5432/todo_db`.
- Keep credentials out of committed files; use runtime prompts/environment variables instead of hardcoding secrets.

## High-Level Architecture

- The API is mounted under `settings.api_prefix` (default `/api/v1`) in `app/main.py`, and TODO endpoints are registered at `/todos`, so effective routes are `/api/v1/todos/...`.
- Request flow is strictly layered: `routes/todos_router.py` (HTTP boundary + parameter validation) → `services/todo_service.py` (business behavior and 404 decisions) → `repo/todo_repository.py` (SQLAlchemy queries/commits).
- Runtime persistence uses async SQLAlchemy sessions from `app/core/database.py` with `settings.async_database_url`; Alembic uses the sync URL from the same settings object in `alembic/env.py`.
- Telemetry/logging are initialized at app startup: `setup_telemetry()` + `instrument_app(app)` + `CorrelationIdMiddleware`, and logs are emitted as JSON via `app/core/logging/logger.py` with trace/correlation fields when available.
- Tests run against in-memory SQLite, not PostgreSQL: `tests/conftest.py` overrides `get_db` with `sqlite+aiosqlite:///:memory:` and `StaticPool`, then exercises the API through HTTPX `AsyncClient`.
- Azure deployment is hook-driven via `azure.yaml`: preprovision and postprovision scripts prepare infra/db access, and postdeploy runs `infra/scripts/run_migrations.sh` so schema + seed behavior aligns with app deploys.

## Key Repository Conventions

- Preserve layering boundaries: route handlers should depend on `TodoService`, and data access should stay in repositories (avoid direct DB session logic in routes).
- Keep response shaping in the service layer (`TodoRead.model_validate(...)` and paginated envelope keys `items/total/limit/offset`) to match current API contracts.
- Schema normalization is part of the contract: `TodoCreate`/`TodoUpdate` validators trim strings and reject empty titles after whitespace trimming.
- Logging convention is structured JSON with contextual `extra={...}` fields; reuse `get_logger(...)` and include relevant IDs/paths in `extra` data.
- Query parameter constraints are explicit in routers (`limit: ge=1, le=100`, `offset: ge=0`) and should be maintained when extending list endpoints.
- Dependency installation source of truth is `pyproject.toml`; install dependencies with `pip install '.[dev]'`.
