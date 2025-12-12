"""
Session Manager
===============

Manages active sessions with MCP servers.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, List, Any
from enum import Enum

from ..common.logger import get_logger
from ..common.exceptions import ConnectionError

logger = get_logger(__name__)


class SessionState(Enum):
    """Session state."""
    
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    CLOSING = "closing"


@dataclass
class Session:
    """
    Represents a session with an MCP server.
    
    A session tracks:
    - Connection state
    - Server capabilities
    - Available tools and resources
    - Health metrics
    """
    
    id: str
    server_name: str
    server_url: str
    state: SessionState = SessionState.DISCONNECTED
    
    # Server info (populated after initialize)
    server_version: Optional[str] = None
    protocol_version: Optional[str] = None
    capabilities: Dict[str, Any] = field(default_factory=dict)
    
    # Available primitives
    tools: List[Dict[str, Any]] = field(default_factory=list)
    resources: List[Dict[str, Any]] = field(default_factory=list)
    prompts: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metrics
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: Optional[datetime] = None
    request_count: int = 0
    error_count: int = 0
    
    # Internal
    _transport: Any = None
    
    @property
    def is_ready(self) -> bool:
        """Check if session is ready for requests."""
        return self.state == SessionState.READY
    
    @property
    def is_connected(self) -> bool:
        """Check if session is connected."""
        return self.state in (SessionState.CONNECTED, SessionState.INITIALIZING, SessionState.READY)
    
    def record_activity(self) -> None:
        """Record session activity."""
        self.last_activity = datetime.utcnow()
        self.request_count += 1
    
    def record_error(self) -> None:
        """Record session error."""
        self.error_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "server_name": self.server_name,
            "server_url": self.server_url,
            "state": self.state.value,
            "server_version": self.server_version,
            "protocol_version": self.protocol_version,
            "tools_count": len(self.tools),
            "resources_count": len(self.resources),
            "prompts_count": len(self.prompts),
            "request_count": self.request_count,
            "error_count": self.error_count,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
        }


class SessionManager:
    """
    Manages multiple sessions with MCP servers.
    
    Features:
    - Track active sessions
    - Add/remove sessions
    - Handle multiple concurrent connections
    - Session lifecycle management
    """
    
    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._lock = asyncio.Lock()
        self._session_id_counter = 0
    
    def _generate_session_id(self, server_name: str) -> str:
        """Generate unique session ID."""
        self._session_id_counter += 1
        return f"{server_name}_{self._session_id_counter}"
    
    async def create_session(
        self,
        server_name: str,
        server_url: str,
    ) -> Session:
        """
        Create a new session.
        
        Args:
            server_name: Name of the server
            server_url: URL of the server
            
        Returns:
            Created session
        """
        async with self._lock:
            session_id = self._generate_session_id(server_name)
            
            session = Session(
                id=session_id,
                server_name=server_name,
                server_url=server_url,
            )
            
            self._sessions[session_id] = session
            logger.info(f"Created session: {session_id} for {server_url}")
            
            return session
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        async with self._lock:
            return self._sessions.get(session_id)
    
    async def get_session_by_server(self, server_name: str) -> Optional[Session]:
        """Get session by server name."""
        async with self._lock:
            for session in self._sessions.values():
                if session.server_name == server_name:
                    return session
            return None
    
    async def get_ready_session(self, server_name: str) -> Optional[Session]:
        """Get a ready session for a server."""
        session = await self.get_session_by_server(server_name)
        if session and session.is_ready:
            return session
        return None
    
    async def list_sessions(self) -> List[Session]:
        """List all sessions."""
        async with self._lock:
            return list(self._sessions.values())
    
    async def list_ready_sessions(self) -> List[Session]:
        """List all ready sessions."""
        async with self._lock:
            return [s for s in self._sessions.values() if s.is_ready]
    
    async def update_session_state(
        self,
        session_id: str,
        state: SessionState,
    ) -> None:
        """Update session state."""
        async with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].state = state
                logger.debug(f"Session {session_id} state: {state.value}")
    
    async def remove_session(self, session_id: str) -> Optional[Session]:
        """
        Remove a session.
        
        Args:
            session_id: Session ID to remove
            
        Returns:
            Removed session or None
        """
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                logger.info(f"Removed session: {session_id}")
            return session
    
    async def close_all(self) -> None:
        """Close all sessions."""
        async with self._lock:
            session_ids = list(self._sessions.keys())
        
        for session_id in session_ids:
            await self.remove_session(session_id)
        
        logger.info("Closed all sessions")
    
    def __len__(self) -> int:
        """Get number of sessions."""
        return len(self._sessions)
    
    @property
    def session_count(self) -> int:
        """Get session count."""
        return len(self._sessions)
    
    @property
    def ready_session_count(self) -> int:
        """Get ready session count."""
        return sum(1 for s in self._sessions.values() if s.is_ready)


class SessionPool:
    """
    Pool of sessions for load balancing across multiple servers.
    
    Useful for connecting to multiple instances of the same service.
    """
    
    def __init__(self, max_sessions_per_server: int = 3):
        self.max_sessions_per_server = max_sessions_per_server
        self._pools: Dict[str, List[Session]] = {}
        self._lock = asyncio.Lock()
        self._round_robin: Dict[str, int] = {}
    
    async def add_session(self, server_name: str, session: Session) -> None:
        """Add session to pool."""
        async with self._lock:
            if server_name not in self._pools:
                self._pools[server_name] = []
                self._round_robin[server_name] = 0
            
            if len(self._pools[server_name]) < self.max_sessions_per_server:
                self._pools[server_name].append(session)
    
    async def get_session(self, server_name: str) -> Optional[Session]:
        """Get next available session (round-robin)."""
        async with self._lock:
            if server_name not in self._pools:
                return None
            
            pool = self._pools[server_name]
            ready = [s for s in pool if s.is_ready]
            
            if not ready:
                return None
            
            # Round-robin selection
            idx = self._round_robin[server_name] % len(ready)
            self._round_robin[server_name] = idx + 1
            
            return ready[idx]
    
    async def remove_session(self, server_name: str, session: Session) -> None:
        """Remove session from pool."""
        async with self._lock:
            if server_name in self._pools:
                if session in self._pools[server_name]:
                    self._pools[server_name].remove(session)

