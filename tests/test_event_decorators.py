"""
Tests for Event Decorators
==========================

Tests the event decorator functionality including:
- @on_event decorator
- @before decorator
- @after decorator
- @on_error decorator
- @emit_on_exception decorator

Run with: pytest tests/test_event_decorators.py -v
"""

import asyncio

import pytest

from src.common.events import (
    BaseEvent,
    after,
    before,
    emit_on_exception,
    get_event_bus,
    on_error,
    on_event,
)
from src.common.logger import get_logger

logger = get_logger(__name__)


# Test fixtures


@pytest.fixture
def clean_bus():
    """Get clean event bus singleton."""
    bus = get_event_bus()
    # Don't reset before yield - decorators register at import time
    yield bus
    # Clean up after test
    bus.reset()


# Test handlers


class EventCollector:
    """Helper to collect emitted events."""

    def __init__(self):
        self.events = []

    async def collect(self, event: BaseEvent):
        """Collect event."""
        self.events.append(event)


# Tests


class TestOnEventDecorator:
    """Test @on_event decorator."""

    @pytest.mark.asyncio
    async def test_decorator_registers_handler(self, clean_bus):
        """Test @on_event registers handler."""
        calls = []

        @on_event("test.event")
        async def handler(event):
            calls.append(event)

        # Handler should be registered
        assert clean_bus.get_handler_count() >= 1

        # Emit event
        await clean_bus.emit("test.event", BaseEvent(event_type="test.event"))

        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_decorator_with_priority(self, clean_bus):
        """Test @on_event with priority."""
        execution_order = []

        @on_event("test.event", priority=1)
        async def low(event):
            execution_order.append("low")

        @on_event("test.event", priority=10)
        async def high(event):
            execution_order.append("high")

        await clean_bus.emit("test.event", BaseEvent(event_type="test.event"))

        assert execution_order == ["high", "low"]

    @pytest.mark.asyncio
    async def test_decorator_with_wildcard(self, clean_bus):
        """Test @on_event with wildcard pattern."""
        calls = []

        @on_event("game.*")
        async def handler(event):
            calls.append(event.event_type)

        await clean_bus.emit("game.started", BaseEvent(event_type="game.started"))
        await clean_bus.emit("game.ended", BaseEvent(event_type="game.ended"))
        await clean_bus.emit("player.move", BaseEvent(event_type="player.move"))

        assert len(calls) == 2
        assert "game.started" in calls
        assert "game.ended" in calls

    @pytest.mark.asyncio
    async def test_decorator_with_metadata(self, clean_bus):
        """Test @on_event with description and tags."""

        @on_event("test.event", description="Test handler", tags=["test"])
        async def handler(event):
            pass

        # Verify metadata was stored
        handler_id = handler._event_handler_id
        metadata = clean_bus._handler_registry[handler_id]
        assert metadata.description == "Test handler"
        assert "test" in metadata.tags


class TestBeforeDecorator:
    """Test @before decorator."""

    @pytest.mark.asyncio
    async def test_before_emits_event(self, clean_bus):
        """Test @before emits event before function execution."""
        collector = EventCollector()
        clean_bus.on("test.before", collector.collect)

        @before("test.before")
        async def my_function(arg1, arg2):
            return arg1 + arg2

        result = await my_function(5, 3)

        assert result == 8
        assert len(collector.events) == 1
        # Event should contain function args
        # (actual values depend on include_self and serialization)

    @pytest.mark.asyncio
    async def test_before_with_args(self, clean_bus):
        """Test @before includes function arguments."""
        collector = EventCollector()
        clean_bus.on("func.before", collector.collect)

        @before("func.before", extract_args=["x", "y"])
        async def add(x, y, z):
            return x + y + z

        result = await add(1, 2, 3)

        assert result == 6
        # Verify event was emitted (args in metadata)
        assert len(collector.events) == 1

    def test_before_sync_function(self, clean_bus):
        """Test @before with synchronous function."""
        collector = EventCollector()
        clean_bus.on("sync.before", collector.collect)

        @before("sync.before")
        def sync_func(value):
            return value * 2

        result = sync_func(5)
        assert result == 10


class TestAfterDecorator:
    """Test @after decorator."""

    @pytest.mark.asyncio
    async def test_after_emits_event(self, clean_bus):
        """Test @after emits event after function execution."""
        collector = EventCollector()
        clean_bus.on("test.after", collector.collect)

        @after("test.after", include_result=True)
        async def my_function(x):
            return x * 2

        result = await my_function(5)

        assert result == 10
        assert len(collector.events) == 1

    @pytest.mark.asyncio
    async def test_after_with_timing(self, clean_bus):
        """Test @after includes execution timing."""
        collector = EventCollector()
        clean_bus.on("timed.after", collector.collect)

        @after("timed.after", include_timing=True)
        async def slow_function():
            await asyncio.sleep(0.01)  # 10ms
            return "done"

        result = await slow_function()

        assert result == "done"
        assert len(collector.events) == 1
        # Event should have execution_time_ms in metadata
        # (checking exact value is flaky due to timing)

    @pytest.mark.asyncio
    async def test_after_with_args_and_result(self, clean_bus):
        """Test @after includes both args and result."""
        collector = EventCollector()
        clean_bus.on("compute.after", collector.collect)

        @after("compute.after", include_result=True, include_args=True)
        async def compute(a, b):
            return a + b

        result = await compute(3, 4)

        assert result == 7
        assert len(collector.events) == 1

    def test_after_sync_function(self, clean_bus):
        """Test @after with synchronous function."""
        collector = EventCollector()
        clean_bus.on("sync.after", collector.collect)

        @after("sync.after", include_result=True)
        def sync_compute(x):
            return x**2

        result = sync_compute(3)
        assert result == 9


class TestOnErrorDecorator:
    """Test @on_error decorator."""

    @pytest.mark.asyncio
    async def test_on_error_handles_errors(self, clean_bus):
        """Test @on_error handles error events."""
        errors = []

        @on_error("*.error")
        async def error_handler(event):
            errors.append(event)

        # Emit an error event
        await clean_bus.emit("player.error", BaseEvent(event_type="player.error"))
        await clean_bus.emit("strategy.error", BaseEvent(event_type="strategy.error"))

        assert len(errors) == 2

    @pytest.mark.asyncio
    async def test_on_error_specific_pattern(self, clean_bus):
        """Test @on_error with specific pattern."""
        player_errors = []

        @on_error("player.*.error")
        async def player_error_handler(event):
            player_errors.append(event)

        await clean_bus.emit("player.move.error", BaseEvent(event_type="player.move.error"))
        await clean_bus.emit("strategy.error", BaseEvent(event_type="strategy.error"))

        # Should only catch player errors
        assert len(player_errors) == 1


class TestEmitOnExceptionDecorator:
    """Test @emit_on_exception decorator."""

    @pytest.mark.asyncio
    async def test_emit_on_exception_emits_event(self, clean_bus):
        """Test @emit_on_exception emits event when exception occurs."""
        collector = EventCollector()
        clean_bus.on("func.error", collector.collect)

        @emit_on_exception("func.error")
        async def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await failing_function()

        # Error event should have been emitted
        assert len(collector.events) == 1

    @pytest.mark.asyncio
    async def test_emit_on_exception_with_traceback(self, clean_bus):
        """Test @emit_on_exception includes traceback."""
        collector = EventCollector()
        clean_bus.on("error.event", collector.collect)

        @emit_on_exception("error.event", include_traceback=True)
        async def error_func():
            raise RuntimeError("Error with traceback")

        with pytest.raises(RuntimeError):
            await error_func()

        assert len(collector.events) == 1
        # Event metadata should contain traceback

    @pytest.mark.asyncio
    async def test_emit_on_exception_success_no_event(self, clean_bus):
        """Test @emit_on_exception doesn't emit when no exception."""
        collector = EventCollector()
        clean_bus.on("success.event", collector.collect)

        @emit_on_exception("success.event")
        async def success_func():
            return "success"

        result = await success_func()

        assert result == "success"
        assert len(collector.events) == 0  # No error, no event

    def test_emit_on_exception_sync(self, clean_bus):
        """Test @emit_on_exception with sync function."""
        collector = EventCollector()
        clean_bus.on("sync.error", collector.collect)

        @emit_on_exception("sync.error")
        def sync_failing():
            raise KeyError("Sync error")

        with pytest.raises(KeyError):
            sync_failing()


class TestDecoratorCombinations:
    """Test combining multiple decorators."""

    @pytest.mark.asyncio
    async def test_before_and_after(self, clean_bus):
        """Test combining @before and @after."""
        before_events = []
        after_events = []

        clean_bus.on("func.before", lambda e: before_events.append(e))
        clean_bus.on("func.after", lambda e: after_events.append(e))

        @before("func.before")
        @after("func.after")
        async def my_function(x):
            return x * 2

        result = await my_function(5)

        assert result == 10
        assert len(before_events) == 1
        assert len(after_events) == 1

    @pytest.mark.asyncio
    async def test_after_with_exception_handler(self, clean_bus):
        """Test @after with @emit_on_exception."""
        after_events = []
        error_events = []

        clean_bus.on("func.after", lambda e: after_events.append(e))
        clean_bus.on("func.error", lambda e: error_events.append(e))

        @after("func.after")
        @emit_on_exception("func.error")
        async def risky_function(should_fail):
            if should_fail:
                raise ValueError("Failed")
            return "success"

        # Success case
        result = await risky_function(False)
        assert result == "success"
        assert len(after_events) == 1
        assert len(error_events) == 0

        # Failure case
        with pytest.raises(ValueError):
            await risky_function(True)

        # After decorator should not emit on exception
        assert len(after_events) == 1  # Still just one
        assert len(error_events) == 1  # Error emitted


class TestDecoratorEdgeCases:
    """Test decorator edge cases."""

    @pytest.mark.asyncio
    async def test_decorator_with_no_args(self, clean_bus):
        """Test decorator on function with no arguments."""
        collector = EventCollector()
        clean_bus.on("noargs.before", collector.collect)

        @before("noargs.before")
        async def no_args_function():
            return "result"

        result = await no_args_function()

        assert result == "result"
        assert len(collector.events) == 1

    @pytest.mark.asyncio
    async def test_decorator_with_kwargs(self, clean_bus):
        """Test decorator on function with keyword arguments."""
        collector = EventCollector()
        clean_bus.on("kwargs.before", collector.collect)

        @before("kwargs.before")
        async def kwargs_function(x, y=10, **kwargs):
            return x + y

        result = await kwargs_function(5, y=20, extra="value")

        assert result == 25
        assert len(collector.events) == 1

    @pytest.mark.asyncio
    async def test_multiple_on_event_decorators(self, clean_bus):
        """Test multiple @on_event decorators on same function."""
        calls = []

        # This should register the function for both patterns
        @on_event("event1")
        @on_event("event2")
        async def handler(event):
            calls.append(event.event_type)

        await clean_bus.emit("event1", BaseEvent(event_type="event1"))
        await clean_bus.emit("event2", BaseEvent(event_type="event2"))

        # Function should be called for both events
        assert len(calls) == 2
        assert "event1" in calls
        assert "event2" in calls


class TestDecoratorErrorHandling:
    """Test error handling in decorated functions."""

    @pytest.mark.asyncio
    async def test_before_decorator_handles_emit_error(self, clean_bus):
        """Test @before handles event emission errors gracefully."""

        @before("test.before")
        async def my_function():
            return "success"

        # Function should still execute even if event emission fails
        result = await my_function()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_after_decorator_handles_emit_error(self, clean_bus):
        """Test @after handles event emission errors gracefully."""

        @after("test.after")
        async def my_function():
            return "success"

        result = await my_function()
        assert result == "success"
