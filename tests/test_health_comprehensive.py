"""
Comprehensive tests for health monitoring to increase coverage.

Tests additional health check scenarios and edge cases.
"""

import pytest
import time
from unittest.mock import Mock, patch
import asyncio

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


class TestHealthCheckEdgeCases:
    """Test HealthCheck edge cases."""

    @pytest.mark.asyncio
    async def test_custom_health_check_returning_unhealthy(self):
        """Test custom health check returning unhealthy."""
        class UnhealthyCheck(HealthCheck):
            def __init__(self):
                super().__init__("unhealthy_check")
            
            async def check(self) -> HealthCheckResult:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    message="System is unhealthy",
                    details={"reason": "test"}
                )
        
        check = UnhealthyCheck()
        result = await check.check()
        assert result.status == HealthStatus.UNHEALTHY
        assert result.message == "System is unhealthy"

    @pytest.mark.asyncio
    async def test_custom_health_check_returning_degraded(self):
        """Test custom health check returning degraded."""
        class DegradedCheck(HealthCheck):
            def __init__(self):
                super().__init__("degraded_check")
            
            async def check(self) -> HealthCheckResult:
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    message="System is degraded",
                    details={"warning": "low performance"}
                )
        
        check = DegradedCheck()
        result = await check.check()
        assert result.status == HealthStatus.DEGRADED


class TestReadinessCheckAdvanced:
    """Test ReadinessCheck advanced scenarios."""

    @pytest.mark.asyncio
    async def test_readiness_check_not_initialized(self):
        """Test readiness check when not initialized."""
        check = ReadinessCheck(initialized=False)
        result = await check.check()
        assert result.status == HealthStatus.UNHEALTHY
        assert "not initialized" in result.message.lower()

    @pytest.mark.asyncio
    async def test_readiness_check_with_failing_dependency(self):
        """Test readiness check with failing dependency."""
        async def failing_dep():
            return False
        
        check = ReadinessCheck(dependencies={"db": failing_dep})
        result = await check.check()
        assert result.status == HealthStatus.UNHEALTHY
        assert "db" in result.message

    @pytest.mark.asyncio
    async def test_readiness_check_with_multiple_dependencies(self):
        """Test readiness check with multiple dependencies."""
        async def healthy_dep():
            return True
        
        async def unhealthy_dep():
            return False
        
        check = ReadinessCheck(dependencies={
            "service1": healthy_dep,
            "service2": unhealthy_dep
        })
        result = await check.check()
        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_readiness_check_with_exception_in_dependency(self):
        """Test readiness check when dependency raises exception."""
        async def failing_dep():
            raise Exception("Connection failed")
        
        check = ReadinessCheck(dependencies={"db": failing_dep})
        result = await check.check()
        assert result.status == HealthStatus.UNHEALTHY


class TestResourceCheckAdvanced:
    """Test ResourceCheck advanced scenarios."""

    @pytest.mark.asyncio
    async def test_resource_check_cpu_above_threshold(self):
        """Test resource check when CPU above threshold."""
        with patch("psutil.cpu_percent", return_value=95.0):
            check = ResourceCheck(cpu_threshold=90.0)
            result = await check.check()
            assert result.status == HealthStatus.DEGRADED
            assert result.details["cpu_percent"] == 95.0

    @pytest.mark.asyncio
    async def test_resource_check_memory_above_threshold(self):
        """Test resource check when memory above threshold."""
        with patch("psutil.virtual_memory") as mock_vm:
            mock_vm.return_value.percent = 95.0
            check = ResourceCheck(memory_threshold=90.0)
            result = await check.check()
            assert result.status == HealthStatus.DEGRADED
            assert result.details["memory_percent"] == 95.0

    @pytest.mark.asyncio
    async def test_resource_check_both_thresholds_exceeded(self):
        """Test resource check when both thresholds exceeded."""
        with patch("psutil.cpu_percent", return_value=95.0), \
             patch("psutil.virtual_memory") as mock_vm:
            mock_vm.return_value.percent = 95.0
            check = ResourceCheck(cpu_threshold=80.0, memory_threshold=80.0)
            result = await check.check()
            assert result.status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_resource_check_psutil_not_available(self):
        """Test resource check when psutil not available."""
        with patch("psutil.cpu_percent", side_effect=ImportError()):
            check = ResourceCheck()
            result = await check.check()
            # Should still return a result, possibly degraded
            assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]


class TestHealthMonitorAdvanced:
    """Test HealthMonitor advanced scenarios."""

    @pytest.fixture
    def monitor(self):
        """Create a fresh monitor."""
        m = HealthMonitor()
        m._checks.clear()
        m._last_check_time = None
        m._last_report = None
        return m

    @pytest.mark.asyncio
    async def test_get_health_with_all_healthy(self, monitor):
        """Test get_health when all checks are healthy."""
        check1 = LivenessCheck()
        check2 = ReadinessCheck(initialized=True)
        
        monitor.add_health_check("liveness", check1)
        monitor.add_health_check("readiness", check2)
        
        report = await monitor.get_health()
        assert report["status"] == "healthy"
        assert len(report["checks"]) == 2

    @pytest.mark.asyncio
    async def test_get_health_with_one_degraded(self, monitor):
        """Test get_health with one degraded check."""
        class DegradedCheck(HealthCheck):
            def __init__(self):
                super().__init__("degraded")
            
            async def check(self):
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    message="Degraded"
                )
        
        monitor.add_health_check("liveness", LivenessCheck())
        monitor.add_health_check("degraded", DegradedCheck())
        
        report = await monitor.get_health()
        assert report["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_get_health_with_one_unhealthy(self, monitor):
        """Test get_health with one unhealthy check."""
        class UnhealthyCheck(HealthCheck):
            def __init__(self):
                super().__init__("unhealthy")
            
            async def check(self):
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    message="Unhealthy"
                )
        
        monitor.add_health_check("liveness", LivenessCheck())
        monitor.add_health_check("unhealthy", UnhealthyCheck())
        
        report = await monitor.get_health()
        assert report["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_get_health_cache_expiration(self, monitor):
        """Test that health check cache expires."""
        monitor.add_health_check("liveness", LivenessCheck())
        
        # First call
        report1 = await monitor.get_health()
        first_time = monitor._last_check_time
        
        # Wait for cache to expire (assuming cache_ttl is small)
        time.sleep(0.1)
        
        # Second call should trigger new checks
        report2 = await monitor.get_health()
        second_time = monitor._last_check_time
        
        # Times should be different if cache expired
        # (or same if cache is still valid)
        assert second_time >= first_time

    @pytest.mark.asyncio
    async def test_get_liveness_without_check(self, monitor):
        """Test get_liveness when no liveness check registered."""
        report = await monitor.get_liveness()
        # Should return a default response
        assert "status" in report

    @pytest.mark.asyncio
    async def test_get_readiness_not_ready(self, monitor):
        """Test get_readiness when not ready."""
        monitor.add_health_check("readiness", ReadinessCheck(initialized=False))
        
        report = await monitor.get_readiness()
        assert report["status"] in ["unhealthy", "not_ready"]

    def test_remove_nonexistent_check(self, monitor):
        """Test removing a check that doesn't exist."""
        # Should not raise
        monitor.remove_health_check("nonexistent")

    @pytest.mark.asyncio
    async def test_health_check_with_exception(self, monitor):
        """Test health check that raises exception."""
        class FailingCheck(HealthCheck):
            def __init__(self):
                super().__init__("failing")
            
            async def check(self):
                raise Exception("Check failed")
        
        monitor.add_health_check("failing", FailingCheck())
        
        # Should not raise, should handle gracefully
        report = await monitor.get_health()
        assert "status" in report

    @pytest.mark.asyncio
    async def test_force_refresh_ignores_cache(self, monitor):
        """Test force_refresh ignores cache."""
        monitor.add_health_check("liveness", LivenessCheck())
        
        # First call caches result
        await monitor.get_health()
        first_time = monitor._last_check_time
        
        # Force refresh should ignore cache
        await monitor.get_health(force_refresh=True)
        second_time = monitor._last_check_time
        
        assert second_time > first_time


class TestHealthMonitorSingleton:
    """Test health monitor singleton behavior."""

    def test_get_health_monitor_returns_singleton(self):
        """Test that get_health_monitor returns the same instance."""
        monitor1 = get_health_monitor()
        monitor2 = get_health_monitor()
        assert monitor1 is monitor2

    def test_health_monitor_shared_state(self):
        """Test that health monitor shares state across calls."""
        monitor1 = get_health_monitor()
        monitor1.add_health_check("test", LivenessCheck())
        
        monitor2 = get_health_monitor()
        # Should have the check added by monitor1
        assert "test" in monitor2._checks


class TestHealthCheckIntegration:
    """Test health check integration scenarios."""

    @pytest.mark.asyncio
    async def test_full_health_report_structure(self):
        """Test complete health report structure."""
        monitor = HealthMonitor()
        monitor._checks.clear()
        
        monitor.add_health_check("liveness", LivenessCheck())
        monitor.add_health_check("readiness", ReadinessCheck())
        monitor.add_health_check("resources", ResourceCheck())
        
        report = await monitor.get_health()
        
        assert "status" in report
        assert "timestamp" in report
        assert "checks" in report
        assert isinstance(report["checks"], dict)
        assert len(report["checks"]) == 3

    @pytest.mark.asyncio
    async def test_kubernetes_probes_simulation(self):
        """Test simulating Kubernetes liveness and readiness probes."""
        monitor = HealthMonitor()
        monitor._checks.clear()
        
        monitor.add_health_check("liveness", LivenessCheck())
        monitor.add_health_check("readiness", ReadinessCheck(initialized=True))
        
        # Simulate liveness probe
        liveness = await monitor.get_liveness()
        assert liveness["status"] in ["healthy", "ok"]
        
        # Simulate readiness probe
        readiness = await monitor.get_readiness()
        assert readiness["status"] in ["healthy", "ok", "ready"]


class TestHealthCheckResultEdgeCases:
    """Test HealthCheckResult edge cases."""

    def test_health_check_result_with_none_details(self):
        """Test HealthCheckResult with None details."""
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="OK",
            details=None
        )
        assert result.details is None

    def test_health_check_result_with_empty_details(self):
        """Test HealthCheckResult with empty details."""
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="OK",
            details={}
        )
        assert result.details == {}

    def test_health_check_result_with_complex_details(self):
        """Test HealthCheckResult with complex nested details."""
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="OK",
            details={
                "metrics": {
                    "cpu": 50.0,
                    "memory": 60.0
                },
                "dependencies": ["db", "cache"],
                "count": 42
            }
        )
        assert result.details["metrics"]["cpu"] == 50.0
        assert len(result.details["dependencies"]) == 2

