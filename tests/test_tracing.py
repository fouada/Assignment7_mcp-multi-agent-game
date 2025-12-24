"""
Tests for observability tracing system.

Tests the TracingManager, Span creation, W3C Trace Context propagation,
sampling, and distributed tracing integration.
"""

import pytest
import time
from typing import Dict, Optional
from src.observability.tracing import (
    TracingManager,
    get_tracing_manager,
    Span,
    SpanContext,
)


@pytest.fixture
def tracing_manager():
    """Create a fresh TracingManager for each test."""
    manager = TracingManager()
    manager.initialize(
        service_name="test_service",
        enabled=True,
        sample_rate=1.0  # Always sample for tests
    )
    # Clear any existing spans
    manager._active_spans.clear()
    manager._completed_spans.clear()
    return manager


@pytest.fixture
def global_tracing():
    """Use the global singleton tracing manager."""
    manager = get_tracing_manager()

    # Store current state
    old_enabled = manager._enabled
    old_sample_rate = manager._sample_rate
    old_service_name = manager._service_name
    old_active = manager._active_spans.copy()
    old_completed = manager._completed_spans.copy()

    # Initialize for test
    manager.initialize(
        service_name="test_service",
        enabled=True,
        sample_rate=1.0
    )
    manager._active_spans.clear()
    manager._completed_spans.clear()

    yield manager

    # Restore state
    manager._enabled = old_enabled
    manager._sample_rate = old_sample_rate
    manager._service_name = old_service_name
    manager._active_spans = old_active
    manager._completed_spans = old_completed


# ============================================================================
# Span Creation Tests
# ============================================================================


def test_start_span(tracing_manager):
    """Test starting a span creates it correctly."""
    span = tracing_manager.start_span("test_operation")

    assert span is not None
    assert span.name == "test_operation"
    assert span.trace_id is not None
    assert span.span_id is not None
    assert span.start_time is not None
    assert span.end_time is None
    assert span.status == "ok"


def test_start_span_with_attributes(tracing_manager):
    """Test span can have attributes."""
    attributes = {
        "http.method": "GET",
        "http.url": "/api/users",
        "user.id": "12345"
    }

    span = tracing_manager.start_span("http_request", attributes=attributes)

    assert span.attributes == attributes
    assert span.attributes["http.method"] == "GET"
    assert span.attributes["user.id"] == "12345"


def test_end_span(tracing_manager):
    """Test ending a span records duration."""
    span = tracing_manager.start_span("test_operation")
    span_id = span.span_id

    time.sleep(0.01)  # Sleep for at least 10ms

    tracing_manager.end_span(span)

    assert span.end_time is not None
    assert span.duration_ms is not None
    assert span.duration_ms >= 10.0  # At least 10ms

    # Should be moved to completed spans
    assert span_id not in tracing_manager._active_spans
    assert len(tracing_manager._completed_spans) > 0


def test_span_context_manager(tracing_manager):
    """Test span as context manager."""
    with tracing_manager.span("context_operation") as span:
        assert span is not None
        assert span.name == "context_operation"
        assert span.start_time is not None
        time.sleep(0.005)

    # After exiting, span should be ended
    assert span.end_time is not None
    assert span.duration_ms >= 5.0


def test_span_context_manager_with_exception(tracing_manager):
    """Test span context manager handles exceptions."""
    try:
        with tracing_manager.span("failing_operation") as span:
            time.sleep(0.005)
            raise ValueError("Test error")
    except ValueError:
        pass

    # Span should still be ended and marked as error
    assert span.end_time is not None
    assert span.status == "error"
    assert "Test error" in span.error_message


# ============================================================================
# Span Hierarchy Tests
# ============================================================================


def test_nested_spans(tracing_manager):
    """Test nested spans maintain parent-child relationship."""
    with tracing_manager.span("parent_operation") as parent_span:
        parent_trace_id = parent_span.trace_id
        parent_span_id = parent_span.span_id

        with tracing_manager.span("child_operation") as child_span:
            # Child should have same trace_id but different span_id
            assert child_span.trace_id == parent_trace_id
            assert child_span.span_id != parent_span_id
            assert child_span.parent_span_id == parent_span_id


def test_sibling_spans(tracing_manager):
    """Test sibling spans share trace but have different span IDs."""
    with tracing_manager.span("parent_operation") as parent_span:
        parent_trace_id = parent_span.trace_id

        with tracing_manager.span("child1") as child1:
            assert child1.trace_id == parent_trace_id
            assert child1.parent_span_id == parent_span.span_id

        with tracing_manager.span("child2") as child2:
            assert child2.trace_id == parent_trace_id
            assert child2.parent_span_id == parent_span.span_id
            # Sibling spans have different span IDs
            assert child2.span_id != child1.span_id


def test_deep_span_nesting(tracing_manager):
    """Test deeply nested spans maintain correct hierarchy."""
    with tracing_manager.span("level1") as span1:
        trace_id = span1.trace_id

        with tracing_manager.span("level2") as span2:
            assert span2.trace_id == trace_id
            assert span2.parent_span_id == span1.span_id

            with tracing_manager.span("level3") as span3:
                assert span3.trace_id == trace_id
                assert span3.parent_span_id == span2.span_id

                with tracing_manager.span("level4") as span4:
                    assert span4.trace_id == trace_id
                    assert span4.parent_span_id == span3.span_id


# ============================================================================
# Span Events and Status Tests
# ============================================================================


def test_add_event_to_span(tracing_manager):
    """Test adding events to a span."""
    with tracing_manager.span("operation_with_events") as span:
        span.add_event("Started processing")
        time.sleep(0.005)
        span.add_event("Checkpoint reached", {"progress": "50%"})
        time.sleep(0.005)
        span.add_event("Completed processing")

    assert len(span.events) == 3
    assert span.events[0]["name"] == "Started processing"
    assert span.events[1]["attributes"]["progress"] == "50%"


def test_set_span_status(tracing_manager):
    """Test setting span status."""
    with tracing_manager.span("test_operation") as span:
        span.set_status("ok", "Operation successful")

    assert span.status == "ok"
    assert span.error_message == "Operation successful"


def test_span_error_status(tracing_manager):
    """Test span automatically marked as error on exception."""
    try:
        with tracing_manager.span("error_operation") as span:
            raise RuntimeError("Something went wrong")
    except RuntimeError:
        pass

    assert span.status == "error"
    assert "Something went wrong" in span.error_message


# ============================================================================
# W3C Trace Context Tests
# ============================================================================


def test_inject_trace_context(tracing_manager):
    """Test injecting trace context into headers."""
    with tracing_manager.span("outgoing_request") as span:
        headers = {}
        headers = tracing_manager.inject_context(headers)

        assert "traceparent" in headers
        # W3C traceparent format: version-trace_id-span_id-flags
        traceparent = headers["traceparent"]
        parts = traceparent.split("-")

        assert len(parts) == 4
        assert parts[0] == "00"  # version
        assert len(parts[1]) == 32  # trace_id (hex)
        assert len(parts[2]) == 16  # span_id (hex)
        assert parts[3] in ["00", "01"]  # flags


def test_extract_trace_context(tracing_manager):
    """Test extracting trace context from headers."""
    # Create a W3C traceparent header
    trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    span_id = "00f067aa0ba902b7"
    traceparent = f"00-{trace_id}-{span_id}-01"

    headers = {"traceparent": traceparent}
    context = tracing_manager.extract_context(headers)

    assert context is not None
    assert context.trace_id == trace_id
    assert context.span_id == span_id


def test_propagate_trace_context(tracing_manager):
    """Test trace context propagation across service boundaries."""
    # Service A starts a span
    with tracing_manager.span("service_a_operation") as span_a:
        trace_id_a = span_a.trace_id

        # Inject context into headers (simulating outgoing request)
        headers = tracing_manager.inject_context({})

        # Service B receives request and extracts context
        context_b = tracing_manager.extract_context(headers)

        # Service B starts a span with extracted context
        with tracing_manager.span("service_b_operation", parent_context=context_b) as span_b:
            # Should have same trace_id but different span_id
            assert span_b.trace_id == trace_id_a
            assert span_b.span_id != span_a.span_id
            assert span_b.parent_span_id == span_a.span_id


def test_extract_invalid_traceparent(tracing_manager):
    """Test handling invalid traceparent header."""
    headers = {"traceparent": "invalid-format"}
    context = tracing_manager.extract_context(headers)

    # Should return None or handle gracefully
    assert context is None


# ============================================================================
# Sampling Tests
# ============================================================================


def test_sampling_always_sample(tracing_manager):
    """Test 100% sampling rate."""
    tracing_manager._sample_rate = 1.0

    sampled_count = 0
    for _ in range(100):
        with tracing_manager.span("sampled_operation") as span:
            if span is not None:
                sampled_count += 1

    assert sampled_count == 100


def test_sampling_never_sample():
    """Test 0% sampling rate."""
    manager = TracingManager()
    manager.initialize(service_name="test", enabled=True, sample_rate=0.0)

    sampled_count = 0
    for _ in range(100):
        with manager.span("unsampled_operation") as span:
            if span is not None:
                sampled_count += 1

    assert sampled_count == 0


def test_sampling_partial():
    """Test partial sampling (probabilistic)."""
    manager = TracingManager()
    manager.initialize(service_name="test", enabled=True, sample_rate=0.5)

    sampled_count = 0
    iterations = 1000

    for _ in range(iterations):
        with manager.span("partial_sample_operation") as span:
            if span is not None:
                sampled_count += 1

    # With 50% sampling and 1000 iterations, expect ~500 ± some variance
    # Allow 20% variance (400-600 range)
    assert 400 <= sampled_count <= 600


def test_disabled_tracing():
    """Test tracing can be completely disabled."""
    manager = TracingManager()
    manager.initialize(service_name="test", enabled=False, sample_rate=1.0)

    with manager.span("disabled_operation") as span:
        pass

    # No spans should be created
    assert len(manager._completed_spans) == 0


# ============================================================================
# SpanContext Tests
# ============================================================================


def test_span_context_creation():
    """Test SpanContext creation."""
    context = SpanContext(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
        sampled=True
    )

    assert context.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert context.span_id == "00f067aa0ba902b7"
    assert context.sampled is True


def test_span_context_to_traceparent():
    """Test SpanContext converts to W3C traceparent format."""
    context = SpanContext(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
        sampled=True
    )

    traceparent = context.to_traceparent()

    assert traceparent == "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"


def test_span_context_from_traceparent():
    """Test SpanContext parses W3C traceparent format."""
    traceparent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"

    context = SpanContext.from_traceparent(traceparent)

    assert context.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert context.span_id == "00f067aa0ba902b7"
    assert context.sampled is True


# ============================================================================
# Global Singleton Tests
# ============================================================================


def test_global_tracing_manager_singleton():
    """Test get_tracing_manager returns the same instance."""
    manager1 = get_tracing_manager()
    manager2 = get_tracing_manager()

    assert manager1 is manager2


def test_global_tracing_usage(global_tracing):
    """Test using the global tracing manager."""
    with global_tracing.span("global_test_operation") as span:
        trace_id = span.trace_id

    # Should be accessible from any call to get_tracing_manager()
    manager = get_tracing_manager()
    assert len(manager._completed_spans) > 0


# ============================================================================
# Performance Tests
# ============================================================================


def test_span_overhead():
    """Test that span creation overhead is minimal."""
    manager = TracingManager()
    manager.initialize(service_name="test", enabled=True, sample_rate=1.0)

    iterations = 1000

    # Measure with tracing
    start = time.perf_counter()
    for _ in range(iterations):
        with manager.span("perf_test"):
            pass
    end = time.perf_counter()
    with_tracing = (end - start) * 1000  # Convert to ms

    # Overhead should be reasonable (< 1ms per span on average)
    avg_overhead = with_tracing / iterations
    assert avg_overhead < 1.0  # Less than 1ms per span


def test_many_spans(tracing_manager):
    """Test creating many spans doesn't cause issues."""
    for i in range(100):
        with tracing_manager.span(f"operation_{i}") as span:
            span.add_event(f"Event {i}")

    assert len(tracing_manager._completed_spans) == 100


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_distributed_trace_workflow(tracing_manager):
    """Test a complete distributed tracing workflow."""
    # Service A: Start request
    with tracing_manager.span("frontend.render", attributes={"user.id": "123"}) as span_frontend:
        trace_id = span_frontend.trace_id
        span_frontend.add_event("Rendering started")

        # Make API call to backend
        headers = tracing_manager.inject_context({})

        # Service B: Receive request
        backend_context = tracing_manager.extract_context(headers)

        with tracing_manager.span("backend.api_call", parent_context=backend_context) as span_backend:
            assert span_backend.trace_id == trace_id
            span_backend.add_event("Processing request")

            # Call database
            with tracing_manager.span("database.query") as span_db:
                assert span_db.trace_id == trace_id
                assert span_db.parent_span_id == span_backend.span_id
                span_db.add_event("Query executed")

            span_backend.add_event("Request processed")

        span_frontend.add_event("Rendering completed")

    # Verify trace structure
    assert len(tracing_manager._completed_spans) == 3


def test_concurrent_traces():
    """Test multiple concurrent traces don't interfere."""
    manager = TracingManager()
    manager.initialize(service_name="test", enabled=True, sample_rate=1.0)

    trace_ids = set()

    # Create multiple independent traces
    for _ in range(10):
        with manager.span("concurrent_operation") as span:
            trace_ids.add(span.trace_id)
            time.sleep(0.001)

    # Each should have a unique trace_id
    assert len(trace_ids) == 10


def test_trace_with_metadata(tracing_manager):
    """Test span with rich metadata."""
    attributes = {
        "http.method": "POST",
        "http.url": "/api/orders",
        "http.status_code": 201,
        "order.id": "ORD-12345",
        "user.id": "USR-67890",
        "items.count": 3,
        "total.amount": 99.99
    }

    with tracing_manager.span("create_order", attributes=attributes) as span:
        span.add_event("Validation passed")
        span.add_event("Order created", {"order_id": "ORD-12345"})
        span.add_event("Email sent", {"recipient": "user@example.com"})

    assert span.attributes == attributes
    assert len(span.events) == 3


def test_export_spans(tracing_manager):
    """Test exporting spans for external systems (Jaeger, Zipkin, etc.)."""
    with tracing_manager.span("exportable_operation") as span:
        span.add_event("Test event")

    # Get completed spans
    completed = list(tracing_manager._completed_spans.values())
    assert len(completed) == 1

    exported_span = completed[0]
    assert exported_span.name == "exportable_operation"
    assert exported_span.trace_id is not None
    assert exported_span.duration_ms is not None
    assert len(exported_span.events) == 1
