"""
HTTP Transport Layer
====================

HTTP-based transport for MCP communication.
Supports both sync and async operations.
"""

import asyncio
import json
from collections.abc import Callable
from importlib.util import find_spec
from typing import Any

from .base import Transport, TransportConfig, TransportError
from .json_rpc import (
    JsonRpcError,
    JsonRpcRequest,
    JsonRpcResponse,
    create_error_response,
    parse_message,
)

try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

HAS_AIOHTTP = find_spec("aiohttp") is not None


class HTTPTransport(Transport):
    """
    HTTP transport implementation using httpx.

    Provides async HTTP communication for MCP protocol.
    """

    def __init__(self, config: TransportConfig | None = None):
        super().__init__(config)
        self._client: httpx.AsyncClient | None = None
        self._url: str | None = None
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def connect(self, url: str) -> None:
        """
        Connect to HTTP endpoint.

        Args:
            url: The URL to connect to (e.g., http://localhost:8000/mcp)
        """
        if not HAS_HTTPX:
            raise TransportError(
                "httpx is required for HTTP transport. Install with: pip install httpx"
            )

        self._url = url

        # Configure client
        timeout = httpx.Timeout(
            connect=10.0,
            read=self.config.timeout,
            write=self.config.timeout,
            pool=5.0,
        )

        limits = httpx.Limits(
            max_keepalive_connections=5,
            max_connections=10,
            keepalive_expiry=30.0,
        )

        self._client = httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            http2=False,  # Use HTTP/1.1 for compatibility
        )

        self._connected = True

    async def disconnect(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False

    async def send(self, data: dict[str, Any]) -> None:
        """
        Send data via HTTP POST.

        Note: For HTTP, send is typically combined with receive in request().
        This method is provided for interface compatibility.
        """
        if not self._connected or not self._client or not self._url:
            raise TransportError("Not connected")

        await self._client.post(
            self._url,
            json=data,
            headers=self._headers,
        )

    async def receive(self) -> dict[str, Any]:
        """
        Receive is not directly supported for HTTP.
        Use request() for request/response pattern.
        """
        raise TransportError(
            "HTTP transport does not support standalone receive. Use request() instead."
        )

    async def request(
        self,
        data: dict[str, Any],
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """
        Send a request and wait for response.

        Args:
            data: The JSON-RPC request data
            timeout: Optional timeout override

        Returns:
            The JSON-RPC response data
        """
        if not self._connected or not self._client or not self._url:
            raise TransportError("Not connected")

        try:
            # Use custom timeout if provided
            request_timeout = timeout or self.config.timeout

            response = await self._client.post(
                self._url,
                json=data,
                headers=self._headers,
                timeout=request_timeout,
            )

            # Check HTTP status
            response.raise_for_status()

            # Parse response
            result: dict[str, Any] = response.json()
            return result

        except httpx.TimeoutException as e:
            raise TransportError(f"Request timed out: {e}", cause=e) from e
        except httpx.HTTPStatusError as e:
            raise TransportError(f"HTTP error: {e.response.status_code}", cause=e) from e
        except httpx.RequestError as e:
            raise TransportError(f"Request error: {e}", cause=e) from e
        except json.JSONDecodeError as e:
            raise TransportError(f"Invalid JSON response: {e}", cause=e) from e

    async def batch_request(
        self,
        requests: list[dict[str, Any]],
        timeout: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Send a batch of requests.

        Args:
            requests: List of JSON-RPC request data
            timeout: Optional timeout override

        Returns:
            List of JSON-RPC response data
        """
        # Note: request() accepts list internally but type hints show dict
        result = await self.request(requests, timeout)  # type: ignore[arg-type]
        # The result will be a list when a list is passed
        if isinstance(result, list):
            return result
        return [result]


class HTTPServerTransport:
    """
    HTTP server transport for handling incoming MCP requests.

    Used by MCP servers to process incoming requests.
    """

    def __init__(self, host: str = "localhost", port: int = 8000):
        self.host = host
        self.port = port
        self._handlers: dict[str, Callable[..., Any]] = {}
        self._running = False

    def register_handler(self, method: str, handler: Callable[..., Any]) -> None:
        """Register a handler for a JSON-RPC method."""
        self._handlers[method] = handler

    async def handle_request(self, data: bytes) -> bytes:
        """
        Handle an incoming request.

        Args:
            data: Raw request data

        Returns:
            Raw response data
        """
        # Parse the message
        message = parse_message(data)

        if isinstance(message, JsonRpcError):
            # Parse error
            response = create_error_response(None, message)
            return json.dumps(response.to_dict()).encode()

        if isinstance(message, JsonRpcRequest):
            return await self._handle_single_request(message)

        # Handle batch - not implemented yet
        return json.dumps({"error": "Batch not supported"}).encode()

    async def _handle_single_request(self, request: JsonRpcRequest) -> bytes:
        """Handle a single JSON-RPC request."""
        # Find handler
        handler = self._handlers.get(request.method)

        if handler is None:
            error = JsonRpcError.method_not_found(request.method)
            response = create_error_response(request.id, error)
        else:
            try:
                # Call handler
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(request.params)
                else:
                    result = handler(request.params)

                response = JsonRpcResponse(id=request.id, result=result)

            except Exception as e:
                error = JsonRpcError.internal_error(str(e))
                response = create_error_response(request.id, error)

        # Don't send response for notifications
        if request.is_notification:
            return b""

        return json.dumps(response.to_dict()).encode()


class RetryableHTTPTransport(HTTPTransport):
    """
    HTTP transport with automatic retry logic.

    Implements exponential backoff with jitter.
    """

    def __init__(
        self,
        config: TransportConfig | None = None,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        jitter_factor: float = 0.1,
    ):
        super().__init__(config)
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter_factor = jitter_factor

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter."""
        import random

        delay: float = min(self.base_delay * (2**attempt), self.max_delay)
        jitter: float = delay * self.jitter_factor * random.random()
        return delay + jitter

    async def request(
        self,
        data: dict[str, Any],
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """
        Send request with automatic retry on failure.
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                return await super().request(data, timeout)

            except TransportError as e:
                last_error = e

                # Check if we should retry
                if attempt >= self.max_retries:
                    break

                # Calculate delay
                delay = self._calculate_delay(attempt)

                # Wait before retry
                await asyncio.sleep(delay)

        raise TransportError(
            f"Request failed after {self.max_retries + 1} attempts", cause=last_error
        )


class ConnectionPool:
    """
    Connection pool for managing multiple HTTP connections.

    Useful for connecting to multiple MCP servers.
    """

    def __init__(self, config: TransportConfig | None = None):
        self.config = config or TransportConfig()
        self._connections: dict[str, HTTPTransport] = {}
        self._lock = asyncio.Lock()

    async def get_connection(self, url: str) -> HTTPTransport:
        """
        Get or create a connection to the specified URL.

        Args:
            url: The server URL

        Returns:
            HTTPTransport connected to the URL
        """
        async with self._lock:
            if url not in self._connections:
                transport = HTTPTransport(self.config)
                await transport.connect(url)
                self._connections[url] = transport

            return self._connections[url]

    async def close_connection(self, url: str) -> None:
        """Close a specific connection."""
        async with self._lock:
            if url in self._connections:
                await self._connections[url].disconnect()
                del self._connections[url]

    async def close_all(self) -> None:
        """Close all connections."""
        async with self._lock:
            for transport in self._connections.values():
                await transport.disconnect()
            self._connections.clear()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_all()
        return False
