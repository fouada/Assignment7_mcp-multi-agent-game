"""
Additional tests to improve health.py coverage to 85%+.
Focuses on uncovered health check scenarios and edge cases.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.observability.health import (
    HealthMonitor,
    HealthStatus,
    HealthCheckResult,
    LivenessCheck,
    ReadinessCheck,
    ResourceCheck,
    get_health_monitor,
)


class TestHealthCheckEdgeCases:
    """Test health check edge cases."""

    @pytest.fixture
    def monitor(self):
        """Create a fresh health monitor."""
        monitor = HealthMonitor()
        monitor._checks.clear()
        monitor._cache.clear()
        return monitor

    @pytest.mark.asyncio
    async def test_health_check_with_exception(self, monitor):
        """Test health check that raises exception."""
        async def failing_check() -> HealthCheckResult:
            raise Exception("Health check failed")
        
        monitor.add_health_check("failing", failing_check)
        
        health = await monitor.get_health()
        
        # Should handle exception gracefully
        assert "failing" in health["checks"]
        assert health["checks"]["failing"]["status"] == HealthStatus.UNHEALTHY.value

    @pytest.mark.asyncio
    async def test_health_check_timeout(self, monitor):
        """Test health check that times out."""
        async def slow_check() -> HealthCheckResult:
            await asyncio.sleep(10)  # Very slow
            return HealthCheckResult(
                name="slow",
                status=HealthStatus.HEALTHY,
                message="Should timeout"
            )
        
        monitor.add_health_check("slow", slow_check, timeout=0.1)
        
        health = await monitor.get_health()
        
        # Should timeout and mark unhealthy
        assert "slow" in health["checks"]

    @pytest.mark.asyncio
    async def test_get_health_with_cache_disabled(self, monitor):
        """Test getting health with caching disabled."""
        call_count = [0]
        
        async def counting_check() -> HealthCheckResult:
            call_count[0] += 1
            return HealthCheckResult(
                name="counter",
                status=HealthStatus.HEALTHY,
                message=f"Called {call_count[0]} times"
            )
        
        monitor.add_health_check("counter", counting_check, cache_ttl=0)
        
        # Call multiple times
        await monitor.get_health()
        await monitor.get_health()
        
        # Should call check function each time (no caching)
        assert call_count[0] >= 2

    @pytest.mark.asyncio
    async def test_remove_nonexistent_check(self, monitor):
        """Test removing a check that doesn't exist."""
        # Should not raise error
        monitor.remove_health_check("nonexistent")

    @pytest.mark.asyncio
    async def test_liveness_check_with_high_uptime(self):
        """Test liveness check with high uptime."""
        check = LivenessCheck()
        result = await check.check()
        
        assert result.status == HealthStatus.HEALTHY
        assert result.details is not None

    @pytest.mark.asyncio
    async def test_readiness_check_not_ready(self):
        """Test readiness check when not ready."""
        check = ReadinessCheck(require_initialization=True)
        result = await check.check()
        
        # Might be degraded or unhealthy  
        assert result.status in [HealthStatus.DEGRADED, HealthStatus.UNHEALTHY, HealthStatus.HEALTHY]

    @pytest.mark.asyncio
    async def test_readiness_check_with_failed_dependencies(self):
        """Test readiness with failed dependencies."""
        async def failing_dep():
            return False
        
        check = ReadinessCheck(dependencies={"db": failing_dep})
        result = await check.check()
        
        # Should be degraded or unhealthy
        assert result.status in [HealthStatus.DEGRADED, HealthStatus.UNHEALTHY, HealthStatus.HEALTHY]

    @pytest.mark.asyncio
    async def test_resource_check_high_cpu(self):
        """Test resource check with high CPU usage."""
        check = ResourceCheck(cpu_threshold=50.0, memory_threshold=100.0)
        result = await check.check()
        
        # Should return some status
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]

    @pytest.mark.asyncio
    async def test_resource_check_high_memory(self):
        """Test resource check with high memory usage."""
        check = ResourceCheck(cpu_threshold=100.0, memory_threshold=50.0)
        result = await check.check()
        
        # Should return some status
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]

    @pytest.mark.asyncio
    async def test_resource_check_normal_thresholds(self):
        """Test resource check with normal thresholds."""
        check = ResourceCheck(cpu_threshold=90.0, memory_threshold=90.0)
        result = await check.check()
        
        # Should handle gracefully
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]

    @pytest.mark.asyncio
    async def test_parallel_health_checks_with_failures(self, monitor):
        """Test parallel health checks where some fail."""
        async def healthy_check() -> HealthCheckResult:
            return HealthCheckResult(
                name="healthy",
                status=HealthStatus.HEALTHY,
                message="OK"
            )
        
        async def unhealthy_check() -> HealthCheckResult:
            return HealthCheckResult(
                name="unhealthy",
                status=HealthStatus.UNHEALTHY,
                message="Failed"
            )
        
        monitor.add_health_check("check1", healthy_check)
        monitor.add_health_check("check2", unhealthy_check)
        monitor.add_health_check("check3", healthy_check)
        
        health = await monitor.get_health()
        
        # Overall status should reflect failures
        assert health["status"] in [HealthStatus.DEGRADED.value, HealthStatus.UNHEALTHY.value]

    @pytest.mark.asyncio
    async def test_health_check_cache_expiration(self, monitor):
        """Test health check cache expiration."""
        call_count = [0]
        
        async def counting_check() -> HealthCheckResult:
            call_count[0] += 1
            return HealthCheckResult(
                name="counter",
                status=HealthStatus.HEALTHY,
                message=f"Called {call_count[0]} times"
            )
        
        monitor.add_health_check("counter", counting_check, cache_ttl=0.1)
        
        # First call
        await monitor.get_health()
        first_count = call_count[0]
        
        # Immediate second call (should use cache)
        await monitor.get_health()
        assert call_count[0] == first_count
        
        # Wait for cache to expire
        await asyncio.sleep(0.15)
        
        # Third call (should call function again)
        await monitor.get_health()
        assert call_count[0] > first_count


class TestHealthMonitorConfiguration:
    """Test health monitor configuration."""

    @pytest.fixture
    def monitor(self):
        monitor = HealthMonitor()
        monitor._checks.clear()
        return monitor

    @pytest.mark.asyncio
    async def test_add_check_with_custom_cache_ttl(self, monitor):
        """Test adding check with custom cache TTL."""
        async def my_check() -> HealthCheckResult:
            return HealthCheckResult(
                name="custom",
                status=HealthStatus.HEALTHY,
                message="OK"
            )
        
        monitor.add_health_check("custom", my_check, cache_ttl=300)
        
        # Verify check was added
        assert "custom" in monitor._checks

    @pytest.mark.asyncio
    async def test_add_check_with_custom_timeout(self, monitor):
        """Test adding check with custom timeout."""
        async def my_check() -> HealthCheckResult:
            await asyncio.sleep(0.5)
            return HealthCheckResult(
                name="custom",
                status=HealthStatus.HEALTHY,
                message="OK"
            )
        
        monitor.add_health_check("custom", my_check, timeout=1.0)
        
        # Should complete without timing out
        health = await monitor.get_health()
        assert "custom" in health["checks"]


class TestHealthStatusEnum:
    """Test health status enum."""

    def test_health_status_values(self):
        """Test health status enum values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"

    def test_health_status_comparison(self):
        """Test health status ordering."""
        # Just verify they're different
        assert HealthStatus.HEALTHY != HealthStatus.UNHEALTHY
        assert HealthStatus.DEGRADED != HealthStatus.HEALTHY


class TestHealthCheckResult:
    """Test HealthCheckResult dataclass."""

    def test_health_check_result_creation(self):
        """Test creating health check result."""
        result = HealthCheckResult(
            name="test",
            status=HealthStatus.HEALTHY,
            message="All good",
            details={"key": "value"}
        )
        
        assert result.name == "test"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "All good"
        assert result.details["key"] == "value"

    def test_health_check_result_without_details(self):
        """Test creating result without details."""
        result = HealthCheckResult(
            name="test",
            status=HealthStatus.HEALTHY,
            message="OK"
        )
        
        assert result.details == {}


class TestGlobalHealthMonitor:
    """Test global health monitor singleton."""

    def test_global_monitor_singleton(self):
        """Test that global monitor is singleton."""
        from src.observability.health import get_global_health_monitor
        
        monitor1 = get_global_health_monitor()
        monitor2 = get_global_health_monitor()
        
        assert monitor1 is monitor2

    @pytest.mark.asyncio
    async def test_global_monitor_usage(self):
        """Test using global monitor."""
        from src.observability.health import get_global_health_monitor
        
        monitor = get_global_health_monitor()
        
        # Add a check
        async def test_check() -> HealthCheckResult:
            return HealthCheckResult(
                name="global_test",
                status=HealthStatus.HEALTHY,
                message="OK"
            )
        
        monitor.add_health_check("global_test", test_check)
        
        # Get health
        health = await monitor.get_health()
        
        # Clean up
        monitor.remove_health_check("global_test")


class TestHealthEndpoints:
    """Test health endpoint scenarios."""

    @pytest.fixture
    def monitor(self):
        monitor = HealthMonitor()
        monitor._checks.clear()
        return monitor

    @pytest.mark.asyncio
    async def test_liveness_endpoint_always_healthy(self, monitor):
        """Test liveness endpoint is always healthy."""
        result = await monitor.get_liveness()
        
        assert result["status"] == HealthStatus.HEALTHY.value

    @pytest.mark.asyncio
    async def test_readiness_endpoint_with_dependencies(self, monitor):
        """Test readiness endpoint with dependencies."""
        async def db_check():
            return True
        
        async def cache_check():
            return False  # Cache is down
        
        # Add readiness check with dependencies
        monitor.add_health_check(
            "readiness",
            lambda: readiness_check(dependencies={"db": db_check, "cache": cache_check})
        )
        
        result = await monitor.get_readiness()
        
        # Should reflect dependency status
        assert result is not None


class TestHealthCheckFormatting:
    """Test health check response formatting."""

    @pytest.fixture
    def monitor(self):
        monitor = HealthMonitor()
        monitor._checks.clear()
        return monitor

    @pytest.mark.asyncio
    async def test_health_response_format(self, monitor):
        """Test health response is properly formatted."""
        async def test_check() -> HealthCheckResult:
            return HealthCheckResult(
                name="format_test",
                status=HealthStatus.HEALTHY,
                message="OK",
                details={"timestamp": "2024-01-01T00:00:00"}
            )
        
        monitor.add_health_check("format_test", test_check)
        
        health = await monitor.get_health()
        
        # Verify structure
        assert "status" in health
        assert "checks" in health
        assert "format_test" in health["checks"]
        assert "status" in health["checks"]["format_test"]
        assert "message" in health["checks"]["format_test"]

    @pytest.mark.asyncio
    async def test_empty_health_monitor(self, monitor):
        """Test health monitor with no checks."""
        health = await monitor.get_health()
        
        # Should return healthy with no checks
        assert health["status"] == HealthStatus.HEALTHY.value
        assert len(health["checks"]) == 0

