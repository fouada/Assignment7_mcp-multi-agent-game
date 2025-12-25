"""
MCP Client Implementation
=========================

Full Model Context Protocol client with:
- Multi-server connection management
- Session management
- Tool discovery and execution
- Resource management
- Message queue
"""

import asyncio
from typing import Any

from ..common.config import ServerConfig
from ..common.exceptions import (
    ConnectionError,
    ProtocolError,
)
from ..common.logger import PerformanceTracker, get_logger
from ..transport.http_transport import HTTPTransport
from ..transport.json_rpc import (
    JsonRpcResponse,
    MCPMethods,
    create_request,
    parse_message,
)
from .connection_manager import ConnectionManager
from .message_queue import MessageQueue
from .resource_manager import ResourceManager
from .session_manager import Session, SessionManager, SessionState
from .tool_registry import ToolExecutor, ToolRegistry

logger = get_logger(__name__)


class MCPClient:
    """
    Model Context Protocol Client.

    Manages connections to multiple MCP servers and provides
    unified access to tools, resources, and prompts.

    Features:
    - Multi-server support with star topology
    - Automatic tool/resource discovery
    - Connection health monitoring
    - Request routing
    - Retry logic with circuit breaker
    """

    def __init__(
        self,
        name: str = "mcp_client",
        version: str = "1.0.0",
    ):
        self.name = name
        self.version = version

        # Core managers
        self.sessions = SessionManager()
        self.tools = ToolRegistry()
        self.connections = ConnectionManager()
        self.resources = ResourceManager()
        self.message_queue = MessageQueue()

        # Transports for each server
        self._transports: dict[str, HTTPTransport] = {}

        # Tool executor
        self._tool_executor = ToolExecutor(self.tools, self)

        # Running state
        self._running = False

        logger.bind(client=name)

    async def connect(
        self,
        server_name: str,
        server_url: str,
        timeout: float = 30.0,
    ) -> Session:
        """
        Connect to an MCP server.

        Args:
            server_name: Name to identify the server
            server_url: URL of the server's MCP endpoint
            timeout: Connection timeout

        Returns:
            Established Session
        """
        logger.info(f"Connecting to {server_name} at {server_url}")

        # Create session
        session = await self.sessions.create_session(server_name, server_url)
        await self.sessions.update_session_state(session.id, SessionState.CONNECTING)

        # Add connection tracking
        await self.connections.add_connection(server_name, server_url)

        try:
            # Create transport
            transport = HTTPTransport()
            await transport.connect(server_url)
            self._transports[server_name] = transport

            session._transport = transport
            await self.sessions.update_session_state(session.id, SessionState.CONNECTED)

            # Initialize MCP session
            await self._initialize_session(session)

            # Mark connection as established
            await self.connections.mark_connected(server_name)

            logger.info(f"Connected to {server_name}")
            return session

        except Exception as e:
            logger.error(f"Failed to connect to {server_name}: {e}")
            await self.sessions.update_session_state(session.id, SessionState.ERROR)
            await self.connections.record_failure(server_name, str(e))
            raise ConnectionError(f"Failed to connect to {server_name}: {e}") from e

    async def connect_to_server(
        self,
        config: ServerConfig,
    ) -> Session:
        """Connect using ServerConfig."""
        return await self.connect(config.name, config.url)

    async def _initialize_session(self, session: Session) -> None:
        """Initialize MCP session with server."""
        await self.sessions.update_session_state(session.id, SessionState.INITIALIZING)

        transport = self._transports.get(session.server_name)
        if not transport:
            raise ConnectionError(f"No transport for {session.server_name}")

        # Send initialize request
        init_request = create_request(
            MCPMethods.INITIALIZE,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {"subscribe": True},
                    "prompts": {},
                },
                "clientInfo": {
                    "name": self.name,
                    "version": self.version,
                }
            }
        )

        response = await transport.request(init_request.to_dict())
        result = self._parse_response(response)

        # Store server info
        session.protocol_version = result.get("protocolVersion")
        session.capabilities = result.get("capabilities", {})
        server_info = result.get("serverInfo", {})
        session.server_version = server_info.get("version")

        # Discover tools
        await self._discover_tools(session)

        # Discover resources
        await self._discover_resources(session)

        # Send initialized notification
        initialized_notification = create_request(
            MCPMethods.INITIALIZED,
            None,
            notification=True,
        )
        await transport.send(initialized_notification.to_dict())

        # Mark session ready
        await self.sessions.update_session_state(session.id, SessionState.READY)

        logger.info(
            f"Session initialized: {session.server_name}",
            tools=len(session.tools),
            resources=len(session.resources),
        )

    async def _discover_tools(self, session: Session) -> None:
        """Discover tools from server."""
        transport = self._transports.get(session.server_name)

        request = create_request(MCPMethods.TOOLS_LIST)
        response = await transport.request(request.to_dict())
        result = self._parse_response(response)

        tools = result.get("tools", [])
        session.tools = tools

        # Register in tool registry
        await self.tools.register_tools_from_server(session.server_name, tools)

    async def _discover_resources(self, session: Session) -> None:
        """Discover resources from server."""
        transport = self._transports.get(session.server_name)

        request = create_request(MCPMethods.RESOURCES_LIST)
        response = await transport.request(request.to_dict())
        result = self._parse_response(response)

        resources = result.get("resources", [])
        session.resources = resources

        # Register in resource manager
        await self.resources.register_resources_from_server(
            session.server_name,
            resources
        )

    def _parse_response(self, response: dict) -> Any:
        """Parse JSON-RPC response and extract result."""
        parsed = parse_message(response)

        if isinstance(parsed, JsonRpcResponse):
            if parsed.is_error:
                raise ProtocolError(
                    f"RPC error: {parsed.error.message}",
                    details={"code": parsed.error.code}
                )
            return parsed.result

        # Raw response
        if "error" in response:
            error = response["error"]
            raise ProtocolError(f"RPC error: {error.get('message', 'Unknown error')}")

        return response.get("result", response)

    async def disconnect(self, server_name: str) -> None:
        """Disconnect from a server."""
        logger.info(f"Disconnecting from {server_name}")

        # Close transport
        if server_name in self._transports:
            await self._transports[server_name].disconnect()
            del self._transports[server_name]

        # Get session
        session = await self.sessions.get_session_by_server(server_name)
        if session:
            await self.sessions.remove_session(session.id)

        # Remove connection tracking
        await self.connections.remove_connection(server_name)

        # Unregister tools and resources
        await self.tools.unregister_server_tools(server_name)
        await self.resources.unregister_server_resources(server_name)

        logger.info(f"Disconnected from {server_name}")

    async def disconnect_all(self) -> None:
        """Disconnect from all servers."""
        server_names = list(self._transports.keys())
        for name in server_names:
            await self.disconnect(name)

    # ========================================================================
    # Tool Execution
    # ========================================================================

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> Any:
        """
        Call a tool on a server.

        Args:
            server_name: Name of the server
            tool_name: Name of the tool
            arguments: Tool arguments
            timeout: Request timeout

        Returns:
            Tool execution result
        """
        # Check circuit breaker
        await self.connections.check_circuit_breaker(server_name)

        transport = self._transports.get(server_name)
        if not transport:
            raise ConnectionError(f"Not connected to {server_name}")

        with PerformanceTracker(f"tool.{server_name}.{tool_name}", logger):
            request = create_request(
                MCPMethods.TOOLS_CALL,
                {
                    "name": tool_name,
                    "arguments": arguments or {},
                }
            )

            try:
                response = await transport.request(request.to_dict(), timeout=timeout)
                result = self._parse_response(response)

                # Record success
                await self.connections.record_success(server_name)

                return result

            except Exception as e:
                await self.connections.record_failure(server_name, str(e))
                raise

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """
        Execute a tool (auto-resolves server).

        The tool name can be namespaced (server.tool) or not.
        """
        return await self._tool_executor.execute(tool_name, arguments)

    # ========================================================================
    # Resource Access
    # ========================================================================

    async def read_resource(
        self,
        server_name: str,
        uri: str,
        use_cache: bool = True,
    ) -> Any:
        """
        Read a resource from a server.

        Args:
            server_name: Name of the server
            uri: Resource URI
            use_cache: Whether to use cached data

        Returns:
            Resource data
        """
        # Check cache first
        if use_cache:
            cached = await self.resources.get_cached(uri)
            if cached is not None:
                return cached

        transport = self._transports.get(server_name)
        if not transport:
            raise ConnectionError(f"Not connected to {server_name}")

        request = create_request(
            MCPMethods.RESOURCES_READ,
            {"uri": uri}
        )

        response = await transport.request(request.to_dict())
        result = self._parse_response(response)

        # Cache result
        contents = result.get("contents", [])
        if contents:
            data = contents[0].get("text", contents[0])
            await self.resources.set_cached(uri, data)
            return data

        return result

    async def subscribe_resource(
        self,
        server_name: str,
        uri: str,
        callback,
    ) -> bool:
        """Subscribe to resource updates."""
        transport = self._transports.get(server_name)
        if not transport:
            raise ConnectionError(f"Not connected to {server_name}")

        # Send subscribe request
        request = create_request(
            MCPMethods.RESOURCES_SUBSCRIBE,
            {"uri": uri}
        )

        await transport.request(request.to_dict())

        # Register local callback
        return await self.resources.subscribe(uri, callback)

    # ========================================================================
    # Protocol Message Handling
    # ========================================================================

    async def send_protocol_message(
        self,
        server_name: str,
        message: dict[str, Any],
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """
        Send a league protocol message.

        Args:
            server_name: Target server
            message: Protocol message
            timeout: Request timeout

        Returns:
            Response
        """
        transport = self._transports.get(server_name)
        if not transport:
            raise ConnectionError(f"Not connected to {server_name}")

        # Wrap in JSON-RPC
        request = create_request(
            "protocol/message",
            {"message": message}
        )

        response = await transport.request(request.to_dict(), timeout=timeout)
        return self._parse_response(response)

    # ========================================================================
    # Lifecycle
    # ========================================================================

    async def start(self) -> None:
        """Start the client."""
        if self._running:
            return

        self._running = True
        await self.connections.start()

        logger.info("MCP Client started")

    async def stop(self) -> None:
        """Stop the client."""
        if not self._running:
            return

        self._running = False

        # Disconnect all
        await self.disconnect_all()

        # Stop managers
        await self.connections.stop()
        await self.sessions.close_all()

        logger.info("MCP Client stopped")

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
        return False

    # ========================================================================
    # Utilities
    # ========================================================================

    def get_all_tools(self) -> list[dict[str, Any]]:
        """Get list of all available tools (sync wrapper)."""
        return asyncio.get_event_loop().run_until_complete(
            self.tools.list_tools()
        )

    async def get_health_report(self) -> dict[str, Any]:
        """Get health report for all connections."""
        sessions = await self.sessions.list_sessions()

        return {
            "client": {
                "name": self.name,
                "version": self.version,
                "running": self._running,
            },
            "sessions": [s.to_dict() for s in sessions],
            "connections": await self.connections.get_health_report(),
            "tools": {
                "count": self.tools.tool_count,
                "servers": self.tools.server_count,
            },
            "resources": await self.resources.get_stats(),
            "message_queue": await self.message_queue.get_stats(),
        }

    @property
    def is_connected(self) -> bool:
        """Check if connected to any server."""
        return len(self._transports) > 0

    @property
    def connected_servers(self) -> list[str]:
        """Get list of connected server names."""
        return list(self._transports.keys())

