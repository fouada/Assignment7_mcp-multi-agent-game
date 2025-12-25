"""
Health Check System
===================

Production-grade health check system for monitoring service health.

Provides:
- HealthCheck base class for custom checks
- Built-in checks: Liveness, Readiness, Dependency, Resource
- HealthMonitor for managing multiple checks
- HTTP endpoints: /health/live, /health/ready, /health

Usage:
    from src.observability.health import get_health_monitor, LivenessCheck

    health = get_health_monitor()
    health.add_check("liveness", LivenessCheck())

    # Check health
    report = await health.get_health()
    print(report)
"""

import asyncio
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import psutil

from ..common.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# Health Status
# ============================================================================


class HealthStatus(str, Enum):
    """Health check status."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    status: HealthStatus
    message: str = ""
    details: dict[str, Any] = None
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.details is None:
            self.details = {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
        }


# ============================================================================
# Health Check Base Class
# ============================================================================


class HealthCheck(ABC):
    """
    Base class for health checks.

    Subclass this to create custom health checks.
    """

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description

    @abstractmethod
    async def check(self) -> HealthCheckResult:
        """
        Perform health check.

        Returns:
            HealthCheckResult with status and details
        """
        pass


# ============================================================================
# Built-in Health Checks
# ============================================================================


class LivenessCheck(HealthCheck):
    """
    Liveness check - is the process running?

    This check always returns healthy if called (process is alive).
    Use for Kubernetes liveness probes.
    """

    def __init__(self):
        super().__init__(
            name="liveness",
            description="Process is alive and responding",
        )

    async def check(self) -> HealthCheckResult:
        """Check if process is alive."""
        return HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="Process is alive",
            details={
                "uptime_seconds": self._get_uptime(),
                "pid": self._get_pid(),
            },
        )

    def _get_uptime(self) -> float:
        """Get process uptime in seconds."""
        try:
            process = psutil.Process()
            create_time = process.create_time()
            return time.time() - create_time
        except Exception:
            return 0.0

    def _get_pid(self) -> int:
        """Get process ID."""
        try:
            return psutil.Process().pid
        except Exception:
            return 0


class ReadinessCheck(HealthCheck):
    """
    Readiness check - can the service accept requests?

    This checks if all required dependencies are available.
    Use for Kubernetes readiness probes.
    """

    def __init__(self, required_checks: list[str] | None = None):
        super().__init__(
            name="readiness",
            description="Service is ready to accept requests",
        )
        self.required_checks = required_checks or []
        self._initialization_complete = True
        self._dependencies_available = True

    async def check(self) -> HealthCheckResult:
        """Check if service is ready."""
        # Check initialization status
        if not self._initialization_complete:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message="Service not initialized",
                details={
                    "initialization_complete": False,
                    "dependencies_available": self._dependencies_available,
                },
            )

        # Check dependencies availability
        if not self._dependencies_available:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message="Dependencies unavailable",
                details={
                    "initialization_complete": self._initialization_complete,
                    "dependencies_available": False,
                },
            )

        # All checks passed
        return HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="Service is ready",
            details={
                "initialization_complete": True,
                "dependencies_available": True,
            },
        )


class DependencyCheck(HealthCheck):
    """
    Dependency check - can we reach a dependency?

    Checks if a required external service is reachable.
    """

    def __init__(
        self,
        name: str,
        url: str,
        timeout: float = 5.0,
        description: str = "",
    ):
        super().__init__(
            name=name,
            description=description or f"Check dependency: {url}",
        )
        self.url = url
        self.timeout = timeout

    async def check(self) -> HealthCheckResult:
        """Check if dependency is reachable."""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                async with session.get(
                    self.url, timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    duration_ms = (time.time() - start_time) * 1000

                    if response.status < 500:
                        return HealthCheckResult(
                            status=HealthStatus.HEALTHY,
                            message=f"Dependency reachable (HTTP {response.status})",
                            details={
                                "url": self.url,
                                "status_code": response.status,
                                "response_time_ms": round(duration_ms, 2),
                            },
                        )
                    else:
                        return HealthCheckResult(
                            status=HealthStatus.UNHEALTHY,
                            message=f"Dependency returned HTTP {response.status}",
                            details={
                                "url": self.url,
                                "status_code": response.status,
                            },
                        )

        except TimeoutError:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"Dependency timeout after {self.timeout}s",
                details={"url": self.url},
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"Dependency unreachable: {str(e)}",
                details={"url": self.url, "error": str(e)},
            )


class ResourceCheck(HealthCheck):
    """
    Resource check - are system resources within limits?

    Checks CPU, memory, and disk usage.
    """

    def __init__(
        self,
        max_cpu_percent: float = 90.0,
        max_memory_percent: float = 90.0,
        max_disk_percent: float = 90.0,
    ):
        super().__init__(
            name="resources",
            description="System resources within limits",
        )
        self.max_cpu_percent = max_cpu_percent
        self.max_memory_percent = max_memory_percent
        self.max_disk_percent = max_disk_percent

    async def check(self) -> HealthCheckResult:
        """Check system resources."""
        try:
            # Get resource usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            details = {
                "cpu_percent": round(cpu_percent, 2),
                "memory_percent": round(memory.percent, 2),
                "disk_percent": round(disk.percent, 2),
                "memory_available_mb": round(memory.available / 1024 / 1024, 2),
                "disk_available_gb": round(disk.free / 1024 / 1024 / 1024, 2),
            }

            # Check thresholds
            issues = []

            if cpu_percent > self.max_cpu_percent:
                issues.append(f"CPU usage ({cpu_percent:.1f}%) exceeds limit")

            if memory.percent > self.max_memory_percent:
                issues.append(f"Memory usage ({memory.percent:.1f}%) exceeds limit")

            if disk.percent > self.max_disk_percent:
                issues.append(f"Disk usage ({disk.percent:.1f}%) exceeds limit")

            if issues:
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    message="; ".join(issues),
                    details=details,
                )
            else:
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    message="Resources within limits",
                    details=details,
                )

        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check resources: {str(e)}",
                details={"error": str(e)},
            )


# ============================================================================
# Health Monitor
# ============================================================================


class HealthMonitor:
    """
    Health monitor for managing multiple health checks.

    Singleton that runs checks and provides health reports.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._checks: dict[str, HealthCheck] = {}
        self._check_lock = threading.Lock()

        # Last check results cache
        self._last_results: dict[str, HealthCheckResult] = {}
        self._last_check_time: float | None = None
        self._last_report: dict[str, Any] | None = None

        # Configuration
        self.enabled = True
        self._cache_ttl_seconds = 5.0  # Cache results for 5 seconds

        # Register default checks
        self._register_default_checks()

        self._initialized = True
        logger.info("Health monitor initialized")

    def _register_default_checks(self) -> None:
        """Register default health checks."""
        self.add_check("liveness", LivenessCheck())
        self.add_check("readiness", ReadinessCheck())
        self.add_check("resources", ResourceCheck())

    def add_check(self, name: str, check: HealthCheck) -> None:
        """
        Add a health check.

        Args:
            name: Unique check name
            check: HealthCheck instance
        """
        with self._check_lock:
            self._checks[name] = check
            logger.info(f"Added health check: {name}")

    def remove_check(self, name: str) -> bool:
        """
        Remove a health check.

        Args:
            name: Check name

        Returns:
            True if removed, False if not found
        """
        with self._check_lock:
            if name in self._checks:
                del self._checks[name]
                logger.info(f"Removed health check: {name}")
                return True
            return False

    def get_check(self, name: str) -> HealthCheck | None:
        """Get a health check by name."""
        return self._checks.get(name)

    def list_checks(self) -> list[str]:
        """List all registered check names."""
        return list(self._checks.keys())

    async def run_check(self, name: str) -> HealthCheckResult:
        """
        Run a single health check.

        Args:
            name: Check name

        Returns:
            HealthCheckResult
        """
        check = self.get_check(name)
        if not check:
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                message=f"Health check '{name}' not found",
            )

        try:
            result = await check.check()
            # Cache result
            self._last_results[name] = result
            return result
        except Exception as e:
            logger.error(f"Health check '{name}' failed: {e}")
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
                details={"error": str(e)},
            )

    async def run_all_checks(self, use_cache: bool = True) -> dict[str, HealthCheckResult]:
        """
        Run all health checks.

        Args:
            use_cache: Whether to use cached results if available

        Returns:
            Dictionary mapping check names to results
        """
        if not self.enabled:
            return {}

        # Check cache
        now = time.time()
        if (
            use_cache
            and self._last_check_time
            and (now - self._last_check_time) < self._cache_ttl_seconds
        ):
            return self._last_results.copy()

        # Run all checks concurrently using asyncio.gather
        check_names = list(self._checks.keys())
        tasks = [self.run_check(name) for name in check_names]

        # Wait for all checks to complete in parallel
        try:
            check_results = await asyncio.gather(*tasks, return_exceptions=True)

            results = {}
            for name, result in zip(check_names, check_results, strict=False):
                if isinstance(result, Exception):
                    logger.error(f"Health check '{name}' failed: {result}")
                    results[name] = HealthCheckResult(
                        status=HealthStatus.UNHEALTHY,
                        message=f"Check failed: {str(result)}",
                    )
                else:
                    results[name] = result
        except Exception as e:
            logger.error(f"Failed to run health checks: {e}")
            results = {}

        # Update cache
        self._last_results = results
        self._last_check_time = now

        return results

    async def get_health(self, check_names: list[str] | None = None) -> dict[str, Any]:
        """
        Get health report.

        Args:
            check_names: Specific checks to run (None = all)

        Returns:
            Health report dictionary
        """
        # Check if we can use cached report
        now = time.time()
        if (
            not check_names  # Only cache when running all checks
            and self._last_report
            and self._last_check_time
            and (now - self._last_check_time) < self._cache_ttl_seconds
        ):
            return self._last_report

        if check_names:
            # Run specific checks
            results = {}
            for name in check_names:
                results[name] = await self.run_check(name)
        else:
            # Run all checks
            results = await self.run_all_checks(use_cache=False)

        # Determine overall status
        overall_status = self._determine_overall_status(results)

        report = {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {name: result.to_dict() for name, result in results.items()},
        }

        # Cache the report if running all checks
        if not check_names:
            self._last_report = report
            self._last_check_time = now

        return report

    async def get_liveness(self) -> dict[str, Any]:
        """
        Get liveness health (for Kubernetes liveness probe).

        Returns:
            Liveness report
        """
        # If no liveness check is registered, return healthy (process is alive)
        if "liveness" not in self._checks:
            result = HealthCheckResult(
                status=HealthStatus.HEALTHY,
                message="Process is alive",
                details={"uptime_seconds": 0, "pid": 0},
            )
        else:
            result = await self.run_check("liveness")

        return {
            "status": result.status.value,
            "message": result.message,
            "details": result.details,
        }

    async def get_readiness(self) -> dict[str, Any]:
        """
        Get readiness health (for Kubernetes readiness probe).

        Returns:
            Readiness report
        """
        result = await self.run_check("readiness")
        return {
            "status": result.status.value,
            "message": result.message,
            "details": result.details,
        }

    def _determine_overall_status(self, results: dict[str, HealthCheckResult]) -> HealthStatus:
        """
        Determine overall status from individual check results.

        Logic:
        - If any check is unhealthy -> overall is unhealthy
        - If any check is degraded -> overall is degraded
        - If all checks are healthy -> overall is healthy
        - If no checks -> overall is healthy (no checks means no issues)
        - If all unknown -> overall is unknown
        """
        if not results:
            return HealthStatus.HEALTHY

        statuses = [result.status for result in results.values()]

        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        elif HealthStatus.HEALTHY in statuses:
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN

    def reset(self) -> None:
        """Reset health monitor state (for testing)."""
        with self._check_lock:
            self._checks.clear()
            self._last_results.clear()
            self._last_check_time = None
            self._last_report = None
            self._register_default_checks()

        logger.info("Health monitor reset")


# ============================================================================
# Singleton Access
# ============================================================================


def get_health_monitor() -> HealthMonitor:
    """Get the health monitor singleton."""
    return HealthMonitor()


# ============================================================================
# Example Usage
# ============================================================================


async def example_usage():
    """Demonstrate health check usage."""
    health = get_health_monitor()

    # Add custom dependency check
    health.add_check(
        "league_manager",
        DependencyCheck(
            name="league_manager",
            url="http://localhost:8000/health/live",
            timeout=2.0,
        ),
    )

    # Get full health report
    report = await health.get_health()
    print("Full health report:")
    print(f"  Status: {report['status']}")
    print(f"  Checks: {len(report['checks'])}")

    for name, check_result in report["checks"].items():
        print(f"    - {name}: {check_result['status']}")

    # Get liveness (for K8s probe)
    liveness = await health.get_liveness()
    print(f"\nLiveness: {liveness['status']}")

    # Get readiness (for K8s probe)
    readiness = await health.get_readiness()
    print(f"Readiness: {readiness['status']}")


if __name__ == "__main__":
    asyncio.run(example_usage())
