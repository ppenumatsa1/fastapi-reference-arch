---
name: repo-auth-entra
description: Use for Microsoft Entra app-only auth setup, role validation, and auth troubleshooting in this repository.
---

# Repo Auth Entra Skill

## Use When

- User asks to configure or verify Microsoft Entra app-only auth for this API.
- User asks about `REQUIRE_AUTH`, `ENTRA_*` variables, or app-role behavior.
- User asks why token validation/authorization failed in deployment verification.

## Not For

- Do not use for general deployment sequencing (`azd provision/deploy`) -> route to `repo-azure-deploy`.
- Do not use for generic architecture placement questions -> route to `repo-architecture`.
- Do not use for telemetry/KQL validation workflows -> route to `repo-observability`.

## Primary References

- docs/guides/auth-setup.md
- app/core/security/auth.py
- app/core/security/dependencies.py
- app/core/security/models.py
- tests/test_auth.py
- tests/test_token_validation.py
- scripts/verify_deployment.sh

## Standard Workflow

1. Confirm auth mode and Entra configuration source.
2. Verify required env variables by target (local vs Azure).
3. Validate role expectations (`Todos.Read`, `Todos.Write`).
4. Run auth-focused tests and deployment verification.

```bash
source .venv/bin/activate
pytest tests/test_auth.py tests/test_token_validation.py -q
./scripts/verify_deployment.sh --base-url https://<fqdn>
```

## Rules

1. Treat `.azure/<env>/.env` as the source for generated Entra deployment values.
2. Keep `REQUIRE_AUTH=false` for local quick iteration unless explicitly testing auth.
3. Enforce app-role semantics: write implies read, but read-only token must not mutate state.
4. Never commit real `ENTRA_CLIENT_SECRET` values to tracked files.
5. When auth fails remotely, verify audience, tenant, and scope before changing code.

## Common Failure Patterns

- Missing or wrong `ENTRA_API_AUDIENCE` / `ENTRA_SCOPE` causing audience mismatch.
- Token obtained for wrong tenant or app registration.
- Assuming local defaults (`REQUIRE_AUTH=false`) in remote validation runs.
- Expecting protected TODO routes to work without `Todos.Read`/`Todos.Write` roles.
