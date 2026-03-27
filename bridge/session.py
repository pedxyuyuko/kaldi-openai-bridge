"""WebSocket session management for kaldi-openai-bridge."""

from __future__ import annotations

import time
import uuid

from bridge.audio import AudioBuffer
from bridge.config import BridgeConfig


class Session:
    """Represents a single WebSocket audio session.

    Each session has its own AudioBuffer for audio isolation.
    """

    def __init__(self, session_id: str) -> None:
        self.session_id: str = session_id
        self.audio: AudioBuffer = AudioBuffer()
        self.created_at: float = time.time()
        self.is_active: bool = True
        self.total_bytes: int = 0

    def feed(self, data: bytes) -> None:
        """Append audio data to the session's buffer."""
        self.audio.feed(data)
        self.total_bytes += len(data)


class SessionManager:
    """Manages concurrent WebSocket sessions.

    Enforces max_concurrent_sessions limit from config.
    """

    def __init__(self, config: BridgeConfig) -> None:
        self._config: BridgeConfig = config
        self._sessions: dict[str, Session] = {}

    def create_session(self) -> str:
        """Create a new session and return its ID.

        Raises:
            RuntimeError: If max concurrent sessions exceeded.
        """
        if not self.check_limits():
            raise RuntimeError(
                f"Max concurrent sessions ({self._config.max_concurrent_sessions}) reached"
            )
        session_id = uuid.uuid4().hex
        self._sessions[session_id] = Session(session_id)
        return session_id

    def get_session(self, session_id: str) -> Session | None:
        """Retrieve a session by ID, or None if not found."""
        return self._sessions.get(session_id)

    def remove_session(self, session_id: str) -> None:
        """Remove a session from the manager."""
        _ = self._sessions.pop(session_id, None)

    def check_limits(self) -> bool:
        """Return True if a new session can be accepted."""
        return self.active_count() < self._config.max_concurrent_sessions

    def active_count(self) -> int:
        """Return the number of active sessions."""
        return len(self._sessions)

    def available_slots(self) -> int:
        """Return the number of available session slots."""
        return max(0, self._config.max_concurrent_sessions - len(self._sessions))
