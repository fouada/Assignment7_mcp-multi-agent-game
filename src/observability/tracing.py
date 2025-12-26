"""
Distributed Tracing System
===========================

OpenTelemetry-compatible distributed tracing for the MCP Game system.

Provides:
- TracingManager singleton for trace management
- Span creation and context propagation
- Trace ID injection/extraction for distributed calls
- Span attributes and events
- Integration with OpenTelemetry exporters

Usage:
    from src.observability.tracing import get_tracing_manager

    tracing = get_tracing_manager()
    tracing.initialize(service_name="mcp_game")

    # Create span
    with tracing.start_span("game_operation") as span:
        span.set_attribute("game_id", "game_001")
        span.add_event("Processing started")
        # Your code here
        span.add_event("Processing completed")
"""

import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Optional

from ..common.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# Span Types
# ============================================================================


@dataclass
class SpanEvent:
    """Event within a span."""

    name: str
    timestamp: float
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """
    Represents a single span in a trace.

    A span represents a unit of work with a start and end time.
    """

    trace_id: str
    span_id: str
    parent_span_id: str | None
    name: str
    start_time: float
    end_time: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    status: str = "ok"  # ok, error
    status_message: str = ""

    @property
    def error_message(self) -> str:
        """Get error message (alias for status_message)."""
        return self.status_message

    def set_attribute(self, key: str, value: Any) -> None:
        """Set span attribute."""
        self.attributes[key] = value

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """Add event to span."""
        event = {
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {},
        }
        self.events.append(event)

    def set_status(self, status: str, message: str = "") -> None:
        """Set span status (ok or error)."""
        self.status = status
        self.status_message = message

    def end(self) -> None:
        """End the span."""
        if self.end_time is None:
            self.end_time = time.time()

    @property
    def duration_ms(self) -> float:
        """Get span duration in milliseconds."""
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000

    def to_dict(self) -> dict[str, Any]:
        """Convert span to dictionary."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "events": self.events,
            "status": self.status,
            "status_message": self.status_message,
        }


@dataclass
class SpanContext:
    """
    Context for a span.

    Used for propagating trace context across service boundaries.
    """

    trace_id: str
    span_id: str
    sampled: bool = True

    @property
    def trace_flags(self) -> int:
        """Get trace flags (1 if sampled, 0 otherwise)."""
        return 1 if self.sampled else 0

    def to_traceparent(self) -> str:
        """
        Convert to W3C traceparent header format.

        Format: version-trace_id-span_id-trace_flags
        Example: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
        """
        flags = "01" if self.sampled else "00"
        return f"00-{self.trace_id}-{self.span_id}-{flags}"

    @classmethod
    def from_traceparent(cls, traceparent: str) -> Optional["SpanContext"]:
        """
        Parse W3C traceparent header.

        Args:
            traceparent: Header value (e.g., "00-trace_id-span_id-01")

        Returns:
            SpanContext or None if invalid
        """
        try:
            parts = traceparent.split("-")
            if len(parts) != 4:
                return None

            version, trace_id, span_id, trace_flags = parts

            if version != "00":
                return None

            sampled = int(trace_flags, 16) == 1

            return cls(
                trace_id=trace_id,
                span_id=span_id,
                sampled=sampled,
            )
        except Exception as e:
            logger.error(f"Failed to parse traceparent: {e}")
            return None


# ============================================================================
# Tracing Manager
# ============================================================================


class TracingManager:
    """
    Centralized tracing manager (Singleton).

    Manages trace creation, span lifecycle, and context propagation.
    Thread-safe for concurrent tracing operations.
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

        self._service_name = "mcp_game"
        self._enabled = True
        self._sample_rate = 1.0  # Sample all traces by default

        # Thread-local storage for current span
        self._current_span = threading.local()

        # Active and completed spans tracking
        self._active_spans: dict[str, Span] = {}
        self._completed_spans: dict[str, Span] = {}
        self._span_lock = threading.Lock()

        # Statistics
        self._stats = {
            "total_spans": 0,
            "sampled_spans": 0,
            "dropped_spans": 0,
        }

        self._initialized = True
        logger.info("Tracing manager initialized")

    @property
    def enabled(self) -> bool:
        """Whether tracing is enabled."""
        return bool(self._enabled)

    @property
    def sample_rate(self) -> float:
        """Current sampling rate."""
        return float(self._sample_rate)

    @property
    def service_name(self) -> str:
        """Service name."""
        return str(self._service_name)

    def initialize(
        self,
        service_name: str = "mcp_game",
        enabled: bool = True,
        sample_rate: float = 1.0,
    ) -> None:
        """
        Initialize tracing configuration.

        Args:
            service_name: Name of the service
            enabled: Whether tracing is enabled
            sample_rate: Sampling rate (0.0 to 1.0)
        """
        self._service_name = service_name
        self._enabled = enabled
        self._sample_rate = max(0.0, min(1.0, sample_rate))

        # Reset state on initialization
        with self._span_lock:
            self._active_spans.clear()
            self._completed_spans.clear()

        logger.info(
            f"Tracing initialized: service={service_name}, "
            f"enabled={enabled}, sample_rate={sample_rate}"
        )

    def generate_trace_id(self) -> str:
        """Generate a new trace ID (32 hex characters)."""
        return uuid.uuid4().hex

    def generate_span_id(self) -> str:
        """Generate a new span ID (16 hex characters)."""
        return uuid.uuid4().hex[:16]

    def should_sample(self) -> bool:
        """Determine if this trace should be sampled."""
        import random

        return bool(random.random() < self._sample_rate)

    def start_span(
        self,
        name: str,
        parent_context: SpanContext | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Span | None:
        """
        Start a new span.

        Args:
            name: Span name
            parent_context: Parent span context (for distributed tracing)
            attributes: Initial span attributes

        Returns:
            New span or None if tracing is disabled or not sampled
        """
        if not self._enabled:
            # Return None for disabled tracing
            return None

        # Check sampling
        if not self.should_sample():
            self._stats["dropped_spans"] += 1
            return None

        # Get trace ID and parent info
        if parent_context:
            trace_id = parent_context.trace_id
            parent_span_id = parent_context.span_id
        else:
            # Check if there's a current span (for nested spans)
            current = self.get_current_span()
            if current and current.trace_id:
                trace_id = current.trace_id
                parent_span_id = current.span_id
            else:
                trace_id = self.generate_trace_id()
                parent_span_id = None

        # Create span
        span = Span(
            trace_id=trace_id,
            span_id=self.generate_span_id(),
            parent_span_id=parent_span_id,
            name=name,
            start_time=time.time(),
            attributes=attributes or {},
        )

        # Add service name
        span.set_attribute("service.name", self._service_name)

        # Track active span
        with self._span_lock:
            self._active_spans[span.span_id] = span

        # Set as current span
        self._set_current_span(span)

        self._stats["total_spans"] += 1
        self._stats["sampled_spans"] += 1

        logger.debug(f"Started span: {name} (trace_id={trace_id[:8]}...)")

        return span

    def end_span(self, span: Span | None) -> None:
        """
        End a span and store it.

        Args:
            span: Span to end (or None if not sampled)
        """
        if span is None or not span.trace_id:
            return

        # End span
        span.end()

        # Move from active to completed
        with self._span_lock:
            if span.span_id in self._active_spans:
                del self._active_spans[span.span_id]
            self._completed_spans[span.span_id] = span

        # Clear current span if it matches
        current = self.get_current_span()
        if current and current.span_id == span.span_id:
            # Restore parent span if any
            if span.parent_span_id and span.parent_span_id in self._active_spans:
                self._set_current_span(self._active_spans[span.parent_span_id])
            else:
                self._set_current_span(None)

        logger.debug(
            f"Ended span: {span.name} "
            f"(duration={span.duration_ms:.2f}ms, "
            f"trace_id={span.trace_id[:8]}...)"
        )

    @contextmanager
    def span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
        parent_context: SpanContext | None = None,
    ):
        """
        Context manager for creating spans.

        Usage:
            with tracing.span("operation") as span:
                if span:  # Check if span was created (sampling/enabled)
                    span.set_attribute("key", "value")
                # Your code here

        Args:
            name: Span name
            attributes: Initial span attributes
            parent_context: Parent span context (for distributed tracing)
        """
        span = self.start_span(name, parent_context=parent_context, attributes=attributes)
        try:
            yield span
        except Exception as e:
            if span:
                span.set_status("error", str(e))
            raise
        finally:
            if span:
                self.end_span(span)

    def get_current_span(self) -> Span | None:
        """Get the current span for this thread."""
        return getattr(self._current_span, "span", None)

    def _set_current_span(self, span: Span | None) -> None:
        """Set the current span for this thread."""
        self._current_span.span = span

    def _create_noop_span(self, name: str) -> Span:
        """Create a no-op span (not recorded)."""
        return Span(
            trace_id="",
            span_id="",
            parent_span_id=None,
            name=name,
            start_time=time.time(),
        )

    # ========================================================================
    # Context Propagation
    # ========================================================================

    def inject_context(self, headers: dict[str, str]) -> dict[str, str]:
        """
        Inject trace context into headers for distributed tracing.

        Args:
            headers: HTTP headers dictionary

        Returns:
            Headers with injected trace context
        """
        current_span = self.get_current_span()
        if not current_span or not current_span.trace_id:
            return headers

        # Create span context
        context = SpanContext(
            trace_id=current_span.trace_id,
            span_id=current_span.span_id,
        )

        # Inject W3C traceparent header
        headers["traceparent"] = context.to_traceparent()

        return headers

    def extract_context(self, headers: dict[str, str]) -> SpanContext | None:
        """
        Extract trace context from headers.

        Args:
            headers: HTTP headers dictionary

        Returns:
            SpanContext or None if not found
        """
        # Try W3C traceparent header (case-insensitive)
        traceparent = None
        for key, value in headers.items():
            if key.lower() == "traceparent":
                traceparent = value
                break

        if not traceparent:
            return None

        return SpanContext.from_traceparent(traceparent)

    # ========================================================================
    # Export and Statistics
    # ========================================================================

    def get_completed_spans(self, clear: bool = True) -> list[Span]:
        """
        Get all completed spans.

        Args:
            clear: Whether to clear the spans after retrieving

        Returns:
            List of completed spans
        """
        with self._span_lock:
            spans = list(self._completed_spans.values())
            if clear:
                self._completed_spans.clear()
            return spans

    def export_spans_json(self, clear: bool = True) -> list[dict[str, Any]]:
        """
        Export completed spans as JSON-serializable list.

        Args:
            clear: Whether to clear spans after export

        Returns:
            List of span dictionaries
        """
        spans = self.get_completed_spans(clear=clear)
        return [span.to_dict() for span in spans]

    def get_statistics(self) -> dict[str, Any]:
        """Get tracing statistics."""
        return {
            **self._stats,
            "pending_spans": len(self._completed_spans),
            "sample_rate": self._sample_rate,
            "enabled": self._enabled,
        }

    def reset(self) -> None:
        """Reset tracing state (for testing)."""
        with self._span_lock:
            self._active_spans.clear()
            self._completed_spans.clear()

        self._stats = {
            "total_spans": 0,
            "sampled_spans": 0,
            "dropped_spans": 0,
        }

        logger.info("Tracing reset")


# ============================================================================
# Singleton Access
# ============================================================================


def get_tracing_manager() -> TracingManager:
    """Get the tracing manager singleton."""
    return TracingManager()


# ============================================================================
# Decorator for Automatic Tracing
# ============================================================================


def trace_function(name: str | None = None, attributes: dict[str, Any] | None = None):
    """
    Decorator to automatically trace a function.

    Usage:
        @trace_function("my_operation")
        async def my_function(arg1, arg2):
            # Your code here
            pass
    """

    def decorator(func):
        import functools
        import inspect

        span_name = name or f"{func.__module__}.{func.__name__}"

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                tracing = get_tracing_manager()
                with tracing.span(span_name, attributes=attributes) as span:
                    # Add function arguments as attributes
                    span.set_attribute("function", func.__name__)
                    return await func(*args, **kwargs)

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                tracing = get_tracing_manager()
                with tracing.span(span_name, attributes=attributes) as span:
                    # Add function arguments as attributes
                    span.set_attribute("function", func.__name__)
                    return func(*args, **kwargs)

            return sync_wrapper

    return decorator


# ============================================================================
# Example Usage
# ============================================================================


async def example_usage():
    """Demonstrate tracing usage."""
    tracing = get_tracing_manager()
    tracing.initialize(service_name="mcp_game", sample_rate=1.0)

    # Create a span
    with tracing.span("game_operation") as span:
        span.set_attribute("game_id", "game_001")
        span.set_attribute("player_count", 2)
        span.add_event("Game started")

        # Simulate work
        time.sleep(0.1)

        # Create child span
        with tracing.span("player_move") as child_span:
            child_span.set_attribute("player_id", "player_001")
            child_span.add_event("Move calculated")
            time.sleep(0.05)

        span.add_event("Game completed")

    # Get completed spans
    spans = tracing.export_spans_json()
    print(f"Exported {len(spans)} spans")

    # Context propagation example
    headers = {}
    headers = tracing.inject_context(headers)
    print(f"Injected traceparent: {headers.get('traceparent')}")

    # Extract context
    context = tracing.extract_context(headers)
    if context:
        print(f"Extracted trace_id: {context.trace_id}")

    # Statistics
    stats = tracing.get_statistics()
    print(f"Tracing stats: {stats}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(example_usage())
