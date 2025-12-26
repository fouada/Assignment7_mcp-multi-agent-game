"""
Middleware Base Classes
=======================

Production-grade middleware abstractions for request/response processing.

Provides:
- Middleware: Base class for all middleware
- RequestContext: Request processing context
- ResponseContext: Response processing context
- MiddlewareError: Base exception for middleware errors

Middleware Pattern:
    Each middleware can:
    1. Process request before handler (before)
    2. Process response after handler (after)
    3. Handle errors (on_error)
    4. Short-circuit the pipeline (return response early)

Usage:
    class MyMiddleware(Middleware):
        async def before(self, context: RequestContext) -> RequestContext:
            # Modify request before handler
            context.state['timestamp'] = time.time()
            return context

        async def after(self, context: ResponseContext) -> ResponseContext:
            # Modify response after handler
            duration = time.time() - context.request.state['timestamp']
            context.response['duration_ms'] = duration * 1000
            return context
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# ============================================================================
# Context Classes
# ============================================================================


@dataclass
class RequestContext:
    """
    Request processing context.

    Flows through the middleware pipeline, allowing each middleware
    to inspect and modify the request.
    """

    # Original request data
    request: dict[str, Any]

    # Request metadata (headers, auth, etc.)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Shared state between middleware
    state: dict[str, Any] = field(default_factory=dict)

    # Client information
    client_id: str | None = None
    client_ip: str | None = None

    # Request timing
    received_at: datetime = field(default_factory=datetime.utcnow)

    # Short-circuit response (set by middleware to bypass handler)
    response: dict[str, Any] | None = None

    def set_response(self, response: dict[str, Any]) -> None:
        """
        Set a response to short-circuit the pipeline.

        When set, remaining middleware and the handler are skipped,
        and this response is returned immediately.
        """
        self.response = response

    def has_response(self) -> bool:
        """Check if a short-circuit response was set."""
        return self.response is not None


@dataclass
class ResponseContext:
    """
    Response processing context.

    Flows back through the middleware pipeline after handler execution,
    allowing each middleware to inspect and modify the response.
    """

    # Response data
    response: dict[str, Any]

    # Response metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    # Shared state from request (read-only access)
    state: dict[str, Any] = field(default_factory=dict)

    # Original request for reference
    request: RequestContext | None = None

    # Response timing
    completed_at: datetime = field(default_factory=datetime.utcnow)

    # Error information (if any)
    error: Exception | None = None
    error_handled: bool = False


# ============================================================================
# Middleware Base Class
# ============================================================================


class Middleware:
    """
    Base class for all middleware.

    Middleware can intercept and modify requests/responses in the pipeline.
    Each middleware can implement three hooks:

    1. before(context) - Process request before handler
    2. after(context) - Process response after handler
    3. on_error(context, error) - Handle errors

    Middleware execution order:
        Request Flow (before):
            M1.before → M2.before → M3.before → Handler

        Response Flow (after):
            Handler → M3.after → M2.after → M1.after

        Error Flow (on_error):
            Error → M3.on_error → M2.on_error → M1.on_error
    """

    def __init__(
        self,
        name: str | None = None,
        enabled: bool = True,
        config: dict[str, Any] | None = None,
    ):
        """
        Initialize middleware.

        Args:
            name: Middleware name (defaults to class name)
            enabled: Whether middleware is enabled
            config: Middleware-specific configuration
        """
        self.name = name or self.__class__.__name__
        self.enabled = enabled
        self.config = config or {}

    async def before(self, context: RequestContext) -> RequestContext:
        """
        Process request before handler execution.

        This method is called for each request in priority order (high to low).
        Middleware can:
        - Inspect and modify the request
        - Add metadata or state
        - Short-circuit by setting context.response
        - Raise exceptions to halt processing

        Args:
            context: Request context

        Returns:
            Modified request context

        Raises:
            MiddlewareError: If processing fails
        """
        return context

    async def after(self, context: ResponseContext) -> ResponseContext:
        """
        Process response after handler execution.

        This method is called for each response in reverse priority order.
        Middleware can:
        - Inspect and modify the response
        - Add metadata
        - Access request state
        - Raise exceptions for post-processing errors

        Args:
            context: Response context

        Returns:
            Modified response context

        Raises:
            MiddlewareError: If processing fails
        """
        return context

    async def on_error(
        self,
        context: RequestContext,
        error: Exception,
    ) -> dict[str, Any] | None:
        """
        Handle errors that occur during request processing.

        This method is called when an exception occurs in:
        - Another middleware
        - The handler
        - Response processing

        Middleware can:
        - Log the error
        - Transform the error into a response
        - Re-raise the error
        - Return None to let other middleware handle it

        Args:
            context: Request context at time of error
            error: The exception that occurred

        Returns:
            Optional response to use instead of error
            Return None to let error propagate
        """
        return None

    def __repr__(self) -> str:
        """String representation."""
        status = "enabled" if self.enabled else "disabled"
        return f"<{self.name} ({status})>"


# ============================================================================
# Middleware Exceptions
# ============================================================================


class MiddlewareError(Exception):
    """Base exception for middleware errors."""

    def __init__(
        self,
        message: str,
        middleware_name: str | None = None,
        original_error: Exception | None = None,
    ):
        super().__init__(message)
        self.middleware_name = middleware_name
        self.original_error = original_error


class MiddlewareConfigError(MiddlewareError):
    """Middleware configuration error."""

    pass


class MiddlewareTimeoutError(MiddlewareError):
    """Middleware execution timeout."""

    pass


class MiddlewareValidationError(MiddlewareError):
    """Middleware validation error."""

    pass


# ============================================================================
# Handler Type Aliases
# ============================================================================


# Type alias for request handlers
RequestHandler = Callable[[dict[str, Any]], dict[str, Any]]
AsyncRequestHandler = Callable[[dict[str, Any]], Any]  # Returns awaitable
