from typing import List, Optional


class AdapterException(Exception):
    """Base exception for all adapter errors"""

    pass


class AuthenticationException(AdapterException):
    """Authentication failed or session invalid"""

    pass


class DataFetchException(AdapterException):
    """Failed to fetch data from portal"""

    def __init__(
        self, message: str, data_type: str, original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.data_type = data_type
        self.original_error = original_error


class FeatureNotSupportedException(AdapterException):
    """Requested feature not supported by this portal"""

    pass


class SessionExpiredException(AuthenticationException):
    """Session/token has expired"""

    pass


class MFARequiredException(AuthenticationException):
    """Multi-factor authentication required"""

    def __init__(self, message: str, available_methods: List[str]):
        super().__init__(message)
        self.available_methods = available_methods


class ParsingException(AdapterException):
    """Failed to parse portal response"""

    pass
