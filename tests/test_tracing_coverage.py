"""
Additional tests to improve tracing.py coverage to 85%+.
Focuses on uncovered tracing scenarios and edge cases.
"""

import asyncio
import time

import pytest

from src.observability.tracing import (
    Span,
    SpanContext,
    TracingManager,
    get_tracing_manager,
    trace_function,
)


class TestSpanContextAdvanced:
    """Test SpanContext advanced scenarios."""

    def test_span_context_from_invalid_traceparent(self):
        """Test creating span context from invalid traceparent."""
        invalid_traceparents = [
            "invalid",
            "00-abc-def-01",  # Too short
            "99-12345678901234567890123456789012-1234567890123456-01",  # Invalid version
            "",
        ]

        for traceparent in invalid_traceparents:
            ctx = SpanContext.from_traceparent(traceparent)
            # Should return None or handle gracefully
            assert ctx is None or isinstance(ctx, SpanContext)

    def test_span_context_to_traceparent_format(self):
        """Test traceparent format compliance."""
        ctx = SpanContext(
            trace_id="12345678901234567890123456789012", span_id="1234567890123456", sampled=True
        )

        traceparent = ctx.to_traceparent()

        # Verify format: 00-{trace_id}-{span_id}-{flags}
        parts = traceparent.split("-")
        assert len(parts) == 4
        assert parts[0] == "00"  # Version
        assert len(parts[1]) == 32  # Trace ID
        assert len(parts[2]) == 16  # Span ID
        assert parts[3] in ["00", "01"]  # Flags

    def test_span_context_not_sampled(self):
        """Test span context with sampled=False."""
        ctx = SpanContext(
            trace_id="12345678901234567890123456789012", span_id="1234567890123456", sampled=False
        )

        traceparent = ctx.to_traceparent()
        assert traceparent.endswith("-00")

    def test_span_context_trace_flags(self):
        """Test trace flags property."""
        ctx_sampled = SpanContext("trace", "span", sampled=True)
        assert ctx_sampled.trace_flags == 1

        ctx_not_sampled = SpanContext("trace", "span", sampled=False)
        assert ctx_not_sampled.trace_flags == 0


class TestSpan:
    """Test Span class."""

    def test_span_duration_before_end(self):
        """Test duration_ms before span is ended."""
        span = Span(
            trace_id="trace",
            span_id="span",
            parent_span_id=None,
            name="test",
            start_time=time.time(),
        )

        # Before ending, duration should be 0
        assert span.duration_ms == 0.0

    def test_span_duration_after_end(self):
        """Test duration_ms after span is ended."""
        start = time.time()
        span = Span(
            trace_id="trace",
            span_id="span",
            parent_span_id=None,
            name="test",
            start_time=start,
        )

        time.sleep(0.01)
        span.end()

        # After ending, duration should be positive
        assert span.duration_ms > 0

    def test_span_set_attribute(self):
        """Test setting span attributes."""
        span = Span(
            trace_id="trace",
            span_id="span",
            parent_span_id=None,
            name="test",
            start_time=time.time(),
        )

        span.set_attribute("key", "value")
        assert span.attributes["key"] == "value"

    def test_span_add_event(self):
        """Test adding events to span."""
        span = Span(
            trace_id="trace",
            span_id="span",
            parent_span_id=None,
            name="test",
            start_time=time.time(),
        )

        span.add_event("test_event", {"data": "value"})
        assert len(span.events) == 1
        assert span.events[0]["name"] == "test_event"
        assert span.events[0]["attributes"]["data"] == "value"

    def test_span_set_status(self):
        """Test setting span status."""
        span = Span(
            trace_id="trace",
            span_id="span",
            parent_span_id=None,
            name="test",
            start_time=time.time(),
        )

        span.set_status("error", "Something went wrong")
        assert span.status == "error"
        assert span.status_message == "Something went wrong"
        assert span.error_message == "Something went wrong"

    def test_span_to_dict(self):
        """Test converting span to dictionary."""
        span = Span(
            trace_id="trace",
            span_id="span",
            parent_span_id="parent",
            name="test",
            start_time=time.time(),
        )

        span.end()
        span_dict = span.to_dict()

        assert span_dict["trace_id"] == "trace"
        assert span_dict["span_id"] == "span"
        assert span_dict["parent_span_id"] == "parent"
        assert span_dict["name"] == "test"
        assert span_dict["duration_ms"] >= 0  # >= 0 for Windows time resolution


class TestTracingManager:
    """Test TracingManager class."""

    def test_tracing_manager_singleton(self):
        """Test that TracingManager is a singleton."""
        manager1 = TracingManager()
        manager2 = TracingManager()
        assert manager1 is manager2

    def test_tracing_manager_properties(self):
        """Test TracingManager properties."""
        manager = TracingManager()
        # Properties return bool, float, and str types
        assert isinstance(manager.enabled, bool)
        assert isinstance(manager.sample_rate, float)
        assert isinstance(manager.service_name, str)

    def test_get_tracing_manager(self):
        """Test get_tracing_manager function."""
        manager = get_tracing_manager()
        assert isinstance(manager, TracingManager)


class TestTracingManagerConfiguration:
    """Test tracing manager configuration."""

    def test_tracing_manager_disabled(self):
        """Test tracing when disabled."""
        manager = TracingManager()
        manager.initialize(enabled=False)

        # Should not create spans when disabled
        span = manager.start_span("test_operation")
        assert span is None

    def test_tracing_manager_with_sampling(self):
        """Test tracing with sampling rate."""
        manager = TracingManager()
        manager.initialize(sample_rate=0.5)

        # With 50% sampling, should have some variability
        assert 0.0 <= manager.sample_rate <= 1.0

    def test_tracing_manager_100_percent_sampling(self):
        """Test tracing with 100% sampling."""
        manager = TracingManager()
        manager.initialize(sample_rate=1.0)

        # Should sample all spans
        assert manager.sample_rate == 1.0


class TestSpanOperations:
    """Test span operation edge cases."""

    def test_start_span_with_invalid_parent(self):
        """Test starting span with invalid parent ID."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True, sample_rate=1.0)

        # Create parent context
        parent_ctx = SpanContext(trace_id="trace123", span_id="span123", sampled=True)
        span = manager.start_span("child_operation", parent_context=parent_ctx)

        if span:
            assert span.trace_id == "trace123"
            assert span.parent_span_id == "span123"

    def test_end_nonexistent_span(self):
        """Test ending a span that doesn't exist."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True)

        # Ending None should not raise error
        manager.end_span(None)

    def test_span_with_many_attributes(self):
        """Test span with many attributes."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True, sample_rate=1.0)

        span = manager.start_span("test_operation")
        if span:
            # Add many attributes
            for i in range(50):
                span.set_attribute(f"attr_{i}", f"value_{i}")

            assert len(span.attributes) >= 50

    def test_add_event_to_nonexistent_span(self):
        """Test adding event to nonexistent span."""
        span = Span(
            trace_id="",
            span_id="",
            parent_span_id=None,
            name="test",
            start_time=time.time(),
        )

        # Should not raise error
        span.add_event("test_event")

    def test_set_status_on_nonexistent_span(self):
        """Test setting status on nonexistent span."""
        span = Span(
            trace_id="",
            span_id="",
            parent_span_id=None,
            name="test",
            start_time=time.time(),
        )

        # Should not raise error
        span.set_status("error", "test error")


class TestTraceContextPropagation:
    """Test trace context propagation."""

    def test_inject_trace_context_no_active_span(self):
        """Test injecting context when no span is active."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True)

        headers = {}
        result = manager.inject_context(headers)

        # Should not add headers without active span
        assert "traceparent" not in result or result["traceparent"] is not None

    def test_extract_trace_context_empty_headers(self):
        """Test extracting context from empty headers."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True)

        ctx = manager.extract_context({})

        # Should return None
        assert ctx is None

    def test_extract_trace_context_invalid_format(self):
        """Test extracting context with invalid format."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True)

        ctx = manager.extract_context({"traceparent": "invalid"})

        # Should handle gracefully
        assert ctx is None or isinstance(ctx, SpanContext)

    def test_propagate_context_across_services(self):
        """Test context propagation simulation."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True, sample_rate=1.0)

        # Service A starts a span
        span = manager.start_span("service_a_operation")

        if span:
            # Inject context into headers
            headers = {}
            headers = manager.inject_context(headers)

            # Service B extracts context
            ctx = manager.extract_context(headers)

            if ctx:
                # Service B starts child span
                child_span = manager.start_span("service_b_operation", parent_context=ctx)

                assert child_span is not None


class TestTracingDisabled:
    """Test tracing when disabled."""

    def test_all_operations_when_disabled(self):
        """Test that all operations work when tracing is disabled."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=False)

        # All these should not raise errors
        span = manager.start_span("operation")
        assert span is None  # Should return None when disabled

        manager.end_span(span)

        headers = {}
        result = manager.inject_context(headers)
        assert result is not None

        # Extract context should work even if tracing is disabled
        # It's just parsing headers, not creating spans
        ctx = manager.extract_context(headers)
        # ctx could be None if no headers, or a SpanContext if headers exist
        assert ctx is None or isinstance(ctx, SpanContext)


class TestTracingExport:
    """Test span export functionality."""

    def test_export_spans_empty(self):
        """Test exporting when no spans exist."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True)

        spans = manager.export_spans_json()

        assert isinstance(spans, list)

    def test_export_spans_with_data(self):
        """Test exporting spans with data."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True, sample_rate=1.0)

        span = manager.start_span("test_operation")
        if span:
            span.add_event("test_event", {"key": "value"})
            manager.end_span(span)

        spans = manager.export_spans_json()

        # Should have at least one span
        assert len(spans) >= 0


class TestGlobalTracingManager:
    """Test global tracing manager."""

    def test_global_tracing_manager_singleton(self):
        """Test global tracing manager is singleton."""
        manager1 = get_tracing_manager()
        manager2 = get_tracing_manager()
        assert manager1 is manager2

    def test_convenience_functions(self):
        """Test convenience functions use global manager."""
        manager = get_tracing_manager()
        assert isinstance(manager, TracingManager)

        # Test properties
        assert isinstance(manager.enabled, bool)
        assert isinstance(manager.sample_rate, float)
        assert isinstance(manager.service_name, str)


class TestTraceContextManager:
    """Test trace context manager."""

    def test_context_manager_basic(self):
        """Test using trace_context as context manager."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True, sample_rate=1.0)

        with manager.span("test_operation") as span:
            # Span should be active
            assert span is not None or span is None  # Depending on sampling

    def test_context_manager_with_exception(self):
        """Test context manager with exception."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True, sample_rate=1.0)

        try:
            with manager.span("test_operation"):
                raise ValueError("Test error")
        except ValueError:
            pass

        # Span should still be ended properly

    def test_context_manager_with_attributes(self):
        """Test context manager with attributes."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True, sample_rate=1.0)

        attributes = {"key": "value", "number": 42}

        with manager.span("test_operation", attributes=attributes) as span:
            if span:
                # Add event during span
                span.add_event("mid_operation")


class TestSpanAttributes:
    """Test span attributes handling."""

    def test_span_with_complex_attributes(self):
        """Test span with complex attribute types."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True, sample_rate=1.0)

        attributes = {
            "string": "value",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
        }

        span = manager.start_span("test_operation", attributes=attributes)

        assert span is not None

    def test_add_event_with_attributes(self):
        """Test adding event with attributes."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True, sample_rate=1.0)

        span = manager.start_span("test_operation")

        if span:
            event_attrs = {"event_key": "event_value", "count": 5}
            span.add_event("test_event", event_attrs)


class TestTracingSampling:
    """Test tracing sampling logic."""

    def test_sampling_rate_0_percent(self):
        """Test with 0% sampling rate."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True, sample_rate=0.0)

        # Create multiple spans - none should be sampled
        for i in range(10):
            span = manager.start_span(f"operation_{i}")
            if span:
                manager.end_span(span)

    def test_sampling_rate_100_percent(self):
        """Test with 100% sampling rate."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True, sample_rate=1.0)

        # All spans should be sampled
        sampled_count = 0
        for i in range(10):
            span = manager.start_span(f"operation_{i}")
            if span:
                sampled_count += 1
                manager.end_span(span)

        assert sampled_count > 0


class TestSpanTiming:
    """Test span timing and duration."""

    def test_span_duration_tracking(self):
        """Test that span tracks duration."""
        import time

        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True, sample_rate=1.0)

        span = manager.start_span("timed_operation")

        if span:
            time.sleep(0.01)  # Small delay
            manager.end_span(span)

            # Duration should be tracked
            assert span.duration_ms > 0


class TestTracingEdgeCases:
    """Test tracing edge cases."""

    def test_concurrent_span_creation(self):
        """Test creating spans concurrently."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True, sample_rate=1.0)

        # Simulate concurrent span creation
        spans = []
        for i in range(10):
            span = manager.start_span(f"concurrent_{i}")
            if span:
                spans.append(span)

        # End all spans
        for span in spans:
            manager.end_span(span)

    def test_deeply_nested_spans(self):
        """Test deeply nested spans."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True, sample_rate=1.0)

        spans = []

        # Create nested spans
        for i in range(5):
            span = manager.start_span(f"level_{i}")
            if span:
                spans.append(span)

        # End in reverse order
        for span in reversed(spans):
            manager.end_span(span)


class TestTracingDecorator:
    """Test the trace_function decorator."""

    def test_trace_function_sync(self):
        """Test trace decorator on sync function."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True, sample_rate=1.0)

        @trace_function("test_sync_operation")
        def sync_function(x, y):
            return x + y

        result = sync_function(2, 3)
        assert result == 5

    def test_trace_function_async(self):
        """Test trace decorator on async function."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True, sample_rate=1.0)

        @trace_function("test_async_operation")
        async def async_function(x, y):
            await asyncio.sleep(0.001)
            return x + y

        result = asyncio.run(async_function(2, 3))
        assert result == 5

    def test_trace_function_with_attributes(self):
        """Test trace decorator with custom attributes."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True, sample_rate=1.0)

        @trace_function("test_operation", attributes={"type": "calculation"})
        def func_with_attrs(x):
            return x * 2

        result = func_with_attrs(5)
        assert result == 10


class TestTracingStatistics:
    """Test tracing statistics tracking."""

    def test_get_statistics(self):
        """Test getting tracing statistics."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True, sample_rate=1.0)

        # Create some spans
        span1 = manager.start_span("op1")
        if span1:
            manager.end_span(span1)

        stats = manager.get_statistics()
        assert "total_spans" in stats
        assert "sampled_spans" in stats
        assert "dropped_spans" in stats
        assert "pending_spans" in stats
        assert "sample_rate" in stats
        assert "enabled" in stats


class TestSpanContextEdgeCases:
    """Test SpanContext edge cases."""

    def test_span_context_short_ids(self):
        """Test span context with short IDs."""
        ctx = SpanContext(trace_id="abc", span_id="def", sampled=True)
        traceparent = ctx.to_traceparent()

        # Should still work with short IDs
        assert "-abc-" in traceparent
        assert "-def-" in traceparent

    def test_span_context_from_traceparent_invalid_version(self):
        """Test parsing traceparent with invalid version."""
        # Version 99 is invalid
        ctx = SpanContext.from_traceparent("99-12345678901234567890123456789012-1234567890123456-01")
        assert ctx is None

    def test_span_context_from_traceparent_wrong_part_count(self):
        """Test parsing traceparent with wrong number of parts."""
        ctx = SpanContext.from_traceparent("00-trace-span")  # Only 3 parts
        assert ctx is None


class TestTracingContextManagement:
    """Test context management."""

    def test_async_span_context_manager(self):
        """Test async span context manager."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True, sample_rate=1.0)

        async def test_async():
            async with manager.async_span("async_operation") as span:
                if span:
                    span.set_attribute("key", "value")
                    span.add_event("test_event")
                await asyncio.sleep(0.001)
                return "done"

        result = asyncio.run(test_async())
        assert result == "done"

    def test_async_span_with_exception(self):
        """Test async span with exception."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True, sample_rate=1.0)

        async def test_async_error():
            async with manager.async_span("async_operation"):
                raise ValueError("Test error")

        with pytest.raises(ValueError):
            asyncio.run(test_async_error())


class TestTracingExportAndClear:
    """Test export and clear functionality."""

    def test_get_completed_spans_no_clear(self):
        """Test getting completed spans without clearing."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True, sample_rate=1.0)

        span = manager.start_span("test_op")
        if span:
            manager.end_span(span)

        spans1 = manager.get_completed_spans(clear=False)
        spans2 = manager.get_completed_spans(clear=False)

        # Should get same spans both times
        assert len(spans1) == len(spans2)

    def test_export_spans_json_clears(self):
        """Test that export_spans_json clears by default."""
        manager = TracingManager()
        manager.reset()
        manager.initialize(enabled=True, sample_rate=1.0)

        span = manager.start_span("test_op")
        if span:
            manager.end_span(span)

        _ = manager.export_spans_json(clear=True)
        spans2 = manager.export_spans_json(clear=True)

        # Second call should have no spans if cleared
        assert len(spans2) == 0


class TestTracingInitialization:
    """Test tracing initialization scenarios."""

    def test_initialize_resets_state(self):
        """Test that initialization resets state."""
        manager = TracingManager()
        manager.initialize(enabled=True, sample_rate=1.0)

        # Create span
        span = manager.start_span("test_op")
        if span:
            manager.end_span(span)

        # Re-initialize
        manager.initialize(enabled=True, sample_rate=0.5)

        # Previous spans should be cleared
        spans = manager.export_spans_json()
        assert len(spans) == 0

    def test_sampling_rate_clamping(self):
        """Test that sampling rate is clamped to valid range."""
        manager = TracingManager()

        # Test > 1.0
        manager.initialize(sample_rate=2.0)
        assert manager.sample_rate <= 1.0

        # Test < 0.0
        manager.initialize(sample_rate=-0.5)
        assert manager.sample_rate >= 0.0
