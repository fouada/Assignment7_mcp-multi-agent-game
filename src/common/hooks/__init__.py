"""
Hooks System
============

Production-grade hooks system for the MCP Multi-Agent Game League.

This module provides a comprehensive hooks framework inspired by WordPress,
VS Code, and pytest plugin systems.

Features:
- Before/after/around hook decorators
- Priority-based execution order
- Async and sync hook support
- Hook context passing and modification
- Error isolation and recovery
- Hook registration and discovery
- Performance profiling hooks

Usage:
    from src.common.hooks import HookManager, before_hook, after_hook

    # Get hook manager instance
    hook_manager = get_hook_manager()

    # Register a hook
    @before_hook("match.start", priority=10)
    async def log_match_start(context):
        print(f"Match starting: {context.match_id}")

    # Execute hooks
    await hook_manager.execute("match.start", context={"match_id": "M001"})

Hook Points:
    Agent Lifecycle:
    - agent.registered
    - agent.started
    - agent.stopped

    Match Lifecycle:
    - match.created
    - match.started
    - match.round.started
    - match.round.completed
    - match.completed

    Player Actions:
    - player.decision.before
    - player.decision.after
    - player.move.validate
    - player.move.submit

    Tournament Events:
    - tournament.started
    - tournament.round.started
    - tournament.round.completed
    - tournament.completed

    Strategy Events:
    - strategy.initialized
    - strategy.decision.before
    - strategy.decision.after
    - strategy.performance.recorded
"""

from .decorators import after_hook, around_hook, before_hook, hook
from .hook_manager import HookManager, get_hook_manager
from .types import (
    HookContext,
    HookExecutionMode,
    HookMetadata,
    HookPriority,
    HookResult,
    HookType,
)

__all__ = [
    # Manager
    "HookManager",
    "get_hook_manager",
    # Decorators
    "hook",
    "before_hook",
    "after_hook",
    "around_hook",
    # Types
    "HookContext",
    "HookType",
    "HookPriority",
    "HookMetadata",
    "HookResult",
    "HookExecutionMode",
]
