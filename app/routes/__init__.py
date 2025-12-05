from fastapi import APIRouter

from app.routes import todos_router

api_router = APIRouter()
api_router.include_router(todos_router.router, prefix="/todos", tags=["todos"])
