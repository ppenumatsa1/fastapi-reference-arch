"""Repository for user persistence operations."""

from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, PersistenceError
from app.core.logging.logger import get_logger
from app.modules.users.model import User
from app.modules.users.schemas import UserCreate, UserUpdate

logger = get_logger(__name__)


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self, limit: int, offset: int) -> Sequence[User]:
        stmt = select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
        logger.info("Fetching user list")
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self) -> int:
        stmt = select(func.count(User.id))
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def search_by_name(
        self,
        query: str,
        limit: int,
        offset: int,
    ) -> Sequence[User]:
        pattern = f"%{query}%"
        stmt = (
            select(User)
            .where(
                or_(
                    User.first_name.ilike(pattern),
                    User.last_name.ilike(pattern),
                )
            )
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        logger.info(
            "Searching users by name",
            extra={"query": query, "limit": limit, "offset": offset},
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_name(self, query: str) -> int:
        pattern = f"%{query}%"
        stmt = select(func.count(User.id)).where(
            or_(
                User.first_name.ilike(pattern),
                User.last_name.ilike(pattern),
            )
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def create(self, payload: UserCreate) -> User:
        user = User(**payload.model_dump())
        self.session.add(user)

        try:
            await self.session.commit()
            await self.session.refresh(user)
        except IntegrityError as exc:
            await self.session.rollback()
            logger.warning("Create user failed due to integrity error")
            raise ConflictError("User create conflict", cause=exc) from exc
        except SQLAlchemyError as exc:
            await self.session.rollback()
            logger.exception("Create user failed due to database error")
            raise PersistenceError("Failed to create user", cause=exc) from exc

        logger.info("Created user", extra={"user_id": user.id, "email": user.email})
        return user

    async def update_by_id(self, user_id: int, payload: UserUpdate) -> User:
        stmt = select(User).where(User.id == user_id).with_for_update()
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("User not found")

        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(user, key, value)
        self.session.add(user)

        try:
            await self.session.commit()
            await self.session.refresh(user)
        except IntegrityError as exc:
            await self.session.rollback()
            logger.warning("Update user failed due to integrity error")
            raise ConflictError("User update conflict", cause=exc) from exc
        except SQLAlchemyError as exc:
            await self.session.rollback()
            logger.exception("Update user failed due to database error")
            raise PersistenceError("Failed to update user", cause=exc) from exc

        logger.info("Updated user", extra={"user_id": user.id})
        return user

    async def delete_by_id(self, user_id: int) -> None:
        stmt = select(User).where(User.id == user_id).with_for_update()
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("User not found")

        await self.session.delete(user)

        try:
            await self.session.commit()
        except SQLAlchemyError as exc:
            await self.session.rollback()
            logger.exception("Delete user failed due to database error")
            raise PersistenceError("Failed to delete user", cause=exc) from exc

        logger.info("Deleted user", extra={"user_id": user.id})
