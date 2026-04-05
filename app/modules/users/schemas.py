"""Internal module schemas for user resources.

These models intentionally mirror current API v1 fields, but they remain
module-owned so internal logic can evolve independently from versioned API
contracts.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class UserBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=320)

    @model_validator(mode="after")
    def normalize_text(self) -> UserBase:
        self.first_name = self.first_name.strip()
        self.last_name = self.last_name.strip()
        self.email = self.email.strip().lower()

        if not self.first_name:
            raise ValueError("first_name must not be empty or whitespace")
        if not self.last_name:
            raise ValueError("last_name must not be empty or whitespace")
        if "@" not in self.email:
            raise ValueError("email must be a valid email address")

        return self


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    email: str | None = Field(None, min_length=3, max_length=320)
    is_active: bool | None = None

    @model_validator(mode="after")
    def normalize_text(self) -> UserUpdate:
        if self.first_name is not None:
            self.first_name = self.first_name.strip()
            if not self.first_name:
                raise ValueError("first_name must not be empty or whitespace")

        if self.last_name is not None:
            self.last_name = self.last_name.strip()
            if not self.last_name:
                raise ValueError("last_name must not be empty or whitespace")

        if self.email is not None:
            self.email = self.email.strip().lower()
            if "@" not in self.email:
                raise ValueError("email must be a valid email address")

        return self


class UserRead(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    items: list[UserRead]
    total: int
    limit: int
    offset: int
