"""OpenTelemetry instrumentation setup for Application Insights."""

import logging
import sys
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.trace import SpanContext, TraceFlags

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_telemetry_configured = False
_fastapi_instrumented = False
_sqlalchemy_instrumented = False


class _SpanNoiseFilterProcessor(SpanProcessor):
    """Drop low-value ASGI internal spans before export."""

    def on_start(self, span, parent_context=None):  # type: ignore[override]
        return

    def on_end(self, span):  # type: ignore[override]
        name = getattr(span, "name", "")
        attributes = getattr(span, "attributes", {}) or {}
        asgi_event = attributes.get("asgi.event.type")

        if asgi_event in {"http.request", "http.response.start", "http.response.body"}:
            _mark_span_not_sampled(span)
            return

        if isinstance(name, str) and name.endswith((" http receive", " http send")):
            _mark_span_not_sampled(span)

    def shutdown(self):  # type: ignore[override]
        return

    def force_flush(self, timeout_millis: int = 30000):  # type: ignore[override]
        return True


def setup_telemetry() -> None:
    """Configure OpenTelemetry; keep tracing active even without Azure exporter."""
    global _telemetry_configured

    if _telemetry_configured:
        return

    settings = get_settings()

    if not settings.enable_telemetry:
        _ensure_tracer_provider(settings.app_name, add_console_exporter=True)
        logger.info(
            "Telemetry disabled by configuration (ENABLE_TELEMETRY=false)",
            extra={"app_env": settings.app_env},
        )
        return

    if not settings.applicationinsights_connection_string:
        _ensure_tracer_provider(settings.app_name, add_console_exporter=True)
        logger.info(
            (
                "Application Insights connection string not set. "
                "Telemetry exporter disabled; tracing still active for correlation."
            ),
            extra={"app_env": settings.app_env},
        )
        return

    try:
        from azure.monitor.opentelemetry import configure_azure_monitor

        configure_azure_monitor(
            connection_string=settings.applicationinsights_connection_string,
            logger_name="user_api",
            span_processors=[_SpanNoiseFilterProcessor()],
        )
        _telemetry_configured = True

        logger.debug(
            "Application Insights telemetry configured successfully",
            extra={"app_env": settings.app_env},
        )

    except ImportError as e:
        logger.warning(
            f"OpenTelemetry packages not available: {e}. "
            "Install with: pip install azure-monitor-opentelemetry "
            "opentelemetry-instrumentation-fastapi"
        )
    except Exception as e:
        logger.error(f"Failed to configure Application Insights: {e}")


def instrument_app(app: Any) -> None:
    """Instrument FastAPI application with OpenTelemetry."""
    global _fastapi_instrumented
    global _sqlalchemy_instrumented

    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        if not _fastapi_instrumented:
            FastAPIInstrumentor.instrument_app(
                app,
                exclude_spans=["receive", "send"],
            )
            _fastapi_instrumented = True

        if not _sqlalchemy_instrumented:
            SQLAlchemyInstrumentor().instrument()
            _sqlalchemy_instrumented = True

        logger.debug("FastAPI and SQLAlchemy instrumented for telemetry")

    except ImportError:
        logger.warning("OpenTelemetry instrumentation packages not available")
    except Exception as e:
        logger.error(f"Failed to instrument application: {e}")


def get_current_trace_id() -> str | None:
    """Get the current trace ID if available."""
    try:
        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            return format(span.get_span_context().trace_id, "032x")
    except Exception:
        pass
    return None


def get_current_span_id() -> str | None:
    """Get the current span ID if available."""
    try:
        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            return format(span.get_span_context().span_id, "016x")
    except Exception:
        pass
    return None


def get_current_correlation_id() -> str | None:
    """Correlation ID derived from active trace/span."""
    try:
        trace_id = get_current_trace_id()
        span_id = get_current_span_id()
        if trace_id and span_id:
            return f"{trace_id}-{span_id}"
    except Exception:
        pass
    return None


def _ensure_tracer_provider(
    service_name: str, add_console_exporter: bool = False
) -> None:
    """Ensure tracer provider exists so spans are created without Azure exporter."""
    try:
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            ConsoleSpanExporter,
            SimpleSpanProcessor,
        )

        if isinstance(trace.get_tracer_provider(), TracerProvider):
            return

        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)

        if add_console_exporter:
            console_out = logger.handlers[0].stream if logger.handlers else sys.stdout
            provider.add_span_processor(
                SimpleSpanProcessor(ConsoleSpanExporter(out=console_out))
            )

        trace.set_tracer_provider(provider)
    except ImportError as e:
        logger.warning(
            "OpenTelemetry SDK not available to set tracer provider: "
            f"{e}. Spans will be no-op."
        )


def _mark_span_not_sampled(span: Any) -> None:
    """Mutate span context sampling flag so exporters ignore noisy spans."""
    context = getattr(span, "context", None)
    if context is None:
        context = getattr(span, "_context", None)
    if context is None:
        return

    span._context = SpanContext(  # noqa: SLF001
        trace_id=context.trace_id,
        span_id=context.span_id,
        is_remote=context.is_remote,
        trace_flags=TraceFlags(TraceFlags.DEFAULT),
        trace_state=context.trace_state,
    )
