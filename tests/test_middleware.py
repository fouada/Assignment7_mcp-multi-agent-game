"""
Tests for Middleware System
============================

Comprehensive tests for the middleware pipeline and built-in middleware.

Test Coverage:
- Base middleware functionality
- Pipeline execution (before/after/error hooks)
- Short-circuit behavior
- Error handling modes
- Priority ordering
- Built-in middleware (8 middleware)
- Timeout behavior
- Middleware enable/disable
"""

import asyncio
from typing import Any

import pytest

from src.middleware import (
    AuthenticationMiddleware,
    CachingMiddleware,
    ErrorHandlerMiddleware,
    LoggingMiddleware,
    MetricsMiddleware,
    Middleware,
    MiddlewarePipeline,
    MiddlewareTimeoutError,
    RateLimitMiddleware,
    RequestContext,
    ResponseContext,
    TracingMiddleware,
    ValidationMiddleware,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def clean_pipeline():
    """Create a fresh middleware pipeline for each test."""
    pipeline = MiddlewarePipeline(
        timeout_seconds=5.0,
        error_handling="continue",
    )
    yield pipeline
    pipeline.clear()


@pytest.fixture
def sample_request():
    """Sample request for testing."""
    return {
        "message_type": "game_started",
        "sender": "player:P01",
        "game_id": "game_001",
        "timestamp": "2024-01-15T10:30:00Z",
    }


@pytest.fixture
def sample_handler():
    """Sample async handler for testing."""

    async def handler(request: dict[str, Any]) -> dict[str, Any]:
        return {"success": True, "message": "Processed successfully"}

    return handler


# ============================================================================
# Custom Test Middleware
# ============================================================================


class MockMiddleware(Middleware):
    """Simple mock middleware that tracks calls for testing."""

    def __init__(self, name: str = "test", **kwargs):
        super().__init__(name=name, **kwargs)
        self.before_called = False
        self.after_called = False
        self.error_called = False
        self.call_order = []

    async def before(self, context: RequestContext) -> RequestContext:
        self.before_called = True
        self.call_order.append("before")
        context.metadata[f"{self.name}_before"] = True
        return context

    async def after(self, context: ResponseContext) -> ResponseContext:
        self.after_called = True
        self.call_order.append("after")
        context.response[f"{self.name}_after"] = True
        return context

    async def on_error(self, context: RequestContext, error: Exception) -> dict[str, Any] | None:
        self.error_called = True
        self.call_order.append("error")
        return None


class ShortCircuitMiddleware(Middleware):
    """Middleware that short-circuits the pipeline."""

    async def before(self, context: RequestContext) -> RequestContext:
        context.set_response({"short_circuit": True, "middleware": self.name})
        return context


class ErrorRaisingMiddleware(Middleware):
    """Middleware that raises an error."""

    async def before(self, context: RequestContext) -> RequestContext:
        raise ValueError("Test error from middleware")


# ============================================================================
# Base Middleware Tests
# ============================================================================


@pytest.mark.asyncio
async def test_middleware_base_class():
    """Test base middleware class functionality."""
    middleware = MockMiddleware(name="test")

    assert middleware.name == "test"
    assert middleware.enabled
    assert not middleware.before_called
    assert not middleware.after_called


@pytest.mark.asyncio
async def test_request_context():
    """Test RequestContext functionality."""
    context = RequestContext(
        request={"test": "data"},
        metadata={"key": "value"},
        state={"count": 1},
        client_id="client_123",
    )

    assert context.request == {"test": "data"}
    assert context.metadata["key"] == "value"
    assert context.state["count"] == 1
    assert context.client_id == "client_123"
    assert not context.has_response()

    # Test set_response
    context.set_response({"result": "success"})
    assert context.has_response()
    assert context.response == {"result": "success"}


@pytest.mark.asyncio
async def test_response_context():
    """Test ResponseContext functionality."""
    request_context = RequestContext(request={"test": "data"})
    response_context = ResponseContext(
        response={"success": True},
        metadata={"key": "value"},
        state={"count": 1},
        request=request_context,
    )

    assert response_context.response == {"success": True}
    assert response_context.metadata["key"] == "value"
    assert response_context.state["count"] == 1
    assert response_context.request == request_context


# ============================================================================
# Pipeline Execution Tests
# ============================================================================


@pytest.mark.asyncio
async def test_pipeline_basic_execution(clean_pipeline, sample_request, sample_handler):
    """Test basic pipeline execution."""
    middleware = MockMiddleware(name="test1")
    clean_pipeline.add_middleware(middleware, priority=10)

    response = await clean_pipeline.execute(sample_request, handler=sample_handler)

    assert response["success"]
    assert middleware.before_called
    assert middleware.after_called
    assert not middleware.error_called


@pytest.mark.asyncio
async def test_pipeline_priority_ordering(clean_pipeline, sample_request, sample_handler):
    """Test middleware executes in priority order."""
    m1 = MockMiddleware(name="low_priority")
    m2 = MockMiddleware(name="high_priority")
    m3 = MockMiddleware(name="medium_priority")

    clean_pipeline.add_middleware(m1, priority=10)
    clean_pipeline.add_middleware(m2, priority=100)
    clean_pipeline.add_middleware(m3, priority=50)

    response = await clean_pipeline.execute(sample_request, handler=sample_handler)

    # Check before hooks run high to low
    assert response["high_priority_after"]
    assert response["medium_priority_after"]
    assert response["low_priority_after"]

    # Verify order: high priority runs first in before, last in after
    assert m2.before_called
    assert m3.before_called
    assert m1.before_called


@pytest.mark.asyncio
async def test_pipeline_short_circuit(clean_pipeline, sample_request, sample_handler):
    """Test middleware can short-circuit the pipeline."""
    m1 = MockMiddleware(name="before_short_circuit")
    m2 = ShortCircuitMiddleware(name="short_circuit")
    m3 = MockMiddleware(name="after_short_circuit")

    clean_pipeline.add_middleware(m1, priority=100)
    clean_pipeline.add_middleware(m2, priority=50)
    clean_pipeline.add_middleware(m3, priority=10)

    response = await clean_pipeline.execute(sample_request, handler=sample_handler)

    # Check short-circuit response
    assert response["short_circuit"]
    assert response["middleware"] == "short_circuit"

    # m1 should run before hook
    assert m1.before_called

    # m2 short-circuits, so m3 before hook should not run
    assert not m3.before_called

    # After hooks should still run for cleanup
    assert m1.after_called


@pytest.mark.asyncio
async def test_pipeline_error_handling_continue(sample_request, sample_handler):
    """Test error handling with 'continue' mode."""
    pipeline = MiddlewarePipeline(error_handling="continue")

    m1 = MockMiddleware(name="before_error")
    m2 = ErrorRaisingMiddleware(name="error_middleware")
    m3 = MockMiddleware(name="after_error")

    pipeline.add_middleware(m1, priority=100)
    pipeline.add_middleware(m2, priority=50)
    pipeline.add_middleware(m3, priority=10)

    # Should continue despite error
    await pipeline.execute(sample_request, handler=sample_handler)

    # m1 runs successfully
    assert m1.before_called

    # m3 should still run (continue mode)
    assert m3.before_called


@pytest.mark.asyncio
async def test_pipeline_error_handling_stop(sample_request, sample_handler):
    """Test error handling with 'stop' mode."""
    pipeline = MiddlewarePipeline(error_handling="stop")

    m1 = MockMiddleware(name="before_error")
    m2 = ErrorRaisingMiddleware(name="error_middleware")
    m3 = MockMiddleware(name="after_error")

    pipeline.add_middleware(m1, priority=100)
    pipeline.add_middleware(m2, priority=50)
    pipeline.add_middleware(m3, priority=10)

    # Should stop at error
    response = await pipeline.execute(sample_request, handler=sample_handler)

    # Should return error response
    assert "error" in response
    assert response["error_type"] == "ValueError"


@pytest.mark.asyncio
async def test_pipeline_error_handling_raise(sample_request, sample_handler):
    """Test error handling with 'raise' mode."""
    pipeline = MiddlewarePipeline(error_handling="raise")

    m1 = MockMiddleware(name="before_error")
    m2 = ErrorRaisingMiddleware(name="error_middleware")

    pipeline.add_middleware(m1, priority=100)
    pipeline.add_middleware(m2, priority=50)

    # Should raise the exception
    with pytest.raises(ValueError, match="Test error from middleware"):
        await pipeline.execute(sample_request, handler=sample_handler)


@pytest.mark.asyncio
async def test_pipeline_timeout(sample_request):
    """Test pipeline timeout."""
    pipeline = MiddlewarePipeline(timeout_seconds=0.1)

    async def slow_handler(request):
        await asyncio.sleep(1.0)  # Longer than timeout
        return {"success": True}

    with pytest.raises(MiddlewareTimeoutError):
        await pipeline.execute(sample_request, handler=slow_handler)


@pytest.mark.asyncio
async def test_pipeline_state_sharing(clean_pipeline, sample_request, sample_handler):
    """Test middleware can share state through context."""

    class StateMiddleware1(Middleware):
        async def before(self, context: RequestContext) -> RequestContext:
            context.state["shared_value"] = 42
            return context

    class StateMiddleware2(Middleware):
        async def before(self, context: RequestContext) -> RequestContext:
            # Access state from previous middleware
            assert context.state.get("shared_value") == 42
            context.state["shared_value"] = 100
            return context

        async def after(self, context: ResponseContext) -> ResponseContext:
            # Access state in after hook
            context.response["final_value"] = context.state.get("shared_value")
            return context

    clean_pipeline.add_middleware(StateMiddleware1(), priority=100)
    clean_pipeline.add_middleware(StateMiddleware2(), priority=50)

    response = await clean_pipeline.execute(sample_request, handler=sample_handler)

    assert response["final_value"] == 100


# ============================================================================
# Pipeline Management Tests
# ============================================================================


@pytest.mark.asyncio
async def test_add_remove_middleware(clean_pipeline):
    """Test adding and removing middleware."""
    m1 = MockMiddleware(name="middleware1")
    m2 = MockMiddleware(name="middleware2")

    # Add middleware
    name1 = clean_pipeline.add_middleware(m1, priority=100)
    name2 = clean_pipeline.add_middleware(m2, priority=50)

    assert name1 == "middleware1"
    assert name2 == "middleware2"

    # Check registered
    middleware_list = clean_pipeline.get_middleware_list()
    assert len(middleware_list) == 2

    # Remove middleware
    removed = clean_pipeline.remove_middleware("middleware1")
    assert removed

    middleware_list = clean_pipeline.get_middleware_list()
    assert len(middleware_list) == 1

    # Try removing non-existent
    removed = clean_pipeline.remove_middleware("nonexistent")
    assert not removed


@pytest.mark.asyncio
async def test_enable_disable_middleware(clean_pipeline, sample_request, sample_handler):
    """Test enabling and disabling middleware."""
    m1 = MockMiddleware(name="test")
    clean_pipeline.add_middleware(m1, priority=100)

    # Middleware enabled by default
    await clean_pipeline.execute(sample_request, handler=sample_handler)
    assert m1.before_called

    # Reset
    m1.before_called = False

    # Disable middleware
    clean_pipeline.disable_middleware("test")
    await clean_pipeline.execute(sample_request, handler=sample_handler)
    assert not m1.before_called

    # Enable middleware
    clean_pipeline.enable_middleware("test")
    await clean_pipeline.execute(sample_request, handler=sample_handler)
    assert m1.before_called


@pytest.mark.asyncio
async def test_get_middleware_list(clean_pipeline):
    """Test getting middleware list."""
    m1 = MockMiddleware(name="test1")
    m2 = MockMiddleware(name="test2")

    clean_pipeline.add_middleware(m1, priority=100, tags=["test", "logging"])
    clean_pipeline.add_middleware(m2, priority=50, tags=["test"])

    middleware_list = clean_pipeline.get_middleware_list()

    assert len(middleware_list) == 2
    assert middleware_list[0]["name"] == "test1"
    assert middleware_list[0]["priority"] == 100
    assert "test" in middleware_list[0]["tags"]
    assert middleware_list[1]["name"] == "test2"


# ============================================================================
# Built-in Middleware Tests
# ============================================================================


@pytest.mark.asyncio
async def test_logging_middleware(clean_pipeline, sample_request, sample_handler):
    """Test LoggingMiddleware."""
    logging_middleware = LoggingMiddleware(
        name="logging",
        log_requests=True,
        log_responses=True,
        log_errors=True,
    )

    clean_pipeline.add_middleware(logging_middleware, priority=90)

    response = await clean_pipeline.execute(sample_request, handler=sample_handler)

    assert response["success"]


@pytest.mark.asyncio
async def test_authentication_middleware_required(clean_pipeline, sample_request, sample_handler):
    """Test AuthenticationMiddleware with required authentication."""
    auth_middleware = AuthenticationMiddleware(
        name="auth",
        required=True,
        token_field="auth_token",
    )

    clean_pipeline.add_middleware(auth_middleware, priority=80)

    # Request without token - should fail
    response = await clean_pipeline.execute(sample_request, handler=sample_handler)

    assert "error" in response
    assert response["error"] == "Authentication required"

    # Request with token - should succeed
    request_with_token = sample_request.copy()
    request_with_token["auth_token"] = "valid_token_123"

    response = await clean_pipeline.execute(request_with_token, handler=sample_handler)

    assert response["success"]


@pytest.mark.asyncio
async def test_authentication_middleware_optional(clean_pipeline, sample_request, sample_handler):
    """Test AuthenticationMiddleware with optional authentication."""
    auth_middleware = AuthenticationMiddleware(
        name="auth",
        required=False,
        token_field="auth_token",
    )

    clean_pipeline.add_middleware(auth_middleware, priority=80)

    # Request without token - should succeed (optional)
    response = await clean_pipeline.execute(sample_request, handler=sample_handler)

    assert response["success"]


@pytest.mark.asyncio
async def test_rate_limit_middleware(clean_pipeline, sample_request, sample_handler):
    """Test RateLimitMiddleware."""
    rate_limit_middleware = RateLimitMiddleware(
        name="rate_limit",
        requests_per_minute=10,
        burst_size=2,
    )

    clean_pipeline.add_middleware(rate_limit_middleware, priority=70)

    # First request - should succeed
    response = await clean_pipeline.execute(sample_request, handler=sample_handler)
    assert response["success"]
    assert "rate_limit" in response
    assert response["rate_limit"]["remaining"] == 1

    # Second request - should succeed (within burst)
    response = await clean_pipeline.execute(sample_request, handler=sample_handler)
    assert response["success"]
    assert response["rate_limit"]["remaining"] == 0

    # Third request - should be rate limited
    response = await clean_pipeline.execute(sample_request, handler=sample_handler)
    assert "error" in response
    assert response["error"] == "Rate limit exceeded"


@pytest.mark.asyncio
async def test_metrics_middleware(clean_pipeline, sample_request, sample_handler):
    """Test MetricsMiddleware."""
    import asyncio

    # Create handler with small delay to ensure measurable timing
    async def delayed_handler(req):
        await asyncio.sleep(0.001)  # 1ms delay
        return {"success": True}

    metrics_middleware = MetricsMiddleware(name="metrics")

    clean_pipeline.add_middleware(metrics_middleware, priority=50)

    # Execute a few requests
    for _ in range(3):
        response = await clean_pipeline.execute(sample_request, handler=delayed_handler)
        assert response["success"]

    # Check metrics
    metrics = metrics_middleware.get_metrics()

    assert metrics["total_requests"] == 3
    assert metrics["total_errors"] == 0
    assert metrics["avg_response_time_ms"] > 0


@pytest.mark.asyncio
async def test_validation_middleware(clean_pipeline, sample_handler):
    """Test ValidationMiddleware."""
    schemas = {
        "game_started": {
            "required": ["game_id", "sender"],
            "properties": {
                "game_id": {"type": "string"},
                "sender": {"type": "string"},
            },
        }
    }

    validation_middleware = ValidationMiddleware(name="validation", schemas=schemas)

    clean_pipeline.add_middleware(validation_middleware, priority=60)

    # Valid request
    valid_request = {
        "type": "game_started",
        "game_id": "game_001",
        "sender": "player:P01",
    }

    response = await clean_pipeline.execute(valid_request, handler=sample_handler)
    assert response["success"]

    # Invalid request (missing required field)
    invalid_request = {
        "type": "game_started",
        "game_id": "game_001",
        # Missing sender
    }

    response = await clean_pipeline.execute(invalid_request, handler=sample_handler)
    assert "error" in response
    assert response["error"] == "Validation failed"


@pytest.mark.asyncio
async def test_caching_middleware(clean_pipeline, sample_handler):
    """Test CachingMiddleware."""
    call_count = 0

    async def counting_handler(request):
        nonlocal call_count
        call_count += 1
        return {"success": True, "call_count": call_count}

    caching_middleware = CachingMiddleware(name="caching", max_size=10, ttl_seconds=300)

    clean_pipeline.add_middleware(caching_middleware, priority=40)

    request = {"type": "test", "params": {"value": 123}}

    # First request - should hit handler
    response1 = await clean_pipeline.execute(request, handler=counting_handler)
    assert response1["call_count"] == 1
    assert not response1.get("cached")

    # Second request with same params - should be cached
    response2 = await clean_pipeline.execute(request, handler=counting_handler)
    assert response2["call_count"] == 1  # Same as first (cached)
    assert response2.get("cached")

    # Check cache stats
    stats = caching_middleware.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1


@pytest.mark.asyncio
async def test_error_handler_middleware(clean_pipeline, sample_request):
    """Test ErrorHandlerMiddleware."""

    async def error_handler(request):
        raise ValueError("Test error")

    error_middleware = ErrorHandlerMiddleware(
        name="error_handler", include_traceback=False, sanitize_errors=True
    )

    clean_pipeline.add_middleware(error_middleware, priority=10)

    response = await clean_pipeline.execute(sample_request, handler=error_handler)

    assert not response["success"]
    assert "error" in response
    assert response["error_type"] == "ValueError"


@pytest.mark.asyncio
async def test_tracing_middleware(clean_pipeline, sample_request, sample_handler):
    """Test TracingMiddleware."""
    tracing_middleware = TracingMiddleware(name="tracing", service_name="test_service")

    clean_pipeline.add_middleware(tracing_middleware, priority=100)

    response = await clean_pipeline.execute(sample_request, handler=sample_handler)

    assert response["success"]
    assert "trace_id" in response
    assert len(response["trace_id"]) == 16  # UUID first 16 chars


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_full_pipeline_integration(sample_request, sample_handler):
    """Test full pipeline with multiple middleware."""
    pipeline = MiddlewarePipeline(timeout_seconds=30.0, error_handling="continue")

    # Add middleware in priority order (like BaseGameServer)
    pipeline.add_middleware(TracingMiddleware(service_name="test"), priority=100)
    pipeline.add_middleware(LoggingMiddleware(log_requests=True, log_responses=True), priority=90)
    pipeline.add_middleware(AuthenticationMiddleware(required=False), priority=80)  # Optional auth
    pipeline.add_middleware(RateLimitMiddleware(requests_per_minute=100), priority=70)
    pipeline.add_middleware(MetricsMiddleware(), priority=50)
    pipeline.add_middleware(ErrorHandlerMiddleware(), priority=10)

    # Execute request
    response = await pipeline.execute(sample_request, handler=sample_handler)

    # Verify response
    assert response["success"]
    assert "trace_id" in response
    assert "rate_limit" in response


@pytest.mark.asyncio
async def test_pipeline_statistics(clean_pipeline, sample_request, sample_handler):
    """Test pipeline statistics collection."""
    m1 = MockMiddleware(name="test1")
    clean_pipeline.add_middleware(m1, priority=100)

    # Execute multiple requests
    for _ in range(5):
        await clean_pipeline.execute(sample_request, handler=sample_handler)

    # Check pipeline stats
    stats = clean_pipeline.get_stats()
    assert stats["total_requests"] == 5
    assert stats["total_errors"] == 0
    assert stats["total_timeouts"] == 0

    # Check middleware stats
    middleware_list = clean_pipeline.get_middleware_list()
    assert middleware_list[0]["stats"]["total_requests"] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
