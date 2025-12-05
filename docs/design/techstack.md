# Tech Stack

| Layer             | Choice                 | Notes                                                                       |
| ----------------- | ---------------------- | --------------------------------------------------------------------------- |
| API               | FastAPI                | Async-friendly, automatic docs, dependency injection.                       |
| ORM               | SQLAlchemy 2.x         | Declarative models, Alembic migrations.                                     |
| DB                | PostgreSQL 15          | Backed by Docker Compose service for local dev.                             |
| Config            | pydantic-settings      | `.env` ingestion, type-safe settings.                                       |
| Schema Validation | Pydantic v2            | Ensures request/response models stay validated and serialized consistently. |
| Lint/Format       | Ruff, Black, isort     | Enforced before pre-commit adoption.                                        |
| Testing           | pytest, httpx (later)  | Fixtures will target repository/service layers.                             |
| CI/CD             | GitHub Actions         | Runs lint, format check, tests, Docker build.                               |
| Future            | Azure Bicep + Entra ID | Reserved for infrastructure/auth follow-up.                                 |

## Developer Workflow Commands

The `Makefile` captures the common local workflows so contributors avoid memorizing long commands:

- `make setup`: Installs dependencies, runs `pre-commit install`, applies Alembic migrations, and seeds baseline data.
- `make up` / `make down`: Starts or stops the Docker Compose stack for Postgres and related services.
- `make lint`, `make format`, `make test`: Mirror the CI steps (Ruff, Black/isort, pytest) to keep local checks aligned with pipelines.

Each target is idempotent and documented inline so `make help` stays informative.
