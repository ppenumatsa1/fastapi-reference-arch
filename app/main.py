"""FastAPI application entry point."""

from fastapi import APIRouter, FastAPI

from app.core.config import get_settings
from app.core.logging.logger import get_logger
from app.core.middleware.correlation import CorrelationIdMiddleware
from app.core.observability.telemetry import instrument_app, setup_telemetry
from app.routes import todos_router

settings = get_settings()
logger = get_logger("todo_api.app")

# Initialize telemetry before creating the app
setup_telemetry()

app = FastAPI(title=settings.app_name, debug=settings.app_debug)

# Instrument the app for OpenTelemetry
instrument_app(app)

# Propagate correlation/trace context via headers and logs
app.add_middleware(CorrelationIdMiddleware)

api_router = APIRouter()
api_router.include_router(todos_router.router, prefix="/todos", tags=["todos"])
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    logger.info("Health check invoked")
    return {"status": "ok", "service": settings.app_name}
