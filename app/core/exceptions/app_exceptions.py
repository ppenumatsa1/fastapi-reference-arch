"""Domain-specific exception hierarchy."""


class AppError(Exception):
    """Base exception for predictable application errors."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)
