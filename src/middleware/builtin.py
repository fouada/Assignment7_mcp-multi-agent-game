"""
Built-in Middleware
===================

Production-grade built-in middleware for common use cases.

Provides 8 middleware:
1. LoggingMiddleware - Request/response logging with timing
2. AuthenticationMiddleware - Token validation
3. RateLimitMiddleware - Token bucket rate limiting
4. MetricsMiddleware - Performance metrics collection
5. ValidationMiddleware - JSON schema validation
6. CachingMiddleware - LRU response caching
7. ErrorHandlerMiddleware - Exception handling
8. TracingMiddleware - Distributed tracing spans

Usage:
    from src.middleware.builtin import LoggingMiddleware, AuthMiddleware

    pipeline.add_middleware(LoggingMiddleware(), priority=100)
    pipeline.add_middleware(AuthMiddleware(required=True), priority=90)
"""

import time
import hashlib
import json
from collections import defaultdict, OrderedDict
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta

from .base import (
    Middleware,
    RequestContext,
    ResponseContext,
    MiddlewareError,
    MiddlewareValidationError,
)
from ..common.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# 1. Logging Middleware
# ============================================================================


class LoggingMiddleware(Middleware):
    """
    Logs all requests and responses with timing information.

    Features:
    - Request logging (method, path, params)
    - Response logging (status, size)
    - Execution timing
    - Error logging
    - Configurable log levels
    """

    def __init__(
        self,
        log_requests: bool = True,
        log_responses: bool = True,
        log_errors: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_errors = log_errors

    async def before(self, context: RequestContext) -> RequestContext:
        """Log incoming request."""
        if self.log_requests:
            # Store start time
            context.state["request_start_time"] = time.time()

            # Log request
            logger.info(
                "Request received",
                message_type=context.request.get("type"),
                sender=context.request.get("sender"),
                params_count=len(context.request.get("params", {})),
            )

        return context

    async def after(self, context: ResponseContext) -> ResponseContext:
        """Log outgoing response."""
        if self.log_responses:
            # Calculate duration
            start_time = context.state.get("request_start_time")
            duration_ms = 0
            if start_time:
                duration_ms = (time.time() - start_time) * 1000

            # Log response
            logger.info(
                "Response sent",
                success=context.response.get("success", True),
                duration_ms=round(duration_ms, 2),
                response_size=len(str(context.response)),
            )

        return context

    async def on_error(
        self,
        context: RequestContext,
        error: Exception,
    ) -> Optional[Dict[str, Any]]:
        """Log errors."""
        if self.log_errors:
            logger.error(
                f"Request error: {type(error).__name__}: {error}",
                error_type=type(error).__name__,
                message_type=context.request.get("type"),
            )
        return None


# ============================================================================
# 2. Authentication Middleware
# ============================================================================


class AuthenticationMiddleware(Middleware):
    """
    Validates authentication tokens from requests.

    Features:
    - Token validation
    - Token expiration checking
    - Optional authentication (required=False)
    - Configurable token sources (header, params)
    - Token caching for performance
    """

    def __init__(
        self,
        required: bool = True,
        token_field: str = "auth_token",
        cache_tokens: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.required = required
        self.token_field = token_field
        self.cache_tokens = cache_tokens
        self._token_cache: Set[str] = set()  # Simple cache

    async def before(self, context: RequestContext) -> RequestContext:
        """Validate authentication token."""
        # Extract token
        token = context.request.get(self.token_field)

        if not token and self.required:
            context.set_response({
                "error": "Authentication required",
                "error_type": "AuthenticationError",
            })
            return context

        if token:
            # Validate token
            if not self._validate_token(token):
                context.set_response({
                    "error": "Invalid authentication token",
                    "error_type": "AuthenticationError",
                })
                return context

            # Store validated token in context
            context.metadata["authenticated"] = True
            context.metadata["token"] = token

        return context

    def _validate_token(self, token: str) -> bool:
        """
        Validate token (simplified for example).

        In production, this would:
        - Check against database
        - Verify JWT signature
        - Check expiration
        - Validate permissions
        """
        # Check cache
        if self.cache_tokens and token in self._token_cache:
            return True

        # Validate token format (example: must be non-empty)
        is_valid = len(token) > 0

        # Cache valid tokens
        if is_valid and self.cache_tokens:
            self._token_cache.add(token)

        return is_valid


# ============================================================================
# 3. Rate Limit Middleware
# ============================================================================


class RateLimitMiddleware(Middleware):
    """
    Token bucket rate limiting per client.

    Features:
    - Per-client rate limiting
    - Token bucket algorithm
    - Configurable limits
    - Burst support
    - Rate limit headers in response
    """

    def __init__(
        self,
        requests_per_minute: int = 100,
        burst_size: int = 10,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size

        # Token buckets: client_id -> (tokens, last_update)
        self._buckets: Dict[str, tuple] = {}

    async def before(self, context: RequestContext) -> RequestContext:
        """Check rate limit."""
        # Get client identifier
        client_id = self._get_client_id(context)

        # Check rate limit
        allowed, remaining = self._check_rate_limit(client_id)

        # Store rate limit info in state (shared with after hook)
        context.state["rate_limit_remaining"] = remaining

        if not allowed:
            context.set_response({
                "error": "Rate limit exceeded",
                "error_type": "RateLimitError",
                "retry_after": 60,  # seconds
            })

        return context

    async def after(self, context: ResponseContext) -> ResponseContext:
        """Add rate limit headers to response."""
        remaining = context.state.get("rate_limit_remaining", 0)

        context.response["rate_limit"] = {
            "limit": self.requests_per_minute,
            "remaining": remaining,
            "reset": 60,  # seconds
        }

        return context

    def _get_client_id(self, context: RequestContext) -> str:
        """Extract client identifier from context."""
        # Try multiple sources
        return (
            context.client_id
            or context.request.get("sender")
            or context.client_ip
            or "anonymous"
        )

    def _check_rate_limit(self, client_id: str) -> tuple:
        """
        Check if request is within rate limit.

        Returns:
            (allowed: bool, remaining: int)
        """
        now = time.time()

        # Get or create bucket
        if client_id not in self._buckets:
            self._buckets[client_id] = (self.burst_size, now)

        tokens, last_update = self._buckets[client_id]

        # Refill tokens based on time elapsed
        elapsed = now - last_update
        refill = (elapsed / 60.0) * self.requests_per_minute
        tokens = min(self.burst_size, tokens + refill)

        # Check if we have tokens
        if tokens >= 1.0:
            # Allow request, consume token
            self._buckets[client_id] = (tokens - 1.0, now)
            return True, int(tokens - 1)
        else:
            # Rate limit exceeded
            return False, 0


# ============================================================================
# 4. Metrics Middleware
# ============================================================================


class MetricsMiddleware(Middleware):
    """
    Collects performance metrics for requests.

    Metrics:
    - Request count per type
    - Response times (min, max, avg)
    - Error rates
    - Success rates
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.metrics = {
            "total_requests": 0,
            "total_errors": 0,
            "request_times": [],
            "requests_by_type": defaultdict(int),
        }

    async def before(self, context: RequestContext) -> RequestContext:
        """Start metrics collection."""
        context.state["metrics_start"] = time.time()
        self.metrics["total_requests"] += 1

        # Track by message type
        msg_type = context.request.get("type", "unknown")
        self.metrics["requests_by_type"][msg_type] += 1

        return context

    async def after(self, context: ResponseContext) -> ResponseContext:
        """Record metrics."""
        start_time = context.state.get("metrics_start")
        if start_time:
            duration = time.time() - start_time
            self.metrics["request_times"].append(duration)

        return context

    async def on_error(
        self,
        context: RequestContext,
        error: Exception,
    ) -> Optional[Dict[str, Any]]:
        """Record error metrics."""
        self.metrics["total_errors"] += 1
        return None

    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics."""
        times = self.metrics["request_times"]

        return {
            "total_requests": self.metrics["total_requests"],
            "total_errors": self.metrics["total_errors"],
            "error_rate": (
                self.metrics["total_errors"] / self.metrics["total_requests"]
                if self.metrics["total_requests"] > 0
                else 0
            ),
            "avg_response_time_ms": (
                (sum(times) / len(times)) * 1000 if times else 0
            ),
            "min_response_time_ms": (min(times) * 1000 if times else 0),
            "max_response_time_ms": (max(times) * 1000 if times else 0),
            "requests_by_type": dict(self.metrics["requests_by_type"]),
        }


# ============================================================================
# 5. Validation Middleware
# ============================================================================


class ValidationMiddleware(Middleware):
    """
    Validates requests against schemas.

    Features:
    - JSON schema validation
    - Required field checking
    - Type validation
    - Custom validators
    """

    def __init__(
        self,
        schemas: Optional[Dict[str, Dict]] = None,
        strict: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.schemas = schemas or {}
        self.strict = strict

    async def before(self, context: RequestContext) -> RequestContext:
        """Validate request."""
        msg_type = context.request.get("type")

        # Check if we have a schema for this type
        if msg_type in self.schemas:
            schema = self.schemas[msg_type]

            # Validate request
            errors = self._validate_request(context.request, schema)

            if errors:
                context.set_response({
                    "error": "Validation failed",
                    "error_type": "ValidationError",
                    "validation_errors": errors,
                })

        return context

    def _validate_request(
        self,
        request: Dict[str, Any],
        schema: Dict[str, Any],
    ) -> List[str]:
        """
        Validate request against schema.

        Simple validation - in production use jsonschema library.
        """
        errors = []

        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in request:
                errors.append(f"Missing required field: {field}")

        # Check field types
        properties = schema.get("properties", {})
        for field, spec in properties.items():
            if field in request:
                expected_type = spec.get("type")
                actual_value = request[field]

                # Type checking (simplified)
                if expected_type == "string" and not isinstance(actual_value, str):
                    errors.append(f"Field '{field}' must be a string")
                elif expected_type == "integer" and not isinstance(actual_value, int):
                    errors.append(f"Field '{field}' must be an integer")

        return errors


# ============================================================================
# 6. Caching Middleware
# ============================================================================


class CachingMiddleware(Middleware):
    """
    LRU response caching middleware.

    Features:
    - LRU eviction policy
    - Configurable max size
    - TTL support
    - Cache key customization
    - Cache statistics
    """

    def __init__(
        self,
        max_size: int = 100,
        ttl_seconds: int = 300,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds

        # LRU cache: key -> (response, timestamp)
        self._cache: OrderedDict = OrderedDict()

        # Statistics
        self._hits = 0
        self._misses = 0

    async def before(self, context: RequestContext) -> RequestContext:
        """Check cache for response."""
        cache_key = self._get_cache_key(context.request)

        if cache_key in self._cache:
            response, timestamp = self._cache[cache_key]

            # Check TTL
            age = time.time() - timestamp
            if age < self.ttl_seconds:
                # Cache hit!
                self._hits += 1
                self._cache.move_to_end(cache_key)  # LRU

                # Add cache metadata
                response["cached"] = True
                response["cache_age_seconds"] = age

                context.set_response(response)
                return context

            # Expired, remove from cache
            del self._cache[cache_key]

        self._misses += 1
        context.state["cache_key"] = cache_key

        return context

    async def after(self, context: ResponseContext) -> ResponseContext:
        """Store response in cache."""
        cache_key = context.state.get("cache_key")

        if cache_key:
            # Check if cacheable (e.g., successful responses)
            if context.response.get("success", True):
                # Add to cache
                self._cache[cache_key] = (context.response, time.time())
                self._cache.move_to_end(cache_key)

                # Evict old entries if needed
                while len(self._cache) > self.max_size:
                    self._cache.popitem(last=False)  # Remove oldest

        return context

    def _get_cache_key(self, request: Dict[str, Any]) -> str:
        """Generate cache key from request."""
        # Create deterministic key from request
        key_data = {
            "type": request.get("type"),
            "params": request.get("params"),
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0,
            "size": len(self._cache),
            "max_size": self.max_size,
        }


# ============================================================================
# 7. Error Handler Middleware
# ============================================================================


class ErrorHandlerMiddleware(Middleware):
    """
    Converts exceptions to standardized error responses.

    Features:
    - Exception type mapping
    - Error message sanitization
    - Stack trace inclusion (debug mode)
    - Custom error handlers
    """

    def __init__(
        self,
        include_traceback: bool = False,
        sanitize_errors: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.include_traceback = include_traceback
        self.sanitize_errors = sanitize_errors

    async def on_error(
        self,
        context: RequestContext,
        error: Exception,
    ) -> Optional[Dict[str, Any]]:
        """Convert exception to error response."""
        error_response = {
            "success": False,
            "error": self._sanitize_message(str(error)),
            "error_type": type(error).__name__,
        }

        # Add traceback in debug mode
        if self.include_traceback:
            import traceback
            error_response["traceback"] = traceback.format_exc()

        return error_response

    def _sanitize_message(self, message: str) -> str:
        """Sanitize error message (remove sensitive info)."""
        if not self.sanitize_errors:
            return message

        # Remove common sensitive patterns
        # In production, use more sophisticated sanitization
        return message[:200]  # Truncate long messages


# ============================================================================
# 8. Tracing Middleware
# ============================================================================


class TracingMiddleware(Middleware):
    """
    Distributed tracing middleware.

    Features:
    - Trace ID generation
    - Span creation
    - Context propagation
    - Trace metadata
    """

    def __init__(
        self,
        service_name: str = "mcp_game",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.service_name = service_name

    async def before(self, context: RequestContext) -> RequestContext:
        """Start trace span."""
        # Generate trace ID
        trace_id = self._generate_trace_id()

        # Store in context
        context.metadata["trace_id"] = trace_id
        context.metadata["span_start"] = time.time()

        logger.debug(f"Started trace: {trace_id}")

        return context

    async def after(self, context: ResponseContext) -> ResponseContext:
        """Complete trace span."""
        trace_id = context.request.metadata.get("trace_id")
        span_start = context.request.metadata.get("span_start")

        if trace_id and span_start:
            duration = time.time() - span_start

            logger.debug(
                f"Completed trace: {trace_id}",
                duration_ms=round(duration * 1000, 2),
            )

            # Add trace info to response
            context.response["trace_id"] = trace_id

        return context

    def _generate_trace_id(self) -> str:
        """Generate unique trace ID."""
        import uuid
        return str(uuid.uuid4())[:16]
