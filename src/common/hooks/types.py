"""
Hook Types and Data Structures
================================

Type definitions for the hooks system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional


class HookType(Enum):
    """Hook execution type."""

    BEFORE = "before"  # Execute before main action
    AFTER = "after"  # Execute after main action
    AROUND = "around"  # Wraps main action (can modify input/output)
    FILTER = "filter"  # Modify data before passing to next hook
    ACTION = "action"  # Side effect only, no data modification


class HookPriority(Enum):
    """Standard hook priorities."""

    HIGHEST = 100  # Critical hooks that must run first
    HIGH = 75  # High priority hooks
    NORMAL = 50  # Default priority
    LOW = 25  # Low priority hooks
    LOWEST = 10  # Hooks that should run last


class HookExecutionMode(Enum):
    """Hook execution mode."""

    SEQUENTIAL = "sequential"  # Execute hooks one by one
    PARALLEL = "parallel"  # Execute hooks in parallel (async only)
    FIRST_SUCCESS = "first_success"  # Stop after first successful hook
    FIRST_FAILURE = "first_failure"  # Stop after first failed hook


@dataclass
class HookMetadata:
    """
    Metadata for a registered hook.

    Attributes:
        hook_id: Unique identifier for this hook instance
        hook_name: Name of the hook point (e.g., "match.started")
        hook_type: Type of hook (before, after, around, etc.)
        handler: The callable function/method
        priority: Execution priority (higher = earlier)
        is_async: Whether handler is async
        plugin_name: Name of plugin that registered this hook
        description: Human-readable description
        tags: Categorization tags
        enabled: Whether hook is currently enabled
        registered_at: When hook was registered
        execution_count: Number of times hook has been executed
        total_execution_time: Total time spent executing hook (ms)
        last_execution_time: Last execution timestamp
        last_error: Last error encountered (if any)
    """

    hook_id: str
    hook_name: str
    hook_type: HookType
    handler: Callable
    priority: int = HookPriority.NORMAL.value
    is_async: bool = True
    plugin_name: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    enabled: bool = True

    # Statistics
    registered_at: datetime = field(default_factory=datetime.utcnow)
    execution_count: int = 0
    total_execution_time: float = 0.0
    last_execution_time: Optional[datetime] = None
    last_error: Optional[Exception] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hook_id": self.hook_id,
            "hook_name": self.hook_name,
            "hook_type": self.hook_type.value,
            "priority": self.priority,
            "is_async": self.is_async,
            "plugin_name": self.plugin_name,
            "description": self.description,
            "tags": self.tags,
            "enabled": self.enabled,
            "registered_at": self.registered_at.isoformat(),
            "execution_count": self.execution_count,
            "total_execution_time": self.total_execution_time,
            "last_execution_time": self.last_execution_time.isoformat()
            if self.last_execution_time
            else None,
            "last_error": str(self.last_error) if self.last_error else None,
        }


@dataclass
class HookContext:
    """
    Context passed to hook handlers.

    Provides access to:
    - Original event data
    - Modified data from previous hooks
    - System resources
    - Hook execution metadata

    Attributes:
        event_name: Name of the event that triggered hooks
        data: Event data (can be modified by hooks)
        original_data: Original event data (immutable)
        metadata: Hook execution metadata
        cancelled: Whether execution should be cancelled
        error: Error encountered during execution
    """

    event_name: str
    data: dict[str, Any] = field(default_factory=dict)
    original_data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    cancelled: bool = False
    error: Optional[Exception] = None

    def __post_init__(self):
        """Initialize original_data if not provided."""
        if not self.original_data:
            self.original_data = self.data.copy()

    def get(self, key: str, default: Any = None) -> Any:
        """Get data value by key."""
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set data value by key."""
        self.data[key] = value

    def has(self, key: str) -> bool:
        """Check if key exists in data."""
        return key in self.data

    def cancel(self, reason: str = "") -> None:
        """Cancel execution."""
        self.cancelled = True
        self.metadata["cancel_reason"] = reason

    def is_cancelled(self) -> bool:
        """Check if execution is cancelled."""
        return self.cancelled

    def set_error(self, error: Exception) -> None:
        """Set error."""
        self.error = error
        self.metadata["error"] = str(error)

    def has_error(self) -> bool:
        """Check if error occurred."""
        return self.error is not None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_name": self.event_name,
            "data": self.data,
            "metadata": self.metadata,
            "cancelled": self.cancelled,
            "error": str(self.error) if self.error else None,
        }


@dataclass
class HookResult:
    """
    Result of hook execution.

    Attributes:
        success: Whether all hooks executed successfully
        context: Final hook context after all hooks
        hooks_executed: Number of hooks executed
        execution_time: Total execution time (ms)
        errors: List of errors encountered
        cancelled: Whether execution was cancelled
        results: Individual hook results
    """

    success: bool
    context: HookContext
    hooks_executed: int = 0
    execution_time: float = 0.0
    errors: list[Exception] = field(default_factory=list)
    cancelled: bool = False
    results: list[Any] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "context": self.context.to_dict(),
            "hooks_executed": self.hooks_executed,
            "execution_time": self.execution_time,
            "errors": [str(e) for e in self.errors],
            "cancelled": self.cancelled,
            "results": self.results,
        }


# Hook function signature
HookHandler = Callable[[HookContext], Any]
AsyncHookHandler = Callable[[HookContext], Any]  # Returns coroutine
