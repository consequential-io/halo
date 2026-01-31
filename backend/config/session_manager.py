"""
Session Manager - In-memory session storage for analysis workflows.

Stores analysis results and recommendations per session for multi-step workflows.
Sessions expire after 60 minutes.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from threading import Lock
from typing import Any


@dataclass
class Session:
    """Session data container."""
    session_id: str
    tenant: str
    created_at: datetime
    expires_at: datetime
    analysis_result: dict[str, Any] | None = None
    recommendations: dict[str, Any] | None = None
    execution_result: dict[str, Any] | None = None
    all_ads: list[dict] | None = None


class SessionManager:
    """
    In-memory session manager for analysis workflows.

    Singleton pattern - use get_session_manager() to get instance.
    """

    _instance: "SessionManager | None" = None
    _lock = Lock()

    def __new__(cls) -> "SessionManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        """Initialize session storage."""
        self._sessions: dict[str, Session] = {}
        self._session_ttl_minutes = 60

    def create_session(self, tenant: str) -> Session:
        """
        Create a new session.

        Args:
            tenant: Tenant identifier (e.g., 'TL', 'WH')

        Returns:
            New Session object
        """
        self._cleanup_expired()

        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        session = Session(
            session_id=session_id,
            tenant=tenant,
            created_at=now,
            expires_at=now + timedelta(minutes=self._session_ttl_minutes),
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Session | None:
        """
        Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session if found and not expired, None otherwise
        """
        session = self._sessions.get(session_id)
        if session is None:
            return None

        if datetime.now(timezone.utc) > session.expires_at:
            del self._sessions[session_id]
            return None

        return session

    def update_session(
        self,
        session_id: str,
        analysis_result: dict[str, Any] | None = None,
        recommendations: dict[str, Any] | None = None,
        execution_result: dict[str, Any] | None = None,
        all_ads: list[dict] | None = None,
    ) -> Session | None:
        """
        Update session data.

        Args:
            session_id: Session identifier
            analysis_result: Analysis output to store
            recommendations: Recommendations output to store
            execution_result: Execution output to store
            all_ads: All ads data to store

        Returns:
            Updated session or None if not found
        """
        session = self.get_session(session_id)
        if session is None:
            return None

        if analysis_result is not None:
            session.analysis_result = analysis_result
        if recommendations is not None:
            session.recommendations = recommendations
        if execution_result is not None:
            session.execution_result = execution_result
        if all_ads is not None:
            session.all_ads = all_ads

        return session

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def _cleanup_expired(self) -> int:
        """Remove expired sessions. Returns count of removed sessions."""
        now = datetime.now(timezone.utc)
        expired = [
            sid for sid, s in self._sessions.items()
            if now > s.expires_at
        ]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)

    def get_active_session_count(self) -> int:
        """Get count of active (non-expired) sessions."""
        self._cleanup_expired()
        return len(self._sessions)


# Singleton accessor
def get_session_manager() -> SessionManager:
    """Get the singleton session manager instance."""
    return SessionManager()
