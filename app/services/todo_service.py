"""Application service encapsulating todo workflows."""

from collections.abc import Sequence

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging.logger import get_logger
from app.core.schemas.todo import TodoCreate, TodoRead, TodoUpdate
from app.repo.todo_repository import TodoRepository

logger = get_logger(__name__)


class TodoService:
    def __init__(self, session: AsyncSession):
        self.repository = TodoRepository(session)

    async def list_todos(self) -> Sequence[TodoRead]:
        logger.debug("List todos invoked")
        todos = await self.repository.list()
        logger.debug("List todos completed", extra={"count": len(todos)})
        return [TodoRead.model_validate(todo) for todo in todos]

    async def get_todo(self, todo_id: int) -> TodoRead:
        logger.debug("Get todo invoked", extra={"todo_id": todo_id})
        todo = await self.repository.get(todo_id)
        if not todo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Todo not found",
            )
        logger.debug("Get todo completed", extra={"todo_id": todo_id})
        return TodoRead.model_validate(todo)

    async def create_todo(self, payload: TodoCreate) -> TodoRead:
        logger.info("Create todo invoked")
        todo = await self.repository.create(payload)
        logger.info("Create todo completed", extra={"todo_id": todo.id})
        return TodoRead.model_validate(todo)

    async def update_todo(self, todo_id: int, payload: TodoUpdate) -> TodoRead:
        logger.info("Update todo invoked", extra={"todo_id": todo_id})
        todo = await self.repository.get(todo_id)
        if not todo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Todo not found",
            )
        updated = await self.repository.update(todo, payload)
        logger.info("Update todo completed", extra={"todo_id": todo_id})
        return TodoRead.model_validate(updated)

    async def delete_todo(self, todo_id: int) -> None:
        logger.info("Delete todo invoked", extra={"todo_id": todo_id})
        todo = await self.repository.get(todo_id)
        if not todo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Todo not found",
            )
        await self.repository.delete(todo)
        logger.info("Delete todo completed", extra={"todo_id": todo_id})
