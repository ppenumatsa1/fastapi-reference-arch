# Pilot Skill Test Plan

This plan defines prompt matrices and pass criteria for repository skills.

Execution logs are stored separately in `.github/skills/PILOT_TEST_RUNS.md`.
Keep only the latest 3 runs in that file.

## How To Run

1. Use Copilot Chat in this repo context.
2. Submit each prompt exactly as written.
3. Record observed routed skill and outcome.
4. Mark each test `pass` only if all checks pass.

## Scoring Rules

- Routing accuracy target: >= 90% (9/10 prompts routed to expected skill).
- Overall quality target: >= 90% prompts pass all checks.
- If a prompt fails, capture why in notes and refine only the relevant skill.

## Phase 1 Prompt Matrix

| ID  | Prompt                                                                                    | Expected Skill                               | Pass Checks                                                                                              |
| --- | ----------------------------------------------------------------------------------------- | -------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| A1  | "Where should I put mapping logic for a new Orders feature in this repo?"                 | `repo-architecture`                          | Recommends `app/modules/orders/mapper.py`; preserves router->service->repository layering.               |
| A2  | "I am adding `/api/v1/orders`; what files should change and what should stay untouched?"  | `repo-architecture`                          | Mentions `app/api/v1/routers`, `app/api/v1/schemas`, `app/modules/orders/*`; avoids direct DB in router. |
| A3  | "Review this plan: route directly calls repository for speed. Is it okay?"                | `repo-architecture`                          | Explicitly flags as anti-pattern; keeps service boundary.                                                |
| D1  | "Run safe Azure deploy steps for this repo."                                              | `repo-azure-deploy`                          | Uses `azd env list`, `azd provision --preview`, `azd deploy`, then verification sequence.                |
| D2  | "`azd deploy` failed in postdeploy migration. What should I check first?"                 | `repo-azure-deploy`                          | Checks `infra/scripts/run_migrations.sh`, env values, DB auth mode, migration revision chain.            |
| D3  | "I changed Bicep. Give me the safest command order before merge."                         | `repo-azure-deploy`                          | Includes preview-first workflow and validation commands; avoids skipping preflight.                      |
| O1  | "Validate observability after deploy and confirm todo custom events/metrics are flowing." | `repo-observability`                         | Runs verify script + Kusto suite; checks requests/dependencies/traces/customEvents/customMetrics.        |
| O2  | "`run-observability-suite.sh` shows zero customEvents. How do I triage?"                  | `repo-observability`                         | Checks telemetry env vars, traffic generation, ingestion delay, and dependency POST `/v2/track`.         |
| O3  | "Show me operation timeline debugging steps for one failed request."                      | `repo-observability`                         | Uses `end-to-end-flow-by-operation.kql` and operation correlation guidance.                              |
| X1  | "Optimize Azure costs for this subscription."                                             | Not pilot (expect `azure-cost-optimization`) | Should not route to pilot skills; should defer to Azure cost skill.                                      |

## Phase 1 Results Sheet (Template)

| ID  | Expected Skill          | Observed Skill | Route Pass (Y/N) | Quality Pass (Y/N) | Notes |
| --- | ----------------------- | -------------- | ---------------- | ------------------ | ----- |
| A1  | repo-architecture       |                |                  |                    |       |
| A2  | repo-architecture       |                |                  |                    |       |
| A3  | repo-architecture       |                |                  |                    |       |
| D1  | repo-azure-deploy       |                |                  |                    |       |
| D2  | repo-azure-deploy       |                |                  |                    |       |
| D3  | repo-azure-deploy       |                |                  |                    |       |
| O1  | repo-observability      |                |                  |                    |       |
| O2  | repo-observability      |                |                  |                    |       |
| O3  | repo-observability      |                |                  |                    |       |
| X1  | azure-cost-optimization |                |                  |                    |       |

## Phase 1 Exit Criteria

Proceed to Phase 2 only if:

1. Routing accuracy >= 90%.
2. Quality pass rate >= 90%.
3. No repeated critical failure pattern across more than one prompt category.

## Phase 2 Prompt Matrix

This matrix validates the newly added skills:

1. `repo-testing`
2. `repo-auth-entra`
3. `repo-migration-safety`
4. `repo-doc-sync`

| ID  | Prompt                                                                                         | Expected Skill                     | Pass Checks                                                                                                    |
| --- | ---------------------------------------------------------------------------------------------- | ---------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| T1  | "I changed TodoService list behavior; what test command order should I run before merge?"      | `repo-testing`                     | Recommends venv activation, `make lint`, focused pytest, then `make test`.                                     |
| T2  | "Add tests for title whitespace validation. Where should they go and what should they assert?" | `repo-testing`                     | Places tests under `tests/` and validates whitespace rejection behavior without DB-layer shortcuts.            |
| E1  | "`verify_deployment.sh` against Azure returns 401. What Entra checks come first?"              | `repo-auth-entra`                  | Checks `ENTRA_*` values, audience/scope/tenant alignment, app roles, and target mode assumptions.              |
| E2  | "How should `Todos.Read` and `Todos.Write` be used for app-only clients here?"                 | `repo-auth-entra`                  | Explains role intent and write-implies-read behavior.                                                          |
| M1  | "I added a new todo column. What migration safety checks do you require before deploy?"        | `repo-migration-safety`            | Covers revision/down_revision integrity, upgrade/downgrade expectations, migration script run, and validation. |
| M2  | "`azd deploy` failed during alembic upgrade. What do we inspect first in this repo?"           | `repo-migration-safety`            | Prioritizes `infra/scripts/run_migrations.sh`, auth mode, env resolution, and migration chain checks.          |
| S1  | "I changed verify defaults and auth behavior. Which docs must be updated?"                     | `repo-doc-sync`                    | Identifies README + auth/ops docs and aligns command examples with actual script behavior.                     |
| S2  | "Check if our docs are still consistent with current make targets and scripts."                | `repo-doc-sync`                    | Compares README/docs against Makefile and scripts, then suggests concrete sync edits.                          |
| X2  | "Run safe Azure deploy steps for this repo."                                                   | `repo-azure-deploy` (non-Phase 2)  | Should not route to Phase 2 skills; should route to deploy skill.                                              |
| X3  | "Validate telemetry and run the KQL observability suite."                                      | `repo-observability` (non-Phase 2) | Should not route to Phase 2 skills; should route to observability skill.                                       |

## Phase 2 Results Sheet (Template)

| ID  | Expected Skill        | Observed Skill | Route Pass (Y/N) | Quality Pass (Y/N) | Notes |
| --- | --------------------- | -------------- | ---------------- | ------------------ | ----- |
| T1  | repo-testing          |                |                  |                    |       |
| T2  | repo-testing          |                |                  |                    |       |
| E1  | repo-auth-entra       |                |                  |                    |       |
| E2  | repo-auth-entra       |                |                  |                    |       |
| M1  | repo-migration-safety |                |                  |                    |       |
| M2  | repo-migration-safety |                |                  |                    |       |
| S1  | repo-doc-sync         |                |                  |                    |       |
| S2  | repo-doc-sync         |                |                  |                    |       |
| X2  | repo-azure-deploy     |                |                  |                    |       |
| X3  | repo-observability    |                |                  |                    |       |

## Global Scoring Rules

- Routing accuracy target: >= 90%.
- Overall quality target: >= 90%.
- If a prompt fails, capture why and refine only the relevant skill.

## Ambiguity Stress Matrix

Use these prompts to validate tie-break behavior when two skills could appear relevant.

| ID  | Prompt                                                                             | Candidate Skills                             | Expected Skill       | Pass Checks                                                                                         |
| --- | ---------------------------------------------------------------------------------- | -------------------------------------------- | -------------------- | --------------------------------------------------------------------------------------------------- |
| B1  | "`azd deploy` failed in postdeploy migration after schema change. What next?"      | `repo-azure-deploy`, `repo-migration-safety` | `repo-azure-deploy`  | Uses deploy workflow first, then migration checks with explicit handoff rationale.                  |
| B2  | "401s in verify_deployment and some tests fail. Where should I start?"             | `repo-auth-entra`, `repo-testing`            | `repo-auth-entra`    | Starts with auth mode/env/role checks before test refactoring guidance.                             |
| B3  | "README endpoint docs and module structure notes look stale after refactor."       | `repo-doc-sync`, `repo-architecture`         | `repo-doc-sync`      | Prioritizes doc alignment and references architecture only as supporting context.                   |
| B4  | "Observability suite fails after deploy. Is this deploy issue or telemetry issue?" | `repo-azure-deploy`, `repo-observability`    | `repo-observability` | Runs telemetry validation sequence first and only escalates deploy if signals indicate infra issue. |

## Negative Control Matrix

Each prompt should route away from the named non-target skill.

| ID  | Prompt                                                               | Must Not Route To       | Expected Skill       | Pass Checks                                                                   |
| --- | -------------------------------------------------------------------- | ----------------------- | -------------------- | ----------------------------------------------------------------------------- |
| N1  | "Add app-role guidance for Todos.Read and Todos.Write in auth docs." | `repo-testing`          | `repo-auth-entra`    | Focuses on auth role semantics, not test workflow.                            |
| N2  | "I changed Bicep and need safest deploy order before merge."         | `repo-migration-safety` | `repo-azure-deploy`  | Uses preview/deploy/verify flow, avoids migration-only framing.               |
| N3  | "Fix flaky API test around todo validation in CI."                   | `repo-doc-sync`         | `repo-testing`       | Gives deterministic test remediation guidance, not documentation update flow. |
| N4  | "KQL shows no customMetrics after traffic generation."               | `repo-azure-deploy`     | `repo-observability` | Uses telemetry triage workflow and ingestion delay checks.                    |

## Robustness Variant Rules

For each matrix (Phase 1, Phase 2, Ambiguity, Negative Control), add one noisy variant for at least 3 prompts:

- Typo variant: misspell one or two keywords.
- Verbose variant: add unrelated context paragraph before the prompt.
- Mixed-intent variant: append one secondary request and confirm primary intent still routes correctly.
