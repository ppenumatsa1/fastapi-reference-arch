"""Application service encapsulating user workflows."""

from time import perf_counter

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging.logger import get_logger
from app.core.observability import emit_business_event, record_user_operation_metric
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserCreate, UserRead, UserUpdate

logger = get_logger(__name__)


class UserService:
    def __init__(self, session: AsyncSession):
        self.repository = UserRepository(session)

    async def list_users(self, limit: int, offset: int):
        started = perf_counter()
        logger.info("List users invoked", extra={"limit": limit, "offset": offset})
        users = await self.repository.list(limit=limit, offset=offset)
        total = await self.repository.count()
        logger.info(
            "List users completed",
            extra={
                "returned": len(users),
                "total": total,
                "limit": limit,
                "offset": offset,
            },
        )
        duration_ms = (perf_counter() - started) * 1000
        record_user_operation_metric(
            action="list", outcome="success", duration_ms=duration_ms
        )
        emit_business_event(
            "user.list.completed",
            {
                "user.action": "list",
                "user.returned": len(users),
                "user.total": total,
            },
        )
        return {
            "items": [UserRead.model_validate(user) for user in users],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def search_users_by_name(self, query: str, limit: int, offset: int):
        started = perf_counter()
        normalized_query = query.strip()
        logger.info(
            "Search users by name invoked",
            extra={"query": normalized_query, "limit": limit, "offset": offset},
        )
        users = await self.repository.search_by_name(
            query=normalized_query,
            limit=limit,
            offset=offset,
        )
        total = await self.repository.count_by_name(normalized_query)
        logger.info(
            "Search users by name completed",
            extra={
                "query": normalized_query,
                "returned": len(users),
                "total": total,
                "limit": limit,
                "offset": offset,
            },
        )
        duration_ms = (perf_counter() - started) * 1000
        record_user_operation_metric(
            action="search", outcome="success", duration_ms=duration_ms
        )
        emit_business_event(
            "user.search.completed",
            {
                "user.action": "search",
                "user.query": normalized_query,
                "user.returned": len(users),
                "user.total": total,
            },
        )
        return {
            "items": [UserRead.model_validate(user) for user in users],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def create_user(self, payload: UserCreate) -> UserRead:
        started = perf_counter()
        logger.info("Create user invoked")
        user = await self.repository.create(payload)
        logger.info("Create user completed", extra={"user_id": user.id})
        duration_ms = (perf_counter() - started) * 1000
        record_user_operation_metric(
            action="create", outcome="success", duration_ms=duration_ms
        )
        emit_business_event(
            "user.create.completed",
            {"user.action": "create", "user.id": user.id},
        )
        return UserRead.model_validate(user)

    async def update_user(self, user_id: int, payload: UserUpdate) -> UserRead:
        started = perf_counter()
        logger.info("Update user invoked", extra={"user_id": user_id})
        try:
            updated = await self.repository.update_by_id(user_id, payload)
        except NotFoundError:
            duration_ms = (perf_counter() - started) * 1000
            record_user_operation_metric(
                action="update", outcome="not_found", duration_ms=duration_ms
            )
            emit_business_event(
                "user.update.not_found",
                {"user.action": "update", "user.id": user_id},
            )
            raise
        logger.info("Update user completed", extra={"user_id": user_id})
        duration_ms = (perf_counter() - started) * 1000
        record_user_operation_metric(
            action="update", outcome="success", duration_ms=duration_ms
        )
        emit_business_event(
            "user.update.completed",
            {"user.action": "update", "user.id": user_id},
        )
        return UserRead.model_validate(updated)

    async def delete_user(self, user_id: int) -> None:
        started = perf_counter()
        logger.info("Delete user invoked", extra={"user_id": user_id})
        try:
            await self.repository.delete_by_id(user_id)
        except NotFoundError:
            duration_ms = (perf_counter() - started) * 1000
            record_user_operation_metric(
                action="delete", outcome="not_found", duration_ms=duration_ms
            )
            emit_business_event(
                "user.delete.not_found",
                {"user.action": "delete", "user.id": user_id},
            )
            raise
        logger.info("Delete user completed", extra={"user_id": user_id})
        duration_ms = (perf_counter() - started) * 1000
        record_user_operation_metric(
            action="delete", outcome="success", duration_ms=duration_ms
        )
        emit_business_event(
            "user.delete.completed",
            {"user.action": "delete", "user.id": user_id},
        )
