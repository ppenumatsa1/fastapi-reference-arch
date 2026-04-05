---
name: repo-observability
description: Use for telemetry validation, KQL checks, and troubleshooting Application Insights/Log Analytics behavior in this repository.
---

# Repo Observability Skill

## Use When

- User asks to validate telemetry after deployment.
- User asks to investigate missing requests/dependencies/traces/custom events/metrics.
- User asks for KQL workflow in this repo.
- User asks for operation-id based timeline analysis using repo KQL scripts.

## Not For

- Do not use for running or planning infrastructure/app deployments -> route to `repo-azure-deploy`.
- Do not use for architecture/file placement/layering decisions -> route to `repo-architecture`.
- Do not use for broad Azure production incident triage outside this repo validation workflow -> route to `azure-diagnostics`.

## Primary References

- docs/guides/observability-validation.md
- docs/design/instrument-flow.md
- scripts/kusto/run-observability-suite.sh
- scripts/kusto/\*.kql
- app/core/observability/telemetry.py
- app/core/observability/signals.py

## Standard Workflow

1. Generate fresh traffic:

```bash
./scripts/verify_deployment.sh --env azure
```

2. Run full suite:

```bash
./scripts/kusto/run-observability-suite.sh --output json
```

3. If needed, run end-to-end timeline query from scripts/kusto/end-to-end-flow-by-operation.kql.

## Rules

1. Validate both platform telemetry (requests, dependencies, traces) and business telemetry (todo.\* events/metrics).
2. Wait for ingestion delay before declaring telemetry missing.
3. Prefer operation-centric analysis with request + dependency + trace + customEvent correlation.
4. Treat this skill as repository validation-first: verify expected instrumentation and data flow before escalating to platform-level incident diagnostics.

## Common Failure Patterns

- Missing APPLICATIONINSIGHTS_CONNECTION_STRING or ENABLE_TELEMETRY.
- No fresh traffic generated before running KQL checks.
- Ingestion delay interpreted as telemetry loss.
