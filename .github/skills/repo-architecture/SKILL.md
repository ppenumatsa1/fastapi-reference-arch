---
name: repo-architecture
description: Use for questions or changes about project layering, module boundaries, API contracts, and where code should live in this FastAPI reference architecture.
---

# Repo Architecture Skill

## Use When

- User asks where to place code.
- User asks for architecture review or modularity guidance.
- User asks to add or refactor features in this repository.
- User asks about adding a new module, router, schema, service, repository, mapper, or migration touchpoints for a feature.

## Not For

- Do not use for running deployment commands (`azd`, Bicep apply/provision) -> route to `repo-azure-deploy`.
- Do not use for telemetry/KQL validation and postdeploy observability checks -> route to `repo-observability`.
- Do not use for Azure cost, quota, or RBAC optimization tasks -> route to dedicated Azure skills.

## Primary References

- docs/design/projectstructure.md
- docs/guides/template-playbook.md
- docs/design/userflow.md
- app/main.py
- app/api/v1/routers/todos.py
- app/modules/todos/service.py
- app/modules/todos/repository.py

## Rules

1. Keep layering strict: API router -> service -> repository.
2. Keep API DTOs in app/api/v1/schemas and internal schemas in app/modules/\*/schemas.
3. Keep route handlers free from direct DB session logic.
4. Keep response shaping and domain error decisions in services.
5. Raise AppError subclasses for domain/application faults and rely on global exception handlers.
6. For new features, keep feature-local artifacts together under `app/modules/<feature>/` and expose only API contracts through `app/api/v1`.

## Quick Validation

Run after architecture-affecting changes:

```bash
source .venv/bin/activate && make lint && make test
```

## Common Failure Patterns

- Router importing repository directly.
- Service returning raw ORM model instead of module/API schema.
- API versioning leakage into module internals.
