"""Session Manager - Singleton session service for ADK agents."""

from typing import Optional
import logging

try:
    from google.adk.sessions import InMemorySessionService
    from google.adk.runners import Runner
    HAS_ADK = True
except ImportError:
    HAS_ADK = False
    InMemorySessionService = None  # type: ignore
    Runner = None  # type: ignore

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Singleton session manager for ADK agents.

    Provides a shared session service across all agents to maintain
    conversation context and state.
    """

    _instance: Optional["SessionManager"] = None
    _session_service: Optional[InMemorySessionService] = None

    def __new__(cls) -> "SessionManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize the session service."""
        if HAS_ADK and InMemorySessionService:
            self._session_service = InMemorySessionService()
            logger.info("SessionManager initialized with InMemorySessionService")
        else:
            logger.warning("ADK not available, SessionManager running in mock mode")

    @property
    def session_service(self) -> Optional[InMemorySessionService]:
        """Get the session service instance."""
        return self._session_service

    async def create_session(
        self,
        app_name: str = "agatha",
        user_id: str = "default_user"
    ):
        """
        Create a new session.

        Args:
            app_name: Application name
            user_id: User identifier

        Returns:
            Session object or None if ADK not available
        """
        if self._session_service is None:
            logger.warning("Session service not available")
            return None

        session = await self._session_service.create_session(
            app_name=app_name,
            user_id=user_id
        )
        logger.debug(f"Created session: {session.id}")
        return session

    async def get_session(
        self,
        app_name: str,
        user_id: str,
        session_id: str
    ):
        """
        Get an existing session.

        Args:
            app_name: Application name
            user_id: User identifier
            session_id: Session ID

        Returns:
            Session object or None
        """
        if self._session_service is None:
            return None

        try:
            return await self._session_service.get_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id
            )
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None

    def create_runner(self, agent, app_name: str = "agatha"):
        """
        Create a Runner for an agent using the shared session service.

        Args:
            agent: The ADK agent
            app_name: Application name

        Returns:
            Runner instance or None if ADK not available
        """
        if not HAS_ADK or Runner is None or self._session_service is None:
            return None

        return Runner(
            agent=agent,
            app_name=app_name,
            session_service=self._session_service,
        )


# Singleton instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get the singleton SessionManager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
