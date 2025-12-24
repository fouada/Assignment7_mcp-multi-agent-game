"""
Event Decorators
================

Convenient decorators for event handling and hook registration.

Provides:
- @on_event: Register handler for specific event pattern
- @before: Emit event before function execution
- @after: Emit event after function execution
- @on_error: Register handler for error events

Usage:
    from src.common.events import on_event, before, after

    # Register handler
    @on_event("game.started", priority=10)
    async def on_game_start(event):
        print(f"Game {event.game_id} started!")

    # Emit before function
    @before("player.move.before")
    async def decide_move(self, game_id, round_number, ...):
        # Event emitted with function args before execution
        move = ...
        return move

    # Emit after function
    @after("player.move.after")
    async def decide_move(self, game_id, round_number, ...):
        move = ...
        # Event emitted with function result after execution
        return move
"""

import functools
import inspect
import time
from typing import Any, Callable, Optional, TypeVar

from ..logger import get_logger
from .bus import get_event_bus
from .types import BaseEvent

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def on_event(
    pattern: str,
    priority: int = 0,
    description: str = "",
    tags: Optional[list] = None,
) -> Callable[[F], F]:
    """
    Decorator to register a function as an event handler.

    Args:
        pattern: Event pattern to match (supports wildcards)
        priority: Handler priority (higher = earlier execution)
        description: Handler description
        tags: Tags for categorizing handler

    Returns:
        Decorated function

    Examples:
        @on_event("game.started", priority=10)
        async def on_game_start(event):
            print(f"Game {event.game_id} started!")

        @on_event("game.*")
        async def on_any_game_event(event):
            print(f"Game event: {event.event_type}")

        @on_event("player.*.move", priority=5, tags=["analytics"])
        async def track_player_moves(event):
            # Track player move analytics
            pass
    """

    def decorator(func: F) -> F:
        # Register handler immediately
        bus = get_event_bus()
        handler_id = bus.on(
            pattern=pattern,
            handler=func,
            priority=priority,
            description=description or func.__doc__ or "",
            tags=tags,
        )

        # Store handler ID on function for potential unregistration
        func._event_handler_id = handler_id  # type: ignore
        func._event_pattern = pattern  # type: ignore

        return func

    return decorator


def before(
    event_type: str,
    include_self: bool = True,
    extract_args: Optional[list] = None,
) -> Callable[[F], F]:
    """
    Decorator to emit an event before function execution.

    The event will include function arguments as metadata.

    Args:
        event_type: Event type to emit
        include_self: Whether to include 'self' argument (for methods)
        extract_args: Specific argument names to include (None = all)

    Returns:
        Decorated function

    Examples:
        @before("player.move.before")
        async def decide_move(self, game_id, round_number, my_score, opponent_score):
            # Event emitted with all args: game_id, round_number, my_score, opponent_score
            move = ...
            return move

        @before("strategy.compute.before", extract_args=["game_id", "round_number"])
        async def compute_strategy(self, game_id, round_number, history):
            # Event only includes game_id and round_number
            pass
    """

    def decorator(func: F) -> F:
        bus = get_event_bus()

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Extract arguments
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()

                # Build event data
                event_data = {}
                for name, value in bound_args.arguments.items():
                    # Skip 'self' if not included
                    if not include_self and name == "self":
                        continue

                    # Filter by extract_args if provided
                    if extract_args is not None and name not in extract_args:
                        continue

                    # Skip non-serializable values
                    if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                        event_data[name] = value

                # Emit event
                try:
                    await bus.emit(event_type, **event_data)
                except Exception as e:
                    logger.error(f"Error emitting before event '{event_type}': {e}")

                # Execute function
                return await func(*args, **kwargs)

            return async_wrapper  # type: ignore

        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Extract arguments
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()

                # Build event data
                event_data = {}
                for name, value in bound_args.arguments.items():
                    if not include_self and name == "self":
                        continue
                    if extract_args is not None and name not in extract_args:
                        continue
                    if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                        event_data[name] = value

                # Emit event synchronously
                try:
                    bus.emit_sync(event_type, **event_data)
                except Exception as e:
                    logger.error(f"Error emitting before event '{event_type}': {e}")

                # Execute function
                return func(*args, **kwargs)

            return sync_wrapper  # type: ignore

    return decorator


def after(
    event_type: str,
    include_result: bool = True,
    include_args: bool = False,
    extract_args: Optional[list] = None,
    include_timing: bool = False,
) -> Callable[[F], F]:
    """
    Decorator to emit an event after function execution.

    The event will include function result and optionally arguments.

    Args:
        event_type: Event type to emit
        include_result: Whether to include function result in event
        include_args: Whether to include function arguments in event
        extract_args: Specific argument names to include (None = all if include_args)
        include_timing: Whether to include execution time in event

    Returns:
        Decorated function

    Examples:
        @after("player.move.after")
        async def decide_move(self, game_id, round_number):
            move = 5
            # Event emitted with result: {"result": 5}
            return move

        @after("player.move.after", include_args=True, include_timing=True)
        async def decide_move(self, game_id, round_number):
            move = 5
            # Event emitted with: {"result": 5, "game_id": "123", "round_number": 1, "execution_time_ms": 15.2}
            return move
    """

    def decorator(func: F) -> F:
        bus = get_event_bus()

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time() if include_timing else None

                # Execute function
                result = await func(*args, **kwargs)

                # Build event data
                event_data = {}

                if include_result:
                    # Only include serializable results
                    if isinstance(result, (str, int, float, bool, list, dict, type(None))):
                        event_data["result"] = result

                if include_args:
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()

                    for name, value in bound_args.arguments.items():
                        if name == "self":
                            continue
                        if extract_args is not None and name not in extract_args:
                            continue
                        if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                            event_data[name] = value

                if include_timing and start_time is not None:
                    execution_time = (time.time() - start_time) * 1000  # ms
                    event_data["execution_time_ms"] = round(execution_time, 2)

                # Emit event
                try:
                    await bus.emit(event_type, **event_data)
                except Exception as e:
                    logger.error(f"Error emitting after event '{event_type}': {e}")

                return result

            return async_wrapper  # type: ignore

        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time() if include_timing else None

                # Execute function
                result = func(*args, **kwargs)

                # Build event data
                event_data = {}

                if include_result:
                    if isinstance(result, (str, int, float, bool, list, dict, type(None))):
                        event_data["result"] = result

                if include_args:
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()

                    for name, value in bound_args.arguments.items():
                        if name == "self":
                            continue
                        if extract_args is not None and name not in extract_args:
                            continue
                        if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                            event_data[name] = value

                if include_timing and start_time is not None:
                    execution_time = (time.time() - start_time) * 1000
                    event_data["execution_time_ms"] = round(execution_time, 2)

                # Emit event synchronously
                try:
                    bus.emit_sync(event_type, **event_data)
                except Exception as e:
                    logger.error(f"Error emitting after event '{event_type}': {e}")

                return result

            return sync_wrapper  # type: ignore

    return decorator


def on_error(
    pattern: str = "*.error",
    priority: int = 0,
    reraise: bool = False,
) -> Callable[[F], F]:
    """
    Decorator to register a handler specifically for error events.

    Args:
        pattern: Error event pattern to match (default: "*.error")
        priority: Handler priority
        reraise: Whether to re-raise the exception after handling

    Returns:
        Decorated function

    Examples:
        @on_error("player.*.error")
        async def handle_player_errors(event):
            print(f"Player error: {event.error_message}")
            # Send alert, log to external system, etc.

        @on_error()  # Matches all error events
        async def handle_all_errors(event):
            print(f"Error in {event.source}: {event.error_message}")
    """

    def decorator(func: F) -> F:
        # Register as regular event handler
        bus = get_event_bus()
        handler_id = bus.on(
            pattern=pattern,
            handler=func,
            priority=priority,
            description=func.__doc__ or "Error handler",
            tags=["error_handler"],
        )

        func._event_handler_id = handler_id  # type: ignore
        func._event_pattern = pattern  # type: ignore
        func._error_reraise = reraise  # type: ignore

        return func

    return decorator


def emit_on_exception(event_type: str, include_traceback: bool = True) -> Callable[[F], F]:
    """
    Decorator to emit an event when function raises an exception.

    Args:
        event_type: Event type to emit
        include_traceback: Whether to include traceback in event

    Returns:
        Decorated function

    Examples:
        @emit_on_exception("strategy.error")
        async def decide_move(self, game_id, round_number):
            # If this raises an exception, event is emitted
            move = some_computation()
            return move
    """

    def decorator(func: F) -> F:
        bus = get_event_bus()

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    import traceback as tb

                    event_data = {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "function": func.__name__,
                    }

                    if include_traceback:
                        event_data["traceback"] = tb.format_exc()

                    # Emit error event
                    try:
                        await bus.emit(event_type, **event_data)
                    except Exception as emit_error:
                        logger.error(f"Error emitting exception event: {emit_error}")

                    # Re-raise original exception
                    raise

            return async_wrapper  # type: ignore

        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    import traceback as tb

                    event_data = {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "function": func.__name__,
                    }

                    if include_traceback:
                        event_data["traceback"] = tb.format_exc()

                    try:
                        bus.emit_sync(event_type, **event_data)
                    except Exception as emit_error:
                        logger.error(f"Error emitting exception event: {emit_error}")

                    raise

            return sync_wrapper  # type: ignore

    return decorator
