from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set
from .data_models import (
    AuthCredentials,
    AuthenticationResult,
    SessionToken,
    StudentProfile,
    Course,
    Grade,
    ScheduleEntry,
    Transcript,
    SemesterInfo,
    PortalFeature,
)
from .authenticator import BaseAuthenticator
from .exeptions import (
    AuthenticationException,
    FeatureNotSupportedException,
)


class BasePortalAdapter(ABC):
    """
    Base interface that ALL university portal adapters must implement.
    This defines the contract for interacting with any student portal.
    """

    def __init__(self, authenticator: BaseAuthenticator, config: Dict[str, Any]):
        """
        Initialize adapter with authenticator and configuration.

        Args:
            authenticator: Authentication strategy for this portal
            config: Portal-specific configuration
        """
        self.authenticator = authenticator
        self.config = config
        self._session_token: Optional[SessionToken] = None

    # ==================== METADATA ====================

    @property
    @abstractmethod
    def university_name(self) -> str:
        """Return university name (e.g., 'MIT')"""
        pass

    @property
    @abstractmethod
    def university_domain(self) -> str:
        """Return university domain (e.g., 'mit.edu')"""
        pass

    @property
    @abstractmethod
    def supported_features(self) -> Set[PortalFeature]:
        """
        Return set of features this portal supports.

        Example:
            {PortalFeature.COURSES, PortalFeature.GRADES, PortalFeature.SCHEDULE}
        """
        pass

    def supports_feature(self, feature: PortalFeature) -> bool:
        """Check if this adapter supports a specific feature"""
        return feature in self.supported_features

    # ==================== AUTHENTICATION ====================

    async def authenticate(self, credentials: AuthCredentials) -> AuthenticationResult:
        """
        Authenticate user and store session.

        Args:
            credentials: User credentials

        Returns:
            AuthenticationResult

        Raises:
            AuthenticationException: If authentication fails
        """
        result = await self.authenticator.authenticate(credentials)

        if result.success:
            self._session_token = result.session_token

        return result

    async def ensure_authenticated(self):
        """
        Ensure we have a valid session, refresh if needed.

        Raises:
            AuthenticationException: If not authenticated
        """
        if not self._session_token:
            raise AuthenticationException(
                "Not authenticated. Call authenticate() first."
            )

        # Check if token expired
        if self._session_token.is_expired():
            result = await self.authenticator.refresh_session(self._session_token)
            if result.success:
                self._session_token = result.session_token
            else:
                raise AuthenticationException("Session expired and refresh failed")

    # ==================== CORE DATA FETCHING ====================

    @abstractmethod
    async def get_student_profile(self) -> StudentProfile:
        """
        Fetch student profile/personal information.

        Returns:
            StudentProfile with normalized data

        Raises:
            AuthenticationException: If not authenticated
            DataFetchException: If fetch fails
        """
        pass

    @abstractmethod
    async def get_courses(self, semester: Optional[str] = None) -> List[Course]:
        """
        Fetch enrolled courses.

        Args:
            semester: Specific semester (None for current)

        Returns:
            List of Course objects

        Raises:
            AuthenticationException: If not authenticated
            DataFetchException: If fetch fails
            FeatureNotSupportedException: If portal doesn't support courses
        """
        pass

    @abstractmethod
    async def get_grades(self, semester: Optional[str] = None) -> List[Grade]:
        """
        Fetch grades.

        Args:
            semester: Specific semester (None for all)

        Returns:
            List of Grade objects

        Raises:
            AuthenticationException: If not authenticated
            DataFetchException: If fetch fails
            FeatureNotSupportedException: If portal doesn't support grades
        """
        pass

    @abstractmethod
    async def get_schedule(self, semester: Optional[str] = None) -> List[ScheduleEntry]:
        """
        Fetch class schedule/timetable.

        Args:
            semester: Specific semester (None for current)

        Returns:
            List of ScheduleEntry objects

        Raises:
            AuthenticationException: If not authenticated
            DataFetchException: If fetch fails
            FeatureNotSupportedException: If portal doesn't support schedule
        """
        pass

    # ==================== OPTIONAL FEATURES ====================

    async def get_transcript(self) -> Transcript:
        """
        Fetch academic transcript.

        Returns:
            Transcript object

        Raises:
            FeatureNotSupportedException: If not supported
        """
        if PortalFeature.TRANSCRIPT not in self.supported_features:
            raise FeatureNotSupportedException(
                f"Transcript not supported for {self.university_name}"
            )
        raise NotImplementedError()

    async def get_available_semesters(self) -> List[SemesterInfo]:
        """
        Get list of available semesters/terms.

        Returns:
            List of SemesterInfo objects
        """
        raise NotImplementedError("This adapter doesn't support semester discovery")

    # ==================== UTILITY METHODS ====================

    async def close(self):
        """Cleanup resources (close HTTP clients, etc.)"""
        if self._session_token:
            try:
                await self.authenticator.logout(self._session_token)
            except:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import asyncio

        asyncio.run(self.close())
