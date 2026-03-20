# Pilot Skill Routing (Phase 1 + Phase 2)

Use this mapping during pilot validation.

## Route To `repo-architecture`

- "Where should this code live?"
- "Is this change following our layering?"
- "Refactor this endpoint/service/repository flow"

## Route To `repo-azure-deploy`

- "Run azd deploy"
- "Check my Bicep/azd deployment workflow"
- "Why did postdeploy migration fail?"

## Route To `repo-observability`

- "Validate telemetry"
- "Run KQL suite"
- "Why are custom events/metrics missing?"

## Route To `repo-testing`

- "Run tests for this change"
- "Why is pytest failing?"
- "Add tests for this endpoint/service behavior"

## Route To `repo-auth-entra`

- "Set up Entra auth for this API"
- "Why is token validation failing?"
- "How do Todos.Read/Todos.Write roles work here?"

## Route To `repo-migration-safety`

- "Create/review this Alembic migration"
- "Why did postdeploy migration fail?"
- "Is this schema change safe and reversible?"

## Route To `repo-doc-sync`

- "Update README/docs after these changes"
- "Check if docs match current commands"
- "Sync architecture docs with implementation"

## Pilot Success Criteria

1. Correct routing for at least 90% of test prompts.
2. Commands are executable without manual correction.
3. Output includes clear next action on failures.
