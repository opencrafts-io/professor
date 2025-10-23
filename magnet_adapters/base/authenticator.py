from abc import ABC, abstractmethod
from typing import Any, Dict
from .data_models import (
    AuthCredentials,
    AuthMethodType,
    AuthenticationResult,
    SessionToken,
)


class BaseAuthenticator(ABC):
    """
    Base interface for all authentication strategies.
    Each university portal's authentication method extends this.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize authenticator with configuration.

        Args:
            config: Dictionary containing authentication configuration
                    (URLs, client IDs, etc.)
        """
        self.config = config

    @property
    @abstractmethod
    def auth_method_type(self) -> AuthMethodType:
        """Return the type of authentication this implements"""
        pass

    @abstractmethod
    async def authenticate(self, credentials: AuthCredentials) -> AuthenticationResult:
        """
        Authenticate user with provided credentials.

        Args:
            credentials: User credentials

        Returns:
            AuthenticationResult with session token if successful
        """
        pass

    @abstractmethod
    async def refresh_session(
        self, session_token: SessionToken
    ) -> AuthenticationResult:
        """
        Refresh an existing session/token.

        Args:
            session_token: Existing session token

        Returns:
            New AuthenticationResult with refreshed token
        """
        pass

    @abstractmethod
    async def validate_session(self, session_token: SessionToken) -> bool:
        """
        Check if a session token is still valid.

        Args:
            session_token: Token to validate

        Returns:
            True if valid, False otherwise
        """
        pass

    @abstractmethod
    async def logout(self, session_token: SessionToken) -> bool:
        """
        Logout and invalidate session.

        Args:
            session_token: Session to invalidate

        Returns:
            True if successful
        """
        pass

    # Optional: For MFA support
    async def send_mfa_code(self, credentials: AuthCredentials, method: str) -> bool:
        """
        Send MFA code to user (if supported).

        Args:
            credentials: User credentials
            method: MFA method ('sms', 'email', 'app')

        Returns:
            True if code sent successfully
        """
        raise NotImplementedError("MFA not supported by this authenticator")

    async def verify_mfa_code(
        self, credentials: AuthCredentials
    ) -> AuthenticationResult:
        """
        Verify MFA code and complete authentication.

        Args:
            credentials: Credentials with MFA code

        Returns:
            AuthenticationResult
        """
        raise NotImplementedError("MFA not supported by this authenticator")
