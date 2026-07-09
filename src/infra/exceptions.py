class AppException(Exception):
    """Base exception for the application."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR"
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class LLMException(AppException):
    """Exception for LLM-related errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 502,
        error_code: str = "LLM_ERROR"
    ):
        super().__init__(message, status_code, error_code)


class ValidationException(AppException):
    """Exception for validation errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "VALIDATION_ERROR"
    ):
        super().__init__(message, status_code=400, error_code=error_code)


class ConfigException(AppException):
    """Exception for configuration errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "CONFIG_ERROR"
    ):
        super().__init__(message, status_code=500, error_code=error_code)
