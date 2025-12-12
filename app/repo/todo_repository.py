"""Repository for todo persistence operations."""

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging.logger import get_logger
from app.core.models.todo import Todo
from app.core.schemas.todo import TodoCreate, TodoUpdate
from app.repo.base import BaseRepository

logger = get_logger(__name__)


class TodoRepository(BaseRepository[Todo]):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def list(self, limit: int, offset: int) -> Sequence[Todo]:
        stmt = select(Todo).order_by(Todo.created_at.desc()).limit(limit).offset(offset)
        logger.debug("Fetching todo list")
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self) -> int:
        stmt = select(func.count(Todo.id))
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def get(self, todo_id: int) -> Todo | None:
        logger.debug("Fetching todo", extra={"todo_id": todo_id})
        return await self.session.get(Todo, todo_id)

    async def create(self, payload: TodoCreate) -> Todo:
        todo = Todo(**payload.model_dump())
        self.session.add(todo)
        await self.session.commit()
        await self.session.refresh(todo)
        logger.info("Created todo", extra={"todo_id": todo.id, "title": todo.title})
        return todo

    async def update(self, todo: Todo, payload: TodoUpdate) -> Todo:
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(todo, key, value)
        self.session.add(todo)
        await self.session.commit()
        await self.session.refresh(todo)
        logger.info("Updated todo", extra={"todo_id": todo.id})
        return todo

    async def delete(self, todo: Todo) -> None:
        await self.session.delete(todo)
        await self.session.commit()
        logger.info("Deleted todo", extra={"todo_id": todo.id})
