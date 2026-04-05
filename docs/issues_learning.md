# Issues and Learnings

## 1) Broad text replacement introduced contract drift

- Symptom:
  - Endpoint names changed to users, but payload fields still resembled the old task-oriented contract.
- Root cause:
  - Mechanical rename replaced entity names without re-shaping data model semantics.
- Fix:
  - Reworked API/module schemas, ORM model, migration, tests, and seed data around the user contract (`first_name`, `last_name`, `email`, `is_active`).
- Learning:
  - Perform structural contract review after large rename operations, not only string replacement checks.

## 2) No-auth scope required explicit script/docs cleanup

- Symptom:
  - Deployment verification and guides still referenced auth toggles and token workflows.
- Root cause:
  - Original template behavior included auth helpers that no longer apply to this variant.
- Fix:
  - Removed auth runtime surfaces and aligned verification/docs to no-auth behavior while preserving DB Entra mode for PostgreSQL access in Azure.
- Learning:
  - Treat operational scripts and docs as first-class deliverables during scope changes.

## 3) Observability queries lagged behind API/domain rename

- Symptom:
  - KQL suite queries still filtered on legacy endpoints and outdated custom dimensions.
- Root cause:
  - Query assets are decoupled from app code and require deliberate updates.
- Fix:
  - Updated KQL queries to `/api/v1/users` and `user.*` dimensions/metrics.
- Learning:
  - Include observability artifacts in feature migration checklists from the start.
