"""
Base Game Server
================

Base class for game-specific MCP servers (League Manager, Referee, Player).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime
import asyncio

from .mcp_server import MCPServer, Tool, Resource
from ..common.logger import get_logger
from ..common.protocol import (
    PROTOCOL_VERSION,
    MessageType,
    MessageFactory,
    validate_message,
)
from ..common.exceptions import ProtocolError, ValidationError

logger = get_logger(__name__)


class BaseGameServer(MCPServer):
    """
    Base class for game servers.
    
    Extends MCPServer with game-specific functionality:
    - Protocol message handling
    - League protocol validation
    - Common game tools
    """
    
    def __init__(
        self,
        name: str,
        server_type: str,  # "league_manager", "referee", "player"
        league_id: str = "league_2024_01",
        **kwargs
    ):
        super().__init__(name, **kwargs)
        
        self.server_type = server_type
        self.league_id = league_id
        
        # Set sender format according to protocol spec (Section 2.4.4)
        # - league_manager: "league_manager" (single instance, no ID)
        # - referee: "referee:REF01" (type:id format)
        # - player: "player:P01" (type:id format)
        if server_type == "league_manager":
            sender = "league_manager"
        elif server_type == "referee":
            sender = f"referee:{name}"
        else:  # player
            sender = f"player:{name}"
        
        self.message_factory = MessageFactory(
            sender=sender,
            league_id=league_id,
        )
        
        # Register common protocol handler
        self.register_handler("protocol/message", self._handle_protocol_message)
        
        # Register common tools
        self._register_common_tools()
    
    def _register_common_tools(self) -> None:
        """Register tools common to all game servers."""
        
        # Heartbeat tool
        @self.tool("heartbeat", "Check server health")
        async def heartbeat(params: Dict) -> Dict:
            uptime = 0.0
            if self._start_time:
                uptime = (datetime.now() - self._start_time).total_seconds()
            
            return self.message_factory.heartbeat_response(uptime)
        
        # Protocol info tool
        @self.tool("get_protocol_info", "Get protocol version information")
        async def get_protocol_info(params: Dict) -> Dict:
            return {
                "protocol": PROTOCOL_VERSION,
                "server_type": self.server_type,
                "server_name": self.name,
                "league_id": self.league_id,
            }
    
    async def _handle_protocol_message(self, params: Optional[Dict]) -> Dict[str, Any]:
        """
        Handle a league protocol message.
        
        This validates the message format and dispatches to the appropriate handler.
        """
        if not params:
            raise ValidationError("Missing message params")
        
        message = params.get("message")
        if not message:
            raise ValidationError("Missing message field")
        
        # Validate protocol
        is_valid, error = validate_message(message)
        if not is_valid:
            raise ProtocolError(error)
        
        # Get message type
        msg_type = message.get("message_type")
        
        # Dispatch to specific handler
        handler_name = f"_handle_{msg_type.lower()}"
        handler = getattr(self, handler_name, None)
        
        if handler is None:
            raise ValidationError(f"Unsupported message type: {msg_type}")
        
        return await handler(message)
    
    async def send_protocol_message(
        self,
        target_url: str,
        message: Dict[str, Any],
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """
        Send a protocol message to another server.
        
        Args:
            target_url: The target server URL
            message: The protocol message
            timeout: Request timeout
            
        Returns:
            Response from target server
        """
        from ..transport.http_transport import HTTPTransport
        from ..transport.json_rpc import create_request
        
        # Validate our outgoing message
        is_valid, error = validate_message(message)
        if not is_valid:
            raise ProtocolError(f"Invalid outgoing message: {error}")
        
        # Create JSON-RPC request
        request = create_request(
            method="protocol/message",
            params={"message": message},
        )
        
        # Send via HTTP transport
        transport = HTTPTransport()
        try:
            await transport.connect(target_url)
            response = await transport.request(request.to_dict(), timeout=timeout)
            return response
        finally:
            await transport.disconnect()
    
    # ========================================================================
    # Override in subclasses
    # ========================================================================
    
    async def on_start(self) -> None:
        """Called when server starts. Override in subclasses."""
        pass
    
    async def on_stop(self) -> None:
        """Called when server stops. Override in subclasses."""
        pass
    
    async def start(self) -> None:
        """Start the server."""
        await super().start()
        await self.on_start()
    
    async def stop(self) -> None:
        """Stop the server."""
        await self.on_stop()
        await super().stop()


class GameServerRegistry:
    """
    Registry for tracking game servers.
    
    Used by league manager to track all servers.
    """
    
    def __init__(self):
        self._servers: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def register(
        self,
        server_id: str,
        server_type: str,
        endpoint: str,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Register a server."""
        async with self._lock:
            self._servers[server_id] = {
                "id": server_id,
                "type": server_type,
                "endpoint": endpoint,
                "metadata": metadata or {},
                "registered_at": datetime.utcnow().isoformat(),
                "status": "active",
            }
            logger.info(f"Registered server: {server_id} at {endpoint}")
    
    async def unregister(self, server_id: str) -> None:
        """Unregister a server."""
        async with self._lock:
            if server_id in self._servers:
                del self._servers[server_id]
                logger.info(f"Unregistered server: {server_id}")
    
    async def get(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Get server info."""
        async with self._lock:
            return self._servers.get(server_id)
    
    async def get_by_type(self, server_type: str) -> list[Dict[str, Any]]:
        """Get all servers of a type."""
        async with self._lock:
            return [
                s for s in self._servers.values()
                if s["type"] == server_type
            ]
    
    async def get_all(self) -> list[Dict[str, Any]]:
        """Get all registered servers."""
        async with self._lock:
            return list(self._servers.values())
    
    async def update_status(self, server_id: str, status: str) -> None:
        """Update server status."""
        async with self._lock:
            if server_id in self._servers:
                self._servers[server_id]["status"] = status

