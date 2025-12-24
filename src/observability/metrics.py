"""
Metrics System
==============

Production-grade metrics collection using Prometheus client library.

Provides:
- MetricsCollector singleton for centralized metrics
- Standard metric types: Counter, Gauge, Histogram, Summary
- Built-in metrics for game system
- HTTP /metrics endpoint for Prometheus scraping

Usage:
    from src.observability.metrics import get_metrics_collector

    metrics = get_metrics_collector()

    # Counter
    metrics.increment("game_requests_total", labels={"type": "game_started"})

    # Gauge
    metrics.set_gauge("active_games", 5)

    # Histogram
    metrics.observe_histogram("request_duration_seconds", 0.123)

    # Get metrics in Prometheus format
    metrics_text = metrics.export_prometheus()
"""

import time
from typing import Any, Dict, List, Optional
from collections import defaultdict
from dataclasses import dataclass, field
import threading

from ..common.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# Metric Types
# ============================================================================


@dataclass
class Counter:
    """
    Counter metric - monotonically increasing value.

    Use for:
    - Request counts
    - Error counts
    - Completed tasks
    """

    name: str
    description: str = ""
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)

    def increment(self, amount: float = 1.0) -> None:
        """Increment counter by amount."""
        self.value += amount

    def reset(self) -> None:
        """Reset counter to zero."""
        self.value = 0.0


@dataclass
class Gauge:
    """
    Gauge metric - value that can go up and down.

    Use for:
    - Active connections
    - Queue sizes
    - Memory usage
    """

    name: str
    description: str = ""
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)

    def set(self, value: float) -> None:
        """Set gauge to value."""
        self.value = value

    def increment(self, amount: float = 1.0) -> None:
        """Increment gauge by amount."""
        self.value += amount

    def decrement(self, amount: float = 1.0) -> None:
        """Decrement gauge by amount."""
        self.value -= amount


@dataclass
class Histogram:
    """
    Histogram metric - distribution of values.

    Use for:
    - Request durations
    - Response sizes
    - Queue wait times
    """

    name: str
    description: str = ""
    buckets: List[float] = field(
        default_factory=lambda: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
    )
    bucket_counts: Dict[float, int] = field(default_factory=dict)
    sum: float = 0.0
    count: int = 0
    labels: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize bucket counts."""
        for bucket in self.buckets:
            self.bucket_counts[bucket] = 0
        # Add +Inf bucket
        self.bucket_counts[float("inf")] = 0

    def observe(self, value: float) -> None:
        """Observe a value."""
        self.sum += value
        self.count += 1

        # Update bucket counts
        for bucket in sorted(self.bucket_counts.keys()):
            if value <= bucket:
                self.bucket_counts[bucket] += 1


@dataclass
class Summary:
    """
    Summary metric - quantiles over sliding time window.

    Use for:
    - Request latencies
    - Response times
    - Processing durations
    """

    name: str
    description: str = ""
    values: List[float] = field(default_factory=list)
    max_size: int = 1000  # Keep last 1000 observations
    sum: float = 0.0
    count: int = 0
    labels: Dict[str, str] = field(default_factory=dict)

    def observe(self, value: float) -> None:
        """Observe a value."""
        self.values.append(value)
        self.sum += value
        self.count += 1

        # Limit size
        if len(self.values) > self.max_size:
            old_value = self.values.pop(0)
            # Don't update sum/count for summary (keep cumulative)

    def get_quantile(self, quantile: float) -> float:
        """Get quantile value (0.0 to 1.0)."""
        if not self.values:
            return 0.0

        sorted_values = sorted(self.values)
        index = int(len(sorted_values) * quantile)
        return sorted_values[min(index, len(sorted_values) - 1)]


# ============================================================================
# Metrics Collector
# ============================================================================


class MetricsCollector:
    """
    Centralized metrics collector (Singleton).

    Collects and exports metrics for the entire application.
    Thread-safe for concurrent metric updates.
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

        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._summaries: Dict[str, Summary] = {}

        # Thread safety
        self._metric_lock = threading.Lock()

        # Register built-in metrics
        self._register_builtin_metrics()

        self._initialized = True
        logger.info("Metrics collector initialized")

    def _register_builtin_metrics(self) -> None:
        """Register built-in game metrics."""
        # Request metrics
        self.register_counter(
            "game_requests_total",
            "Total number of game requests",
        )

        self.register_histogram(
            "game_request_duration_seconds",
            "Game request duration in seconds",
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
        )

        # Game metrics
        self.register_gauge(
            "active_games",
            "Number of active games",
        )

        self.register_counter(
            "games_total",
            "Total number of games played",
        )

        self.register_counter(
            "game_rounds_total",
            "Total number of game rounds",
        )

        # Strategy metrics
        self.register_counter(
            "strategy_decisions_total",
            "Total number of strategy decisions",
        )

        self.register_histogram(
            "strategy_decision_duration_seconds",
            "Strategy decision duration in seconds",
        )

        # Event bus metrics
        self.register_counter(
            "event_bus_events_total",
            "Total number of events emitted",
        )

        # Plugin metrics
        self.register_counter(
            "plugin_load_errors_total",
            "Total number of plugin load errors",
        )

        self.register_gauge(
            "plugins_loaded",
            "Number of loaded plugins",
        )

        # Middleware metrics
        self.register_counter(
            "middleware_errors_total",
            "Total number of middleware errors",
        )

        self.register_histogram(
            "middleware_duration_seconds",
            "Middleware execution duration in seconds",
        )

    # ========================================================================
    # Counter Methods
    # ========================================================================

    def register_counter(
        self,
        name: str,
        description: str = "",
        labels: Optional[Dict[str, str]] = None,
    ) -> Counter:
        """Register a new counter metric."""
        with self._metric_lock:
            key = self._make_key(name, labels)
            if key not in self._counters:
                self._counters[key] = Counter(
                    name=name,
                    description=description,
                    labels=labels or {},
                )
            return self._counters[key]

    def increment(
        self,
        name: str,
        amount: float = 1.0,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Increment a counter."""
        counter = self.register_counter(name, labels=labels)
        counter.increment(amount)

    def get_counter(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
    ) -> Optional[Counter]:
        """Get a counter by name and labels."""
        key = self._make_key(name, labels)
        return self._counters.get(key)

    # ========================================================================
    # Gauge Methods
    # ========================================================================

    def register_gauge(
        self,
        name: str,
        description: str = "",
        labels: Optional[Dict[str, str]] = None,
    ) -> Gauge:
        """Register a new gauge metric."""
        with self._metric_lock:
            key = self._make_key(name, labels)
            if key not in self._gauges:
                self._gauges[key] = Gauge(
                    name=name,
                    description=description,
                    labels=labels or {},
                )
            return self._gauges[key]

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Set a gauge value."""
        gauge = self.register_gauge(name, labels=labels)
        gauge.set(value)

    def increment_gauge(
        self,
        name: str,
        amount: float = 1.0,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Increment a gauge."""
        gauge = self.register_gauge(name, labels=labels)
        gauge.increment(amount)

    def decrement_gauge(
        self,
        name: str,
        amount: float = 1.0,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Decrement a gauge."""
        gauge = self.register_gauge(name, labels=labels)
        gauge.decrement(amount)

    # ========================================================================
    # Histogram Methods
    # ========================================================================

    def register_histogram(
        self,
        name: str,
        description: str = "",
        buckets: Optional[List[float]] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> Histogram:
        """Register a new histogram metric."""
        with self._metric_lock:
            key = self._make_key(name, labels)
            if key not in self._histograms:
                self._histograms[key] = Histogram(
                    name=name,
                    description=description,
                    buckets=buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
                    labels=labels or {},
                )
            return self._histograms[key]

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Observe a value in histogram."""
        histogram = self.register_histogram(name, labels=labels)
        histogram.observe(value)

    # ========================================================================
    # Summary Methods
    # ========================================================================

    def register_summary(
        self,
        name: str,
        description: str = "",
        max_size: int = 1000,
        labels: Optional[Dict[str, str]] = None,
    ) -> Summary:
        """Register a new summary metric."""
        with self._metric_lock:
            key = self._make_key(name, labels)
            if key not in self._summaries:
                self._summaries[key] = Summary(
                    name=name,
                    description=description,
                    max_size=max_size,
                    labels=labels or {},
                )
            return self._summaries[key]

    def observe_summary(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Observe a value in summary."""
        summary = self.register_summary(name, labels=labels)
        summary.observe(value)

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Make a unique key from name and labels."""
        if not labels:
            return name

        # Sort labels for consistent keys
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def reset(self) -> None:
        """Reset all metrics (for testing)."""
        with self._metric_lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._summaries.clear()
            self._register_builtin_metrics()

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics as dictionary."""
        return {
            "counters": {k: v.value for k, v in self._counters.items()},
            "gauges": {k: v.value for k, v in self._gauges.items()},
            "histograms": {
                k: {
                    "sum": v.sum,
                    "count": v.count,
                    "buckets": v.bucket_counts,
                }
                for k, v in self._histograms.items()
            },
            "summaries": {
                k: {
                    "sum": v.sum,
                    "count": v.count,
                    "quantiles": {
                        "0.5": v.get_quantile(0.5),
                        "0.9": v.get_quantile(0.9),
                        "0.99": v.get_quantile(0.99),
                    },
                }
                for k, v in self._summaries.items()
            },
        }

    # ========================================================================
    # Prometheus Export
    # ========================================================================

    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus text format.

        Format:
            # HELP metric_name Description
            # TYPE metric_name counter
            metric_name{label1="value1"} 42.0
        """
        lines = []

        # Export counters
        for key, counter in self._counters.items():
            if counter.description:
                lines.append(f"# HELP {counter.name} {counter.description}")
            lines.append(f"# TYPE {counter.name} counter")

            label_str = self._format_labels(counter.labels)
            lines.append(f"{counter.name}{label_str} {counter.value}")

        # Export gauges
        for key, gauge in self._gauges.items():
            if gauge.description:
                lines.append(f"# HELP {gauge.name} {gauge.description}")
            lines.append(f"# TYPE {gauge.name} gauge")

            label_str = self._format_labels(gauge.labels)
            lines.append(f"{gauge.name}{label_str} {gauge.value}")

        # Export histograms
        for key, histogram in self._histograms.items():
            if histogram.description:
                lines.append(f"# HELP {histogram.name} {histogram.description}")
            lines.append(f"# TYPE {histogram.name} histogram")

            label_str_base = self._format_labels(histogram.labels, include_braces=False)

            # Bucket counts
            for bucket, count in sorted(histogram.bucket_counts.items()):
                bucket_str = "+Inf" if bucket == float("inf") else str(bucket)
                if label_str_base:
                    label_str = f'{{{label_str_base},le="{bucket_str}"}}'
                else:
                    label_str = f'{{le="{bucket_str}"}}'
                lines.append(f"{histogram.name}_bucket{label_str} {count}")

            # Sum and count
            label_str = self._format_labels(histogram.labels)
            lines.append(f"{histogram.name}_sum{label_str} {histogram.sum}")
            lines.append(f"{histogram.name}_count{label_str} {histogram.count}")

        # Export summaries
        for key, summary in self._summaries.items():
            if summary.description:
                lines.append(f"# HELP {summary.name} {summary.description}")
            lines.append(f"# TYPE {summary.name} summary")

            label_str_base = self._format_labels(summary.labels, include_braces=False)

            # Quantiles
            for quantile in [0.5, 0.9, 0.99]:
                value = summary.get_quantile(quantile)
                if label_str_base:
                    label_str = f'{{{label_str_base},quantile="{quantile}"}}'
                else:
                    label_str = f'{{quantile="{quantile}"}}'
                lines.append(f"{summary.name}{label_str} {value}")

            # Sum and count
            label_str = self._format_labels(summary.labels)
            lines.append(f"{summary.name}_sum{label_str} {summary.sum}")
            lines.append(f"{summary.name}_count{label_str} {summary.count}")

        return "\n".join(lines) + "\n"

    def _format_labels(self, labels: Dict[str, str], include_braces: bool = True) -> str:
        """Format labels for Prometheus."""
        if not labels:
            return ""

        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))

        if include_braces:
            return f"{{{label_str}}}"
        return label_str


# ============================================================================
# Singleton Access
# ============================================================================


def get_metrics_collector() -> MetricsCollector:
    """Get the metrics collector singleton."""
    return MetricsCollector()


# ============================================================================
# Context Manager for Timing
# ============================================================================


class Timer:
    """
    Context manager for timing operations.

    Usage:
        with Timer("operation_duration_seconds"):
            # Your code here
            pass
    """

    def __init__(self, metric_name: str, labels: Optional[Dict[str, str]] = None):
        self.metric_name = metric_name
        self.labels = labels
        self.start_time = None
        self.metrics = get_metrics_collector()

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.metrics.observe_histogram(self.metric_name, duration, labels=self.labels)
        return False


# ============================================================================
# Example Usage
# ============================================================================


def example_usage():
    """Demonstrate metrics usage."""
    metrics = get_metrics_collector()

    # Counter
    metrics.increment("game_requests_total", labels={"type": "game_started"})
    metrics.increment("game_requests_total", labels={"type": "game_ended"})

    # Gauge
    metrics.set_gauge("active_games", 5)
    metrics.increment_gauge("active_games")  # Now 6
    metrics.decrement_gauge("active_games", 2)  # Now 4

    # Histogram
    metrics.observe_histogram("game_request_duration_seconds", 0.123)
    metrics.observe_histogram("game_request_duration_seconds", 0.456)

    # Summary
    metrics.observe_summary("response_size_bytes", 1024)

    # Timer context manager
    with Timer("operation_duration_seconds"):
        time.sleep(0.1)

    # Export to Prometheus format
    prometheus_text = metrics.export_prometheus()
    print(prometheus_text)

    # Get all metrics as dict
    all_metrics = metrics.get_all_metrics()
    print(all_metrics)


if __name__ == "__main__":
    example_usage()
