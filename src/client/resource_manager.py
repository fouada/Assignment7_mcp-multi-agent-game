"""
Resource Manager
================

Manages resources from MCP servers with:
- Resource discovery
- Subscription mechanism
- Caching
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from ..common.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CachedResource:
    """
    Cached resource data.
    """

    uri: str
    server_name: str
    data: Any
    mime_type: str = "application/json"

    # Cache metadata
    cached_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    version: int = 0

    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def update(self, data: Any) -> None:
        """Update cached data."""
        self.data = data
        self.cached_at = datetime.utcnow()
        self.version += 1


@dataclass
class ResourceInfo:
    """
    Information about a resource.
    """

    uri: str
    name: str
    server_name: str
    description: str = ""
    mime_type: str = "application/json"

    # Subscription state
    subscribed: bool = False
    subscription_callbacks: list[Callable] = field(default_factory=list)


class ResourceManager:
    """
    Manages resources from multiple MCP servers.

    Features:
    - Resource discovery and listing
    - Subscription mechanism for updates
    - Caching with TTL
    """

    def __init__(
        self,
        cache_ttl: float = 60.0,  # Default cache TTL in seconds
    ):
        self.cache_ttl = cache_ttl

        # Resources indexed by URI
        self._resources: dict[str, ResourceInfo] = {}

        # Resources grouped by server
        self._by_server: dict[str, dict[str, ResourceInfo]] = {}

        # Cache
        self._cache: dict[str, CachedResource] = {}

        # Subscriptions
        self._subscriptions: dict[str, list[Callable]] = {}

        self._lock = asyncio.Lock()

    async def register_resource(
        self,
        server_name: str,
        resource_data: dict[str, Any],
    ) -> ResourceInfo:
        """
        Register a resource from a server.

        Args:
            server_name: Name of the server
            resource_data: Resource data from MCP resources/list

        Returns:
            ResourceInfo
        """
        async with self._lock:
            uri = resource_data.get("uri", "")
            name = resource_data.get("name", "")
            description = resource_data.get("description", "")
            mime_type = resource_data.get("mimeType", "application/json")

            resource_info = ResourceInfo(
                uri=uri,
                name=name,
                server_name=server_name,
                description=description,
                mime_type=mime_type,
            )

            self._resources[uri] = resource_info

            if server_name not in self._by_server:
                self._by_server[server_name] = {}
            self._by_server[server_name][uri] = resource_info

            logger.debug(f"Registered resource: {uri} from {server_name}")

            return resource_info

    async def register_resources_from_server(
        self,
        server_name: str,
        resources: list[dict[str, Any]],
    ) -> list[ResourceInfo]:
        """Register multiple resources from a server."""
        registered = []
        for res_data in resources:
            resource_info = await self.register_resource(server_name, res_data)
            registered.append(resource_info)

        logger.info(f"Registered {len(registered)} resources from {server_name}")
        return registered

    async def unregister_server_resources(self, server_name: str) -> int:
        """Remove all resources from a server."""
        async with self._lock:
            if server_name not in self._by_server:
                return 0

            count = 0
            for uri in list(self._by_server[server_name].keys()):
                if uri in self._resources:
                    del self._resources[uri]
                if uri in self._cache:
                    del self._cache[uri]
                count += 1

            del self._by_server[server_name]

            logger.info(f"Unregistered {count} resources from {server_name}")
            return count

    async def get_resource_info(self, uri: str) -> ResourceInfo | None:
        """Get resource info by URI."""
        async with self._lock:
            return self._resources.get(uri)

    async def list_resources(self) -> list[dict[str, Any]]:
        """List all resources."""
        async with self._lock:
            return [
                {
                    "uri": r.uri,
                    "name": r.name,
                    "description": r.description,
                    "mimeType": r.mime_type,
                    "server": r.server_name,
                }
                for r in self._resources.values()
            ]

    async def list_resources_by_server(
        self,
        server_name: str,
    ) -> list[dict[str, Any]]:
        """List resources from a specific server."""
        async with self._lock:
            if server_name not in self._by_server:
                return []
            return [
                {
                    "uri": r.uri,
                    "name": r.name,
                    "description": r.description,
                    "mimeType": r.mime_type,
                }
                for r in self._by_server[server_name].values()
            ]

    # ========================================================================
    # Caching
    # ========================================================================

    async def get_cached(self, uri: str) -> Any | None:
        """
        Get cached resource data.

        Returns None if not cached or expired.
        """
        async with self._lock:
            cached = self._cache.get(uri)
            if cached and not cached.is_expired:
                return cached.data
            return None

    async def set_cached(
        self,
        uri: str,
        data: Any,
        ttl: float | None = None,
    ) -> None:
        """
        Cache resource data.

        Args:
            uri: Resource URI
            data: Data to cache
            ttl: Cache TTL in seconds (uses default if not specified)
        """
        async with self._lock:
            resource = self._resources.get(uri)
            if not resource:
                logger.warning(f"Caching unknown resource: {uri}")
                server_name = "unknown"
            else:
                server_name = resource.server_name

            ttl = ttl or self.cache_ttl
            expires_at = datetime.utcnow() + timedelta(seconds=ttl)

            if uri in self._cache:
                self._cache[uri].update(data)
                self._cache[uri].expires_at = expires_at
            else:
                self._cache[uri] = CachedResource(
                    uri=uri,
                    server_name=server_name,
                    data=data,
                    expires_at=expires_at,
                )

    async def invalidate_cache(self, uri: str) -> bool:
        """Invalidate cached data for a resource."""
        async with self._lock:
            if uri in self._cache:
                del self._cache[uri]
                return True
            return False

    async def clear_cache(self) -> int:
        """Clear all cached data."""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    # ========================================================================
    # Subscriptions
    # ========================================================================

    async def subscribe(
        self,
        uri: str,
        callback: Callable[[str, Any], None],
    ) -> bool:
        """
        Subscribe to resource updates.

        Args:
            uri: Resource URI
            callback: Function to call on updates (uri, data)

        Returns:
            True if subscription was created
        """
        async with self._lock:
            resource = self._resources.get(uri)
            if not resource:
                logger.warning(f"Subscribing to unknown resource: {uri}")
                return False

            if uri not in self._subscriptions:
                self._subscriptions[uri] = []

            self._subscriptions[uri].append(callback)
            resource.subscribed = True

            logger.debug(f"Subscribed to resource: {uri}")
            return True

    async def unsubscribe(
        self,
        uri: str,
        callback: Callable | None = None,
    ) -> bool:
        """
        Unsubscribe from resource updates.

        Args:
            uri: Resource URI
            callback: Specific callback to remove (removes all if None)

        Returns:
            True if unsubscription was successful
        """
        async with self._lock:
            if uri not in self._subscriptions:
                return False

            if callback:
                if callback in self._subscriptions[uri]:
                    self._subscriptions[uri].remove(callback)
            else:
                self._subscriptions[uri].clear()

            if not self._subscriptions[uri]:
                del self._subscriptions[uri]
                if uri in self._resources:
                    self._resources[uri].subscribed = False

            logger.debug(f"Unsubscribed from resource: {uri}")
            return True

    async def notify_update(self, uri: str, data: Any) -> int:
        """
        Notify subscribers of resource update.

        Args:
            uri: Resource URI
            data: New data

        Returns:
            Number of callbacks notified
        """
        # Update cache
        await self.set_cached(uri, data)

        # Get callbacks
        async with self._lock:
            callbacks = list(self._subscriptions.get(uri, []))

        # Notify subscribers
        count = 0
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(uri, data)
                else:
                    callback(uri, data)
                count += 1
            except Exception as e:
                logger.error(f"Subscription callback error for {uri}: {e}")

        return count

    # ========================================================================
    # Statistics
    # ========================================================================

    @property
    def resource_count(self) -> int:
        """Get total resource count."""
        return len(self._resources)

    @property
    def cache_count(self) -> int:
        """Get cached resource count."""
        return len(self._cache)

    @property
    def subscription_count(self) -> int:
        """Get total subscription count."""
        return sum(len(cbs) for cbs in self._subscriptions.values())

    async def get_stats(self) -> dict[str, Any]:
        """Get resource manager statistics."""
        async with self._lock:
            return {
                "total_resources": len(self._resources),
                "by_server": {name: len(resources) for name, resources in self._by_server.items()},
                "cache": {
                    "entries": len(self._cache),
                    "expired": sum(1 for c in self._cache.values() if c.is_expired),
                },
                "subscriptions": {
                    "total": sum(len(cbs) for cbs in self._subscriptions.values()),
                    "resources": len(self._subscriptions),
                },
            }
