"""FastAPI application entry point."""

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import get_logger
from app.routes import api_router

settings = get_settings()
logger = get_logger("todo_api.app")

app = FastAPI(title=settings.app_name, debug=settings.app_debug)
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    logger.info("Health check invoked")
    return {"status": "ok", "service": settings.app_name}
