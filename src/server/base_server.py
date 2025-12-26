"""
Base Game Server
================

Base class for game-specific MCP servers (League Manager, Referee, Player).
"""

import asyncio
from datetime import datetime
from typing import Any

from ..common.exceptions import ProtocolError, ValidationError
from ..common.logger import get_logger
from ..common.protocol import (
    PROTOCOL_VERSION,
    MessageFactory,
    validate_message,
)
from ..middleware import (
    AuthenticationMiddleware,
    ErrorHandlerMiddleware,
    LoggingMiddleware,
    MetricsMiddleware,
    MiddlewarePipeline,
    RateLimitMiddleware,
    TracingMiddleware,
)
from ..observability import (
    Timer,
    get_health_monitor,
    get_metrics_collector,
    get_tracing_manager,
)
from .mcp_server import MCPServer

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
        enable_middleware: bool = True,
        enable_observability: bool = True,
        **kwargs,
    ):
        super().__init__(name, **kwargs)

        self.server_type = server_type
        self.league_id = league_id
        self.enable_middleware = enable_middleware
        self.enable_observability = enable_observability

        # Set sender format according to protocol spec
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

        # Initialize observability (metrics, tracing, health)
        if enable_observability:
            self._initialize_observability()

        # Initialize middleware pipeline
        self.middleware_pipeline: MiddlewarePipeline | None = None
        if enable_middleware:
            self._initialize_middleware()

        # Register common protocol handler
        self.register_handler("protocol/message", self._handle_protocol_message)

        # Register common tools
        self._register_common_tools()

    def _initialize_observability(self) -> None:
        """
        Initialize observability infrastructure (metrics, tracing, health).

        Sets up:
        1. Metrics collector - Prometheus-compatible metrics
        2. Tracing manager - OpenTelemetry distributed tracing
        3. Health monitor - Liveness/readiness health checks

        All systems are singletons and thread-safe.
        """
        logger.info(f"Initializing observability for {self.server_type}")

        # Get singletons
        self.metrics = get_metrics_collector()
        self.tracing = get_tracing_manager()
        self.health = get_health_monitor()

        # Initialize tracing with service name
        service_name = f"mcp_game_{self.server_type}"
        self.tracing.initialize(
            service_name=service_name,
            enabled=True,
            sample_rate=0.1,  # 10% sampling by default
        )

        # Add server-specific metrics
        self.metrics.set_gauge(
            "server_info",
            1.0,
            labels={
                "server_type": self.server_type,
                "server_name": self.name,
                "league_id": self.league_id,
            },
        )

        logger.info(
            f"Observability initialized: "
            f"metrics={self.metrics is not None}, "
            f"tracing={self.tracing.enabled}, "
            f"health={len(self.health.list_checks())} checks"
        )

    def _initialize_middleware(self) -> None:
        """
        Initialize middleware pipeline with production-grade middleware.

        Adds 6 essential middleware in priority order:
        1. Tracing (100) - Distributed tracing
        2. Logging (90) - Request/response logging
        3. Authentication (80) - Token validation (optional for some agents)
        4. Rate Limiting (70) - Token bucket rate limiting
        5. Metrics (50) - Performance metrics
        6. Error Handler (10) - Exception handling

        Note: Caching and Validation are available but disabled by default.
        """
        logger.info(f"Initializing middleware pipeline for {self.server_type}")

        # Create pipeline
        self.middleware_pipeline = MiddlewarePipeline(
            timeout_seconds=30.0,
            error_handling="continue",  # Continue on middleware errors
        )

        # Add middleware in priority order (high to low)

        # 1. Tracing - highest priority to capture full request lifecycle
        self.middleware_pipeline.add_middleware(
            TracingMiddleware(
                name="tracing",
                service_name=f"mcp_game_{self.server_type}",
            ),
            priority=100,
        )

        # 2. Logging - log all requests/responses
        self.middleware_pipeline.add_middleware(
            LoggingMiddleware(
                name="logging",
                log_requests=True,
                log_responses=True,
                log_errors=True,
            ),
            priority=90,
        )

        # 3. Authentication - validate tokens (optional for league_manager)
        # League manager doesn't require auth for registration
        auth_required = self.server_type != "league_manager"
        self.middleware_pipeline.add_middleware(
            AuthenticationMiddleware(
                name="authentication",
                required=auth_required,
                token_field="auth_token",
                cache_tokens=True,
            ),
            priority=80,
        )

        # 4. Rate Limiting - prevent abuse
        # Different limits per agent type
        rate_limits = {
            "league_manager": 200,  # Higher limit for league manager
            "referee": 150,  # Medium limit for referees
            "player": 100,  # Standard limit for players
        }
        requests_per_minute = rate_limits.get(self.server_type, 100)

        self.middleware_pipeline.add_middleware(
            RateLimitMiddleware(
                name="rate_limit",
                requests_per_minute=requests_per_minute,
                burst_size=10,
            ),
            priority=70,
        )

        # 5. Metrics - collect performance data
        self.middleware_pipeline.add_middleware(
            MetricsMiddleware(name="metrics"),
            priority=50,
        )

        # 6. Error Handler - convert exceptions to error responses (lowest priority)
        self.middleware_pipeline.add_middleware(
            ErrorHandlerMiddleware(
                name="error_handler",
                include_traceback=False,  # Don't expose tracebacks in production
                sanitize_errors=True,
            ),
            priority=10,
        )

        logger.info(
            f"Middleware pipeline initialized with "
            f"{len(self.middleware_pipeline.get_middleware_list())} middleware"
        )

    def _register_common_tools(self) -> None:
        """Register tools common to all game servers."""

        # Heartbeat tool
        @self.tool("heartbeat", "Check server health")
        async def heartbeat(params: dict) -> dict:
            uptime = 0.0
            if self._start_time:
                uptime = (datetime.now() - self._start_time).total_seconds()

            return self.message_factory.heartbeat_response(uptime)

        # Protocol info tool
        @self.tool("get_protocol_info", "Get protocol version information")
        async def get_protocol_info(params: dict) -> dict:
            return {
                "protocol": PROTOCOL_VERSION,
                "server_type": self.server_type,
                "server_name": self.name,
                "league_id": self.league_id,
            }

        # Observability tools (if enabled)
        if self.enable_observability:
            # Metrics endpoint - Prometheus format
            @self.tool("get_metrics", "Get Prometheus metrics")
            async def get_metrics(params: dict) -> dict:
                """
                Export metrics in Prometheus text format.

                Returns:
                    Metrics in Prometheus exposition format
                """
                metrics_text = self.metrics.export_prometheus()
                return {
                    "success": True,
                    "format": "prometheus",
                    "metrics": metrics_text,
                    "content_type": "text/plain; version=0.0.4",
                }

            # Full health check
            @self.tool("get_health", "Get full health report")
            async def get_health(params: dict) -> dict:
                """
                Get comprehensive health report with all checks.

                Returns:
                    Health report with status and check details
                """
                report = await self.health.get_health()
                return {
                    "success": True,
                    **report,
                }

            # Liveness probe (Kubernetes)
            @self.tool("get_health_live", "Liveness health check")
            async def get_health_live(params: dict) -> dict:
                """
                Liveness check for Kubernetes probes.

                Returns HEALTHY if process is alive.

                Returns:
                    Liveness status
                """
                liveness = await self.health.get_liveness()
                return {
                    "success": True,
                    **liveness,
                }

            # Readiness probe (Kubernetes)
            @self.tool("get_health_ready", "Readiness health check")
            async def get_health_ready(params: dict) -> dict:
                """
                Readiness check for Kubernetes probes.

                Returns HEALTHY if service can accept requests.

                Returns:
                    Readiness status
                """
                readiness = await self.health.get_readiness()
                return {
                    "success": True,
                    **readiness,
                }

    async def _handle_protocol_message(self, params: dict | None) -> dict[str, Any]:
        """
        Handle a league protocol message through middleware pipeline.

        This validates the message format and dispatches to the appropriate handler,
        optionally executing through the middleware pipeline for production-grade
        request processing (logging, auth, rate limiting, metrics, etc.).

        Includes observability:
        - Distributed tracing spans
        - Request metrics (count, duration)
        - Error tracking
        """
        if not params:
            raise ValidationError("Missing message params")

        message = params.get("message")
        if not message:
            raise ValidationError("Missing message field")

        # Extract message type for metrics/tracing
        msg_type = message.get("message_type", "unknown")

        # Start tracing span (if observability enabled)
        if self.enable_observability:
            tracing_context = self.tracing.span(
                f"protocol.{msg_type}",
                attributes={
                    "message_type": msg_type,
                    "sender": message.get("sender", "unknown"),
                    "server_type": self.server_type,
                },
            )
        else:
            tracing_context = None

        # Execute with tracing and metrics
        try:
            if tracing_context:
                async with tracing_context as span:  # type: ignore[attr-defined]
                    return await self._execute_protocol_message(message, span)
            else:
                return await self._execute_protocol_message(message, None)

        except Exception:
            # Record error metrics
            if self.enable_observability:
                self.metrics.increment(
                    "game_requests_total",
                    labels={
                        "type": msg_type,
                        "status": "error",
                        "server_type": self.server_type,
                    },
                )
            raise

    async def _execute_protocol_message(
        self, message: dict[str, Any], span: Any | None = None
    ) -> dict[str, Any]:
        """
        Execute protocol message handling with observability.

        Args:
            message: Protocol message
            span: Optional tracing span

        Returns:
            Response dictionary
        """
        msg_type = message.get("message_type", "unknown")

        # Record request metric
        if self.enable_observability:
            self.metrics.increment(
                "game_requests_total",
                labels={
                    "type": msg_type,
                    "server_type": self.server_type,
                },
            )

        # Time the request
        if self.enable_observability:
            timer = Timer(
                "game_request_duration_seconds",
                labels={"type": msg_type, "server_type": self.server_type},
            )
            timer.__enter__()
        else:
            timer = None

        try:
            # If middleware is disabled, use original direct flow
            if not self.enable_middleware or self.middleware_pipeline is None:
                # Validate protocol
                is_valid, error = validate_message(message)
                if not is_valid:
                    raise ProtocolError(error or "Invalid message")

                # Get message type
                msg_type = message.get("message_type")

                # Dispatch to specific handler
                handler_name = f"_handle_{msg_type.lower()}" if msg_type else "_handle_unknown"
                handler = getattr(self, handler_name, None)

                if handler is None:
                    raise ValidationError(f"Unsupported message type: {msg_type}")

                response = await handler(message)

                # Add span event if tracing
                if span:
                    span.add_event("Handler completed", {"msg_type": msg_type})

                return response

            # Execute through middleware pipeline
            async def protocol_handler(request: dict[str, Any]) -> dict[str, Any]:
                """
                Inner handler that validates and dispatches protocol messages.

                This is called by the middleware pipeline after all before hooks.
                """
                # Validate protocol
                is_valid, error = validate_message(request)
                if not is_valid:
                    raise ProtocolError(error or "Protocol error")

                # Get message type
                msg_type = request.get("message_type")

                # Dispatch to specific handler
                handler_name = f"_handle_{msg_type.lower()}" if msg_type else "_handle_unknown"
                handler = getattr(self, handler_name, None)

                if handler is None:
                    raise ValidationError(f"Unsupported message type: {msg_type}")

                # Add span event
                if span:
                    span.add_event("Calling handler", {"handler": handler_name})

                return await handler(request)

            # Execute through middleware pipeline
            # Flow: Tracing → Logging → Auth → Rate Limit → Metrics → Handler → Error Handler
            response = await self.middleware_pipeline.execute(
                request=message,
                handler=protocol_handler,
            )

            # Add span event
            if span:
                span.add_event("Middleware pipeline completed")

            return response

        finally:
            # Close timer
            if timer:
                timer.__exit__(None, None, None)

    async def send_protocol_message(
        self,
        target_url: str,
        message: dict[str, Any],
        timeout: float = 30.0,
    ) -> dict[str, Any]:
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
        self._servers: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def register(
        self,
        server_id: str,
        server_type: str,
        endpoint: str,
        metadata: dict | None = None,
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

    async def get(self, server_id: str) -> dict[str, Any] | None:
        """Get server info."""
        async with self._lock:
            return self._servers.get(server_id)

    async def get_by_type(self, server_type: str) -> list[dict[str, Any]]:
        """Get all servers of a type."""
        async with self._lock:
            return [s for s in self._servers.values() if s["type"] == server_type]

    async def get_all(self) -> list[dict[str, Any]]:
        """Get all registered servers."""
        async with self._lock:
            return list(self._servers.values())

    async def update_status(self, server_id: str, status: str) -> None:
        """Update server status."""
        async with self._lock:
            if server_id in self._servers:
                self._servers[server_id]["status"] = status
