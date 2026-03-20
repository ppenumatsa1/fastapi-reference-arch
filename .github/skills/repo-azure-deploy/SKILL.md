---
name: repo-azure-deploy
description: Use for safe deployment operations in this repo using azd, Bicep modules, deployment hooks, and postdeploy migrations.
---

# Repo Azure Deploy Skill

## Use When

- User asks to provision, deploy, or verify Azure environment for this repo.
- User asks about azd hooks, Bicep wiring, or migration behavior.
- User asks for safe command ordering before merge/release.

## Not For

- Do not use for module/file placement or layering design questions -> route to `repo-architecture`.
- Do not use for deep telemetry triage or KQL result interpretation after traffic is generated -> route to `repo-observability`.
- Do not use for Azure cost optimization requests -> route to `azure-cost-optimization`.

## Primary References

- azure.yaml
- infra/bicep/README.md
- infra/hooks/preprovision.sh
- infra/hooks/postprovision.sh
- infra/scripts/run_migrations.sh
- scripts/verify_deployment.sh

## Standard Workflow

1. Confirm active environment.
2. Preview infra changes.
3. Deploy application.
4. Verify endpoint behavior.
5. Validate observability data.

```bash
azd env list
azd provision --preview
azd deploy
./scripts/verify_deployment.sh --env azure
./scripts/kusto/run-observability-suite.sh
```

## Rules

1. Do not skip preflight preview when infra changes are involved.
2. Assume postdeploy migration hook is required and must succeed.
3. Prefer azd env values as source of truth for deployment context.
4. Avoid hardcoding resource identifiers in docs or commands.

## Common Failure Patterns

- Migration failures during postdeploy.
- Missing azd env values (for example CONTAINER*APP_FQDN, ENTRA*\*).
- Running verify script with wrong auth/target mode.
