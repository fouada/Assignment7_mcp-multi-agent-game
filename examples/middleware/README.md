# Custom Middleware Examples

This directory contains complete, production-ready examples of custom middleware for the MCP Game system.

## Overview

The middleware system provides a composable, priority-based pipeline for processing requests and responses. Custom middleware can be used for:
- **Authentication & Authorization**: Token validation, RBAC, API keys
- **Logging & Auditing**: Detailed request/response logging, audit trails
- **Request/Response Transformation**: Normalization, enrichment, format conversion
- **Performance**: Caching, throttling, metrics collection
- **Security**: Input validation, rate limiting, PII filtering

## Examples Included

### 1. RequestLoggerMiddleware
**File**: `custom_middleware.py`

Logs detailed request and response information to structured JSON files.

**Features**:
- Structured JSONL logging
- Request/response correlation via request_id
- Timing information
- Optional PII filtering

**Usage**:
```python
from examples.middleware.custom_middleware import RequestLoggerMiddleware

logger = RequestLoggerMiddleware(
    log_file="requests.jsonl",
    log_request_body=True,
    log_response_body=True,
    filter_pii=True
)
pipeline.add_middleware(logger, priority=90)
```

**Output Example** (`requests.jsonl`):
```json
{"timestamp": "2024-01-15T10:30:00.123Z", "request_id": "a1b2c3d4", "type": "request", "message_type": "game_started", "sender": "player:P01"}
{"timestamp": "2024-01-15T10:30:00.456Z", "request_id": "a1b2c3d4", "type": "response", "duration_ms": 333.45, "success": true}
```

### 2. JWTAuthMiddleware
**File**: `custom_middleware.py`

JWT token-based authentication with role-based access control.

**Features**:
- JWT signature validation
- Token expiration checking
- Role-based access control (RBAC)
- Token blacklisting

**Usage**:
```python
from examples.middleware.custom_middleware import JWTAuthMiddleware

auth = JWTAuthMiddleware(
    secret_key="your-secret-key",
    required=True,
    required_roles=["player", "referee"],
    token_field="auth_token"
)
pipeline.add_middleware(auth, priority=80)
```

**Token Format**:
```json
{
  "user_id": "player_001",
  "roles": ["player"],
  "exp": 1705315800
}
```

### 3. RequestTransformMiddleware
**File**: `custom_middleware.py`

Transforms and enriches incoming requests.

**Features**:
- Add server-side timestamps
- Normalize message formats
- Add request metadata
- Convert legacy formats

**Usage**:
```python
from examples.middleware.custom_middleware import RequestTransformMiddleware

transformer = RequestTransformMiddleware(
    add_timestamps=True,
    normalize_case=True,
    add_server_metadata=True
)
pipeline.add_middleware(transformer, priority=85)
```

**Transformation Example**:
```python
# Before:
{"message_type": "GAME_STARTED", "game_id": "game_001"}

# After:
{
  "message_type": "game_started",  # Normalized
  "game_id": "game_001",
  "server_received_at": "2024-01-15T10:30:00.123Z",  # Added
  "metadata": {
    "processed_by": "mcp_game_server",
    "pipeline_version": "1.0.0",
    "transform_applied": true
  }
}
```

### 4. ResponseEnhancerMiddleware
**File**: `custom_middleware.py`

Enhances outgoing responses with additional metadata.

**Features**:
- Add response timestamps
- Add processing duration
- Add API version
- Add deprecation warnings

**Usage**:
```python
from examples.middleware.custom_middleware import ResponseEnhancerMiddleware

enhancer = ResponseEnhancerMiddleware(
    api_version="1.0.0",
    add_version=True,
    add_timing=True,
    add_request_id=True
)
pipeline.add_middleware(enhancer, priority=40)
```

**Enhanced Response**:
```json
{
  "success": true,
  "result": {...},
  "api_version": "1.0.0",
  "processing_time_ms": 45.67,
  "request_id": "a1b2c3d4",
  "server_timestamp": "2024-01-15T10:30:00.456Z"
}
```

### 5. ConditionalMiddleware
**File**: `custom_middleware.py`

Runs middleware logic conditionally based on request properties.

**Features**:
- Run only for specific message types
- Run only for specific senders
- Run only during certain time windows
- Custom condition functions

**Usage**:
```python
from examples.middleware.custom_middleware import ConditionalMiddleware, RequestLoggerMiddleware

# Only log game_started messages
game_started_logger = ConditionalMiddleware(
    condition=lambda ctx: ctx.request.get("message_type") == "game_started",
    middleware=RequestLoggerMiddleware(log_file="game_started.jsonl")
)
pipeline.add_middleware(game_started_logger, priority=75)

# Run middleware for specific players
player_specific = ConditionalMiddleware(
    condition=lambda ctx: ctx.request.get("sender", "").startswith("player:P01"),
    middleware=CustomMiddleware()
)

# Run middleware during business hours
import datetime
business_hours = ConditionalMiddleware(
    condition=lambda ctx: 9 <= datetime.datetime.now().hour < 17,
    middleware=BusinessHoursMiddleware()
)
```

## Creating Your Own Middleware

### Step 1: Extend the Middleware Base Class

```python
from src.middleware import Middleware, RequestContext, ResponseContext
from typing import Any, Dict, Optional

class MyCustomMiddleware(Middleware):
    """
    My custom middleware description.

    Features:
    - Feature 1
    - Feature 2
    """

    def __init__(self, config_param: str = "default", **kwargs):
        super().__init__(**kwargs)
        self.config_param = config_param

    async def before(self, context: RequestContext) -> RequestContext:
        """
        Called before the request handler.

        Use this to:
        - Validate requests
        - Authenticate/authorize
        - Transform requests
        - Short-circuit by calling context.set_response()
        """
        # Your logic here
        return context

    async def after(self, context: ResponseContext) -> ResponseContext:
        """
        Called after the request handler.

        Use this to:
        - Transform responses
        - Add metadata
        - Log results
        """
        # Your logic here
        return context

    async def on_error(
        self,
        context: RequestContext,
        error: Exception
    ) -> Optional[Dict[str, Any]]:
        """
        Called when an error occurs.

        Use this to:
        - Convert exceptions to error responses
        - Log errors
        - Handle specific error types

        Return None to let other middleware handle the error,
        or return a dict to use as the error response.
        """
        # Your error handling here
        return None
```

### Step 2: Register in Pipeline

```python
from src.middleware import MiddlewarePipeline

pipeline = MiddlewarePipeline()

# Add your middleware with priority
# Higher priority = runs earlier in the pipeline
pipeline.add_middleware(MyCustomMiddleware(config_param="value"), priority=75)
```

### Step 3: Integrate with BaseGameServer

```python
from src.server.base_server import BaseGameServer

class MyGameServer(BaseGameServer):
    def __init__(self, name: str, **kwargs):
        super().__init__(name, server_type="my_server", **kwargs)

        # Middleware is already initialized by BaseGameServer
        # Add additional custom middleware
        self.middleware_pipeline.add_middleware(
            MyCustomMiddleware(),
            priority=75
        )
```

## Middleware Execution Order

Middleware executes in priority order (higher = earlier):

```
Request Flow:
  → Tracing (100)
  → Logging (90)
  → Request Transform (85)
  → Authentication (80)
  → Conditional (75)
  → Rate Limiting (70)
  → Validation (60)
  → Metrics (50)
  → Response Enhancer (40)
  → Error Handler (10)
  → [YOUR HANDLER]
  ← Error Handler (10)
  ← Response Enhancer (40)
  ← Metrics (50)
  ← Validation (60)
  ← Rate Limiting (70)
  ← Conditional (75)
  ← Authentication (80)
  ← Request Transform (85)
  ← Logging (90)
  ← Tracing (100)
Response
```

## Best Practices

### 1. **Use Appropriate Priority**
- **100-90**: Tracing, logging (capture everything)
- **90-80**: Authentication, authorization (security first)
- **80-70**: Rate limiting, validation (protect resources)
- **70-50**: Business logic, caching (performance)
- **50-40**: Metrics, monitoring (observability)
- **40-10**: Response transformation (final touches)
- **10-0**: Error handling (last resort)

### 2. **Handle Errors Gracefully**
```python
async def before(self, context: RequestContext) -> RequestContext:
    try:
        # Your logic
        pass
    except Exception as e:
        logger.error(f"Middleware error: {e}")
        # Either set error response or let error handler deal with it
        context.set_response({
            "error": str(e),
            "error_type": type(e).__name__
        })
    return context
```

### 3. **Use Context for State**
```python
async def before(self, context: RequestContext) -> RequestContext:
    # Store data in context.state (shared between before/after)
    context.state["my_data"] = some_value
    return context

async def after(self, context: ResponseContext) -> ResponseContext:
    # Access data from before hook
    my_data = context.state.get("my_data")
    return context
```

### 4. **Short-Circuit When Needed**
```python
async def before(self, context: RequestContext) -> RequestContext:
    if not self._is_valid(context.request):
        # Short-circuit: skip handler and remaining before hooks
        context.set_response({
            "error": "Invalid request",
            "error_type": "ValidationError"
        })
    return context
```

### 5. **Make Middleware Configurable**
```python
class ConfigurableMiddleware(Middleware):
    def __init__(
        self,
        enabled: bool = True,
        log_level: str = "INFO",
        filter_patterns: List[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.enabled = enabled
        self.log_level = log_level
        self.filter_patterns = filter_patterns or []
```

## Testing Middleware

```python
import pytest
from src.middleware import MiddlewarePipeline, RequestContext, ResponseContext

@pytest.mark.asyncio
async def test_my_middleware():
    # Create middleware
    middleware = MyCustomMiddleware(config_param="test")

    # Test before hook
    context = RequestContext(request={"message_type": "test"})
    result = await middleware.before(context)

    assert result.metadata.get("processed") == True

    # Test after hook
    response_context = ResponseContext(
        response={"success": True},
        state={},
        request=context
    )
    result = await middleware.after(response_context)

    assert "enhanced" in result.response
```

## Configuration

Middleware can be configured via `config/middleware/middleware_config.json`:

```json
{
  "pipeline": {
    "enabled": true,
    "timeout_seconds": 30.0,
    "error_handling": "continue"
  },
  "middleware": [
    {
      "name": "my_custom",
      "enabled": true,
      "priority": 75,
      "config": {
        "param1": "value1",
        "param2": "value2"
      }
    }
  ]
}
```

## Running Examples

```bash
# Run the example usage
cd examples/middleware
python custom_middleware.py

# This will:
# 1. Create a pipeline with all 5 middleware
# 2. Process a sample request
# 3. Show the enhanced response
# 4. Create log files demonstrating functionality
```

## Further Reading

- **Middleware System**: `src/middleware/README.md`
- **Middleware Pipeline**: `src/middleware/pipeline.py`
- **Built-in Middleware**: `src/middleware/builtin.py`
- **Base Server Integration**: `src/server/base_server.py:86-180`

## Support

For questions or issues with custom middleware:
1. Check the built-in middleware examples in `src/middleware/builtin.py`
2. Review the middleware tests in `tests/test_middleware.py`
3. See the Middleware documentation in `docs/MIDDLEWARE.md`
