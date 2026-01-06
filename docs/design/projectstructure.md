# Project Structure

```
fastapi-reference-arch/
├── app/
│   ├── main.py
│   ├── models/
│   │   └── todo.py
│   ├── schemas/
│   │   └── todo.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── exceptions/
│   │   │   └── app_exceptions.py
│   │   ├── logging/
│   │   │   └── logger.py
│   │   ├── middleware/
│   │   ├── observability/
│   │   │   └── telemetry.py
│   │   ├── security/
│   │   └── utils/
│   ├── repo/
│   │   ├── base.py
│   │   └── todo_repository.py
│   ├── routes/
│   │   └── todos_router.py
│   └── services/
│       └── todo_service.py
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 20241205_create_todos_table.py
├── infra/
│   ├── bicep/
│   │   ├── main.bicep
│   │   ├── main.parameters.json
│   │   └── modules/
│   │       ├── aca.bicep
│   │       ├── identity.bicep
│   │       ├── keyvault.bicep
│   │       ├── monitoring.bicep
│   │       ├── network.bicep
│   │       ├── postgres.bicep
│   │       ├── rbac.bicep
│   │       └── registry.bicep
│   ├── hooks/
│   │   ├── postpackage.sh
│   │   ├── postprovision.sh
│   │   └── preprovision.sh
│   └── scripts/
│       ├── bootstrap_db.sh
│       └── run_migrations.sh
├── scripts/
│   ├── format.sh
│   ├── lint.sh
│   ├── seed_data.py
│   └── test.sh
├── tests/
│   ├── conftest.py
│   └── test_todos.py
├── docs/
│   └── design/
│       ├── prd.md
│       ├── projectstructure.md
│       ├── techstack.md
│       └── userflow.md
├── alembic.ini
├── azure.yaml
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── pyproject.toml
├── README.md
└── requirements.txt
```

## Naming Conventions

- Files/directories: `snake_case`
- Classes: `PascalCase`
- Routes: plural nouns (`/todos`, `/api/v1/todos`)
- Services/repositories: mirror entity names (`TodoService`, `TodoRepository`)

## Directory Purposes

- **app/**: FastAPI application code
  - **models/**: SQLAlchemy ORM models (domain entities)
  - **schemas/**: Pydantic schemas (request/response DTOs)
  - **core/**: shared infrastructure (config, database, exceptions, logging, observability)
  - **repo/**: data access layer (repositories)
  - **routes/**: API route handlers (routers)
  - **services/**: business logic layer
- **alembic/**: database migration scripts
- **infra/**: infrastructure-as-code (Bicep), deployment hooks, and scripts
- **scripts/**: development automation (lint, format, test, seed)
- **tests/**: pytest test suites
- **docs/design/**: architecture and design documentation

## Design Rationale

### Domain vs. Infrastructure Separation

Models (`app/models`) and schemas (`app/schemas`) are kept at the application root level, separate from `core/`, to maintain a clear distinction between:

- **Domain artifacts**: Business entities (SQLAlchemy models) and API contracts (Pydantic schemas) that change with feature requirements
- **Infrastructure concerns**: Configuration, database engine, logging, middleware, and observability that change with operational requirements

This separation:
- Improves cognitive clarity for feature developers who primarily work with models/schemas
- Reduces coupling between domain logic and infrastructure utilities
- Makes import paths more intuitive (`from app.models import Todo` vs. `from app.core.models import Todo`)
- Facilitates future bounded context organization if the application grows
