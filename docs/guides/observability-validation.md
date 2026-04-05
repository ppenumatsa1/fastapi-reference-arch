# Observability Validation Guide

This guide documents how to validate end-to-end telemetry in Azure Application Insights, including custom events and custom metrics.

## Prerequisites

1. Active `azd` environment with `APPLICATIONINSIGHTS_CONNECTION_STRING` set.
2. Logged in Azure CLI (`az login`) and selected correct subscription.
3. Deployed app endpoint reachable.

## 1. Generate Fresh Telemetry

Run the Azure smoke test to create a predictable request flow:

```bash
source .venv/bin/activate
./scripts/verify_deployment.sh --env azure
```

This produces health, list, create, and get requests and triggers business telemetry in service code.

## 2. Run Full KQL Observability Suite

Run the suite:

```bash
./scripts/kusto/run-observability-suite.sh --output json
```

The suite validates:

1. `requests` in last 30m
2. `dependencies` in last 30m
3. `traces` in last 30m
4. `customEvents` with `user.*` names in last 60m
5. `customMetrics` with `user.*` names in last 60m

Expected success message:

```text
Validation passed.
```

## 3. Run Per-Operation Timeline Query

Run the operation timeline query:

```bash
APP_ID=$(azd env get-values --output json | jq -r '.APPLICATIONINSIGHTS_CONNECTION_STRING' | sed -n 's/.*ApplicationId=\([^;]*\).*/\1/p')
az monitor app-insights query \
  --app "$APP_ID" \
  --analytics-query "$(cat scripts/kusto/end-to-end-flow-by-operation.kql)" \
  -o json
```

This query shows a chronological union of:

1. request
2. dependency
3. trace
4. exception
5. customEvent
6. customMetric

## Verified Example (March 7, 2026)

A `GET /api/v1/users/{user_id}` operation showed:

1. request row with `resultCode=200`
2. DB dependency (`connect`)
3. structured traces (`Get user ...`)
4. business trace (`user.get.completed`)
5. matching `customEvent` (`user.get.completed`, with `user.action` and `user.id`)
6. `POST /v2/track` dependency to App Insights ingestion endpoint

## Notes On Correlation

1. `customEvents` are emitted with operation tags so they can be correlated by `operation_Id`.
2. `customMetrics` may not always carry operation-level IDs in every ingestion path.
3. For operation-centric debugging, prefer request + dependency + trace + customEvent.
4. For KPI/trend analysis, use `customMetrics` (`user.operations.count`, `user.operations.duration.ms`).

## Troubleshooting

If `customEvents` remain zero:

1. Confirm `ENABLE_TELEMETRY=true` on the running app.
2. Confirm `APPLICATIONINSIGHTS_CONNECTION_STRING` is set in the app environment.
3. Wait 20-60 seconds for ingestion latency, then rerun the query.
4. Look for `POST /v2/track` in `dependencies` to confirm event ingestion attempts.
5. Run the suite again after generating fresh traffic.
