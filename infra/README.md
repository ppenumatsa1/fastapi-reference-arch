# Infrastructure Overview

Infrastructure automation assets live here. Current focus is local tooling; Azure Bicep templates and deployment manifests will be added in a later iteration.

## Scripts

- `scripts/bootstrap_db.sh` – ensures the PostgreSQL container is ready and applies Alembic migrations.
- `scripts/run_migrations.sh` – helper invoked by CI/CD to run Alembic upgrades.

## Future Work

- Azure Bicep modules for managed PostgreSQL + container hosting.
- Entra ID integration wiring (app registration, secrets, and role bindings).
