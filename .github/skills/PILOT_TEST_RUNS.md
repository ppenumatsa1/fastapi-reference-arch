# Pilot Skill Test Runs

This file stores execution history for pilot evaluations.
Keep only the latest 3 runs.

## Quality Rubric (1-5)

Use this rubric for each run summary.

- Correctness: Is the routed skill and advice technically correct for the prompt?
- Actionability: Are steps/commands specific and executable in this repo?
- Safety: Does guidance avoid risky shortcuts and preserve boundaries?
- Repo Specificity: Does output reference correct files, scripts, and conventions?

Scoring guidance:

- 5 = excellent and production-ready.
- 4 = strong with minor gaps.
- 3 = acceptable but needs follow-up.
- 2 = weak and likely misleads.
- 1 = incorrect or unsafe.

Run summary template (append for each new run):

- Routing accuracy: <value>
- Quality pass rate: <value>
- Correctness (1-5): <value>
- Actionability (1-5): <value>
- Safety (1-5): <value>
- Repo Specificity (1-5): <value>
- Overlap issues: <none|details>
- Regressions vs prior run: <none|details>

## Run 002 - Phase 1 Post-Hardening Dry Run (2026-03-20)

| ID  | Expected Skill          | Observed Skill     | Route Pass (Y/N) | Quality Pass (Y/N) | Notes                                                                           |
| --- | ----------------------- | ------------------ | ---------------- | ------------------ | ------------------------------------------------------------------------------- |
| A1  | repo-architecture       | repo-architecture  | Y                | Y                  | Explicit feature placement triggers improved module mapping confidence.         |
| A2  | repo-architecture       | repo-architecture  | Y                | Y                  | Feature-addition triggers correctly scope API and module files.                 |
| A3  | repo-architecture       | repo-architecture  | Y                | Y                  | Router -> repository anti-pattern is explicitly rejected.                       |
| D1  | repo-azure-deploy       | repo-azure-deploy  | Y                | Y                  | Safe preview-first deploy order remains intact.                                 |
| D2  | repo-azure-deploy       | repo-azure-deploy  | Y                | Y                  | Postdeploy migration-first triage remains clear.                                |
| D3  | repo-azure-deploy       | repo-azure-deploy  | Y                | Y                  | Preflight requirement for Bicep changes remains explicit.                       |
| O1  | repo-observability      | repo-observability | Y                | Y                  | Validation flow confirms platform and business telemetry checks.                |
| O2  | repo-observability      | repo-observability | Y                | Y                  | Missing custom events triage includes env, traffic, and ingestion delay checks. |
| O3  | repo-observability      | repo-observability | Y                | Y                  | Operation timeline guidance remains aligned with repo KQL workflow.             |
| X1  | azure-cost-optimization | non-pilot          | Y                | Y                  | Pilot skills correctly exclude Azure cost optimization scope.                   |

Summary:

- Routing accuracy: 100% (10/10)
- Quality pass rate: 100% (10/10)
- Correctness (1-5): 5
- Actionability (1-5): 5
- Safety (1-5): 5
- Repo Specificity (1-5): 5
- Regression check: none.

## Run 003 - Phase 2 Dry Run (2026-03-20)

| ID  | Expected Skill        | Observed Skill        | Route Pass (Y/N) | Quality Pass (Y/N) | Notes                                                                              |
| --- | --------------------- | --------------------- | ---------------- | ------------------ | ---------------------------------------------------------------------------------- |
| T1  | repo-testing          | repo-testing          | Y                | Y                  | Recommends venv -> lint -> focused pytest -> full suite flow.                      |
| T2  | repo-testing          | repo-testing          | Y                | Y                  | Places validation tests under tests and keeps API-boundary assertions.             |
| E1  | repo-auth-entra       | repo-auth-entra       | Y                | Y                  | Prioritizes ENTRA vars, audience/scope/tenant, and role checks for 401 triage.     |
| E2  | repo-auth-entra       | repo-auth-entra       | Y                | Y                  | Correctly explains Users.Read/Users.Write and write-implies-read behavior.         |
| M1  | repo-migration-safety | repo-migration-safety | Y                | Y                  | Covers revision integrity, safe sequencing, and migration validation.              |
| M2  | repo-migration-safety | repo-migration-safety | Y                | Y                  | Correctly prioritizes migration hook script, auth mode, and revision chain checks. |
| S1  | repo-doc-sync         | repo-doc-sync         | Y                | Y                  | Identifies README and auth/ops docs for behavior sync updates.                     |
| S2  | repo-doc-sync         | repo-doc-sync         | Y                | Y                  | Aligns docs against Makefile/scripts and proposes concrete sync checks.            |
| X2  | repo-azure-deploy     | repo-azure-deploy     | Y                | Y                  | Control prompt routed to deploy skill, not Phase 2 skills.                         |
| X3  | repo-observability    | repo-observability    | Y                | Y                  | Control prompt routed to observability skill, not Phase 2 skills.                  |

Summary:

- Routing accuracy: 100% (10/10)
- Quality pass rate: 100% (10/10)
- Correctness (1-5): 5
- Actionability (1-5): 5
- Safety (1-5): 5
- Repo Specificity (1-5): 5
- Regression check: none.
- Overlap check: none.

## Run 004 - Phase 3 Ambiguity + Negative Control Dry Run (2026-03-20)

| ID  | Expected Skill     | Observed Skill     | Route Pass (Y/N) | Quality Pass (Y/N) | Notes                                                                               |
| --- | ------------------ | ------------------ | ---------------- | ------------------ | ----------------------------------------------------------------------------------- |
| B1  | repo-azure-deploy  | repo-azure-deploy  | Y                | Y                  | Ambiguous deploy vs migration case resolved to deploy-first with migration handoff. |
| B2  | repo-auth-entra    | repo-auth-entra    | Y                | Y                  | Ambiguous auth vs testing case resolved to auth-first due 401 and token context.    |
| B3  | repo-doc-sync      | repo-doc-sync      | Y                | Y                  | Ambiguous docs vs architecture case resolved to docs synchronization first.         |
| B4  | repo-observability | repo-observability | Y                | Y                  | Ambiguous deploy vs telemetry case resolved to observability-first triage.          |
| N1  | repo-auth-entra    | repo-auth-entra    | Y                | Y                  | Negative control passed: did not route to repo-testing.                             |
| N2  | repo-azure-deploy  | repo-azure-deploy  | Y                | Y                  | Negative control passed: did not route to repo-migration-safety.                    |
| N3  | repo-testing       | repo-testing       | Y                | Y                  | Negative control passed: did not route to repo-doc-sync.                            |
| N4  | repo-observability | repo-observability | Y                | Y                  | Negative control passed: did not route to repo-azure-deploy.                        |
| V1  | repo-azure-deploy  | repo-azure-deploy  | Y                | Y                  | Typo robustness variant preserved correct routing.                                  |
| V2  | repo-testing       | repo-testing       | Y                | Y                  | Verbose-context robustness variant preserved correct routing.                       |
| V3  | repo-auth-entra    | repo-auth-entra    | Y                | Y                  | Mixed-intent robustness variant preserved primary-intent routing.                   |

Summary:

- Routing accuracy: 100% (11/11)
- Quality pass rate: 100% (11/11)
- Correctness (1-5): 5
- Actionability (1-5): 5
- Safety (1-5): 5
- Repo Specificity (1-5): 5
- Regression check: none (maintained from prior 100/100 baseline).
- Overlap check: none.
