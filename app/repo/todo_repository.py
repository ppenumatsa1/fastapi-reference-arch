"""Repository for todo persistence operations."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging.logger import get_logger
from app.core.models import Todo
from app.core.schemas import TodoCreate, TodoUpdate
from app.repo.base import BaseRepository

logger = get_logger(__name__)


class TodoRepository(BaseRepository[Todo]):
    def __init__(self, session: Session):
        super().__init__(session)

    def list(self) -> Sequence[Todo]:
        stmt = select(Todo).order_by(Todo.created_at.desc())
        logger.debug("Fetching todo list")
        return self.session.execute(stmt).scalars().all()

    def get(self, todo_id: int) -> Todo | None:
        logger.debug("Fetching todo", extra={"todo_id": todo_id})
        return self.session.get(Todo, todo_id)

    def create(self, payload: TodoCreate) -> Todo:
        todo = Todo(**payload.model_dump())
        self.session.add(todo)
        self.session.commit()
        self.session.refresh(todo)
        logger.info("Created todo", extra={"todo_id": todo.id, "title": todo.title})
        return todo

    def update(self, todo: Todo, payload: TodoUpdate) -> Todo:
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(todo, key, value)
        self.session.add(todo)
        self.session.commit()
        self.session.refresh(todo)
        logger.info("Updated todo", extra={"todo_id": todo.id})
        return todo

    def delete(self, todo: Todo) -> None:
        self.session.delete(todo)
        self.session.commit()
        logger.info("Deleted todo", extra={"todo_id": todo.id})
