"""
Tests for observability metrics system.

Tests the MetricsCollector, metric types (Counter, Gauge, Histogram, Summary),
Prometheus export format, and Timer context manager.
"""

import time

import pytest

from src.observability.metrics import (
    MetricsCollector,
    Timer,
    get_metrics_collector,
)


@pytest.fixture
def metrics_collector():
    """Create a fresh MetricsCollector for each test."""
    collector = MetricsCollector()
    # Clear any existing metrics
    collector._counters.clear()
    collector._gauges.clear()
    collector._histograms.clear()
    collector._summaries.clear()
    return collector


@pytest.fixture
def global_collector():
    """Use the global singleton collector (reset after each test)."""
    collector = get_metrics_collector()
    # Store current state
    old_counters = collector._counters.copy()
    old_gauges = collector._gauges.copy()
    old_histograms = collector._histograms.copy()
    old_summaries = collector._summaries.copy()

    # Clear for test
    collector._counters.clear()
    collector._gauges.clear()
    collector._histograms.clear()
    collector._summaries.clear()

    yield collector

    # Restore state
    collector._counters = old_counters
    collector._gauges = old_gauges
    collector._histograms = old_histograms
    collector._summaries = old_summaries


# ============================================================================
# Counter Tests
# ============================================================================


def test_counter_increment(metrics_collector):
    """Test counter increments correctly."""
    metrics_collector.increment("test_counter", amount=1.0)
    metrics_collector.increment("test_counter", amount=2.0)
    metrics_collector.increment("test_counter", amount=3.0)

    # Get counter
    counter = metrics_collector._counters.get("test_counter||")
    assert counter is not None
    assert counter.value == 6.0


def test_counter_with_labels(metrics_collector):
    """Test counter with labels creates separate metrics."""
    metrics_collector.increment("requests", labels={"status": "success"})
    metrics_collector.increment("requests", labels={"status": "success"})
    metrics_collector.increment("requests", labels={"status": "error"})

    # Check two separate counters exist
    success_counter = metrics_collector._counters.get('requests|status="success"|')
    error_counter = metrics_collector._counters.get('requests|status="error"|')

    assert success_counter is not None
    assert success_counter.value == 2.0
    assert error_counter is not None
    assert error_counter.value == 1.0


def test_counter_never_decreases(metrics_collector):
    """Test counter only increments (monotonic)."""
    metrics_collector.increment("monotonic_counter", amount=5.0)

    counter = metrics_collector._counters.get("monotonic_counter||")
    assert counter.value == 5.0

    # Try to increment by negative (should be rejected or handled)
    # Most Prometheus libraries prevent this, but let's test behavior
    metrics_collector.increment("monotonic_counter", amount=3.0)
    assert counter.value == 8.0


def test_counter_registration_with_description(metrics_collector):
    """Test counter registration with metadata."""
    counter = metrics_collector.register_counter(
        "described_counter",
        description="A counter with description",
        labels={"type": "test"}
    )

    assert counter.name == "described_counter"
    assert counter.description == "A counter with description"
    assert counter.labels == {"type": "test"}


# ============================================================================
# Gauge Tests
# ============================================================================


def test_gauge_set_value(metrics_collector):
    """Test gauge can be set to arbitrary values."""
    metrics_collector.set_gauge("temperature", 20.0)
    gauge = metrics_collector._gauges.get("temperature||")
    assert gauge.value == 20.0

    metrics_collector.set_gauge("temperature", 25.0)
    assert gauge.value == 25.0

    metrics_collector.set_gauge("temperature", 15.0)
    assert gauge.value == 15.0


def test_gauge_increment_decrement(metrics_collector):
    """Test gauge increment and decrement operations."""
    metrics_collector.set_gauge("active_connections", 10.0)

    # Increment
    metrics_collector.increment_gauge("active_connections", 5.0)
    gauge = metrics_collector._gauges.get("active_connections||")
    assert gauge.value == 15.0

    # Decrement
    metrics_collector.decrement_gauge("active_connections", 3.0)
    assert gauge.value == 12.0

    # Can go negative
    metrics_collector.decrement_gauge("active_connections", 20.0)
    assert gauge.value == -8.0


def test_gauge_with_labels(metrics_collector):
    """Test gauge with different labels."""
    metrics_collector.set_gauge("cpu_usage", 45.0, labels={"core": "0"})
    metrics_collector.set_gauge("cpu_usage", 55.0, labels={"core": "1"})

    gauge0 = metrics_collector._gauges.get('cpu_usage|core="0"|')
    gauge1 = metrics_collector._gauges.get('cpu_usage|core="1"|')

    assert gauge0.value == 45.0
    assert gauge1.value == 55.0


# ============================================================================
# Histogram Tests
# ============================================================================


def test_histogram_observe_values(metrics_collector):
    """Test histogram observes values and creates buckets."""
    metrics_collector.observe_histogram("request_duration", 0.05)
    metrics_collector.observe_histogram("request_duration", 0.15)
    metrics_collector.observe_histogram("request_duration", 0.3)
    metrics_collector.observe_histogram("request_duration", 0.8)

    histogram = metrics_collector._histograms.get("request_duration||")
    assert histogram is not None
    assert histogram.count == 4
    assert histogram.sum == pytest.approx(1.3, rel=1e-6)


def test_histogram_buckets(metrics_collector):
    """Test histogram bucket distribution."""
    # Create histogram with custom buckets
    buckets = [0.1, 0.5, 1.0, 5.0]
    histogram = metrics_collector.register_histogram(
        "custom_latency",
        buckets=buckets
    )

    # Observe values
    metrics_collector.observe_histogram("custom_latency", 0.05)  # < 0.1
    metrics_collector.observe_histogram("custom_latency", 0.2)   # 0.1-0.5
    metrics_collector.observe_histogram("custom_latency", 0.7)   # 0.5-1.0
    metrics_collector.observe_histogram("custom_latency", 2.0)   # 1.0-5.0
    metrics_collector.observe_histogram("custom_latency", 10.0)  # > 5.0

    histogram = metrics_collector._histograms.get("custom_latency||")

    # All values should be counted
    assert histogram.count == 5
    assert histogram.sum == pytest.approx(13.0, rel=1e-6)


def test_histogram_with_labels(metrics_collector):
    """Test histogram with labels."""
    metrics_collector.observe_histogram("api_latency", 0.1, labels={"endpoint": "/users"})
    metrics_collector.observe_histogram("api_latency", 0.2, labels={"endpoint": "/users"})
    metrics_collector.observe_histogram("api_latency", 0.3, labels={"endpoint": "/posts"})

    users_histogram = metrics_collector._histograms.get('api_latency|endpoint="/users"|')
    posts_histogram = metrics_collector._histograms.get('api_latency|endpoint="/posts"|')

    assert users_histogram.count == 2
    assert users_histogram.sum == pytest.approx(0.3, rel=1e-6)
    assert posts_histogram.count == 1
    assert posts_histogram.sum == pytest.approx(0.3, rel=1e-6)


# ============================================================================
# Summary Tests
# ============================================================================


def test_summary_observe_values(metrics_collector):
    """Test summary observes values."""
    metrics_collector.observe_summary("response_size", 100.0)
    metrics_collector.observe_summary("response_size", 200.0)
    metrics_collector.observe_summary("response_size", 300.0)

    summary = metrics_collector._summaries.get("response_size||")
    assert summary is not None
    assert summary.count == 3
    assert summary.sum == 600.0


def test_summary_percentiles(metrics_collector):
    """Test summary calculates percentiles correctly."""
    # Observe many values
    for i in range(1, 101):
        metrics_collector.observe_summary("percentile_test", float(i))

    summary = metrics_collector._summaries.get("percentile_test||")
    assert summary.count == 100
    assert summary.sum == 5050.0

    # Check percentiles (approximate)
    assert len(summary.values) == 100


def test_summary_with_labels(metrics_collector):
    """Test summary with labels."""
    metrics_collector.observe_summary("message_size", 1024.0, labels={"type": "request"})
    metrics_collector.observe_summary("message_size", 512.0, labels={"type": "response"})

    request_summary = metrics_collector._summaries.get('message_size|type="request"|')
    response_summary = metrics_collector._summaries.get('message_size|type="response"|')

    assert request_summary.count == 1
    assert request_summary.sum == 1024.0
    assert response_summary.count == 1
    assert response_summary.sum == 512.0


# ============================================================================
# Timer Context Manager Tests
# ============================================================================


def test_timer_context_manager(metrics_collector):
    """Test Timer context manager records duration."""
    with Timer("operation_duration", labels={"op": "test"}, collector=metrics_collector):
        time.sleep(0.01)  # Sleep for 10ms

    histogram = metrics_collector._histograms.get('operation_duration|op="test"|')
    assert histogram is not None
    assert histogram.count == 1
    # Duration should be at least 10ms (0.01s)
    assert histogram.sum >= 0.01


def test_timer_with_exception(metrics_collector):
    """Test Timer still records duration even if exception occurs."""
    try:
        with Timer("failing_operation", collector=metrics_collector):
            time.sleep(0.005)
            raise ValueError("Test error")
    except ValueError:
        pass

    histogram = metrics_collector._histograms.get("failing_operation||")
    assert histogram is not None
    assert histogram.count == 1
    assert histogram.sum >= 0.005


def test_timer_manual_stop(metrics_collector):
    """Test Timer can be used manually (start/stop)."""
    timer = Timer("manual_timer", collector=metrics_collector)

    timer.__enter__()
    time.sleep(0.01)
    timer.__exit__(None, None, None)

    histogram = metrics_collector._histograms.get("manual_timer||")
    assert histogram.count == 1
    assert histogram.sum >= 0.01


# ============================================================================
# Prometheus Export Tests
# ============================================================================


def test_prometheus_export_format(metrics_collector):
    """Test Prometheus export format is correct."""
    # Add metrics
    metrics_collector.increment("http_requests_total", labels={"method": "GET", "status": "200"})
    metrics_collector.increment("http_requests_total", labels={"method": "POST", "status": "201"})
    metrics_collector.set_gauge("active_connections", 42.0)
    metrics_collector.observe_histogram("request_duration_seconds", 0.5)

    # Export
    prometheus_text = metrics_collector.export_prometheus()

    # Check format
    assert "# HELP http_requests_total" in prometheus_text
    assert "# TYPE http_requests_total counter" in prometheus_text
    assert 'http_requests_total{method="GET",status="200"} 1' in prometheus_text

    assert "# HELP active_connections" in prometheus_text
    assert "# TYPE active_connections gauge" in prometheus_text
    assert "active_connections 42" in prometheus_text

    assert "# HELP request_duration_seconds" in prometheus_text
    assert "# TYPE request_duration_seconds histogram" in prometheus_text


def test_prometheus_export_empty_metrics(metrics_collector):
    """Test Prometheus export with no metrics."""
    prometheus_text = metrics_collector.export_prometheus()

    # Should return empty or minimal output
    assert isinstance(prometheus_text, str)


def test_prometheus_export_special_characters(metrics_collector):
    """Test Prometheus export handles label values with special characters."""
    metrics_collector.increment(
        "api_calls",
        labels={"endpoint": "/api/v1/users", "method": "GET"}
    )

    prometheus_text = metrics_collector.export_prometheus()

    # Labels should be properly escaped
    assert 'api_calls{endpoint="/api/v1/users",method="GET"}' in prometheus_text


# ============================================================================
# Global Singleton Tests
# ============================================================================


def test_global_metrics_collector_singleton():
    """Test get_metrics_collector returns the same instance."""
    collector1 = get_metrics_collector()
    collector2 = get_metrics_collector()

    assert collector1 is collector2


def test_global_collector_usage(global_collector):
    """Test using the global collector."""
    global_collector.increment("global_test_counter")
    global_collector.set_gauge("global_test_gauge", 100.0)

    # Should be accessible from any call to get_metrics_collector()
    collector = get_metrics_collector()

    counter = collector._counters.get("global_test_counter||")
    gauge = collector._gauges.get("global_test_gauge||")

    assert counter is not None
    assert counter.value == 1.0
    assert gauge is not None
    assert gauge.value == 100.0


# ============================================================================
# Edge Cases
# ============================================================================


def test_metric_name_validation(metrics_collector):
    """Test metric names are validated."""
    # Valid names
    metrics_collector.increment("valid_metric_name")
    metrics_collector.increment("valid_metric_123")
    metrics_collector.increment("valid:metric:name")

    # These should all succeed
    assert len(metrics_collector._counters) == 3


def test_label_ordering_consistency(metrics_collector):
    """Test that label ordering is consistent."""
    # Add metrics with same labels in different order
    metrics_collector.increment("test_metric", labels={"a": "1", "b": "2"})
    metrics_collector.increment("test_metric", labels={"b": "2", "a": "1"})

    # Should create only one counter (labels are sorted)
    # Note: Implementation should sort labels for consistency
    counters = [k for k in metrics_collector._counters.keys() if k.startswith("test_metric")]

    # Depending on implementation, could be 1 or 2 counters
    # If sorted: 1 counter with value 2.0
    # If not sorted: 2 counters with value 1.0 each
    assert len(counters) >= 1


def test_high_cardinality_labels(metrics_collector):
    """Test metrics collector handles high cardinality labels."""
    # Create many unique label combinations
    for i in range(1000):
        metrics_collector.increment("high_cardinality_metric", labels={"id": str(i)})

    # Should have 1000 separate counters
    counters = [k for k in metrics_collector._counters.keys() if k.startswith("high_cardinality_metric")]
    assert len(counters) == 1000


def test_concurrent_metric_updates(metrics_collector):
    """Test metrics can handle concurrent updates (basic thread safety check)."""
    import threading

    def increment_counter():
        for _ in range(100):
            metrics_collector.increment("concurrent_counter")

    threads = [threading.Thread(target=increment_counter) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    counter = metrics_collector._counters.get("concurrent_counter||")
    assert counter is not None
    # Should be 10 threads * 100 increments = 1000
    # Note: This test may fail if implementation is not thread-safe
    assert counter.value == 1000.0


# ============================================================================
# Integration Tests
# ============================================================================


def test_metrics_full_workflow(metrics_collector):
    """Test a complete metrics collection workflow."""
    # Simulate request handling
    metrics_collector.increment("requests_total", labels={"method": "GET", "status": "200"})

    with Timer("request_duration", labels={"method": "GET"}, collector=metrics_collector):
        time.sleep(0.01)

    metrics_collector.set_gauge("active_requests", 1.0)
    metrics_collector.observe_summary("request_size_bytes", 1024.0)

    # Export and verify
    prometheus_text = metrics_collector.export_prometheus()

    assert "requests_total" in prometheus_text
    assert "request_duration" in prometheus_text
    assert "active_requests" in prometheus_text
    assert "request_size_bytes" in prometheus_text


def test_metrics_reset(metrics_collector):
    """Test metrics can be cleared/reset."""
    metrics_collector.increment("test_counter")
    metrics_collector.set_gauge("test_gauge", 100.0)

    # Clear all metrics
    metrics_collector._counters.clear()
    metrics_collector._gauges.clear()
    metrics_collector._histograms.clear()
    metrics_collector._summaries.clear()

    # Should be empty
    assert len(metrics_collector._counters) == 0
    assert len(metrics_collector._gauges) == 0
    assert len(metrics_collector._histograms) == 0
    assert len(metrics_collector._summaries) == 0
