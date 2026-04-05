# Instrumentation Flow — FastAPI reference arch

This document describes end-to-end instrumentation flow for the app and how telemetry is produced and exported to Application Insights (Azure Monitor). It includes an ASCII diagram and a step-by-step walk-through targeted at this repository's wiring (`app/core/observability/telemetry.py`, `app/core/middleware/correlation.py`, `app/main.py`).

ASCII flow diagram

Client
|
| HTTP request (traceparent, x-correlation-id optional)
v
Load Balancer / Ingress
|
v
Container (FastAPI app)
|
+-- Startup -------------------------------
| 1) configure_azure_monitor(...) sets exporter, Resource (service.name) and TracerProvider
| 2) add CorrelationIdMiddleware to app (reads/extracts headers; does NOT create server spans)
| 3) instrument_app(app): FastAPIInstrumentor, SQLAlchemyInstrumentor (idempotent)
| - FastAPI instrumentation excludes low-level receive/send spans
| - span processor drops ASGI event noise before export
|
+-- Request Handling ----------------------
| ASGI entry -> FastAPIInstrumentor wraps ASGI and creates a SERVER span (server-kind)
| -> Starlette/FastAPI request lifecycle begins
| -> Correlation middleware (reads trace context, x-correlation-id) attaches ids to `request.state`
| -> Router resolves endpoint -> endpoint handler runs
| -> Business code can create additional child spans via Tracer (`tracer.start_as_current_span`) for domain operations
| -> Database calls: SQLAlchemy instrumentation produces dependency spans (client spans)
| -> Outbound HTTP calls: only if explicit HTTP client instrumentation is enabled
| -> Exceptions: if unhandled, instrumentation records exception events on the current span
| -> Response generated
| -> FastAPIInstrumentor ends the server span
| -> Correlation middleware sets response headers (`traceparent`, `x-correlation-id`) and optional logging
|
+-- Export / Ingestion --------------------
TracerProvider BatchExport -> Azure Monitor exporter (configure_azure_monitor)
-> Application Insights ingestion
-> Data appears in App Insights tables (mapping rules): - `requests`: server-kind spans representing incoming HTTP requests - `dependencies`: client spans (DB, HTTP) - `exceptions`: recorded exceptions - `traces`: custom trace logs and events

Detailed step-by-step explanation

Startup ordering and rationale

- configure_azure_monitor(...)
  - Creates an OpenTelemetry `TracerProvider`, configures Azure Monitor exporter, and sets resource attributes (e.g., `service.name`). Use this function as the canonical wiring point.
  - The function should be idempotent — repeated calls should no-op if already configured.

- Add `CorrelationIdMiddleware`
  - Purpose: extract incoming `traceparent` and `x-correlation-id`, attach them to `request.state` for logging, and ensure the response includes correlation headers.
  - Important: the middleware must NOT create a synthetic server span. Let the framework instrumentor own server span lifecycle.

- instrument the app (FastAPIInstrumentor, SQLAlchemyInstrumentor)
  - Apply framework instrumentors after middleware registration (so middleware can observe the context but not try to own the span).
  - Ensure instrumentors are applied idempotently (guard with module-level flags).
  - Configure FastAPI instrumentation with `exclude_spans=["receive", "send"]`.
  - Apply a span processor that marks ASGI event spans (`http.request`, `http.response.start`, `http.response.body`) as not sampled.

Incoming request flow (runtime)

1. Request reaches ASGI entrypoint.
2. FastAPIInstrumentor (instrumentation library) creates a SERVER span and sets it as the current context.
3. Correlation middleware runs and extracts context headers — it attaches the existing trace/span ids (from the framework span) to `request.state` for logger enrichment, and generates/propagates `x-correlation-id` if missing.
4. Endpoint executes. Business code can add child spans using the tracer API.
5. SQLAlchemy, HTTP client instrumentations create dependency spans as children of the current span, enabling end-to-end correlation between incoming request and outgoing dependencies.
6. If an exception occurs, the instrumentation records exception details on the active span and the exception is captured in `exceptions` table in App Insights.
7. The server span closes when the ASGI response completes; exporter batches and sends telemetry to Azure Monitor.

How Application Insights tables are populated

- `requests` table: populated from server-kind spans created by the FastAPI/Starlette instrumentor. Key attributes that influence mapping:
  - `span.kind=server`
  - `http.method`, `http.route`, `http.status_code`, `http.target` attributes set by the framework instrumentor

- `dependencies` table: populated by client spans (DB, HTTP). SQLAlchemy and HTTP instrumentations set attributes like `db.system`, `db.name`, `http.method`, `http.url`.

- `exceptions`: populated when spans record exception events or when unhandled exceptions bubble up; the exporter maps these to the exceptions table.

Best-practices & common pitfalls

- Do NOT create synthetic server spans in middleware — this breaks Application Insights' `requests` mapping.
- Ensure `service.name` is set consistently in `configure_azure_monitor(...)` so telemetry is grouped correctly.
- Apply instrumentations idempotently to avoid duplicate spans.
- Propagate `traceparent` and `x-correlation-id` for cross-service correlation; middleware should extract and not overwrite inbound trace context.
- Keep low-level ASGI noise reduction in telemetry code so Kusto queries can stay simple and operationally consistent.

Kusto operations in this repo

- Core suite lives under `scripts/kusto/` and covers `requests`, `dependencies`, `exceptions`, and `traces`.
- Use `scripts/kusto/run-observability-suite.sh` for routine checks.
- Use `scripts/kusto/end-to-end-flow-by-operation.kql` for a single-operation timeline by `operation_Id`.

Verification checklist (post-deploy)

- Send test requests to `/health` and an API route; query App Insights with Kusto:
  - `requests | where timestamp > ago(30m) | summarize count()` -- should be > 0
  - `dependencies | where timestamp > ago(30m) | summarize count()`
  - `requests | where name contains "/api/v1/users"` to confirm correct routes
- Confirm that request and dependency spans share the same `operation_Id`/trace id for correlation.

Files to inspect in this repo

- `app/core/observability/telemetry.py` — exporter & instrumentor wiring
- `app/core/middleware/correlation.py` — correlation middleware (no synthetic spans)
- `app/main.py` — startup order (middleware before instrumentation)

---

Generated on: 2026-03-06
