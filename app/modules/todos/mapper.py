"""Mapping helpers between internal todo models and API v1 contracts."""

from app.api.v1.schemas.todos import TodoCreate as ApiTodoCreate
from app.api.v1.schemas.todos import TodoListResponse as ApiTodoListResponse
from app.api.v1.schemas.todos import TodoRead as ApiTodoRead
from app.api.v1.schemas.todos import TodoUpdate as ApiTodoUpdate
from app.modules.todos.schemas import TodoCreate as ModuleTodoCreate
from app.modules.todos.schemas import TodoRead as ModuleTodoRead
from app.modules.todos.schemas import TodoUpdate as ModuleTodoUpdate


def to_module_create(payload: ApiTodoCreate) -> ModuleTodoCreate:
    return ModuleTodoCreate(**payload.model_dump())


def to_module_update(payload: ApiTodoUpdate) -> ModuleTodoUpdate:
    return ModuleTodoUpdate(**payload.model_dump(exclude_unset=True))


def to_api_read(todo: ModuleTodoRead) -> ApiTodoRead:
    return ApiTodoRead.model_validate(todo.model_dump())


def to_api_list_response(data: dict) -> ApiTodoListResponse:
    items = [to_api_read(item) for item in data["items"]]
    return ApiTodoListResponse(
        items=items,
        total=data["total"],
        limit=data["limit"],
        offset=data["offset"],
    )
