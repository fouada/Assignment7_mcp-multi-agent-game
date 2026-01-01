"""
Hook Decorators
===============

Convenient decorators for registering hooks.

Provides decorators inspired by pytest, Flask, and other popular frameworks:
- @hook - Generic hook decorator
- @before_hook - Execute before an action
- @after_hook - Execute after an action
- @around_hook - Wrap an action (modify input/output)

Example:
    @before_hook("match.started", priority=100)
    async def log_match_start(context):
        print(f"Match starting: {context.data['match_id']}")

    @after_hook("player.move", priority=50)
    async def validate_move(context):
        move = context.data['move']
        if not (1 <= move <= 10):
            context.cancel("Invalid move")

    @around_hook("strategy.decide")
    async def profile_strategy(context, next_hook):
        start = time.time()
        result = await next_hook(context)
        duration = time.time() - start
        context.set("decision_time", duration)
        return result
"""

import functools
from typing import Any, Callable

from .hook_manager import get_hook_manager
from .types import HookPriority, HookType

# Re-export for convenience
__all__ = ["hook", "before_hook", "after_hook", "around_hook"]


def hook(
    hook_name: str,
    hook_type: HookType = HookType.ACTION,
    priority: int = HookPriority.NORMAL.value,
    plugin_name: str = "",
    description: str = "",
    tags: list[str] | None = None,
    auto_register: bool = True,
) -> Callable:
    """
    Generic hook decorator.

    Args:
        hook_name: Name of hook point (e.g., "match.started")
        hook_type: Type of hook (BEFORE, AFTER, AROUND, FILTER, ACTION)
        priority: Execution priority (higher = earlier)
        plugin_name: Name of plugin registering this hook
        description: Human-readable description
        tags: Categorization tags
        auto_register: Whether to automatically register hook

    Returns:
        Decorator function

    Example:
        @hook("match.started", hook_type=HookType.BEFORE, priority=100)
        async def log_match(context):
            logger.info(f"Match {context.data['match_id']} started")
    """

    def decorator(func: Callable) -> Callable:
        # Store hook metadata on function
        func._hook_metadata = {  # type: ignore
            "hook_name": hook_name,
            "hook_type": hook_type,
            "priority": priority,
            "plugin_name": plugin_name,
            "description": description or func.__doc__ or "",
            "tags": tags or [],
        }

        # Auto-register if enabled
        if auto_register:
            manager = get_hook_manager()
            hook_id = manager.register(
                hook_name=hook_name,
                handler=func,
                hook_type=hook_type,
                priority=priority,
                plugin_name=plugin_name,
                description=description or func.__doc__ or "",
                tags=tags or [],
            )
            func._hook_id = hook_id  # type: ignore

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def before_hook(
    hook_name: str,
    priority: int = HookPriority.NORMAL.value,
    plugin_name: str = "",
    description: str = "",
    tags: list[str] | None = None,
    auto_register: bool = True,
) -> Callable:
    """
    Decorator for before hooks.

    Before hooks execute before the main action and can:
    - Inspect and modify context data
    - Cancel execution
    - Set error conditions

    Args:
        hook_name: Name of hook point
        priority: Execution priority (higher = earlier)
        plugin_name: Name of plugin
        description: Description
        tags: Categorization tags
        auto_register: Auto-register hook

    Returns:
        Decorator function

    Example:
        @before_hook("match.started", priority=100)
        async def validate_match(context):
            players = context.data.get('players', [])
            if len(players) != 2:
                context.cancel("Invalid number of players")

        @before_hook("player.move.validate")
        async def check_move_range(context):
            move = context.data['move']
            if not (1 <= move <= 10):
                context.set_error(ValueError("Move must be 1-10"))
    """
    return hook(
        hook_name=hook_name,
        hook_type=HookType.BEFORE,
        priority=priority,
        plugin_name=plugin_name,
        description=description,
        tags=tags,
        auto_register=auto_register,
    )


def after_hook(
    hook_name: str,
    priority: int = HookPriority.NORMAL.value,
    plugin_name: str = "",
    description: str = "",
    tags: list[str] | None = None,
    auto_register: bool = True,
) -> Callable:
    """
    Decorator for after hooks.

    After hooks execute after the main action and can:
    - Inspect results
    - Perform cleanup
    - Log outcomes
    - Trigger follow-up actions

    Args:
        hook_name: Name of hook point
        priority: Execution priority (higher = earlier)
        plugin_name: Name of plugin
        description: Description
        tags: Categorization tags
        auto_register: Auto-register hook

    Returns:
        Decorator function

    Example:
        @after_hook("match.completed", priority=50)
        async def save_match_result(context):
            match_id = context.data['match_id']
            winner = context.data['winner']
            await save_to_database(match_id, winner)

        @after_hook("tournament.completed")
        async def announce_winner(context):
            winner = context.data['champion']
            await send_notification(f"Tournament winner: {winner}")
    """
    return hook(
        hook_name=hook_name,
        hook_type=HookType.AFTER,
        priority=priority,
        plugin_name=plugin_name,
        description=description,
        tags=tags,
        auto_register=auto_register,
    )


def around_hook(
    hook_name: str,
    priority: int = HookPriority.NORMAL.value,
    plugin_name: str = "",
    description: str = "",
    tags: list[str] | None = None,
    auto_register: bool = True,
) -> Callable:
    """
    Decorator for around hooks.

    Around hooks wrap the main action and can:
    - Modify input before execution
    - Modify output after execution
    - Add timing/profiling
    - Implement caching
    - Handle errors

    Note: Around hooks receive a `next_hook` parameter which must be called
    to continue execution chain.

    Args:
        hook_name: Name of hook point
        priority: Execution priority (higher = earlier)
        plugin_name: Name of plugin
        description: Description
        tags: Categorization tags
        auto_register: Auto-register hook

    Returns:
        Decorator function

    Example:
        @around_hook("strategy.decide", priority=100)
        async def profile_decision(context, next_hook):
            import time
            start = time.time()

            # Call next hook in chain
            result = await next_hook(context) if next_hook else None

            # Record timing
            duration = time.time() - start
            context.set("decision_time_ms", duration * 1000)

            return result

        @around_hook("player.move.submit")
        async def cache_move(context, next_hook):
            move = context.data['move']

            # Check cache
            if cached_result := get_from_cache(move):
                return cached_result

            # Execute and cache
            result = await next_hook(context) if next_hook else None
            set_in_cache(move, result)

            return result
    """
    return hook(
        hook_name=hook_name,
        hook_type=HookType.AROUND,
        priority=priority,
        plugin_name=plugin_name,
        description=description,
        tags=tags,
        auto_register=auto_register,
    )


def filter_hook(
    hook_name: str,
    priority: int = HookPriority.NORMAL.value,
    plugin_name: str = "",
    description: str = "",
    tags: list[str] | None = None,
    auto_register: bool = True,
) -> Callable:
    """
    Decorator for filter hooks.

    Filter hooks modify data as it passes through the hook chain.
    Each filter receives the data, modifies it, and returns the modified version.

    Args:
        hook_name: Name of hook point
        priority: Execution priority (higher = earlier)
        plugin_name: Name of plugin
        description: Description
        tags: Categorization tags
        auto_register: Auto-register hook

    Returns:
        Decorator function

    Example:
        @filter_hook("player.move.validate")
        async def normalize_move(context):
            # Normalize move to valid range
            move = context.data.get('move', 5)
            normalized = max(1, min(10, move))
            context.set('move', normalized)
            return context

        @filter_hook("match.result.format")
        async def add_metadata(context):
            # Add metadata to result
            result = context.data
            result['timestamp'] = datetime.utcnow().isoformat()
            result['version'] = '1.0.0'
            context.data = result
            return context
    """
    return hook(
        hook_name=hook_name,
        hook_type=HookType.FILTER,
        priority=priority,
        plugin_name=plugin_name,
        description=description,
        tags=tags,
        auto_register=auto_register,
    )
