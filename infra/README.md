# Infrastructure Overview

Infrastructure automation assets live here, including Azure Bicep templates, deployment hooks, and helper scripts used by `azd` flows.

## Bicep Templates

- `bicep/main.bicep` - top-level composition template.
- `bicep/main.parameters.json` - parameter values for deployments.
- `bicep/modules/` - reusable modules for Container Apps, PostgreSQL, monitoring, identity, registry, and RBAC.

## Scripts

- `scripts/bootstrap_db.sh` – ensures the PostgreSQL container is ready and applies Alembic migrations.
- `scripts/run_migrations.sh` – helper invoked by CI/CD to run Alembic upgrades.

## Deployment Hooks

- `hooks/preprovision.sh` - sets baseline azd environment defaults before provisioning.
- `hooks/postprovision.sh` - performs post-provision setup tasks such as database user/permission preparation.

## azd Deployment Flow (Summary)

1. `preprovision.sh` sets baseline environment values before infra provisioning.
2. `bicep/main.bicep` composes and deploys Azure resources.
3. `postprovision.sh` performs post-provision database setup.
4. `scripts/run_migrations.sh` applies Alembic migrations and seed operations during deploy workflows.

Each deploy uses an image tag pattern like `azd-deploy-<timestamp>` for traceability.

For module-specific details, see `bicep/README.md`.

## Future Work

- Optional hardening (network restrictions, private endpoints, tighter firewall rules).
- Extended Entra ID integration patterns for fully passwordless app/data paths.
