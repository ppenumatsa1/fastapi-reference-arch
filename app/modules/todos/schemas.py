"""Pydantic schemas for todo resources."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TodoBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: str | None = Field(None, max_length=1024)

    @model_validator(mode="after")
    def normalize_text(self) -> TodoBase:
        # Strip whitespace and ensure title is not empty after trimming.
        if self.title is not None:
            self.title = self.title.strip()
        if self.description is not None:
            self.description = self.description.strip()

        if not self.title:
            raise ValueError("title must not be empty or whitespace")

        return self


class TodoCreate(TodoBase):
    pass


class TodoUpdate(BaseModel):
    title: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=1024)
    is_completed: bool | None = None

    @model_validator(mode="after")
    def normalize_text(self) -> TodoUpdate:
        # Strip whitespace and ensure provided title is not empty.
        if self.title is not None:
            self.title = self.title.strip()
            if not self.title:
                raise ValueError("title must not be empty or whitespace")

        if self.description is not None:
            self.description = self.description.strip()

        return self


class TodoRead(TodoBase):
    id: int
    is_completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TodoListResponse(BaseModel):
    items: list[TodoRead]
    total: int
    limit: int
    offset: int
