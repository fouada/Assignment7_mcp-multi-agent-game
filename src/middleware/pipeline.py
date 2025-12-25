"""
Middleware Pipeline
===================

Production-grade middleware pipeline for orchestrating request/response processing.

Features:
- Priority-based middleware execution
- Request → Handler → Response flow
- Error handling and recovery
- Middleware enable/disable
- Execution timeout
- Performance metrics

Usage:
    pipeline = MiddlewarePipeline()

    # Add middleware
    pipeline.add_middleware(LoggingMiddleware(), priority=100)
    pipeline.add_middleware(AuthMiddleware(), priority=90)

    # Execute request
    response = await pipeline.execute(request, handler=my_handler)
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from ..common.logger import get_logger
from .base import (
    AsyncRequestHandler,
    Middleware,
    MiddlewareTimeoutError,
    RequestContext,
    ResponseContext,
)

logger = get_logger(__name__)


# ============================================================================
# Middleware Metadata
# ============================================================================


@dataclass
class MiddlewareMetadata:
    """Metadata for registered middleware."""

    middleware: Middleware
    priority: int = 0
    enabled: bool = True
    tags: list[str] = field(default_factory=list)

    # Statistics
    total_requests: int = 0
    total_errors: int = 0
    total_time_ms: float = 0.0


# ============================================================================
# Middleware Pipeline
# ============================================================================


class MiddlewarePipeline:
    """
    Middleware pipeline for request/response processing.

    Manages middleware lifecycle and orchestrates request flow:
        Request → M1.before → M2.before → Handler → M2.after → M1.after → Response

    Features:
    - Priority-based execution (higher = earlier)
    - Middleware enable/disable without removal
    - Error handling with on_error hooks
    - Short-circuit support (bypass remaining middleware)
    - Request/response timing
    - Execution statistics
    """

    def __init__(
        self,
        timeout_seconds: float = 30.0,
        error_handling: str = "continue",  # "continue", "stop", "raise"
    ):
        """
        Initialize middleware pipeline.

        Args:
            timeout_seconds: Maximum execution time for entire pipeline
            error_handling: How to handle middleware errors
                - "continue": Log error, continue to next middleware
                - "stop": Stop pipeline, return error response
                - "raise": Re-raise exception
        """
        self._middleware: list[MiddlewareMetadata] = []
        self._timeout_seconds = timeout_seconds
        self._error_handling = error_handling

        # Statistics
        self._stats = {
            "total_requests": 0,
            "total_errors": 0,
            "total_timeouts": 0,
        }

    def add_middleware(
        self,
        middleware: Middleware,
        priority: int = 0,
        tags: list[str] | None = None,
    ) -> str:
        """
        Add middleware to the pipeline.

        Args:
            middleware: Middleware instance
            priority: Execution priority (higher = earlier)
            tags: Optional tags for categorization

        Returns:
            Middleware name for later reference
        """
        metadata = MiddlewareMetadata(
            middleware=middleware,
            priority=priority,
            enabled=middleware.enabled,
            tags=tags or [],
        )

        self._middleware.append(metadata)

        # Sort by priority (descending)
        self._middleware.sort(key=lambda m: m.priority, reverse=True)

        logger.debug(
            f"Added middleware: {middleware.name} (priority={priority})"
        )

        return middleware.name

    def remove_middleware(self, name: str) -> bool:
        """
        Remove middleware from pipeline.

        Args:
            name: Middleware name

        Returns:
            True if removed, False if not found
        """
        initial_count = len(self._middleware)
        self._middleware = [
            m for m in self._middleware if m.middleware.name != name
        ]

        removed = len(self._middleware) < initial_count

        if removed:
            logger.debug(f"Removed middleware: {name}")

        return removed

    def enable_middleware(self, name: str) -> bool:
        """
        Enable middleware without removing it.

        Args:
            name: Middleware name

        Returns:
            True if enabled, False if not found
        """
        for metadata in self._middleware:
            if metadata.middleware.name == name:
                metadata.enabled = True
                metadata.middleware.enabled = True
                logger.debug(f"Enabled middleware: {name}")
                return True
        return False

    def disable_middleware(self, name: str) -> bool:
        """
        Disable middleware without removing it.

        Args:
            name: Middleware name

        Returns:
            True if disabled, False if not found
        """
        for metadata in self._middleware:
            if metadata.middleware.name == name:
                metadata.enabled = False
                metadata.middleware.enabled = False
                logger.debug(f"Disabled middleware: {name}")
                return True
        return False

    async def execute(
        self,
        request: dict[str, Any],
        handler: AsyncRequestHandler,
        **handler_kwargs,
    ) -> dict[str, Any]:
        """
        Execute request through middleware pipeline.

        Flow:
            1. Create request context
            2. Run before hooks (high to low priority)
            3. Execute handler (if not short-circuited)
            4. Run after hooks (low to high priority)
            5. Return response

        Args:
            request: Request data
            handler: Request handler function
            **handler_kwargs: Additional kwargs for handler

        Returns:
            Response data

        Raises:
            MiddlewareTimeoutError: If execution exceeds timeout
            MiddlewareError: If error_handling is "raise"
        """
        self._stats["total_requests"] += 1
        start_time = time.time()

        # Create request context
        context = RequestContext(
            request=request,
            metadata={},
            state={},
        )

        try:
            # Execute with timeout
            response = await asyncio.wait_for(
                self._execute_pipeline(context, handler, handler_kwargs),
                timeout=self._timeout_seconds,
            )

            return response

        except TimeoutError:
            self._stats["total_timeouts"] += 1
            logger.error(
                f"Middleware pipeline timeout after {self._timeout_seconds}s"
            )
            raise MiddlewareTimeoutError(
                f"Pipeline execution exceeded {self._timeout_seconds}s timeout"
            ) from None

        except Exception as e:
            self._stats["total_errors"] += 1
            logger.error(f"Pipeline execution error: {e}")

            if self._error_handling == "raise":
                raise

            # Return error response
            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "middleware_error": True,
            }

        finally:
            duration = (time.time() - start_time) * 1000
            logger.debug(f"Pipeline execution completed in {duration:.2f}ms")

    async def _execute_pipeline(
        self,
        context: RequestContext,
        handler: AsyncRequestHandler,
        handler_kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute the full middleware pipeline.

        Args:
            context: Request context
            handler: Request handler
            handler_kwargs: Handler kwargs

        Returns:
            Response data
        """
        # Get enabled middleware
        enabled_middleware = [
            m for m in self._middleware if m.enabled
        ]

        # Phase 1: Before hooks (high to low priority)
        for metadata in enabled_middleware:
            if context.has_response():
                # Short-circuit: skip remaining before hooks
                break

            try:
                start = time.time()
                context = await metadata.middleware.before(context)
                duration = (time.time() - start) * 1000

                metadata.total_requests += 1
                metadata.total_time_ms += duration

            except Exception as e:
                logger.error(
                    f"Error in {metadata.middleware.name}.before: {e}"
                )

                # Try error handler
                error_response = await self._handle_error(
                    context, e, enabled_middleware
                )

                if error_response:
                    return error_response

                if self._error_handling == "raise":
                    raise
                elif self._error_handling == "stop":
                    return self._create_error_response(e, metadata.middleware.name)

        # Phase 2: Execute handler (if not short-circuited)
        if context.has_response():
            response_data = context.response
        else:
            try:
                response_data = await handler(context.request, **handler_kwargs)
            except Exception as e:
                logger.error(f"Error in handler: {e}")

                # Try error handlers
                error_response = await self._handle_error(
                    context, e, enabled_middleware
                )

                if error_response:
                    return error_response

                if self._error_handling == "raise":
                    raise

                return self._create_error_response(e, "handler")

        # Create response context
        response_context = ResponseContext(
            response=response_data,
            metadata={},
            state=context.state,
            request=context,
        )

        # Phase 3: After hooks (low to high priority - reverse order)
        for metadata in reversed(enabled_middleware):
            try:
                start = time.time()
                response_context = await metadata.middleware.after(response_context)
                duration = (time.time() - start) * 1000

                metadata.total_time_ms += duration

            except Exception as e:
                logger.error(
                    f"Error in {metadata.middleware.name}.after: {e}"
                )
                metadata.total_errors += 1

                if self._error_handling == "raise":
                    raise
                elif self._error_handling == "stop":
                    return self._create_error_response(e, metadata.middleware.name)

        return response_context.response

    async def _handle_error(
        self,
        context: RequestContext,
        error: Exception,
        middleware_list: list[MiddlewareMetadata],
    ) -> dict[str, Any] | None:
        """
        Handle error using middleware error handlers.

        Args:
            context: Request context
            error: Exception that occurred
            middleware_list: List of enabled middleware

        Returns:
            Optional error response from middleware
        """
        # Call on_error hooks in reverse order
        for metadata in reversed(middleware_list):
            try:
                error_response = await metadata.middleware.on_error(context, error)
                if error_response:
                    return error_response
            except Exception as e:
                logger.error(
                    f"Error in {metadata.middleware.name}.on_error: {e}"
                )

        return None

    def _create_error_response(
        self,
        error: Exception,
        source: str,
    ) -> dict[str, Any]:
        """Create standardized error response."""
        return {
            "error": str(error),
            "error_type": type(error).__name__,
            "source": source,
            "middleware_error": True,
        }

    def get_middleware_list(self) -> list[dict[str, Any]]:
        """
        Get list of registered middleware.

        Returns:
            List of middleware info dicts
        """
        return [
            {
                "name": m.middleware.name,
                "priority": m.priority,
                "enabled": m.enabled,
                "tags": m.tags,
                "stats": {
                    "total_requests": m.total_requests,
                    "total_errors": m.total_errors,
                    "avg_time_ms": (
                        m.total_time_ms / m.total_requests
                        if m.total_requests > 0
                        else 0
                    ),
                },
            }
            for m in self._middleware
        ]

    def get_stats(self) -> dict[str, Any]:
        """
        Get pipeline statistics.

        Returns:
            Statistics dict
        """
        return self._stats.copy()

    def clear(self):
        """Clear all middleware (for testing)."""
        self._middleware.clear()
        logger.debug("Cleared middleware pipeline")
