# Project Structure

```
fastapi-reference-arch/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── routers/
│   │       │   ├── __init__.py
│   │       │   └── users.py
│   │       └── schemas/
│   │           ├── __init__.py
│   │           └── users.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── exceptions/
│   │   │   ├── __init__.py
│   │   │   └── app_exceptions.py
│   │   ├── logging/
│   │   │   ├── __init__.py
│   │   │   └── logger.py
│   │   ├── middleware/
│   │   │   └── correlation.py
│   │   ├── observability/
│   │   │   ├── __init__.py
│   │   │   └── telemetry.py
│   │   └── utils/
│   ├── modules/
│   │   ├── __init__.py
│   │   └── users/
│   │       ├── __init__.py
│   │       ├── mapper.py
│   │       ├── model.py
│   │       ├── repository.py
│   │       ├── schemas.py
│   │       └── service.py
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 20241205_create_users_table.py
├── infra/
│   ├── bicep/
│   │   ├── main.bicep
│   │   ├── main.json
│   │   ├── main.parameters.json
│   │   └── modules/
│   │       ├── aca.bicep
│   │       ├── identity.bicep
│   │       ├── keyvault.bicep
│   │       ├── monitoring.bicep
│   │       ├── postgres.bicep
│   │       ├── rbac.bicep
│   │       └── registry.bicep
│   ├── hooks/
│   │   ├── postprovision.sh
│   │   └── preprovision.sh
│   └── scripts/
│       ├── bootstrap_db.sh
│       └── run_migrations.sh
├── scripts/
│   ├── format.sh
│   ├── kusto/
│   │   ├── requests.kql
│   │   ├── dependencies.kql
│   │   ├── exceptions.kql
│   │   ├── traces.kql
│   │   ├── end-to-end-flow-by-operation.kql
│   │   └── run-observability-suite.sh
│   ├── lint.sh
│   ├── seed_data.py
│   ├── test.sh
│   └── verify_deployment.sh
├── tests/
│   ├── conftest.py
│   └── test_users.py
├── docs/
│   ├── guides/
│   │   ├── error-contract.md
│   │   └── template-playbook.md
│   └── design/
│       ├── instrument-flow.md
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
└── README.md
```

## Naming Conventions

- Files/directories: `snake_case`
- Classes: `PascalCase`
- Routes: plural nouns (`/users`, `/api/v1/users`)
- Services/repositories: mirror entity names (`UserService`, `UserRepository`)

## Directory Purposes

- **app/**: FastAPI application code
  - **api/v1/**: versioned HTTP layer (routers + API contract schemas)
  - **modules/**: feature modules that contain business logic and persistence
    - **modules/users/**: internal user model, service, repository, schemas, and mapping helpers
  - **core/**: shared infrastructure (config, database, exceptions, logging, observability)
- **alembic/**: database migration scripts
- **infra/**: infrastructure-as-code (Bicep), deployment hooks, and scripts
- **scripts/**: development automation (lint, format, test, seed)
  - **scripts/kusto/**: operational observability queries and suite runner
- **tests/**: pytest test suites
- **docs/guides/**: reusable implementation guides and contracts
- **docs/design/**: architecture and design documentation

## Design Rationale

### Versioned API Boundary + Feature Modules

The structure separates external API contracts from internal feature implementation:

- **API boundary (`app/api/v1`)**: request/response contracts and route declarations that are version-specific
- **Feature internals (`app/modules/users`)**: business logic, data access, and persistence models that should stay reusable across API versions
- **Infrastructure (`app/core`)**: platform concerns such as config, db lifecycle, middleware, logging, and telemetry

This separation:

- Keeps version churn isolated to `api/vX` folders
- Allows future `v2` to reuse the same module services/repositories with a different HTTP contract
- Improves discoverability for contributors by making API and module responsibilities explicit

## Reference Playbook

For future projects using this repo as a template:

1. Build each business capability under `app/modules/<feature>/`.
2. Keep HTTP contracts versioned under `app/api/v1/` and avoid leaking API DTOs into services.
3. Raise `AppError` subclasses in services and convert them to HTTP responses with global handlers in `app/main.py`.
4. Introduce `app/api/v2/` only when an API contract change is breaking; keep module internals reusable.
