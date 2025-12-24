"""
Middleware System
=================

Production-grade middleware system for request/response processing.

Provides:
- Middleware base class for custom middleware
- MiddlewarePipeline for orchestrating middleware execution
- 8 built-in middleware for common use cases
- Request/Response context for data flow

Usage:
    from src.middleware import (
        MiddlewarePipeline,
        LoggingMiddleware,
        AuthenticationMiddleware,
        RateLimitMiddleware,
    )

    # Create pipeline
    pipeline = MiddlewarePipeline()

    # Add middleware
    pipeline.add_middleware(LoggingMiddleware(), priority=100)
    pipeline.add_middleware(AuthenticationMiddleware(required=True), priority=90)
    pipeline.add_middleware(RateLimitMiddleware(requests_per_minute=100), priority=80)

    # Execute request
    response = await pipeline.execute(request, handler=my_handler)
"""

from .base import (
    Middleware,
    RequestContext,
    ResponseContext,
    MiddlewareError,
    MiddlewareConfigError,
    MiddlewareTimeoutError,
    MiddlewareValidationError,
)
from .pipeline import MiddlewarePipeline, MiddlewareMetadata
from .builtin import (
    LoggingMiddleware,
    AuthenticationMiddleware,
    RateLimitMiddleware,
    MetricsMiddleware,
    ValidationMiddleware,
    CachingMiddleware,
    ErrorHandlerMiddleware,
    TracingMiddleware,
)

__all__ = [
    # Base classes
    "Middleware",
    "RequestContext",
    "ResponseContext",
    # Exceptions
    "MiddlewareError",
    "MiddlewareConfigError",
    "MiddlewareTimeoutError",
    "MiddlewareValidationError",
    # Pipeline
    "MiddlewarePipeline",
    "MiddlewareMetadata",
    # Built-in middleware
    "LoggingMiddleware",
    "AuthenticationMiddleware",
    "RateLimitMiddleware",
    "MetricsMiddleware",
    "ValidationMiddleware",
    "CachingMiddleware",
    "ErrorHandlerMiddleware",
    "TracingMiddleware",
]
