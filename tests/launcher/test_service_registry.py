"""
Test Service Registry
======================

Unit and integration tests for ServiceRegistry.

Test Coverage:
- Service registration/unregistration
- Service discovery by type/ID
- Health monitoring
- Heartbeat updates
- Edge cases (duplicate registration, invalid IDs, etc.)
"""

import asyncio
from datetime import datetime, timedelta

import pytest

from src.launcher.service_registry import ServiceInfo, ServiceRegistry


@pytest.fixture
def registry():
    """Create a fresh registry instance."""
    # Reset singleton
    ServiceRegistry._instance = None
    reg = ServiceRegistry()
    return reg


@pytest.fixture
async def registry_with_services(registry):
    """Create registry with sample services."""
    await registry.register_service(
        service_id="league_manager",
        service_type="league_manager",
        endpoint="http://localhost:8000",
        metadata={"league_id": "test_league"}
    )
    await registry.register_service(
        service_id="REF01",
        service_type="referee",
        endpoint="http://localhost:8001",
        metadata={"league_id": "test_league"}
    )
    await registry.register_service(
        service_id="REF02",
        service_type="referee",
        endpoint="http://localhost:8002",
        metadata={"league_id": "test_league"}
    )
    await registry.register_service(
        service_id="Player_1",
        service_type="player",
        endpoint="http://localhost:8101",
        metadata={"strategy": "random"}
    )
    return registry


class TestServiceRegistry:
    """Test ServiceRegistry class."""

    def test_singleton_pattern(self):
        """Test that ServiceRegistry is a singleton."""
        reg1 = ServiceRegistry()
        reg2 = ServiceRegistry()

        assert reg1 is reg2
        assert id(reg1) == id(reg2)

    @pytest.mark.asyncio
    async def test_register_service(self, registry):
        """Test registering a service."""
        service_id = "test_service"
        service_type = "test_type"
        endpoint = "http://localhost:9000"
        metadata = {"key": "value"}

        await registry.register_service(
            service_id=service_id,
            service_type=service_type,
            endpoint=endpoint,
            metadata=metadata
        )

        # Verify service is registered
        service = await registry.get_service(service_id)
        assert service is not None
        assert service.service_id == service_id
        assert service.service_type == service_type
        assert service.endpoint == endpoint
        assert service.metadata == metadata
        assert service.status == "active"

    @pytest.mark.asyncio
    async def test_unregister_service(self, registry_with_services):
        """Test unregistering a service."""
        # Unregister existing service
        result = await registry_with_services.unregister_service("REF01")
        assert result is True

        # Verify service is gone
        service = await registry_with_services.get_service("REF01")
        assert service is None

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_service(self, registry):
        """Test unregistering a service that doesn't exist."""
        result = await registry.unregister_service("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_service(self, registry_with_services):
        """Test getting a service by ID."""
        service = await registry_with_services.get_service("league_manager")

        assert service is not None
        assert service.service_id == "league_manager"
        assert service.service_type == "league_manager"
        assert service.endpoint == "http://localhost:8000"

    @pytest.mark.asyncio
    async def test_get_nonexistent_service(self, registry):
        """Test getting a service that doesn't exist."""
        service = await registry.get_service("nonexistent")
        assert service is None

    @pytest.mark.asyncio
    async def test_find_services_by_type(self, registry_with_services):
        """Test finding all services of a given type."""
        # Find all referees
        referees = await registry_with_services.find_services("referee")

        assert len(referees) == 2
        assert all(ref.service_type == "referee" for ref in referees)
        assert {ref.service_id for ref in referees} == {"REF01", "REF02"}

    @pytest.mark.asyncio
    async def test_find_services_no_matches(self, registry_with_services):
        """Test finding services with no matches."""
        services = await registry_with_services.find_services("nonexistent_type")
        assert len(services) == 0

    @pytest.mark.asyncio
    async def test_get_all_services(self, registry_with_services):
        """Test getting all registered services."""
        all_services = await registry_with_services.get_all_services()

        assert len(all_services) == 4
        service_ids = {svc.service_id for svc in all_services}
        assert service_ids == {"league_manager", "REF01", "REF02", "Player_1"}

    @pytest.mark.asyncio
    async def test_update_heartbeat(self, registry_with_services):
        """Test updating service heartbeat."""
        # Get initial heartbeat
        service_before = await registry_with_services.get_service("REF01")
        initial_heartbeat = service_before.last_heartbeat

        # Wait a bit
        await asyncio.sleep(0.1)

        # Update heartbeat
        await registry_with_services.update_heartbeat("REF01")

        # Get updated service
        service_after = await registry_with_services.get_service("REF01")

        # Verify heartbeat was updated
        assert service_after.last_heartbeat > initial_heartbeat
        assert service_after.status == "active"

    @pytest.mark.asyncio
    async def test_health_monitoring_marks_unhealthy(self, registry):
        """Test health monitoring marks services as unhealthy."""
        # Register a service
        await registry.register_service(
            service_id="test_service",
            service_type="test",
            endpoint="http://localhost:9000"
        )

        # Manually set old heartbeat (simulate no heartbeat for 2 minutes)
        service = await registry.get_service("test_service")
        service.last_heartbeat = datetime.utcnow() - timedelta(minutes=2)

        # Run health check
        await registry._check_service_health()

        # Verify service marked unhealthy
        service_after = await registry.get_service("test_service")
        assert service_after.status == "unhealthy"

    @pytest.mark.asyncio
    async def test_start_stop_health_monitoring(self, registry):
        """Test starting and stopping health monitoring."""
        # Start monitoring with short interval
        await registry.start_health_monitoring(interval=1)

        assert registry._health_check_task is not None
        assert not registry._health_check_task.done()

        # Stop monitoring
        await registry.stop_health_monitoring()

        assert registry._health_check_task is None

    @pytest.mark.asyncio
    async def test_health_monitoring_already_running(self, registry):
        """Test starting health monitoring when already running."""
        # Start monitoring
        await registry.start_health_monitoring(interval=1)
        first_task = registry._health_check_task

        # Try to start again
        await registry.start_health_monitoring(interval=1)
        second_task = registry._health_check_task

        # Should be the same task
        assert first_task is second_task

        # Cleanup
        await registry.stop_health_monitoring()


class TestServiceRegistryEdgeCases:
    """Test edge cases for ServiceRegistry."""

    @pytest.mark.asyncio
    async def test_register_duplicate_service_id(self, registry):
        """Test registering a service with duplicate ID."""
        service_id = "duplicate_id"

        # Register first time
        await registry.register_service(
            service_id=service_id,
            service_type="type1",
            endpoint="http://localhost:9000"
        )

        # Register again with same ID
        await registry.register_service(
            service_id=service_id,
            service_type="type2",
            endpoint="http://localhost:9001"
        )

        # Latest registration should overwrite
        service = await registry.get_service(service_id)
        assert service.service_type == "type2"
        assert service.endpoint == "http://localhost:9001"

    @pytest.mark.asyncio
    async def test_register_empty_service_id(self, registry):
        """Test registering a service with empty ID."""
        await registry.register_service(
            service_id="",
            service_type="test",
            endpoint="http://localhost:9000"
        )

        service = await registry.get_service("")
        assert service is not None
        assert service.service_id == ""

    @pytest.mark.asyncio
    async def test_register_with_none_metadata(self, registry):
        """Test registering a service with None metadata."""
        await registry.register_service(
            service_id="test",
            service_type="test",
            endpoint="http://localhost:9000",
            metadata=None
        )

        service = await registry.get_service("test")
        assert service.metadata == {}

    @pytest.mark.asyncio
    async def test_update_heartbeat_nonexistent(self, registry):
        """Test updating heartbeat for nonexistent service."""
        # Should not raise error
        await registry.update_heartbeat("nonexistent")

    @pytest.mark.asyncio
    async def test_find_services_filters_unhealthy(self, registry):
        """Test that find_services only returns active services."""
        # Register services
        await registry.register_service(
            service_id="healthy",
            service_type="test",
            endpoint="http://localhost:9000"
        )
        await registry.register_service(
            service_id="unhealthy",
            service_type="test",
            endpoint="http://localhost:9001"
        )

        # Mark one as unhealthy
        service = await registry.get_service("unhealthy")
        service.status = "unhealthy"

        # Find services should only return active ones
        services = await registry.find_services("test")
        assert len(services) == 1
        assert services[0].service_id == "healthy"

    @pytest.mark.asyncio
    async def test_concurrent_registration(self, registry):
        """Test concurrent service registration."""
        async def register_service(i):
            await registry.register_service(
                service_id=f"service_{i}",
                service_type="test",
                endpoint=f"http://localhost:{9000 + i}"
            )

        # Register 10 services concurrently
        await asyncio.gather(*[register_service(i) for i in range(10)])

        # Verify all services registered
        all_services = await registry.get_all_services()
        assert len(all_services) == 10

    @pytest.mark.asyncio
    async def test_concurrent_unregistration(self, registry):
        """Test concurrent service unregistration."""
        # Register services
        for i in range(10):
            await registry.register_service(
                service_id=f"service_{i}",
                service_type="test",
                endpoint=f"http://localhost:{9000 + i}"
            )

        # Unregister concurrently
        results = await asyncio.gather(*[
            registry.unregister_service(f"service_{i}")
            for i in range(10)
        ])

        # All should succeed
        assert all(results)

        # Verify all services gone
        all_services = await registry.get_all_services()
        assert len(all_services) == 0


class TestServiceInfo:
    """Test ServiceInfo dataclass."""

    def test_service_info_creation(self):
        """Test creating ServiceInfo."""
        service = ServiceInfo(
            service_id="test",
            service_type="test_type",
            endpoint="http://localhost:9000"
        )

        assert service.service_id == "test"
        assert service.service_type == "test_type"
        assert service.endpoint == "http://localhost:9000"
        assert service.status == "active"
        assert isinstance(service.registered_at, datetime)
        assert isinstance(service.last_heartbeat, datetime)

    def test_service_info_with_metadata(self):
        """Test ServiceInfo with metadata."""
        metadata = {"key1": "value1", "key2": "value2"}
        service = ServiceInfo(
            service_id="test",
            service_type="test_type",
            endpoint="http://localhost:9000",
            metadata=metadata
        )

        assert service.metadata == metadata
        assert service.metadata["key1"] == "value1"
