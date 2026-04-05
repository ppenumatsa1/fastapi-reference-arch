"""HTTP routes for user resources (API v1)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.users import UserCreate, UserListResponse, UserRead, UserUpdate
from app.core.database import get_db
from app.core.logging.logger import get_logger
from app.modules.users.mapper import (
    to_api_list_response,
    to_api_read,
    to_module_create,
    to_module_update,
)
from app.modules.users.service import UserService

router = APIRouter()
logger = get_logger(__name__)


def get_user_service(db: Annotated[AsyncSession, Depends(get_db)]) -> UserService:
    return UserService(db)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


@router.get(
    "/",
    response_model=UserListResponse,
)
async def list_users(
    service: UserServiceDep,
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    logger.info(
        "List users request",
        extra={"path": request.url.path, "limit": limit, "offset": offset},
    )
    users = await service.list_users(limit=limit, offset=offset)
    return to_api_list_response(users)


@router.get(
    "/search",
    response_model=UserListResponse,
)
async def search_users_by_name(
    service: UserServiceDep,
    request: Request,
    q: str = Query(..., min_length=1, description="Partial first or last name"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    logger.info(
        "Search users by name request",
        extra={"path": request.url.path, "query": q, "limit": limit, "offset": offset},
    )
    users = await service.search_users_by_name(query=q, limit=limit, offset=offset)
    return to_api_list_response(users)


@router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(payload: UserCreate, service: UserServiceDep, request: Request):
    logger.info("Create user request", extra={"path": request.url.path})
    user = await service.create_user(to_module_create(payload))
    return to_api_read(user)


@router.put(
    "/{user_id}",
    response_model=UserRead,
)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    service: UserServiceDep,
    request: Request,
):
    logger.info(
        "Update user request",
        extra={"user_id": user_id, "path": request.url.path},
    )
    user = await service.update_user(user_id, to_module_update(payload))
    return to_api_read(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_user(user_id: int, service: UserServiceDep, request: Request):
    logger.info(
        "Delete user request",
        extra={"user_id": user_id, "path": request.url.path},
    )
    await service.delete_user(user_id)
    return None
