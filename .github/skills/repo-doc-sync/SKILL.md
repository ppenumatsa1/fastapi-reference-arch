---
name: repo-doc-sync
description: Use for keeping README, guides, and design docs synchronized with real behavior, commands, and repo structure.
---

# Repo Doc Sync Skill

## Use When

- User asks to update docs after code, infra, or workflow changes.
- User asks to verify command examples in docs match actual scripts/make targets.
- User asks to align architecture or contract docs with implementation.

## Not For

- Do not use for implementing runtime code changes -> route to architecture/testing/migration/auth skills as appropriate.
- Do not use for running live deployments -> route to `repo-azure-deploy`.
- Do not use for telemetry incident triage -> route to `repo-observability`.

## Primary References

- README.md
- .github/copilot-instructions.md
- docs/guides/template-playbook.md
- docs/guides/error-contract.md
- docs/guides/auth-setup.md
- docs/guides/observability-validation.md
- docs/design/projectstructure.md

## Standard Workflow

1. Identify behavior/command deltas from code and scripts.
2. Update docs closest to consumer first (`README`, guide pages).
3. Cross-check references and command snippets.
4. Validate docs with quick command sanity run when feasible.

```bash
source .venv/bin/activate
make lint
make test
```

## Rules

1. Keep docs command examples executable as written in this repository.
2. Prefer single source of truth per topic; link to deeper docs instead of duplicating long instructions.
3. Update both developer-facing and operator-facing docs when behavior changes.
4. Keep file paths and route examples aligned with current structure (`app/api/v1`, `app/modules`).
5. When documenting auth/telemetry behavior, reflect local-vs-remote defaults explicitly.

## Common Failure Patterns

- README commands drift from Makefile/scripts behavior.
- Docs mention paths or modules no longer present in the repo.
- Auth and telemetry defaults documented without local-vs-Azure distinction.
- Contract examples not updated after response/error shape changes.
