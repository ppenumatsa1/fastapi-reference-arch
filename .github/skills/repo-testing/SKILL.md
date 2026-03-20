---
name: repo-testing
description: Use for test strategy, pytest execution patterns, and test-safe changes in this FastAPI reference architecture.
---

# Repo Testing Skill

## Use When

- User asks to run tests, debug test failures, or add/update tests.
- User asks for safe command order after code changes (`lint`, `test`, targeted pytest).
- User asks how to test API behavior for routers/services/repositories.

## Not For

- Do not use for deployment/provisioning workflows (`azd`, Bicep) -> route to `repo-azure-deploy`.
- Do not use for migration design or Alembic revision safety -> route to `repo-migration-safety`.
- Do not use for Entra auth setup and app-role configuration -> route to `repo-auth-entra`.

## Primary References

- scripts/test.sh
- scripts/lint.sh
- tests/conftest.py
- tests/test_todos.py
- tests/test_auth.py
- tests/test_token_validation.py
- tests/test_database_entra.py
- pyproject.toml

## Standard Workflow

1. Activate virtual environment.
2. Run lint first for fast feedback.
3. Run focused tests for touched behavior.
4. Run full suite before merge.

```bash
source .venv/bin/activate
make lint
pytest tests/test_todos.py -q
make test
```

## Rules

1. Prefer smallest failing test reproduction before broad refactors.
2. Keep API behavior tests at HTTP boundary using test client fixtures from `tests/conftest.py`.
3. Add or update tests when changing contracts (status codes, response shapes, auth requirements).
4. Keep deterministic assertions; avoid sleep-based flakiness unless validating ingestion delays explicitly.
5. Preserve SQLite-based test isolation in `tests/conftest.py` unless test intent requires alternate DB mode.

## Common Failure Patterns

- Running tests without virtualenv dependencies activated.
- Updating endpoint behavior without matching assertions in API tests.
- Mixing module internals with API DTO expectations in test assertions.
- Assuming PostgreSQL-specific behavior in tests that run against SQLite.
