# Auth Setup (Microsoft Entra App-Only)

This guide explains how to run and verify app-only authentication for the TODO API.

## Environment Flags

Use these in `.env` (local defaults shown):

```env
# Auth
REQUIRE_AUTH=false
ENTRA_TENANT_ID=
ENTRA_API_AUDIENCE=
ENTRA_CLIENT_ID=
ENTRA_CLIENT_SECRET=
ENTRA_SCOPE=
ENTRA_AUTHORITY=https://login.microsoftonline.com
ENTRA_JWKS_CACHE_TTL_SECONDS=3600
ENTRA_CLOCK_SKEW_SECONDS=60

# Telemetry
ENABLE_TELEMETRY=false
```

Recommended defaults:

1. Local development: `REQUIRE_AUTH=false`, `ENABLE_TELEMETRY=false`
2. Remote/hosted verification: `REQUIRE_AUTH=true`, `ENABLE_TELEMETRY=true`

## Source Of Truth For Secrets

1. Generated Entra app registration values are stored in `.azure/<env>/.env` by `azd` hooks.
2. Keep `.env` and `.env.example` in key-sync for variable names only.
3. Do not commit real values for `ENTRA_CLIENT_SECRET` to tracked files.

## App Roles

This project uses split app roles:

1. `Todos.Read` for GET/list operations.
2. `Todos.Write` for create/update/delete operations.

Write implies read at runtime (`Todos.Write` satisfies read checks).

## Verify Script Behavior

`./scripts/verify_deployment.sh` now auto-selects defaults by target:

1. Local target (`http://localhost:8000`):
   - Auth mode: `false`
   - Telemetry check mode: `false`
2. Non-local target (for example `--base-url https://...`):
   - Auth mode: `true`
   - Telemetry check mode: `true`

Auth input resolution precedence:

1. CLI arguments (`--tenant-id`, `--client-id`, `--client-secret`, `--scope`)
2. Process environment variables (`ENTRA_*`)
3. Active `azd env` values

You can override modes explicitly:

```bash
# Force auth on/off
./scripts/verify_deployment.sh --no-require-auth
./scripts/verify_deployment.sh --require-auth --tenant-id <tid> --client-id <cid> --client-secret <secret> --scope <api://.../.default>

# Force telemetry check mode on/off
./scripts/verify_deployment.sh --check-telemetry
./scripts/verify_deployment.sh --skip-telemetry-check
```

## Local Smoke Test

```bash
source .venv/bin/activate
./scripts/verify_deployment.sh --env local
```

## Remote Smoke Test (Auth Enabled)

```bash
source .venv/bin/activate

# Preview then deploy
azd provision --preview
azd up

sleep 10

# verify_deployment auto-loads ENTRA_* values from azd env when needed
./scripts/verify_deployment.sh \
   --base-url https://<your-container-app-fqdn>

sleep 10
./scripts/kusto/run-observability-suite.sh
```

## Notes

1. API authorization uses application roles from the `roles` claim (client credentials flow).
2. Health endpoint (`/health`) is public; TODO endpoints require auth when `REQUIRE_AUTH=true`.
3. Preprovision Entra automation requires directory/application admin permissions in the tenant.
