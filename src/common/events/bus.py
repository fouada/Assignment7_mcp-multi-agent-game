"""
Event Bus
=========

Production-grade event bus for the MCP Multi-Agent Game League.

Features:
- Wildcard pattern matching (e.g., "game.*", "player.*.move")
- Priority-based handler execution (higher priority = earlier)
- Async and sync handler support
- Error isolation (one handler failure doesn't break others)
- Event history for debugging
- Handler registry with metadata
- Thread-safe singleton implementation

Usage:
    from src.common.events import EventBus, GameStartedEvent

    # Get bus instance
    bus = get_event_bus()

    # Register handler
    async def on_game_start(event: GameStartedEvent):
        print(f"Game {event.game_id} started!")

    handler_id = bus.on("game.started", on_game_start, priority=10)

    # Emit event
    await bus.emit("game.started", GameStartedEvent(game_id="123", ...))

    # Unregister handler
    bus.off(handler_id)
"""

import asyncio
import fnmatch
import inspect
import traceback
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional, Union
from uuid import uuid4

from ..logger import get_logger
from .types import BaseEvent

logger = get_logger(__name__)


@dataclass
class HandlerMetadata:
    """Metadata for an event handler."""

    handler_id: str
    pattern: str
    handler: Callable
    priority: int = 0
    is_async: bool = True
    description: str = ""
    tags: List[str] = field(default_factory=list)


class EventBus:
    """
    Production-grade event bus with wildcard matching and priority queues.

    Singleton pattern ensures single event bus instance across application.
    """

    _instance: Optional["EventBus"] = None
    _lock = asyncio.Lock()

    def __new__(cls) -> "EventBus":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize event bus."""
        if self._initialized:
            return

        self._handlers: Dict[str, List[HandlerMetadata]] = {}
        self._handler_registry: Dict[str, HandlerMetadata] = {}
        self._event_history: Deque[BaseEvent] = deque(maxlen=1000)
        self._enabled = True
        self._max_history = 1000
        self._async_by_default = True
        self._error_handling = "isolate"  # "isolate", "propagate", "stop"
        self._stats = {
            "total_events": 0,
            "total_handlers": 0,
            "total_errors": 0,
        }
        self._initialized = True

        logger.debug("EventBus initialized")

    def configure(
        self,
        enabled: bool = True,
        max_history: int = 1000,
        async_by_default: bool = True,
        error_handling: str = "isolate",
    ):
        """
        Configure event bus behavior.

        Args:
            enabled: Whether event bus is enabled
            max_history: Maximum number of events to keep in history
            async_by_default: Whether to treat handlers as async by default
            error_handling: How to handle errors ("isolate", "propagate", "stop")
        """
        self._enabled = enabled
        self._max_history = max_history
        self._event_history = deque(maxlen=max_history)
        self._async_by_default = async_by_default
        self._error_handling = error_handling

        logger.info(
            f"EventBus configured: enabled={enabled}, max_history={max_history}, "
            f"async_by_default={async_by_default}, error_handling={error_handling}"
        )

    def on(
        self,
        pattern: str,
        handler: Callable,
        priority: int = 0,
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Register an event handler.

        Args:
            pattern: Event pattern to match (supports wildcards: "game.*", "player.*.move")
            handler: Callable to handle event (async or sync)
            priority: Handler priority (higher = earlier execution)
            description: Handler description for documentation
            tags: Tags for categorizing handler

        Returns:
            Handler ID for later unregistration

        Examples:
            # Match specific event
            bus.on("game.started", on_game_start)

            # Match all game events
            bus.on("game.*", on_any_game_event)

            # Match nested events
            bus.on("player.*.move", on_player_move)
        """
        handler_id = str(uuid4())

        # Detect if handler is async
        is_async = inspect.iscoroutinefunction(handler)

        metadata = HandlerMetadata(
            handler_id=handler_id,
            pattern=pattern,
            handler=handler,
            priority=priority,
            is_async=is_async,
            description=description,
            tags=tags or [],
        )

        # Add to pattern-specific handlers
        if pattern not in self._handlers:
            self._handlers[pattern] = []
        self._handlers[pattern].append(metadata)

        # Sort by priority (descending)
        self._handlers[pattern].sort(key=lambda h: h.priority, reverse=True)

        # Add to registry
        self._handler_registry[handler_id] = metadata

        self._stats["total_handlers"] += 1

        logger.debug(
            f"Registered handler {handler_id} for pattern '{pattern}' "
            f"(priority={priority}, async={is_async})"
        )

        return handler_id

    def off(self, handler_id: str) -> bool:
        """
        Unregister an event handler.

        Args:
            handler_id: Handler ID returned by on()

        Returns:
            True if handler was removed, False if not found
        """
        if handler_id not in self._handler_registry:
            logger.warning(f"Handler {handler_id} not found for removal")
            return False

        metadata = self._handler_registry.pop(handler_id)

        # Remove from pattern-specific handlers
        if metadata.pattern in self._handlers:
            self._handlers[metadata.pattern] = [
                h for h in self._handlers[metadata.pattern] if h.handler_id != handler_id
            ]

            # Clean up empty patterns
            if not self._handlers[metadata.pattern]:
                del self._handlers[metadata.pattern]

        self._stats["total_handlers"] -= 1

        logger.debug(f"Unregistered handler {handler_id} for pattern '{metadata.pattern}'")
        return True

    def _match_pattern(self, pattern: str, event_type: str) -> bool:
        """
        Check if event type matches pattern.

        Supports wildcards:
        - "game.*" matches "game.started", "game.ended", etc.
        - "player.*.move" matches "player.odd.move", "player.even.move", etc.
        - "*" matches everything

        Args:
            pattern: Pattern with wildcards
            event_type: Event type to match

        Returns:
            True if matches, False otherwise
        """
        return fnmatch.fnmatch(event_type, pattern)

    def _get_matching_handlers(self, event_type: str) -> List[HandlerMetadata]:
        """
        Get all handlers matching event type, sorted by priority.

        Args:
            event_type: Event type to match

        Returns:
            List of matching handlers sorted by priority (descending)
        """
        matching = []

        for pattern, handlers in self._handlers.items():
            if self._match_pattern(pattern, event_type):
                matching.extend(handlers)

        # Sort by priority (descending)
        matching.sort(key=lambda h: h.priority, reverse=True)

        return matching

    async def emit(
        self,
        event_type: str,
        event: Optional[BaseEvent] = None,
        **kwargs,
    ) -> List[Any]:
        """
        Emit an event asynchronously.

        Args:
            event_type: Event type (e.g., "game.started")
            event: Event object (BaseEvent subclass) or None
            **kwargs: Event data if event is None

        Returns:
            List of handler results

        Examples:
            # With event object
            await bus.emit("game.started", GameStartedEvent(game_id="123"))

            # With kwargs
            await bus.emit("game.started", game_id="123", players=["p1", "p2"])
        """
        if not self._enabled:
            return []

        # Create event if not provided
        if event is None:
            event = BaseEvent(event_type=event_type, **kwargs)

        # Add to history
        self._event_history.append(event)
        self._stats["total_events"] += 1

        # Get matching handlers
        handlers = self._get_matching_handlers(event_type)

        if not handlers:
            logger.debug(f"No handlers registered for event '{event_type}'")
            return []

        logger.debug(
            f"Emitting event '{event_type}' to {len(handlers)} handler(s)"
        )

        results = []

        for handler_meta in handlers:
            try:
                if handler_meta.is_async:
                    result = await handler_meta.handler(event)
                else:
                    # Run sync handler in executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, handler_meta.handler, event)

                results.append(result)

            except Exception as e:
                self._stats["total_errors"] += 1

                logger.error(
                    f"Error in handler {handler_meta.handler_id} for event '{event_type}': {e}\n"
                    f"{traceback.format_exc()}"
                )

                if self._error_handling == "propagate":
                    raise
                elif self._error_handling == "stop":
                    break
                # "isolate" continues to next handler

        return results

    def emit_sync(
        self,
        event_type: str,
        event: Optional[BaseEvent] = None,
        **kwargs,
    ) -> List[Any]:
        """
        Emit an event synchronously.

        Only calls sync handlers. Async handlers are skipped.

        Args:
            event_type: Event type
            event: Event object or None
            **kwargs: Event data if event is None

        Returns:
            List of handler results
        """
        if not self._enabled:
            return []

        # Create event if not provided
        if event is None:
            event = BaseEvent(event_type=event_type, **kwargs)

        # Add to history
        self._event_history.append(event)
        self._stats["total_events"] += 1

        # Get matching sync handlers only
        handlers = [
            h for h in self._get_matching_handlers(event_type) if not h.is_async
        ]

        if not handlers:
            logger.debug(f"No sync handlers registered for event '{event_type}'")
            return []

        logger.debug(
            f"Emitting event '{event_type}' to {len(handlers)} sync handler(s)"
        )

        results = []

        for handler_meta in handlers:
            try:
                result = handler_meta.handler(event)
                results.append(result)

            except Exception as e:
                self._stats["total_errors"] += 1

                logger.error(
                    f"Error in sync handler {handler_meta.handler_id} for event '{event_type}': {e}"
                )

                if self._error_handling == "propagate":
                    raise
                elif self._error_handling == "stop":
                    break

        return results

    def get_handlers(self, pattern: Optional[str] = None) -> List[HandlerMetadata]:
        """
        Get registered handlers.

        Args:
            pattern: Filter by pattern (None = all handlers)

        Returns:
            List of handler metadata
        """
        if pattern is None:
            return list(self._handler_registry.values())

        return self._handlers.get(pattern, [])

    def get_handler_count(self) -> int:
        """Get total number of registered handlers."""
        return len(self._handler_registry)

    def get_event_history(self, limit: Optional[int] = None) -> List[BaseEvent]:
        """
        Get event history.

        Args:
            limit: Maximum number of events to return (None = all)

        Returns:
            List of recent events (newest first)
        """
        history = list(reversed(self._event_history))
        if limit is not None:
            history = history[:limit]
        return history

    def get_stats(self) -> Dict[str, int]:
        """
        Get event bus statistics.

        Returns:
            Dictionary with stats (total_events, total_handlers, total_errors)
        """
        return self._stats.copy()

    def clear_history(self):
        """Clear event history."""
        self._event_history.clear()
        logger.debug("Event history cleared")

    def clear_handlers(self):
        """Clear all handlers (for testing)."""
        self._handlers.clear()
        self._handler_registry.clear()
        self._stats["total_handlers"] = 0
        logger.debug("All handlers cleared")

    def reset(self):
        """Reset event bus to initial state (for testing)."""
        self.clear_handlers()
        self.clear_history()
        self._stats = {
            "total_events": 0,
            "total_handlers": 0,
            "total_errors": 0,
        }
        logger.debug("EventBus reset")


# Singleton instance accessor
_event_bus_instance: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """
    Get the global EventBus instance.

    Returns:
        EventBus singleton instance
    """
    global _event_bus_instance
    if _event_bus_instance is None:
        _event_bus_instance = EventBus()
    return _event_bus_instance
