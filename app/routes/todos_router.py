"""HTTP routes for todo resources."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging.logger import get_logger
from app.core.schemas.todo import TodoCreate, TodoRead, TodoUpdate
from app.services.todo_service import TodoService

router = APIRouter()
logger = get_logger(__name__)


def get_todo_service(db: Annotated[AsyncSession, Depends(get_db)]) -> TodoService:
    return TodoService(db)


TodoServiceDep = Annotated[TodoService, Depends(get_todo_service)]


@router.get("/", response_model=list[TodoRead])
async def list_todos(service: TodoServiceDep, request: Request):
    logger.debug("List todos request", extra={"path": request.url.path})
    return await service.list_todos()


@router.get("/{todo_id}", response_model=TodoRead)
async def get_todo(todo_id: int, service: TodoServiceDep, request: Request):
    logger.debug(
        "Get todo request",
        extra={"todo_id": todo_id, "path": request.url.path},
    )
    return await service.get_todo(todo_id)


@router.post("/", response_model=TodoRead, status_code=status.HTTP_201_CREATED)
async def create_todo(payload: TodoCreate, service: TodoServiceDep, request: Request):
    logger.info("Create todo request", extra={"path": request.url.path})
    return await service.create_todo(payload)


@router.put("/{todo_id}", response_model=TodoRead)
async def update_todo(
    todo_id: int,
    payload: TodoUpdate,
    service: TodoServiceDep,
    request: Request,
):
    logger.info(
        "Update todo request",
        extra={"todo_id": todo_id, "path": request.url.path},
    )
    return await service.update_todo(todo_id, payload)


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(todo_id: int, service: TodoServiceDep, request: Request):
    logger.info(
        "Delete todo request",
        extra={"todo_id": todo_id, "path": request.url.path},
    )
    await service.delete_todo(todo_id)
    return None
