"""
Connection Manager
==================

Manages connections to MCP servers with:
- Heartbeat monitoring
- Retry logic with exponential backoff
- Circuit breaker pattern
"""

import asyncio
import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from ..common.exceptions import (
    CircuitBreakerError,
)
from ..common.logger import get_logger

logger = get_logger(__name__)


class ConnectionState(Enum):
    """Connection state."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    UNHEALTHY = "unhealthy"
    CLOSED = "closed"


@dataclass
class ConnectionInfo:
    """Information about a connection."""

    server_name: str
    url: str
    state: ConnectionState = ConnectionState.DISCONNECTED

    # Health metrics
    last_heartbeat: datetime | None = None
    consecutive_failures: int = 0
    total_requests: int = 0
    total_errors: int = 0

    # Timing
    connected_at: datetime | None = None
    last_error: datetime | None = None
    last_error_message: str | None = None

    @property
    def is_healthy(self) -> bool:
        """Check if connection is healthy."""
        return self.state == ConnectionState.CONNECTED and self.consecutive_failures < 3

    @property
    def uptime(self) -> timedelta | None:
        """Get connection uptime."""
        if self.connected_at:
            return datetime.utcnow() - self.connected_at
        return None

    def record_success(self) -> None:
        """Record successful request."""
        self.consecutive_failures = 0
        self.total_requests += 1

    def record_failure(self, error_message: str = "") -> None:
        """Record failed request."""
        self.consecutive_failures += 1
        self.total_errors += 1
        self.last_error = datetime.utcnow()
        self.last_error_message = error_message


class CircuitBreaker:
    """
    Circuit breaker for connection protection.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Requests fail immediately, server is considered down
    - HALF_OPEN: Test mode, limited requests allowed
    """

    class State(Enum):
        CLOSED = "closed"
        OPEN = "open"
        HALF_OPEN = "half_open"

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        timeout: float = 30.0,
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout

        self._state = self.State.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: datetime | None = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> State:
        """Get current state."""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == self.State.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing fast)."""
        return self._state == self.State.OPEN

    async def can_proceed(self) -> bool:
        """
        Check if a request can proceed.

        Returns:
            True if request should be attempted
        """
        async with self._lock:
            if self._state == self.State.CLOSED:
                return True

            if self._state == self.State.OPEN:
                # Check if timeout has elapsed
                if self._last_failure_time:
                    elapsed = (datetime.utcnow() - self._last_failure_time).total_seconds()
                    if elapsed >= self.timeout:
                        # Transition to half-open
                        self._state = self.State.HALF_OPEN
                        self._success_count = 0
                        logger.info("Circuit breaker: OPEN -> HALF_OPEN")
                        return True
                return False

            # HALF_OPEN: allow limited requests
            return True

    async def record_success(self) -> None:
        """Record successful request."""
        async with self._lock:
            self._failure_count = 0

            if self._state == self.State.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._state = self.State.CLOSED
                    logger.info("Circuit breaker: HALF_OPEN -> CLOSED")

    async def record_failure(self) -> None:
        """Record failed request."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.utcnow()

            if self._state == self.State.HALF_OPEN:
                # Immediately re-open
                self._state = self.State.OPEN
                logger.warning("Circuit breaker: HALF_OPEN -> OPEN")
            elif self._failure_count >= self.failure_threshold:
                self._state = self.State.OPEN
                logger.warning(f"Circuit breaker: CLOSED -> OPEN (failures: {self._failure_count})")

    async def reset(self) -> None:
        """Reset the circuit breaker."""
        async with self._lock:
            self._state = self.State.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None


class RetryPolicy:
    """
    Retry policy with exponential backoff and jitter.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter_factor: float = 0.1,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter_factor = jitter_factor

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for retry attempt.

        Uses: delay = min(base * exp^attempt + jitter, max)
        """
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )

        # Add jitter
        jitter = delay * self.jitter_factor * random.random()

        return delay + jitter

    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with retry.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Last exception if all retries fail
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e

                if attempt >= self.max_retries:
                    break

                delay = self.calculate_delay(attempt)
                logger.warning(
                    f"Retry {attempt + 1}/{self.max_retries} after {delay:.2f}s: {e}"
                )
                await asyncio.sleep(delay)

        raise last_error


class ConnectionManager:
    """
    Manages connections to multiple MCP servers.

    Features:
    - Connection lifecycle management
    - Heartbeat monitoring
    - Automatic reconnection
    - Circuit breaker protection
    """

    def __init__(
        self,
        heartbeat_interval: float = 10.0,
        heartbeat_timeout: float = 5.0,
        retry_policy: RetryPolicy | None = None,
    ):
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.retry_policy = retry_policy or RetryPolicy()

        # Connections
        self._connections: dict[str, ConnectionInfo] = {}
        self._circuit_breakers: dict[str, CircuitBreaker] = {}

        # Heartbeat tasks
        self._heartbeat_tasks: dict[str, asyncio.Task] = {}

        # Lock
        self._lock = asyncio.Lock()

        # Running state
        self._running = False

    async def add_connection(
        self,
        server_name: str,
        url: str,
    ) -> ConnectionInfo:
        """
        Add a new connection.

        Args:
            server_name: Name of the server
            url: Server URL

        Returns:
            ConnectionInfo
        """
        async with self._lock:
            conn = ConnectionInfo(
                server_name=server_name,
                url=url,
            )
            self._connections[server_name] = conn
            self._circuit_breakers[server_name] = CircuitBreaker()

            logger.info(f"Added connection: {server_name} -> {url}")
            return conn

    async def remove_connection(self, server_name: str) -> None:
        """Remove a connection."""
        async with self._lock:
            # Stop heartbeat
            if server_name in self._heartbeat_tasks:
                self._heartbeat_tasks[server_name].cancel()
                del self._heartbeat_tasks[server_name]

            # Remove connection
            if server_name in self._connections:
                del self._connections[server_name]

            if server_name in self._circuit_breakers:
                del self._circuit_breakers[server_name]

            logger.info(f"Removed connection: {server_name}")

    async def get_connection(self, server_name: str) -> ConnectionInfo | None:
        """Get connection info."""
        async with self._lock:
            return self._connections.get(server_name)

    async def mark_connected(self, server_name: str) -> None:
        """Mark connection as connected."""
        async with self._lock:
            if server_name in self._connections:
                conn = self._connections[server_name]
                conn.state = ConnectionState.CONNECTED
                conn.connected_at = datetime.utcnow()
                conn.consecutive_failures = 0

    async def mark_disconnected(self, server_name: str) -> None:
        """Mark connection as disconnected."""
        async with self._lock:
            if server_name in self._connections:
                self._connections[server_name].state = ConnectionState.DISCONNECTED

    async def check_circuit_breaker(self, server_name: str) -> bool:
        """
        Check if requests can proceed for a server.

        Returns:
            True if requests should be attempted

        Raises:
            CircuitBreakerError if circuit is open
        """
        cb = self._circuit_breakers.get(server_name)
        if cb is None:
            return True

        if not await cb.can_proceed():
            raise CircuitBreakerError(server_name)

        return True

    async def record_success(self, server_name: str) -> None:
        """Record successful request."""
        async with self._lock:
            if server_name in self._connections:
                self._connections[server_name].record_success()

            if server_name in self._circuit_breakers:
                await self._circuit_breakers[server_name].record_success()

    async def record_failure(
        self,
        server_name: str,
        error_message: str = "",
    ) -> None:
        """Record failed request."""
        async with self._lock:
            if server_name in self._connections:
                self._connections[server_name].record_failure(error_message)

            if server_name in self._circuit_breakers:
                await self._circuit_breakers[server_name].record_failure()

    async def start_heartbeat(
        self,
        server_name: str,
        heartbeat_func: Callable,
    ) -> None:
        """
        Start heartbeat monitoring for a server.

        Args:
            server_name: Server name
            heartbeat_func: Async function to call for heartbeat
        """
        async def heartbeat_loop():
            while self._running:
                try:
                    await asyncio.wait_for(
                        heartbeat_func(),
                        timeout=self.heartbeat_timeout
                    )

                    async with self._lock:
                        if server_name in self._connections:
                            self._connections[server_name].last_heartbeat = datetime.utcnow()
                            self._connections[server_name].consecutive_failures = 0

                except TimeoutError:
                    logger.warning(f"Heartbeat timeout: {server_name}")
                    await self.record_failure(server_name, "Heartbeat timeout")

                except Exception as e:
                    logger.warning(f"Heartbeat failed: {server_name}: {e}")
                    await self.record_failure(server_name, str(e))

                await asyncio.sleep(self.heartbeat_interval)

        async with self._lock:
            if server_name in self._heartbeat_tasks:
                self._heartbeat_tasks[server_name].cancel()

            self._heartbeat_tasks[server_name] = asyncio.create_task(heartbeat_loop())

    async def stop_heartbeat(self, server_name: str) -> None:
        """Stop heartbeat monitoring for a server."""
        async with self._lock:
            if server_name in self._heartbeat_tasks:
                self._heartbeat_tasks[server_name].cancel()
                del self._heartbeat_tasks[server_name]

    async def start(self) -> None:
        """Start the connection manager."""
        self._running = True
        logger.info("Connection manager started")

    async def stop(self) -> None:
        """Stop the connection manager."""
        self._running = False

        # Cancel all heartbeat tasks
        for task in self._heartbeat_tasks.values():
            task.cancel()

        self._heartbeat_tasks.clear()
        logger.info("Connection manager stopped")

    @property
    def connection_count(self) -> int:
        """Get number of connections."""
        return len(self._connections)

    async def get_health_report(self) -> dict[str, Any]:
        """Get health report for all connections."""
        async with self._lock:
            return {
                "connections": {
                    name: {
                        "state": conn.state.value,
                        "is_healthy": conn.is_healthy,
                        "consecutive_failures": conn.consecutive_failures,
                        "total_requests": conn.total_requests,
                        "total_errors": conn.total_errors,
                        "last_heartbeat": conn.last_heartbeat.isoformat() if conn.last_heartbeat else None,
                        "circuit_breaker": self._circuit_breakers[name].state.value if name in self._circuit_breakers else None,
                    }
                    for name, conn in self._connections.items()
                }
            }

