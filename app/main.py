"""FastAPI application entry point."""

from fastapi import APIRouter, FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.v1.routers import todos as todos_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging.logger import get_logger
from app.core.middleware.correlation import CorrelationIdMiddleware
from app.core.observability.telemetry import instrument_app, setup_telemetry

settings = get_settings()
logger = get_logger("todo_api.app")

# Initialize telemetry before creating the app
setup_telemetry()

app = FastAPI(title=settings.app_name, debug=settings.app_debug)


def _configure_exception_handlers(fastapi_app: FastAPI) -> None:
    @fastapi_app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        cause = exc.cause
        logger.warning(
            "Handled application error",
            extra={
                "path": request.url.path,
                "code": exc.code,
                "status": exc.status_code,
                "cause_type": type(cause).__name__ if cause else None,
                "cause_message": str(cause) if cause else None,
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.to_dict()},
        )

    @fastapi_app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        logger.warning("Validation error", extra={"path": request.url.path})
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed",
                },
                "details": jsonable_encoder(exc.errors()),
            },
        )

    @fastapi_app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error", extra={"path": request.url.path})
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Internal server error",
                }
            },
        )


_configure_exception_handlers(app)

# Propagate correlation/trace context via headers and logs
app.add_middleware(CorrelationIdMiddleware)

# Instrument the app for OpenTelemetry
instrument_app(app)

api_router = APIRouter()
api_router.include_router(todos_router.router, prefix="/todos", tags=["todos"])
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    logger.info("Health check invoked")
    return {"status": "ok", "service": settings.app_name}
