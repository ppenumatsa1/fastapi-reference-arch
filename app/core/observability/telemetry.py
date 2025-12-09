"""OpenTelemetry instrumentation setup for Application Insights."""

import logging
from typing import Any

from opentelemetry import trace

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def setup_telemetry() -> None:
    """Configure OpenTelemetry with Azure Monitor if connection string is available."""
    settings = get_settings()

    if not settings.applicationinsights_connection_string:
        logger.info(
            "Application Insights connection string not set. Telemetry disabled."
        )
        return

    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        from opentelemetry.instrumentation.logging import LoggingInstrumentor

        configure_azure_monitor(
            connection_string=settings.applicationinsights_connection_string,
            logger_name=__name__,
        )

        # Add trace context into logs
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
    settings = get_settings()

    if not settings.applicationinsights_connection_string:
        return

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
