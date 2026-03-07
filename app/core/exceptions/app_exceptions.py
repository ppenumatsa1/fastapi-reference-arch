"""Application exception hierarchy and error serialization."""

from __future__ import annotations


class AppError(Exception):
    """Base exception for predictable application errors."""

    status_code = 400
    code = "app_error"

    def __init__(
        self,
        message: str = "Application error",
        *,
        cause: Exception | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.cause = cause

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    status_code = 404
    code = "not_found"


class BadRequestError(AppError):
    """Raised for semantically invalid input."""

    status_code = 400
    code = "bad_request"


class ConflictError(AppError):
    """Raised when a request conflicts with current resource state."""

    status_code = 409
    code = "conflict"


class PersistenceError(AppError):
    """Raised when persistence operations fail unexpectedly."""

    status_code = 500
    code = "persistence_error"
