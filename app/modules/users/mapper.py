"""Mapping helpers between internal user models and API v1 contracts.

This layer keeps API schemas and module schemas decoupled on purpose.
"""

from app.api.v1.schemas.users import UserCreate as ApiUserCreate
from app.api.v1.schemas.users import UserListResponse as ApiUserListResponse
from app.api.v1.schemas.users import UserRead as ApiUserRead
from app.api.v1.schemas.users import UserUpdate as ApiUserUpdate
from app.modules.users.schemas import UserCreate as ModuleUserCreate
from app.modules.users.schemas import UserRead as ModuleUserRead
from app.modules.users.schemas import UserUpdate as ModuleUserUpdate


def to_module_create(payload: ApiUserCreate) -> ModuleUserCreate:
    return ModuleUserCreate(**payload.model_dump())


def to_module_update(payload: ApiUserUpdate) -> ModuleUserUpdate:
    return ModuleUserUpdate(**payload.model_dump(exclude_unset=True))


def to_api_read(user: ModuleUserRead) -> ApiUserRead:
    return ApiUserRead.model_validate(user.model_dump())


def to_api_list_response(data: dict) -> ApiUserListResponse:
    items = [to_api_read(item) for item in data["items"]]
    return ApiUserListResponse(
        items=items,
        total=data["total"],
        limit=data["limit"],
        offset=data["offset"],
    )
