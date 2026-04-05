---
name: repo-migration-safety
description: Use for Alembic migration planning, revision safety checks, and low-risk schema change workflows in this repository.
---

# Repo Migration Safety Skill

## Use When

- User asks to create, review, or troubleshoot Alembic migrations.
- User asks about postdeploy migration hook failures.
- User asks for safe schema-change sequencing across local and Azure deploy paths.

## Not For

- Do not use for general test strategy unrelated to schema changes -> route to `repo-testing`.
- Do not use for deployment orchestration beyond migration-relevant checks -> route to `repo-azure-deploy`.
- Do not use for app-layer architecture refactoring decisions -> route to `repo-architecture`.

## Primary References

- alembic/env.py
- alembic/versions/
- infra/scripts/run_migrations.sh
- app/core/database.py
- app/modules/todos/model.py
- tests/test_database_entra.py

## Standard Workflow

1. Inspect current migration chain and target model changes.
2. Ensure revision identifiers and dependencies are valid.
3. Run migrations in a controlled environment.
4. Validate app behavior and rollback path.

```bash
source .venv/bin/activate
bash ./infra/scripts/run_migrations.sh
make test
```

## Rules

1. Keep Alembic revision IDs concise and stable; avoid oversized identifiers that can break `alembic_version` storage.
2. Ensure each revision has correct `down_revision` and deterministic upgrade/downgrade logic.
3. Prefer additive, backward-compatible schema transitions when possible.
4. Verify migration scripts work in hook execution context (venv, env vars, auth mode selection).
5. Pair schema-affecting changes with relevant tests or verification steps.

## Common Failure Patterns

- Revision ID length or naming issues causing migration-table write failures.
- Incorrect `down_revision` creating branch divergence.
- Migration relying on local-only assumptions (host/user/auth mode).
- Schema change merged without corresponding repository/service behavior checks.
