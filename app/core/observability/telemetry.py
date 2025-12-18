"""OpenTelemetry instrumentation setup for Application Insights."""

import logging
import sys
from typing import Any

from opentelemetry import trace

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def setup_telemetry() -> None:
    """Configure OpenTelemetry; keep tracing active even without Azure exporter."""
    settings = get_settings()

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
        from opentelemetry.instrumentation.logging import LoggingInstrumentor

        configure_azure_monitor(
            connection_string=settings.applicationinsights_connection_string,
            logger_name=__name__,
        )

        # Add trace context into logs when using stdlib logging
        LoggingInstrumentor().instrument(set_logging_format=True)

        logger.info(
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
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        SQLAlchemyInstrumentor().instrument()

        logger.info("FastAPI and SQLAlchemy instrumented for telemetry")

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
