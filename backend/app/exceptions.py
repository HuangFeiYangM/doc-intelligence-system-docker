"""
Custom exceptions for the application.
"""


class AppException(Exception):
    """Base application exception."""

    def __init__(self, message: str, status_code: int = 500, detail: str = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.message)


class ValidationError(AppException):
    """Validation error exception."""

    def __init__(self, message: str, detail: str = None):
        super().__init__(message, status_code=400, detail=detail)


class NotFoundError(AppException):
    """Resource not found exception."""

    def __init__(self, message: str, detail: str = None):
        super().__init__(message, status_code=404, detail=detail)


class ProcessingError(AppException):
    """Document processing error exception."""

    def __init__(self, message: str, detail: str = None):
        super().__init__(message, status_code=422, detail=detail)
