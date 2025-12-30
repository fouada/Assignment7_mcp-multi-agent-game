"""
Tests for Event Bus
===================

Tests the core event bus functionality including:
- Handler registration and unregistration
- Event emission (sync and async)
- Pattern matching (wildcards)
- Handler priorities
- Error handling
- Event history
- Statistics

Run with: pytest tests/test_event_bus.py -v
"""

import asyncio

import pytest

from src.common.events import (
    BaseEvent,
    EventBus,
    GameStartedEvent,
    PlayerMoveAfterEvent,
    get_event_bus,
)
from src.common.logger import get_logger

logger = get_logger(__name__)


# Test fixtures


@pytest.fixture
def clean_event_bus():
    """Get a clean event bus for testing."""
    bus = EventBus()
    bus.reset()
    yield bus
    bus.reset()


# Test helper classes


class MockEventHandler:
    """Mock handler that tracks calls for testing."""

    def __init__(self):
        self.calls = []
        self.async_calls = []

    def sync_handler(self, event: BaseEvent):
        """Synchronous handler."""
        self.calls.append(event)

    async def async_handler(self, event: BaseEvent):
        """Asynchronous handler."""
        self.async_calls.append(event)
        await asyncio.sleep(0.001)  # Simulate async work


# Tests


class TestEventBusBasics:
    """Test basic event bus functionality."""

    def test_singleton(self):
        """Test event bus is singleton."""
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        assert bus1 is bus2

    def test_configure(self, clean_event_bus):
        """Test configuring event bus."""
        clean_event_bus.configure(
            enabled=True,
            max_history=500,
            async_by_default=False,
            error_handling="propagate",
        )

        assert clean_event_bus._enabled is True
        assert clean_event_bus._max_history == 500
        assert clean_event_bus._async_by_default is False
        assert clean_event_bus._error_handling == "propagate"


class TestHandlerRegistration:
    """Test handler registration and unregistration."""

    def test_register_async_handler(self, clean_event_bus):
        """Test registering async handler."""
        handler = MockEventHandler()

        handler_id = clean_event_bus.on(
            pattern="test.event",
            handler=handler.async_handler,
        )

        assert isinstance(handler_id, str)
        assert clean_event_bus.get_handler_count() == 1

    def test_register_sync_handler(self, clean_event_bus):
        """Test registering sync handler."""
        handler = MockEventHandler()

        handler_id = clean_event_bus.on(
            pattern="test.event",
            handler=handler.sync_handler,
        )

        assert clean_event_bus.get_handler_count() == 1
        metadata = clean_event_bus._handler_registry[handler_id]
        assert metadata.is_async is False

    def test_unregister_handler(self, clean_event_bus):
        """Test unregistering handler."""
        handler = MockEventHandler()
        handler_id = clean_event_bus.on("test.event", handler.async_handler)

        result = clean_event_bus.off(handler_id)

        assert result is True
        assert clean_event_bus.get_handler_count() == 0

    def test_unregister_nonexistent_handler(self, clean_event_bus):
        """Test unregistering nonexistent handler returns False."""
        result = clean_event_bus.off("nonexistent_id")
        assert result is False

    def test_handler_with_metadata(self, clean_event_bus):
        """Test registering handler with metadata."""
        handler = MockEventHandler()

        handler_id = clean_event_bus.on(
            pattern="test.*",
            handler=handler.async_handler,
            priority=10,
            description="Test handler",
            tags=["test", "analytics"],
        )

        metadata = clean_event_bus._handler_registry[handler_id]
        assert metadata.priority == 10
        assert metadata.description == "Test handler"
        assert "test" in metadata.tags


class TestPatternMatching:
    """Test event pattern matching."""

    def test_exact_pattern(self, clean_event_bus):
        """Test exact pattern matching."""
        assert clean_event_bus._match_pattern("game.started", "game.started")
        assert not clean_event_bus._match_pattern("game.started", "game.ended")

    def test_wildcard_all(self, clean_event_bus):
        """Test wildcard * matches everything."""
        assert clean_event_bus._match_pattern("*", "game.started")
        assert clean_event_bus._match_pattern("*", "player.move.after")
        assert clean_event_bus._match_pattern("*", "anything")

    def test_wildcard_prefix(self, clean_event_bus):
        """Test prefix wildcard matching."""
        assert clean_event_bus._match_pattern("game.*", "game.started")
        assert clean_event_bus._match_pattern("game.*", "game.ended")
        assert not clean_event_bus._match_pattern("game.*", "player.started")

    def test_wildcard_middle(self, clean_event_bus):
        """Test middle wildcard matching."""
        assert clean_event_bus._match_pattern("player.*.move", "player.odd.move")
        assert clean_event_bus._match_pattern("player.*.move", "player.even.move")
        assert not clean_event_bus._match_pattern("player.*.move", "player.odd.start")

    def test_wildcard_suffix(self, clean_event_bus):
        """Test suffix wildcard matching."""
        assert clean_event_bus._match_pattern("*.error", "game.error")
        assert clean_event_bus._match_pattern("*.error", "player.error")
        assert not clean_event_bus._match_pattern("*.error", "game.started")


class TestEventEmission:
    """Test event emission."""

    @pytest.mark.asyncio
    async def test_emit_async_handler(self, clean_event_bus):
        """Test emitting event to async handler."""
        handler = MockEventHandler()
        clean_event_bus.on("test.event", handler.async_handler)

        event = BaseEvent(event_type="test.event")
        await clean_event_bus.emit("test.event", event)

        assert len(handler.async_calls) == 1
        assert handler.async_calls[0] == event

    @pytest.mark.asyncio
    async def test_emit_sync_handler(self, clean_event_bus):
        """Test emitting event to sync handler (runs in executor)."""
        handler = MockEventHandler()
        clean_event_bus.on("test.event", handler.sync_handler)

        event = BaseEvent(event_type="test.event")
        await clean_event_bus.emit("test.event", event)

        assert len(handler.calls) == 1

    def test_emit_sync(self, clean_event_bus):
        """Test synchronous event emission."""
        handler = MockEventHandler()
        clean_event_bus.on("test.event", handler.sync_handler)

        event = BaseEvent(event_type="test.event")
        clean_event_bus.emit_sync("test.event", event)

        assert len(handler.calls) == 1

    @pytest.mark.asyncio
    async def test_emit_with_kwargs(self, clean_event_bus):
        """Test emitting event with kwargs (creates event)."""
        handler = MockEventHandler()
        clean_event_bus.on("test.event", handler.async_handler)

        await clean_event_bus.emit("test.event", test_data="value")

        assert len(handler.async_calls) == 1
        event = handler.async_calls[0]
        assert event.event_type == "test.event"

    @pytest.mark.asyncio
    async def test_emit_to_multiple_handlers(self, clean_event_bus):
        """Test emitting to multiple handlers."""
        handler1 = TestHandler()
        handler2 = TestHandler()

        clean_event_bus.on("test.event", handler1.async_handler)
        clean_event_bus.on("test.event", handler2.async_handler)

        await clean_event_bus.emit("test.event", BaseEvent(event_type="test.event"))

        assert len(handler1.async_calls) == 1
        assert len(handler2.async_calls) == 1

    @pytest.mark.asyncio
    async def test_emit_no_handlers(self, clean_event_bus):
        """Test emitting event with no handlers."""
        results = await clean_event_bus.emit("no.handlers", BaseEvent(event_type="no.handlers"))
        assert results == []


class TestPriorities:
    """Test handler priorities."""

    @pytest.mark.asyncio
    async def test_priority_order(self, clean_event_bus):
        """Test handlers execute in priority order."""
        execution_order = []

        async def handler_low(event):
            execution_order.append("low")

        async def handler_high(event):
            execution_order.append("high")

        async def handler_medium(event):
            execution_order.append("medium")

        clean_event_bus.on("test.event", handler_low, priority=1)
        clean_event_bus.on("test.event", handler_high, priority=10)
        clean_event_bus.on("test.event", handler_medium, priority=5)

        await clean_event_bus.emit("test.event", BaseEvent(event_type="test.event"))

        # Should execute in order: high, medium, low
        assert execution_order == ["high", "medium", "low"]


class TestErrorHandling:
    """Test error handling in handlers."""

    @pytest.mark.asyncio
    async def test_error_isolate(self, clean_event_bus):
        """Test error isolation continues to next handler."""
        clean_event_bus.configure(error_handling="isolate")

        handler = MockEventHandler()

        async def failing_handler(event):
            raise ValueError("Test error")

        clean_event_bus.on("test.event", failing_handler, priority=10)
        clean_event_bus.on("test.event", handler.async_handler, priority=5)

        # Should not raise, second handler should execute
        await clean_event_bus.emit("test.event", BaseEvent(event_type="test.event"))

        assert len(handler.async_calls) == 1
        stats = clean_event_bus.get_stats()
        assert stats["total_errors"] == 1

    @pytest.mark.asyncio
    async def test_error_propagate(self, clean_event_bus):
        """Test error propagation raises exception."""
        clean_event_bus.configure(error_handling="propagate")

        async def failing_handler(event):
            raise ValueError("Test error")

        clean_event_bus.on("test.event", failing_handler)

        with pytest.raises(ValueError):
            await clean_event_bus.emit("test.event", BaseEvent(event_type="test.event"))

    @pytest.mark.asyncio
    async def test_error_stop(self, clean_event_bus):
        """Test error stop halts execution."""
        clean_event_bus.configure(error_handling="stop")

        handler = MockEventHandler()

        async def failing_handler(event):
            raise ValueError("Test error")

        clean_event_bus.on("test.event", failing_handler, priority=10)
        clean_event_bus.on("test.event", handler.async_handler, priority=5)

        # Should stop after first handler fails
        await clean_event_bus.emit("test.event", BaseEvent(event_type="test.event"))

        # Second handler should not execute
        assert len(handler.async_calls) == 0


class TestEventHistory:
    """Test event history tracking."""

    @pytest.mark.asyncio
    async def test_event_history_stored(self, clean_event_bus):
        """Test events are stored in history."""
        event1 = BaseEvent(event_type="test.event1")
        event2 = BaseEvent(event_type="test.event2")

        await clean_event_bus.emit("test.event1", event1)
        await clean_event_bus.emit("test.event2", event2)

        history = clean_event_bus.get_event_history()
        assert len(history) >= 2
        assert history[0].event_type == "test.event2"  # Most recent first
        assert history[1].event_type == "test.event1"

    @pytest.mark.asyncio
    async def test_event_history_limit(self, clean_event_bus):
        """Test event history respects limit."""
        history = clean_event_bus.get_event_history(limit=1)
        assert len(history) <= 1

    def test_clear_history(self, clean_event_bus):
        """Test clearing event history."""
        clean_event_bus.clear_history()
        history = clean_event_bus.get_event_history()
        assert len(history) == 0


class TestStatistics:
    """Test event bus statistics."""

    @pytest.mark.asyncio
    async def test_stats_tracking(self, clean_event_bus):
        """Test statistics are tracked."""
        handler = MockEventHandler()
        clean_event_bus.on("test.event", handler.async_handler)

        await clean_event_bus.emit("test.event", BaseEvent(event_type="test.event"))
        await clean_event_bus.emit("test.event", BaseEvent(event_type="test.event"))

        stats = clean_event_bus.get_stats()
        assert stats["total_events"] == 2
        assert stats["total_handlers"] == 1

    def test_get_handlers(self, clean_event_bus):
        """Test getting registered handlers."""
        handler = MockEventHandler()

        clean_event_bus.on("test.event1", handler.async_handler)
        clean_event_bus.on("test.event2", handler.async_handler)

        # Get all handlers
        handlers = clean_event_bus.get_handlers()
        assert len(handlers) == 2

        # Get handlers for specific pattern
        handlers1 = clean_event_bus.get_handlers("test.event1")
        assert len(handlers1) == 1

    def test_reset(self, clean_event_bus):
        """Test resetting event bus."""
        handler = MockEventHandler()
        clean_event_bus.on("test.event", handler.async_handler)

        clean_event_bus.reset()

        assert clean_event_bus.get_handler_count() == 0
        assert clean_event_bus.get_stats()["total_events"] == 0


class TestWildcardHandlers:
    """Test wildcard pattern handlers."""

    @pytest.mark.asyncio
    async def test_wildcard_catches_all(self, clean_event_bus):
        """Test * pattern catches all events."""
        handler = MockEventHandler()
        clean_event_bus.on("*", handler.async_handler)

        await clean_event_bus.emit("game.started", BaseEvent(event_type="game.started"))
        await clean_event_bus.emit("player.move", BaseEvent(event_type="player.move"))

        assert len(handler.async_calls) == 2

    @pytest.mark.asyncio
    async def test_multiple_patterns(self, clean_event_bus):
        """Test handler receives events from multiple patterns."""
        handler = MockEventHandler()

        clean_event_bus.on("game.*", handler.async_handler)
        clean_event_bus.on("player.*", handler.async_handler)

        await clean_event_bus.emit("game.started", BaseEvent(event_type="game.started"))
        await clean_event_bus.emit("player.move", BaseEvent(event_type="player.move"))
        await clean_event_bus.emit("match.started", BaseEvent(event_type="match.started"))

        # Should receive 2 events (game and player, not match)
        assert len(handler.async_calls) == 2


class TestEventTypes:
    """Test with actual event types."""

    @pytest.mark.asyncio
    async def test_game_started_event(self, clean_event_bus):
        """Test GameStartedEvent."""
        handler = MockEventHandler()
        clean_event_bus.on("game.started", handler.async_handler)

        event = GameStartedEvent(
            game_id="game_001",
            game_type="even_odd",
            players=["P01", "P02"],
            referee_id="REF01",
        )

        await clean_event_bus.emit("game.started", event)

        assert len(handler.async_calls) == 1
        received = handler.async_calls[0]
        assert received.game_id == "game_001"
        assert received.players == ["P01", "P02"]

    @pytest.mark.asyncio
    async def test_player_move_event(self, clean_event_bus):
        """Test PlayerMoveAfterEvent."""
        handler = MockEventHandler()
        clean_event_bus.on("player.move.after", handler.async_handler)

        event = PlayerMoveAfterEvent(
            player_id="P01",
            game_id="game_001",
            round_number=1,
            move=5,
            decision_time_ms=123.45,
        )

        await clean_event_bus.emit("player.move.after", event)

        assert len(handler.async_calls) == 1
        received = handler.async_calls[0]
        assert received.move == 5
        assert received.decision_time_ms == 123.45


class TestDisabledBus:
    """Test disabled event bus."""

    @pytest.mark.asyncio
    async def test_disabled_bus_no_emit(self, clean_event_bus):
        """Test disabled bus doesn't emit events."""
        clean_event_bus.configure(enabled=False)

        handler = MockEventHandler()
        clean_event_bus.on("test.event", handler.async_handler)

        results = await clean_event_bus.emit("test.event", BaseEvent(event_type="test.event"))

        assert results == []
        assert len(handler.async_calls) == 0
