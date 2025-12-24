"""
Observability System
====================

Production-grade observability infrastructure for the MCP Game system.

Provides three pillars of observability:
1. **Metrics** - Prometheus-compatible metrics collection
2. **Tracing** - OpenTelemetry-compatible distributed tracing
3. **Health** - Health check system with liveness/readiness probes

Usage:
    from src.observability import (
        get_metrics_collector,
        get_tracing_manager,
        get_health_monitor,
    )

    # Metrics
    metrics = get_metrics_collector()
    metrics.increment("requests_total")

    # Tracing
    tracing = get_tracing_manager()
    with tracing.span("operation") as span:
        span.set_attribute("key", "value")

    # Health
    health = get_health_monitor()
    report = await health.get_health()
"""

from .metrics import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    MetricsCollector,
    get_metrics_collector,
    Timer,
)

from .tracing import (
    Span,
    SpanContext,
    SpanEvent,
    TracingManager,
    get_tracing_manager,
    trace_function,
)

from .health import (
    HealthStatus,
    HealthCheckResult,
    HealthCheck,
    LivenessCheck,
    ReadinessCheck,
    DependencyCheck,
    ResourceCheck,
    HealthMonitor,
    get_health_monitor,
)

__all__ = [
    # Metrics
    "Counter",
    "Gauge",
    "Histogram",
    "Summary",
    "MetricsCollector",
    "get_metrics_collector",
    "Timer",
    # Tracing
    "Span",
    "SpanContext",
    "SpanEvent",
    "TracingManager",
    "get_tracing_manager",
    "trace_function",
    # Health
    "HealthStatus",
    "HealthCheckResult",
    "HealthCheck",
    "LivenessCheck",
    "ReadinessCheck",
    "DependencyCheck",
    "ResourceCheck",
    "HealthMonitor",
    "get_health_monitor",
]
