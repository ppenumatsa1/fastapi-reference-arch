"""Middleware to propagate trace/correlation IDs via headers and logging context."""

from fastapi import Request
from opentelemetry import trace
from opentelemetry.trace import Span, SpanContext
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        span = trace.get_current_span()
        span_context = span.get_span_context()
        tracer = trace.get_tracer(__name__)

        if not span_context.is_valid:
            # Ensure a span exists so logs have trace/span IDs even without exporters
            with tracer.start_as_current_span("http.request") as fallback_span:
                correlation_id = _record_context(request, fallback_span)
                response = await call_next(request)
                _set_response_headers(
                    response, fallback_span.get_span_context(), correlation_id
                )
                return response

        correlation_id = _record_context(request, span)
        response = await call_next(request)

        # Instrumentation may create a new span downstream; prefer the latest context
        current_ctx = trace.get_current_span().get_span_context()
        ctx_for_headers = current_ctx if current_ctx.is_valid else span_context
        final_correlation = _correlation_id_from_ctx(ctx_for_headers) or correlation_id

        _set_response_headers(response, ctx_for_headers, final_correlation)
        return response


def _record_context(request: Request, span: Span) -> str:
    ctx = span.get_span_context()
    correlation_id = _correlation_id_from_ctx(ctx) or ""
    trace_id = format(ctx.trace_id, "032x")
    span_id = format(ctx.span_id, "016x")

    request.state.trace_id = trace_id
    request.state.span_id = span_id
    request.state.correlation_id = correlation_id
    return correlation_id


def _set_response_headers(
    response: Response, ctx: SpanContext, correlation_id: str | None
) -> None:
    if ctx and ctx.is_valid:
        trace_flags = format(int(ctx.trace_flags), "02x")
        traceparent = (
            "00-"
            f"{format(ctx.trace_id, '032x')}-"
            f"{format(ctx.span_id, '016x')}-"
            f"{trace_flags}"
        )
        response.headers["traceparent"] = traceparent
    if correlation_id:
        response.headers["x-correlation-id"] = correlation_id


def _correlation_id_from_ctx(ctx: SpanContext) -> str | None:
    if ctx and ctx.is_valid:
        return f"{format(ctx.trace_id, '032x')}-{format(ctx.span_id, '016x')}"
    return None
