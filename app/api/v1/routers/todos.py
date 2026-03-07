"""HTTP routes for todo resources (API v1)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.todos import TodoCreate, TodoListResponse, TodoRead, TodoUpdate
from app.core.database import get_db
from app.core.logging.logger import get_logger
from app.core.security.dependencies import require_roles
from app.modules.todos.mapper import (
    to_api_list_response,
    to_api_read,
    to_module_create,
    to_module_update,
)
from app.modules.todos.service import TodoService

TODO_READ_ROLE = "Todos.Read"
TODO_WRITE_ROLE = "Todos.Write"

router = APIRouter()
logger = get_logger(__name__)


def get_todo_service(db: Annotated[AsyncSession, Depends(get_db)]) -> TodoService:
    return TodoService(db)


TodoServiceDep = Annotated[TodoService, Depends(get_todo_service)]


@router.get(
    "/",
    response_model=TodoListResponse,
    dependencies=[Depends(require_roles(TODO_READ_ROLE))],
)
async def list_todos(
    service: TodoServiceDep,
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    logger.info(
        "List todos request",
        extra={"path": request.url.path, "limit": limit, "offset": offset},
    )
    todos = await service.list_todos(limit=limit, offset=offset)
    return to_api_list_response(todos)


@router.get(
    "/{todo_id}",
    response_model=TodoRead,
    dependencies=[Depends(require_roles(TODO_READ_ROLE))],
)
async def get_todo(todo_id: int, service: TodoServiceDep, request: Request):
    logger.info(
        "Get todo request",
        extra={"todo_id": todo_id, "path": request.url.path},
    )
    todo = await service.get_todo(todo_id)
    return to_api_read(todo)


@router.post(
    "/",
    response_model=TodoRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(TODO_WRITE_ROLE))],
)
async def create_todo(payload: TodoCreate, service: TodoServiceDep, request: Request):
    logger.info("Create todo request", extra={"path": request.url.path})
    todo = await service.create_todo(to_module_create(payload))
    return to_api_read(todo)


@router.put(
    "/{todo_id}",
    response_model=TodoRead,
    dependencies=[Depends(require_roles(TODO_WRITE_ROLE))],
)
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
    todo = await service.update_todo(todo_id, to_module_update(payload))
    return to_api_read(todo)


@router.delete(
    "/{todo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(TODO_WRITE_ROLE))],
)
async def delete_todo(todo_id: int, service: TodoServiceDep, request: Request):
    logger.info(
        "Delete todo request",
        extra={"todo_id": todo_id, "path": request.url.path},
    )
    await service.delete_todo(todo_id)
    return None
