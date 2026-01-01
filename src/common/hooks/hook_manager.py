"""
Hook Manager
============

Central hook registration and execution manager.

This is the core of the hooks system, responsible for:
- Registering hooks from plugins
- Executing hooks in priority order
- Managing hook lifecycle
- Providing hook discovery and introspection
- Performance profiling and monitoring
"""

import asyncio
import fnmatch
import inspect
import time
import traceback
from collections import defaultdict
from typing import Any, Callable, Optional
from uuid import uuid4

from ..logger import get_logger
from .types import (
    HookContext,
    HookExecutionMode,
    HookMetadata,
    HookPriority,
    HookResult,
    HookType,
)

logger = get_logger(__name__)


class HookManager:
    """
    Central hook manager for the plugin system.

    Manages registration, execution, and lifecycle of all hooks.
    Singleton pattern ensures single manager instance.

    Example:
        # Get manager
        manager = get_hook_manager()

        # Register a hook
        hook_id = manager.register(
            hook_name="match.started",
            handler=my_handler,
            priority=HookPriority.HIGH.value
        )

        # Execute hooks
        result = await manager.execute(
            "match.started",
            context_data={"match_id": "M001"}
        )

        # Unregister hook
        manager.unregister(hook_id)
    """

    _instance: Optional["HookManager"] = None

    def __new__(cls) -> "HookManager":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize hook manager."""
        if self._initialized:
            return

        # Hook storage: hook_name -> list of HookMetadata
        self._hooks: dict[str, list[HookMetadata]] = defaultdict(list)

        # Hook registry: hook_id -> HookMetadata
        self._registry: dict[str, HookMetadata] = {}

        # Configuration
        self._enabled = True
        self._default_execution_mode = HookExecutionMode.SEQUENTIAL
        self._error_handling = "isolate"  # "isolate", "propagate", "stop"
        self._max_execution_time = 30.0  # seconds
        self._profiling_enabled = True

        # Statistics
        self._stats = {
            "total_hooks": 0,
            "total_executions": 0,
            "total_errors": 0,
            "total_execution_time": 0.0,
        }

        self._initialized = True
        logger.debug("HookManager initialized")

    def configure(
        self,
        enabled: bool = True,
        default_execution_mode: HookExecutionMode = HookExecutionMode.SEQUENTIAL,
        error_handling: str = "isolate",
        max_execution_time: float = 30.0,
        profiling_enabled: bool = True,
    ):
        """
        Configure hook manager behavior.

        Args:
            enabled: Whether hook execution is enabled
            default_execution_mode: Default execution mode for hooks
            error_handling: Error handling strategy ("isolate", "propagate", "stop")
            max_execution_time: Maximum execution time for hooks (seconds)
            profiling_enabled: Whether to enable performance profiling
        """
        self._enabled = enabled
        self._default_execution_mode = default_execution_mode
        self._error_handling = error_handling
        self._max_execution_time = max_execution_time
        self._profiling_enabled = profiling_enabled

        logger.info(
            f"HookManager configured: enabled={enabled}, "
            f"error_handling={error_handling}, profiling={profiling_enabled}"
        )

    def register(
        self,
        hook_name: str,
        handler: Callable,
        hook_type: HookType = HookType.ACTION,
        priority: int = HookPriority.NORMAL.value,
        plugin_name: str = "",
        description: str = "",
        tags: list[str] | None = None,
    ) -> str:
        """
        Register a hook handler.

        Args:
            hook_name: Name of hook point (e.g., "match.started")
            handler: Callable to execute
            hook_type: Type of hook (before, after, around, etc.)
            priority: Execution priority (higher = earlier)
            plugin_name: Name of plugin registering this hook
            description: Human-readable description
            tags: Categorization tags

        Returns:
            Hook ID for later reference

        Example:
            hook_id = manager.register(
                hook_name="match.started",
                handler=log_match_start,
                hook_type=HookType.BEFORE,
                priority=100,
                plugin_name="logging_plugin"
            )
        """
        # Generate hook ID
        hook_id = str(uuid4())

        # Detect if async
        is_async = inspect.iscoroutinefunction(handler)

        # Create metadata
        metadata = HookMetadata(
            hook_id=hook_id,
            hook_name=hook_name,
            hook_type=hook_type,
            handler=handler,
            priority=priority,
            is_async=is_async,
            plugin_name=plugin_name,
            description=description,
            tags=tags or [],
        )

        # Add to hooks list
        self._hooks[hook_name].append(metadata)

        # Sort by priority (descending)
        self._hooks[hook_name].sort(key=lambda h: h.priority, reverse=True)

        # Add to registry
        self._registry[hook_id] = metadata

        # Update stats
        self._stats["total_hooks"] += 1

        logger.debug(
            f"Hook registered: {hook_id} for '{hook_name}' "
            f"(priority={priority}, async={is_async}, plugin={plugin_name})"
        )

        return hook_id

    def unregister(self, hook_id: str) -> bool:
        """
        Unregister a hook.

        Args:
            hook_id: Hook ID returned by register()

        Returns:
            True if unregistered, False if not found
        """
        if hook_id not in self._registry:
            logger.warning(f"Hook {hook_id} not found for unregistration")
            return False

        metadata = self._registry.pop(hook_id)

        # Remove from hooks list
        if metadata.hook_name in self._hooks:
            self._hooks[metadata.hook_name] = [
                h for h in self._hooks[metadata.hook_name] if h.hook_id != hook_id
            ]

            # Clean up empty lists
            if not self._hooks[metadata.hook_name]:
                del self._hooks[metadata.hook_name]

        # Update stats
        self._stats["total_hooks"] -= 1

        logger.debug(f"Hook unregistered: {hook_id} for '{metadata.hook_name}'")
        return True

    def get_hooks(
        self,
        hook_name: str | None = None,
        plugin_name: str | None = None,
        enabled_only: bool = False,
    ) -> list[HookMetadata]:
        """
        Get registered hooks matching criteria.

        Args:
            hook_name: Filter by hook name (supports wildcards)
            plugin_name: Filter by plugin name
            enabled_only: Only return enabled hooks

        Returns:
            List of matching hook metadata
        """
        hooks = []

        if hook_name:
            # Match by name (with wildcards)
            for name, hook_list in self._hooks.items():
                if fnmatch.fnmatch(name, hook_name):
                    hooks.extend(hook_list)
        else:
            # All hooks
            for hook_list in self._hooks.values():
                hooks.extend(hook_list)

        # Filter by plugin
        if plugin_name:
            hooks = [h for h in hooks if h.plugin_name == plugin_name]

        # Filter by enabled
        if enabled_only:
            hooks = [h for h in hooks if h.enabled]

        return hooks

    async def execute(
        self,
        hook_name: str,
        context_data: dict[str, Any] | None = None,
        execution_mode: HookExecutionMode | None = None,
        timeout: float | None = None,
    ) -> HookResult:
        """
        Execute all hooks for a given hook point.

        Args:
            hook_name: Name of hook point
            context_data: Data to pass to hooks
            execution_mode: How to execute hooks (default: sequential)
            timeout: Maximum execution time (default: from config)

        Returns:
            HookResult with execution details

        Example:
            result = await manager.execute(
                "match.started",
                context_data={"match_id": "M001", "players": ["P1", "P2"]}
            )

            if result.success:
                print(f"Executed {result.hooks_executed} hooks")
        """
        if not self._enabled:
            return HookResult(
                success=True, context=HookContext(event_name=hook_name), hooks_executed=0
            )

        # Create context
        context = HookContext(event_name=hook_name, data=context_data or {})

        # Get matching hooks
        hooks = self.get_hooks(hook_name=hook_name, enabled_only=True)

        if not hooks:
            logger.debug(f"No hooks registered for '{hook_name}'")
            return HookResult(success=True, context=context, hooks_executed=0)

        logger.debug(f"Executing {len(hooks)} hooks for '{hook_name}'")

        # Use default execution mode if not specified
        mode = execution_mode or self._default_execution_mode
        timeout_val = timeout or self._max_execution_time

        # Start timing
        start_time = time.time()

        try:
            # Execute based on mode
            if mode == HookExecutionMode.SEQUENTIAL:
                result = await self._execute_sequential(hooks, context, timeout_val)
            elif mode == HookExecutionMode.PARALLEL:
                result = await self._execute_parallel(hooks, context, timeout_val)
            elif mode == HookExecutionMode.FIRST_SUCCESS:
                result = await self._execute_first_success(hooks, context, timeout_val)
            elif mode == HookExecutionMode.FIRST_FAILURE:
                result = await self._execute_first_failure(hooks, context, timeout_val)
            else:
                result = await self._execute_sequential(hooks, context, timeout_val)

            # Calculate execution time
            execution_time = (time.time() - start_time) * 1000  # ms
            result.execution_time = execution_time

            # Update stats
            self._stats["total_executions"] += 1
            self._stats["total_execution_time"] += execution_time
            if result.errors:
                self._stats["total_errors"] += len(result.errors)

            return result

        except Exception as e:
            logger.error(f"Hook execution failed for '{hook_name}': {e}\n{traceback.format_exc()}")
            return HookResult(
                success=False,
                context=context,
                hooks_executed=0,
                errors=[e],
                execution_time=(time.time() - start_time) * 1000,
            )

    async def _execute_sequential(
        self, hooks: list[HookMetadata], context: HookContext, timeout: float
    ) -> HookResult:
        """Execute hooks sequentially."""
        results = []
        errors = []
        executed = 0

        for hook_meta in hooks:
            if context.is_cancelled():
                break

            try:
                # Execute hook with timeout
                if hook_meta.is_async:
                    result = await asyncio.wait_for(
                        hook_meta.handler(context), timeout=timeout
                    )
                else:
                    # Run sync handler in executor
                    loop = asyncio.get_event_loop()
                    result = await asyncio.wait_for(
                        loop.run_in_executor(None, hook_meta.handler, context),
                        timeout=timeout,
                    )

                results.append(result)
                executed += 1

                # Update hook stats
                hook_meta.execution_count += 1
                hook_meta.last_execution_time = None  # Will be set by datetime.utcnow()

            except asyncio.TimeoutError:
                error = TimeoutError(f"Hook {hook_meta.hook_id} exceeded timeout of {timeout}s")
                errors.append(error)
                logger.error(f"Hook timeout: {hook_meta.hook_name} ({hook_meta.plugin_name})")

                if self._error_handling == "stop":
                    break
                elif self._error_handling == "propagate":
                    raise

            except Exception as e:
                errors.append(e)
                hook_meta.last_error = e
                logger.error(
                    f"Hook error: {hook_meta.hook_name} ({hook_meta.plugin_name}): {e}"
                )

                if self._error_handling == "stop":
                    break
                elif self._error_handling == "propagate":
                    raise

        return HookResult(
            success=len(errors) == 0,
            context=context,
            hooks_executed=executed,
            errors=errors,
            results=results,
            cancelled=context.is_cancelled(),
        )

    async def _execute_parallel(
        self, hooks: list[HookMetadata], context: HookContext, timeout: float
    ) -> HookResult:
        """Execute hooks in parallel."""
        tasks = []

        for hook_meta in hooks:
            if hook_meta.is_async:
                task = asyncio.create_task(hook_meta.handler(context))
            else:
                # Wrap sync handler
                loop = asyncio.get_event_loop()
                task = asyncio.create_task(loop.run_in_executor(None, hook_meta.handler, context))

            tasks.append((hook_meta, task))

        # Wait for all with timeout
        results = []
        errors = []

        try:
            done, pending = await asyncio.wait(
                [task for _, task in tasks], timeout=timeout, return_when=asyncio.ALL_COMPLETED
            )

            # Process results
            for hook_meta, task in tasks:
                try:
                    if task in done:
                        result = task.result()
                        results.append(result)
                        hook_meta.execution_count += 1
                    else:
                        # Timeout
                        task.cancel()
                        errors.append(
                            TimeoutError(f"Hook {hook_meta.hook_id} exceeded timeout")
                        )
                except Exception as e:
                    errors.append(e)
                    hook_meta.last_error = e

        except Exception as e:
            errors.append(e)

        return HookResult(
            success=len(errors) == 0,
            context=context,
            hooks_executed=len(results),
            errors=errors,
            results=results,
        )

    async def _execute_first_success(
        self, hooks: list[HookMetadata], context: HookContext, timeout: float
    ) -> HookResult:
        """Execute hooks until first success."""
        for hook_meta in hooks:
            try:
                if hook_meta.is_async:
                    result = await asyncio.wait_for(
                        hook_meta.handler(context), timeout=timeout
                    )
                else:
                    loop = asyncio.get_event_loop()
                    result = await asyncio.wait_for(
                        loop.run_in_executor(None, hook_meta.handler, context),
                        timeout=timeout,
                    )

                # Success - stop here
                hook_meta.execution_count += 1
                return HookResult(
                    success=True,
                    context=context,
                    hooks_executed=1,
                    results=[result],
                )

            except Exception as e:
                hook_meta.last_error = e
                logger.debug(f"Hook failed, trying next: {hook_meta.hook_name}")
                continue

        # No hooks succeeded
        return HookResult(
            success=False,
            context=context,
            hooks_executed=len(hooks),
            errors=[Exception("No hooks succeeded")],
        )

    async def _execute_first_failure(
        self, hooks: list[HookMetadata], context: HookContext, timeout: float
    ) -> HookResult:
        """Execute hooks until first failure."""
        results = []
        executed = 0

        for hook_meta in hooks:
            try:
                if hook_meta.is_async:
                    result = await asyncio.wait_for(
                        hook_meta.handler(context), timeout=timeout
                    )
                else:
                    loop = asyncio.get_event_loop()
                    result = await asyncio.wait_for(
                        loop.run_in_executor(None, hook_meta.handler, context),
                        timeout=timeout,
                    )

                results.append(result)
                executed += 1
                hook_meta.execution_count += 1

            except Exception as e:
                # Failure - stop here
                hook_meta.last_error = e
                return HookResult(
                    success=False,
                    context=context,
                    hooks_executed=executed,
                    errors=[e],
                    results=results,
                )

        # All hooks succeeded
        return HookResult(
            success=True,
            context=context,
            hooks_executed=executed,
            results=results,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get hook manager statistics."""
        return {
            **self._stats,
            "hook_points": len(self._hooks),
            "enabled": self._enabled,
            "execution_mode": self._default_execution_mode.value,
        }

    def clear(self):
        """Clear all hooks (for testing)."""
        self._hooks.clear()
        self._registry.clear()
        self._stats["total_hooks"] = 0
        logger.debug("All hooks cleared")

    def reset(self):
        """Reset hook manager to initial state (for testing)."""
        self.clear()
        self._stats = {
            "total_hooks": 0,
            "total_executions": 0,
            "total_errors": 0,
            "total_execution_time": 0.0,
        }
        logger.debug("HookManager reset")


# Global instance
_hook_manager: HookManager | None = None


def get_hook_manager() -> HookManager:
    """
    Get the global HookManager instance.

    Returns:
        Singleton HookManager instance
    """
    global _hook_manager
    if _hook_manager is None:
        _hook_manager = HookManager()
    return _hook_manager
