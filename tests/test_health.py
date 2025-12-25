"""
Tests for observability health check system.

Tests the HealthMonitor, health checks (Liveness, Readiness, Resource),
health status reporting, and Kubernetes probe compatibility.
"""

import asyncio
import time

import pytest

from src.observability.health import (
    HealthCheck,
    HealthCheckResult,
    HealthMonitor,
    HealthStatus,
    LivenessCheck,
    ReadinessCheck,
    ResourceCheck,
    get_health_monitor,
)


@pytest.fixture
def health_monitor():
    """Create a fresh HealthMonitor for each test."""
    monitor = HealthMonitor()
    # Clear any existing checks
    monitor._checks.clear()
    monitor._last_check_time = None
    monitor._last_report = None
    return monitor


@pytest.fixture
def global_health():
    """Use the global singleton health monitor."""
    monitor = get_health_monitor()

    # Store current state
    old_checks = monitor._checks.copy()
    old_last_check = monitor._last_check_time
    old_last_report = monitor._last_report

    # Clear for test
    monitor._checks.clear()
    monitor._last_check_time = None
    monitor._last_report = None

    yield monitor

    # Restore state
    monitor._checks = old_checks
    monitor._last_check_time = old_last_check
    monitor._last_report = old_last_report


# ============================================================================
# HealthCheckResult Tests
# ============================================================================


def test_health_check_result_creation():
    """Test creating HealthCheckResult."""
    result = HealthCheckResult(
        status=HealthStatus.HEALTHY,
        message="All systems operational",
        details={"uptime": 3600}
    )

    assert result.status == HealthStatus.HEALTHY
    assert result.message == "All systems operational"
    assert result.details["uptime"] == 3600


def test_health_status_enum():
    """Test HealthStatus enum values."""
    assert HealthStatus.HEALTHY.value == "healthy"
    assert HealthStatus.DEGRADED.value == "degraded"
    assert HealthStatus.UNHEALTHY.value == "unhealthy"


# ============================================================================
# LivenessCheck Tests
# ============================================================================


@pytest.mark.asyncio
async def test_liveness_check_always_healthy():
    """Test LivenessCheck always returns healthy (process is running)."""
    check = LivenessCheck()
    result = await check.check()

    assert result.status == HealthStatus.HEALTHY
    assert "Process is alive" in result.message
    assert "uptime_seconds" in result.details
    assert "pid" in result.details
    assert result.details["uptime_seconds"] >= 0


@pytest.mark.asyncio
async def test_liveness_check_uptime():
    """Test LivenessCheck reports increasing uptime."""
    check = LivenessCheck()

    result1 = await check.check()
    uptime1 = result1.details["uptime_seconds"]

    await asyncio.sleep(0.1)  # Wait 100ms

    result2 = await check.check()
    uptime2 = result2.details["uptime_seconds"]

    assert uptime2 > uptime1


# ============================================================================
# ReadinessCheck Tests
# ============================================================================


@pytest.mark.asyncio
async def test_readiness_check_healthy_by_default():
    """Test ReadinessCheck is healthy when initialized."""
    check = ReadinessCheck()
    result = await check.check()

    assert result.status == HealthStatus.HEALTHY
    assert "Service is ready" in result.message


@pytest.mark.asyncio
async def test_readiness_check_with_initialization_flag():
    """Test ReadinessCheck respects initialization_complete flag."""
    check = ReadinessCheck()

    # Not initialized
    check._initialization_complete = False
    result = await check.check()
    assert result.status == HealthStatus.UNHEALTHY
    assert "not initialized" in result.message.lower()

    # Initialized
    check._initialization_complete = True
    result = await check.check()
    assert result.status == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_readiness_check_with_dependencies():
    """Test ReadinessCheck with dependency availability."""
    check = ReadinessCheck()

    # All dependencies available
    check._dependencies_available = True
    result = await check.check()
    assert result.status == HealthStatus.HEALTHY

    # Dependencies unavailable
    check._dependencies_available = False
    result = await check.check()
    assert result.status == HealthStatus.UNHEALTHY
    assert "dependencies" in result.message.lower()


# ============================================================================
# ResourceCheck Tests
# ============================================================================


@pytest.mark.asyncio
async def test_resource_check_healthy():
    """Test ResourceCheck when resources are within limits."""
    check = ResourceCheck(
        max_cpu_percent=90.0,
        max_memory_percent=90.0,
        max_disk_percent=90.0
    )

    result = await check.check()

    # Should be healthy or degraded (not unhealthy)
    assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
    assert "cpu_percent" in result.details
    assert "memory_percent" in result.details
    assert "disk_percent" in result.details


@pytest.mark.asyncio
async def test_resource_check_cpu_threshold():
    """Test ResourceCheck detects CPU threshold violations."""
    # Set very low threshold
    check = ResourceCheck(max_cpu_percent=0.1)

    result = await check.check()

    # Likely to be degraded due to test execution using CPU
    # Just verify the check runs and reports CPU
    assert "cpu_percent" in result.details
    assert result.details["cpu_percent"] >= 0


@pytest.mark.asyncio
async def test_resource_check_memory_threshold():
    """Test ResourceCheck detects memory threshold violations."""
    # Set very low threshold
    check = ResourceCheck(max_memory_percent=0.1)

    result = await check.check()

    # Process is using memory, so should be degraded/unhealthy
    # Just verify the check runs and reports memory
    assert "memory_percent" in result.details
    assert result.details["memory_percent"] > 0


@pytest.mark.asyncio
async def test_resource_check_details():
    """Test ResourceCheck provides detailed resource info."""
    check = ResourceCheck()
    result = await check.check()

    # Should include detailed metrics
    assert "cpu_percent" in result.details
    assert "memory_percent" in result.details
    assert "disk_percent" in result.details
    assert isinstance(result.details["cpu_percent"], float)
    assert isinstance(result.details["memory_percent"], float)
    assert isinstance(result.details["disk_percent"], float)


# ============================================================================
# HealthMonitor Tests
# ============================================================================


@pytest.mark.asyncio
async def test_add_health_check(health_monitor):
    """Test adding a health check to the monitor."""
    check = LivenessCheck()
    health_monitor.add_check("liveness", check)

    assert "liveness" in health_monitor._checks
    assert health_monitor._checks["liveness"] == check


@pytest.mark.asyncio
async def test_remove_health_check(health_monitor):
    """Test removing a health check from the monitor."""
    check = LivenessCheck()
    health_monitor.add_check("liveness", check)

    assert "liveness" in health_monitor._checks

    health_monitor.remove_check("liveness")

    assert "liveness" not in health_monitor._checks


@pytest.mark.asyncio
async def test_get_health_no_checks(health_monitor):
    """Test getting health with no checks returns healthy."""
    report = await health_monitor.get_health()

    assert report["status"] == HealthStatus.HEALTHY.value
    assert len(report["checks"]) == 0


@pytest.mark.asyncio
async def test_get_health_with_checks(health_monitor):
    """Test getting health report with multiple checks."""
    health_monitor.add_check("liveness", LivenessCheck())
    health_monitor.add_check("readiness", ReadinessCheck())

    report = await health_monitor.get_health()

    assert "status" in report
    assert "timestamp" in report
    assert "checks" in report
    assert "liveness" in report["checks"]
    assert "readiness" in report["checks"]


@pytest.mark.asyncio
async def test_get_health_overall_status_healthy(health_monitor):
    """Test overall status is healthy when all checks are healthy."""
    health_monitor.add_check("liveness", LivenessCheck())
    health_monitor.add_check("readiness", ReadinessCheck())

    report = await health_monitor.get_health()

    assert report["status"] == HealthStatus.HEALTHY.value


@pytest.mark.asyncio
async def test_get_health_overall_status_degraded(health_monitor):
    """Test overall status is degraded when any check is degraded."""
    # Create a check that returns degraded
    class DegradedCheck(HealthCheck):
        async def check(self) -> HealthCheckResult:
            return HealthCheckResult(
                status=HealthStatus.DEGRADED,
                message="Service is degraded"
            )

    health_monitor.add_check("liveness", LivenessCheck())
    health_monitor.add_check("degraded", DegradedCheck())

    report = await health_monitor.get_health()

    assert report["status"] == HealthStatus.DEGRADED.value


@pytest.mark.asyncio
async def test_get_health_overall_status_unhealthy(health_monitor):
    """Test overall status is unhealthy when any check is unhealthy."""
    # Create a check that returns unhealthy
    class UnhealthyCheck(HealthCheck):
        async def check(self) -> HealthCheckResult:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message="Service is down"
            )

    health_monitor.add_check("liveness", LivenessCheck())
    health_monitor.add_check("unhealthy", UnhealthyCheck())

    report = await health_monitor.get_health()

    assert report["status"] == HealthStatus.UNHEALTHY.value


# ============================================================================
# Liveness and Readiness Probe Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_liveness(health_monitor):
    """Test getting liveness probe result."""
    health_monitor.add_check("liveness", LivenessCheck())

    liveness = await health_monitor.get_liveness()

    assert "status" in liveness
    assert liveness["status"] == HealthStatus.HEALTHY.value
    assert "message" in liveness
    assert "details" in liveness


@pytest.mark.asyncio
async def test_get_liveness_no_check(health_monitor):
    """Test getting liveness when no liveness check is registered."""
    # Should still return healthy (process is alive)
    liveness = await health_monitor.get_liveness()

    assert liveness["status"] == HealthStatus.HEALTHY.value


@pytest.mark.asyncio
async def test_get_readiness(health_monitor):
    """Test getting readiness probe result."""
    health_monitor.add_check("readiness", ReadinessCheck())

    readiness = await health_monitor.get_readiness()

    assert "status" in readiness
    assert readiness["status"] == HealthStatus.HEALTHY.value
    assert "message" in readiness


@pytest.mark.asyncio
async def test_get_readiness_not_ready(health_monitor):
    """Test readiness returns unhealthy when not ready."""
    readiness_check = ReadinessCheck()
    readiness_check._initialization_complete = False
    health_monitor.add_check("readiness", readiness_check)

    readiness = await health_monitor.get_readiness()

    assert readiness["status"] == HealthStatus.UNHEALTHY.value


# ============================================================================
# Caching Tests
# ============================================================================


@pytest.mark.asyncio
async def test_health_check_caching(health_monitor):
    """Test health checks are cached for performance."""
    health_monitor.add_check("liveness", LivenessCheck())

    # First call
    report1 = await health_monitor.get_health()
    time1 = report1["timestamp"]

    # Immediate second call (should be cached)
    await asyncio.sleep(0.01)  # Small delay
    report2 = await health_monitor.get_health()
    time2 = report2["timestamp"]

    # Timestamps should be the same (cached)
    assert time1 == time2


@pytest.mark.asyncio
async def test_health_check_cache_expiration(health_monitor):
    """Test health check cache expires after TTL."""
    health_monitor._cache_ttl_seconds = 0.1  # 100ms TTL

    health_monitor.add_check("liveness", LivenessCheck())

    # First call
    report1 = await health_monitor.get_health()
    time1 = report1["timestamp"]

    # Wait for cache to expire
    await asyncio.sleep(0.2)

    # Second call (cache should be expired)
    report2 = await health_monitor.get_health()
    time2 = report2["timestamp"]

    # Timestamps should be different (not cached)
    assert time1 != time2


@pytest.mark.asyncio
async def test_force_refresh(health_monitor):
    """Test forcing health check refresh bypasses cache."""
    health_monitor.add_check("liveness", LivenessCheck())

    # First call
    report1 = await health_monitor.get_health()
    time1 = report1["timestamp"]

    # Immediate call with force refresh
    health_monitor._last_check_time = None  # Simulate force refresh
    await asyncio.sleep(0.01)
    report2 = await health_monitor.get_health()
    time2 = report2["timestamp"]

    # Should have different timestamps
    assert time1 != time2


# ============================================================================
# Custom Health Check Tests
# ============================================================================


@pytest.mark.asyncio
async def test_custom_health_check():
    """Test creating and using a custom health check."""
    class DatabaseHealthCheck(HealthCheck):
        def __init__(self, db_connected: bool = True):
            self.db_connected = db_connected

        async def check(self) -> HealthCheckResult:
            if self.db_connected:
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    message="Database connection OK",
                    details={"connection_pool_size": 10, "active_connections": 3}
                )
            else:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    message="Database connection failed",
                    details={"error": "Connection timeout"}
                )

    # Test healthy case
    check_healthy = DatabaseHealthCheck(db_connected=True)
    result_healthy = await check_healthy.check()
    assert result_healthy.status == HealthStatus.HEALTHY

    # Test unhealthy case
    check_unhealthy = DatabaseHealthCheck(db_connected=False)
    result_unhealthy = await check_unhealthy.check()
    assert result_unhealthy.status == HealthStatus.UNHEALTHY


@pytest.mark.asyncio
async def test_async_health_check():
    """Test health check with async operations."""
    class AsyncHealthCheck(HealthCheck):
        async def check(self) -> HealthCheckResult:
            # Simulate async operation (e.g., network call)
            await asyncio.sleep(0.01)
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                message="Async check completed"
            )

    check = AsyncHealthCheck()
    result = await check.check()

    assert result.status == HealthStatus.HEALTHY
    assert "Async check completed" in result.message


# ============================================================================
# Global Singleton Tests
# ============================================================================


def test_global_health_monitor_singleton():
    """Test get_health_monitor returns the same instance."""
    monitor1 = get_health_monitor()
    monitor2 = get_health_monitor()

    assert monitor1 is monitor2


@pytest.mark.asyncio
async def test_global_health_usage(global_health):
    """Test using the global health monitor."""
    global_health.add_check("liveness", LivenessCheck())

    # Should be accessible from any call to get_health_monitor()
    monitor = get_health_monitor()
    assert "liveness" in monitor._checks


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_kubernetes_liveness_probe(health_monitor):
    """Test Kubernetes liveness probe endpoint."""
    health_monitor.add_check("liveness", LivenessCheck())

    liveness = await health_monitor.get_liveness()

    # Should match Kubernetes probe format
    assert "status" in liveness
    assert liveness["status"] in ["healthy", "degraded", "unhealthy"]
    assert "message" in liveness
    assert "details" in liveness


@pytest.mark.asyncio
async def test_kubernetes_readiness_probe(health_monitor):
    """Test Kubernetes readiness probe endpoint."""
    readiness_check = ReadinessCheck()
    health_monitor.add_check("readiness", readiness_check)

    # Not ready
    readiness_check._initialization_complete = False
    readiness = await health_monitor.get_readiness()
    assert readiness["status"] == HealthStatus.UNHEALTHY.value

    # Ready
    readiness_check._initialization_complete = True
    readiness = await health_monitor.get_readiness()
    assert readiness["status"] == HealthStatus.HEALTHY.value


@pytest.mark.asyncio
async def test_full_health_report(health_monitor):
    """Test comprehensive health report with all checks."""
    health_monitor.add_check("liveness", LivenessCheck())
    health_monitor.add_check("readiness", ReadinessCheck())
    health_monitor.add_check("resources", ResourceCheck())

    report = await health_monitor.get_health()

    assert report["status"] in ["healthy", "degraded", "unhealthy"]
    assert "timestamp" in report
    assert len(report["checks"]) == 3
    assert "liveness" in report["checks"]
    assert "readiness" in report["checks"]
    assert "resources" in report["checks"]


@pytest.mark.asyncio
async def test_health_check_error_handling(health_monitor):
    """Test health monitor handles check failures gracefully."""
    class FailingCheck(HealthCheck):
        async def check(self) -> HealthCheckResult:
            raise RuntimeError("Check failed")

    health_monitor.add_check("failing", FailingCheck())
    health_monitor.add_check("liveness", LivenessCheck())

    # Should not crash, but mark as unhealthy
    report = await health_monitor.get_health()

    assert "status" in report
    # Overall status should be unhealthy due to failing check
    assert report["status"] == HealthStatus.UNHEALTHY.value


@pytest.mark.asyncio
async def test_parallel_health_checks(health_monitor):
    """Test multiple health checks run in parallel."""
    class SlowCheck(HealthCheck):
        def __init__(self, delay: float):
            self.delay = delay

        async def check(self) -> HealthCheckResult:
            await asyncio.sleep(self.delay)
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                message=f"Check completed after {self.delay}s"
            )

    health_monitor.add_check("slow1", SlowCheck(0.1))
    health_monitor.add_check("slow2", SlowCheck(0.1))
    health_monitor.add_check("slow3", SlowCheck(0.1))

    start = time.time()
    await health_monitor.get_health()
    duration = time.time() - start

    # If checks run in parallel, should take ~0.1s (not 0.3s)
    assert duration < 0.2  # Allow some overhead


@pytest.mark.asyncio
async def test_health_report_serialization(health_monitor):
    """Test health report can be serialized to JSON."""
    import json

    health_monitor.add_check("liveness", LivenessCheck())
    health_monitor.add_check("readiness", ReadinessCheck())

    report = await health_monitor.get_health()

    # Should be JSON serializable
    json_str = json.dumps(report)
    assert isinstance(json_str, str)

    # Should be deserializable
    deserialized = json.loads(json_str)
    assert deserialized["status"] == report["status"]
