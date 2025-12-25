"""
Base Transport Interface
========================

Abstract base class for all transport implementations.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any


class TransportError(Exception):
    """Transport-level error."""

    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__(message)
        self.cause = cause


@dataclass
class TransportConfig:
    """Transport configuration."""

    timeout: float = 30.0
    max_retries: int = 3
    keepalive: bool = True
    compression: bool = False


class Transport(ABC):
    """Abstract base class for transport implementations."""

    def __init__(self, config: TransportConfig | None = None):
        self.config = config or TransportConfig()
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if transport is connected."""
        return self._connected

    @abstractmethod
    async def connect(self, url: str) -> None:
        """
        Establish connection to the remote endpoint.

        Args:
            url: The URL to connect to
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the connection."""
        pass

    @abstractmethod
    async def send(self, data: dict[str, Any]) -> None:
        """
        Send data to the remote endpoint.

        Args:
            data: The data to send (will be serialized)
        """
        pass

    @abstractmethod
    async def receive(self) -> dict[str, Any]:
        """
        Receive data from the remote endpoint.

        Returns:
            The received data (deserialized)
        """
        pass

    @abstractmethod
    async def request(
        self,
        data: dict[str, Any],
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """
        Send a request and wait for response.

        Args:
            data: The request data
            timeout: Optional timeout override

        Returns:
            The response data
        """
        pass

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
        return False


class StreamingTransport(Transport):
    """Transport that supports streaming responses."""

    @abstractmethod
    async def stream(
        self,
        data: dict[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Send a request and stream responses.

        Args:
            data: The request data

        Yields:
            Response data chunks
        """
        pass

