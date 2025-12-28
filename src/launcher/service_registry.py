"""
Service Registry - MIT Level
=============================

Provides service discovery and registration for distributed components.

Features:
- Dynamic service registration/unregistration
- Service health monitoring
- Query services by type or ID
- Automatic cleanup of dead services
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..common.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ServiceInfo:
    """Information about a registered service."""

    service_id: str
    service_type: str
    endpoint: str
    registered_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = "active"  # active, inactive, unhealthy


class ServiceRegistry:
    """
    Service registry for component discovery.

    Singleton pattern ensures single registry across application.

    Usage:
        registry = get_service_registry()

        # Register service
        await registry.register_service(
            service_id="REF01",
            service_type="referee",
            endpoint="http://localhost:8001"
        )

        # Find services
        referees = await registry.find_services("referee")
        league = await registry.get_service("league_manager")
    """

    _instance: "ServiceRegistry | None" = None

    def __new__(cls) -> "ServiceRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._services: dict[str, ServiceInfo] = {}
        self._lock = asyncio.Lock()
        self._health_check_task: asyncio.Task | None = None
        self._initialized = True

        logger.info("ServiceRegistry initialized")

    async def start_health_monitoring(self, interval: int = 30):
        """Start background health monitoring."""
        if self._health_check_task:
            return

        async def health_monitor():
            while True:
                await asyncio.sleep(interval)
                await self._check_service_health()

        self._health_check_task = asyncio.create_task(health_monitor())
        logger.info(f"Health monitoring started (interval={interval}s)")

    async def stop_health_monitoring(self):
        """Stop background health monitoring."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
            logger.info("Health monitoring stopped")

    async def register_service(
        self,
        service_id: str,
        service_type: str,
        endpoint: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Register a service."""
        async with self._lock:
            service_info = ServiceInfo(
                service_id=service_id,
                service_type=service_type,
                endpoint=endpoint,
                metadata=metadata or {},
            )

            self._services[service_id] = service_info

            logger.info(
                f"Service registered: {service_id} ({service_type}) at {endpoint}"
            )

    async def unregister_service(self, service_id: str) -> bool:
        """Unregister a service."""
        async with self._lock:
            if service_id in self._services:
                service_info = self._services.pop(service_id)
                logger.info(
                    f"Service unregistered: {service_id} ({service_info.service_type})"
                )
                return True
            return False

    async def get_service(self, service_id: str) -> ServiceInfo | None:
        """Get service by ID."""
        return self._services.get(service_id)

    async def find_services(self, service_type: str) -> list[ServiceInfo]:
        """Find all services of a given type."""
        return [
            service
            for service in self._services.values()
            if service.service_type == service_type and service.status == "active"
        ]

    async def get_all_services(self) -> list[ServiceInfo]:
        """Get all registered services."""
        return list(self._services.values())

    async def update_heartbeat(self, service_id: str) -> None:
        """Update service heartbeat."""
        async with self._lock:
            if service_id in self._services:
                self._services[service_id].last_heartbeat = datetime.utcnow()
                self._services[service_id].status = "active"

    async def _check_service_health(self) -> None:
        """Check health of all registered services."""
        now = datetime.utcnow()
        timeout_seconds = 60

        async with self._lock:
            for service_id, service_info in self._services.items():
                time_since_heartbeat = (now - service_info.last_heartbeat).total_seconds()

                if time_since_heartbeat > timeout_seconds:
                    service_info.status = "unhealthy"
                    logger.warning(
                        f"Service {service_id} marked unhealthy "
                        f"(no heartbeat for {time_since_heartbeat:.0f}s)"
                    )


# Singleton accessor
_registry_instance: ServiceRegistry | None = None


def get_service_registry() -> ServiceRegistry:
    """Get global service registry instance."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ServiceRegistry()
    return _registry_instance
