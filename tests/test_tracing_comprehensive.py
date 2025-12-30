"""
Comprehensive tests for tracing system to increase coverage.

Tests additional tracing functionality including span error handling,
initialization, sampling, and context propagation edge cases.
"""

import pytest
import time
from unittest.mock import Mock, patch

from src.observability.tracing import (
    Span,
    SpanContext,
    SpanEvent,
    TracingManager,
    get_tracing_manager,
)


class TestSpanEvent:
    """Test SpanEvent class."""

    def test_span_event_creation(self):
        """Test creating a SpanEvent."""
        timestamp = time.time()
        event = SpanEvent(
            name="test_event",
            timestamp=timestamp,
            attributes={"key": "value"}
        )
        assert event.name == "test_event"
        assert event.timestamp == timestamp
        assert event.attributes == {"key": "value"}

    def test_span_event_default_attributes(self):
        """Test SpanEvent with default attributes."""
        event = SpanEvent(name="test_event", timestamp=time.time())
        assert event.attributes == {}


class TestSpan:
    """Test Span class additional functionality."""

    def test_span_duration_when_not_ended(self):
        """Test duration is 0 when span not ended."""
        span = Span(
            trace_id="trace1",
            span_id="span1",
            parent_span_id=None,
            name="test_span",
            start_time=time.time()
        )
        assert span.duration_ms == 0.0

    def test_span_error_message_property(self):
        """Test error_message property."""
        span = Span(
            trace_id="trace1",
            span_id="span1",
            parent_span_id=None,
            name="test_span",
            start_time=time.time()
        )
        span.set_status("error", "Test error message")
        assert span.error_message == "Test error message"

    def test_span_end_multiple_times(self):
        """Test ending a span multiple times doesn't change end_time."""
        span = Span(
            trace_id="trace1",
            span_id="span1",
            parent_span_id=None,
            name="test_span",
            start_time=time.time()
        )
        span.end()
        first_end_time = span.end_time
        time.sleep(0.01)
        span.end()  # Should not update
        assert span.end_time == first_end_time

    def test_span_to_dict_with_all_fields(self):
        """Test span to_dict includes all fields."""
        span = Span(
            trace_id="trace1",
            span_id="span1",
            parent_span_id="parent1",
            name="test_span",
            start_time=time.time(),
            attributes={"attr1": "value1"},
            status="error",
            status_message="Error occurred"
        )
        span.add_event("event1", {"event_attr": "value"})
        span.end()
        
        span_dict = span.to_dict()
        assert span_dict["trace_id"] == "trace1"
        assert span_dict["span_id"] == "span1"
        assert span_dict["parent_span_id"] == "parent1"
        assert span_dict["name"] == "test_span"
        assert span_dict["attributes"] == {"attr1": "value1"}
        assert span_dict["status"] == "error"
        assert span_dict["status_message"] == "Error occurred"
        assert len(span_dict["events"]) == 1
        assert span_dict["events"][0]["name"] == "event1"


class TestSpanContext:
    """Test SpanContext additional functionality."""

    def test_span_context_trace_flags_sampled(self):
        """Test trace_flags when sampled is True."""
        context = SpanContext(trace_id="trace1", span_id="span1", sampled=True)
        assert context.trace_flags == 1

    def test_span_context_trace_flags_not_sampled(self):
        """Test trace_flags when sampled is False."""
        context = SpanContext(trace_id="trace1", span_id="span1", sampled=False)
        assert context.trace_flags == 0

    def test_span_context_to_traceparent_not_sampled(self):
        """Test to_traceparent when not sampled."""
        context = SpanContext(trace_id="trace1", span_id="span1", sampled=False)
        traceparent = context.to_traceparent()
        assert traceparent.endswith("-00")

    def test_span_context_from_traceparent_invalid_format(self):
        """Test from_traceparent with invalid format."""
        context = SpanContext.from_traceparent("invalid-format")
        assert context is None

    def test_span_context_from_traceparent_wrong_version(self):
        """Test from_traceparent with wrong version."""
        context = SpanContext.from_traceparent("01-trace1-span1-01")
        assert context is None

    def test_span_context_from_traceparent_not_sampled(self):
        """Test from_traceparent when not sampled."""
        context = SpanContext.from_traceparent("00-trace1-span1-00")
        assert context is not None
        assert context.sampled is False


class TestTracingManagerInitialization:
    """Test TracingManager initialization."""

    def test_tracing_manager_initialization_default(self):
        """Test TracingManager with default initialization."""
        manager = TracingManager()
        assert manager._enabled is True
        assert manager._service_name == "mcp_game"
        assert manager._sample_rate == 1.0

    def test_tracing_manager_initialize(self):
        """Test explicit initialization."""
        manager = TracingManager()
        manager.initialize(
            service_name="test_service",
            enabled=True,
            sample_rate=0.5
        )
        assert manager._service_name == "test_service"
        assert manager._enabled is True
        assert manager._sample_rate == 0.5

    def test_tracing_manager_initialize_disabled(self):
        """Test initialization with tracing disabled."""
        manager = TracingManager()
        manager.initialize(enabled=False)
        assert manager._enabled is False

    def test_tracing_manager_enable_disable(self):
        """Test enable and disable methods."""
        manager = TracingManager()
        manager.disable()
        assert manager._enabled is False
        manager.enable()
        assert manager._enabled is True

    def test_tracing_manager_set_sample_rate(self):
        """Test setting sample rate."""
        manager = TracingManager()
        manager.set_sample_rate(0.25)
        assert manager._sample_rate == 0.25


class TestTracingManagerSpanCreation:
    """Test span creation with different scenarios."""

    def test_start_span_when_disabled(self):
        """Test starting span when tracing is disabled."""
        manager = TracingManager()
        manager.disable()
        
        with manager.start_span("test_span") as span:
            assert span is None

    def test_start_span_with_parent(self):
        """Test starting span with parent."""
        manager = TracingManager()
        manager.enable()
        manager.set_sample_rate(1.0)
        
        with manager.start_span("parent_span") as parent:
            if parent:
                with manager.start_span("child_span") as child:
                    if child:
                        assert child.parent_span_id == parent.span_id
                        assert child.trace_id == parent.trace_id

    def test_start_span_with_attributes(self):
        """Test starting span with attributes."""
        manager = TracingManager()
        manager.enable()
        manager.set_sample_rate(1.0)
        
        with manager.start_span("test_span", attributes={"key": "value"}) as span:
            if span:
                assert span.attributes["key"] == "value"

    def test_start_span_sampling_not_sampled(self):
        """Test span not created when not sampled."""
        manager = TracingManager()
        manager.enable()
        manager.set_sample_rate(0.0)  # Never sample
        
        with manager.start_span("test_span") as span:
            assert span is None


class TestTracingManagerAsyncSpan:
    """Test async span functionality."""

    @pytest.mark.asyncio
    async def test_start_span_async_basic(self):
        """Test async span creation."""
        manager = TracingManager()
        manager.enable()
        manager.set_sample_rate(1.0)
        
        async with manager.start_span_async("async_span") as span:
            if span:
                assert span.name == "async_span"
                assert span.end_time is None
        
        if span:
            assert span.end_time is not None

    @pytest.mark.asyncio
    async def test_start_span_async_with_exception(self):
        """Test async span with exception."""
        manager = TracingManager()
        manager.enable()
        manager.set_sample_rate(1.0)
        
        try:
            async with manager.start_span_async("async_span") as span:
                raise ValueError("Test error")
        except ValueError:
            pass
        
        if span:
            assert span.status == "error"
            assert "Test error" in span.status_message

    @pytest.mark.asyncio
    async def test_start_span_async_disabled(self):
        """Test async span when tracing disabled."""
        manager = TracingManager()
        manager.disable()
        
        async with manager.start_span_async("async_span") as span:
            assert span is None


class TestTracingManagerContextPropagation:
    """Test context propagation."""

    def test_inject_context_no_active_span(self):
        """Test injecting context with no active span."""
        manager = TracingManager()
        headers = {}
        manager.inject_context(headers)
        assert "traceparent" not in headers

    def test_inject_context_with_active_span(self):
        """Test injecting context with active span."""
        manager = TracingManager()
        manager.enable()
        manager.set_sample_rate(1.0)
        
        with manager.start_span("test_span") as span:
            headers = {}
            if span:
                manager.inject_context(headers)
                assert "traceparent" in headers

    def test_extract_context_no_header(self):
        """Test extracting context with no traceparent header."""
        manager = TracingManager()
        headers = {}
        context = manager.extract_context(headers)
        assert context is None

    def test_extract_context_with_header(self):
        """Test extracting context with valid traceparent."""
        manager = TracingManager()
        headers = {"traceparent": "00-trace123-span456-01"}
        context = manager.extract_context(headers)
        assert context is not None
        assert context.trace_id == "trace123"
        assert context.span_id == "span456"


class TestTracingManagerSpanExport:
    """Test span export functionality."""

    def test_export_spans_empty(self):
        """Test exporting when no spans."""
        manager = TracingManager()
        spans = manager.export_spans()
        assert spans == []

    def test_export_spans_with_data(self):
        """Test exporting spans."""
        manager = TracingManager()
        manager.enable()
        manager.set_sample_rate(1.0)
        
        with manager.start_span("span1"):
            pass
        
        with manager.start_span("span2"):
            pass
        
        spans = manager.export_spans()
        assert len(spans) >= 2

    def test_export_spans_clears_buffer(self):
        """Test that export clears the span buffer."""
        manager = TracingManager()
        manager.enable()
        manager.set_sample_rate(1.0)
        
        with manager.start_span("test_span"):
            pass
        
        first_export = manager.export_spans()
        second_export = manager.export_spans()
        
        assert len(first_export) >= 1
        assert len(second_export) == 0


class TestTracingManagerStatistics:
    """Test tracing statistics."""

    def test_get_stats_initial(self):
        """Test getting initial statistics."""
        manager = TracingManager()
        stats = manager.get_stats()
        assert "total_spans" in stats
        assert "active_spans" in stats
        assert "enabled" in stats

    def test_get_stats_after_spans(self):
        """Test statistics after creating spans."""
        manager = TracingManager()
        manager.enable()
        manager.set_sample_rate(1.0)
        
        with manager.start_span("span1"):
            pass
        
        stats = manager.get_stats()
        assert stats["total_spans"] >= 1


class TestTracingManagerReset:
    """Test resetting tracing manager."""

    def test_reset_clears_spans(self):
        """Test that reset clears all spans."""
        manager = TracingManager()
        manager.enable()
        manager.set_sample_rate(1.0)
        
        with manager.start_span("test_span"):
            pass
        
        manager.reset()
        spans = manager.export_spans()
        assert len(spans) == 0

    def test_reset_preserves_settings(self):
        """Test that reset preserves configuration."""
        manager = TracingManager()
        manager.initialize(service_name="test", sample_rate=0.5)
        
        manager.reset()
        
        assert manager._service_name == "test"
        assert manager._sample_rate == 0.5


class TestGlobalTracingManager:
    """Test global tracing manager singleton."""

    def test_get_tracing_manager_singleton(self):
        """Test that get_tracing_manager returns singleton."""
        manager1 = get_tracing_manager()
        manager2 = get_tracing_manager()
        assert manager1 is manager2


class TestTracingEndToEnd:
    """Test end-to-end tracing scenarios."""

    def test_distributed_trace_scenario(self):
        """Test a complete distributed trace scenario."""
        manager = TracingManager()
        manager.enable()
        manager.set_sample_rate(1.0)
        
        # Service A creates a span and propagates context
        with manager.start_span("service_a_operation") as span_a:
            if span_a:
                span_a.set_attribute("service", "A")
                
                # Inject context for service B
                headers = {}
                manager.inject_context(headers)
                
                # Simulate service B receiving the request
                context = manager.extract_context(headers)
                assert context is not None
                
                # Service B creates child span
                with manager.start_span("service_b_operation") as span_b:
                    if span_b:
                        span_b.set_attribute("service", "B")
                        assert span_b.trace_id == span_a.trace_id
                        assert span_b.parent_span_id == span_a.span_id

    def test_error_tracking_scenario(self):
        """Test error tracking through spans."""
        manager = TracingManager()
        manager.enable()
        manager.set_sample_rate(1.0)
        
        try:
            with manager.start_span("operation_with_error") as span:
                if span:
                    span.add_event("operation_started")
                    raise RuntimeError("Simulated error")
        except RuntimeError:
            pass
        
        if span:
            assert span.status == "error"
            assert span.end_time is not None

    def test_nested_spans_scenario(self):
        """Test deeply nested spans."""
        manager = TracingManager()
        manager.enable()
        manager.set_sample_rate(1.0)
        
        with manager.start_span("level_1") as span1:
            if span1:
                with manager.start_span("level_2") as span2:
                    if span2:
                        with manager.start_span("level_3") as span3:
                            if span3:
                                assert span3.parent_span_id == span2.span_id
                                assert span2.parent_span_id == span1.span_id
                                assert span1.trace_id == span2.trace_id == span3.trace_id

