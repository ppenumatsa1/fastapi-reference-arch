"""Application service encapsulating todo workflows."""

from time import perf_counter

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging.logger import get_logger
from app.core.observability import emit_business_event, record_todo_operation_metric
from app.modules.todos.repository import TodoRepository
from app.modules.todos.schemas import TodoCreate, TodoRead, TodoUpdate

logger = get_logger(__name__)


class TodoService:
    def __init__(self, session: AsyncSession):
        self.repository = TodoRepository(session)

    async def list_todos(self, limit: int, offset: int):
        started = perf_counter()
        logger.info("List todos invoked", extra={"limit": limit, "offset": offset})
        todos = await self.repository.list(limit=limit, offset=offset)
        total = await self.repository.count()
        logger.info(
            "List todos completed",
            extra={
                "returned": len(todos),
                "total": total,
                "limit": limit,
                "offset": offset,
            },
        )
        duration_ms = (perf_counter() - started) * 1000
        record_todo_operation_metric(
            action="list", outcome="success", duration_ms=duration_ms
        )
        emit_business_event(
            "todo.list.completed",
            {
                "todo.action": "list",
                "todo.returned": len(todos),
                "todo.total": total,
            },
        )
        return {
            "items": [TodoRead.model_validate(todo) for todo in todos],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def get_todo(self, todo_id: int) -> TodoRead:
        started = perf_counter()
        logger.info("Get todo invoked", extra={"todo_id": todo_id})
        todo = await self.repository.get(todo_id)
        if not todo:
            duration_ms = (perf_counter() - started) * 1000
            record_todo_operation_metric(
                action="get", outcome="not_found", duration_ms=duration_ms
            )
            emit_business_event(
                "todo.get.not_found",
                {"todo.action": "get", "todo.id": todo_id},
            )
            raise NotFoundError("Todo not found")
        logger.info("Get todo completed", extra={"todo_id": todo_id})
        duration_ms = (perf_counter() - started) * 1000
        record_todo_operation_metric(
            action="get", outcome="success", duration_ms=duration_ms
        )
        emit_business_event(
            "todo.get.completed",
            {"todo.action": "get", "todo.id": todo_id},
        )
        return TodoRead.model_validate(todo)

    async def create_todo(self, payload: TodoCreate) -> TodoRead:
        started = perf_counter()
        logger.info("Create todo invoked")
        todo = await self.repository.create(payload)
        logger.info("Create todo completed", extra={"todo_id": todo.id})
        duration_ms = (perf_counter() - started) * 1000
        record_todo_operation_metric(
            action="create", outcome="success", duration_ms=duration_ms
        )
        emit_business_event(
            "todo.create.completed",
            {"todo.action": "create", "todo.id": todo.id},
        )
        return TodoRead.model_validate(todo)

    async def update_todo(self, todo_id: int, payload: TodoUpdate) -> TodoRead:
        started = perf_counter()
        logger.info("Update todo invoked", extra={"todo_id": todo_id})
        try:
            updated = await self.repository.update_by_id(todo_id, payload)
        except NotFoundError:
            duration_ms = (perf_counter() - started) * 1000
            record_todo_operation_metric(
                action="update", outcome="not_found", duration_ms=duration_ms
            )
            emit_business_event(
                "todo.update.not_found",
                {"todo.action": "update", "todo.id": todo_id},
            )
            raise
        logger.info("Update todo completed", extra={"todo_id": todo_id})
        duration_ms = (perf_counter() - started) * 1000
        record_todo_operation_metric(
            action="update", outcome="success", duration_ms=duration_ms
        )
        emit_business_event(
            "todo.update.completed",
            {"todo.action": "update", "todo.id": todo_id},
        )
        return TodoRead.model_validate(updated)

    async def delete_todo(self, todo_id: int) -> None:
        started = perf_counter()
        logger.info("Delete todo invoked", extra={"todo_id": todo_id})
        try:
            await self.repository.delete_by_id(todo_id)
        except NotFoundError:
            duration_ms = (perf_counter() - started) * 1000
            record_todo_operation_metric(
                action="delete", outcome="not_found", duration_ms=duration_ms
            )
            emit_business_event(
                "todo.delete.not_found",
                {"todo.action": "delete", "todo.id": todo_id},
            )
            raise
        logger.info("Delete todo completed", extra={"todo_id": todo_id})
        duration_ms = (perf_counter() - started) * 1000
        record_todo_operation_metric(
            action="delete", outcome="success", duration_ms=duration_ms
        )
        emit_business_event(
            "todo.delete.completed",
            {"todo.action": "delete", "todo.id": todo_id},
        )
