"""Application-level telemetry signals for business events and metrics."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from functools import lru_cache
from urllib import error, request

from opentelemetry import metrics, trace

from app.core.config import get_settings

_meter = metrics.get_meter("todo_api.app")

_todo_ops_counter = _meter.create_counter(
    name="todo.operations.count",
    unit="1",
    description="Count of todo operations by action/outcome.",
)

_todo_ops_duration = _meter.create_histogram(
    name="todo.operations.duration.ms",
    unit="ms",
    description="Duration of todo operations in milliseconds.",
)


def emit_business_event(name: str, attributes: dict[str, object] | None = None) -> None:
    """Emit business telemetry to both trace events and App Insights customEvents."""

    span = trace.get_current_span()
    normalized = _to_otel_attrs(attributes)

    if span and span.get_span_context().is_valid:
        span.add_event(name=name, attributes=normalized)

    _send_custom_event(name=name, attributes=normalized)


def record_todo_operation_metric(
    *,
    action: str,
    outcome: str,
    duration_ms: float,
) -> None:
    """Record low-cardinality custom metrics for todo operations."""

    attrs = {
        "todo.action": action,
        "todo.outcome": outcome,
    }
    _todo_ops_counter.add(1, attributes=attrs)
    _todo_ops_duration.record(duration_ms, attributes=attrs)


def _to_otel_attrs(
    attributes: dict[str, object] | None,
) -> dict[str, str | int | float | bool]:
    if not attributes:
        return {}

    normalized: dict[str, str | int | float | bool] = {}
    for key, value in attributes.items():
        if isinstance(value, str | int | float | bool):
            normalized[key] = value
        else:
            normalized[key] = str(value)
    return normalized


def _send_custom_event(
    *,
    name: str,
    attributes: dict[str, str | int | float | bool],
) -> None:
    """Best-effort custom event ingestion through Application Insights track API."""

    endpoint, instrumentation_key = _get_ai_track_endpoint_and_ikey()
    if not endpoint or not instrumentation_key:
        return

    trace_id, parent_id = _current_operation_tags()
    envelope = {
        "name": "Microsoft.ApplicationInsights.Event",
        "time": datetime.now(UTC).isoformat(),
        "iKey": instrumentation_key,
        "tags": {
            "ai.operation.id": trace_id,
            "ai.operation.parentId": parent_id,
        },
        "data": {
            "baseType": "EventData",
            "baseData": {
                "ver": 2,
                "name": name,
                "properties": {k: str(v) for k, v in attributes.items()},
            },
        },
    }

    payload = json.dumps([envelope]).encode("utf-8")
    req = request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=1.5):  # noqa: S310
            return
    except (error.URLError, TimeoutError, ValueError):
        # Never block user requests on telemetry delivery failures.
        return


@lru_cache(maxsize=1)
def _get_ai_track_endpoint_and_ikey() -> tuple[str | None, str | None]:
    settings = get_settings()
    conn = settings.applicationinsights_connection_string
    if not conn:
        return None, None

    parts = {}
    for token in conn.split(";"):
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        parts[key.strip().lower()] = value.strip()

    instrumentation_key = parts.get("instrumentationkey")
    ingestion_endpoint = parts.get(
        "ingestionendpoint", "https://dc.services.visualstudio.com/"
    )
    endpoint = ingestion_endpoint.rstrip("/") + "/v2/track"
    return endpoint, instrumentation_key


def _current_operation_tags() -> tuple[str, str]:
    span = trace.get_current_span()
    context = span.get_span_context() if span else None
    if context and context.is_valid:
        trace_id = format(context.trace_id, "032x")
        span_id = format(context.span_id, "016x")
        return trace_id, f"|{trace_id}.{span_id}."

    now_id = f"{int(datetime.now(UTC).timestamp() * 1000000):032x}"
    return now_id, ""
