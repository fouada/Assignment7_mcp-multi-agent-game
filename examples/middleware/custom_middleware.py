"""
Custom Middleware Examples
===========================

Demonstrates how to create custom middleware for the MCP Game system.

This file contains 5 complete examples:
1. RequestLoggerMiddleware - Detailed request/response logging
2. JWTAuthMiddleware - JWT token-based authentication
3. RequestTransformMiddleware - Request modification and enrichment
4. ResponseEnhancerMiddleware - Add metadata to responses
5. ConditionalMiddleware - Run middleware based on conditions

Usage:
    from examples.middleware.custom_middleware import RequestLoggerMiddleware

    pipeline = MiddlewarePipeline()
    pipeline.add_middleware(RequestLoggerMiddleware(), priority=90)
"""

import json
import time
import hashlib
from typing import Any, Dict, Optional, Set, List
from datetime import datetime, timedelta

from src.middleware import Middleware, RequestContext, ResponseContext
from src.common.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# Example 1: Request Logger Middleware
# ============================================================================


class RequestLoggerMiddleware(Middleware):
    """
    Logs detailed request and response information to a file.

    Features:
    - Structured JSON logging
    - Request/response correlation via request_id
    - Timing information
    - Optional PII filtering

    Example:
        logger = RequestLoggerMiddleware(
            log_file="requests.jsonl",
            log_request_body=True,
            filter_pii=True
        )
        pipeline.add_middleware(logger, priority=90)
    """

    def __init__(
        self,
        log_file: str = "middleware_requests.jsonl",
        log_request_body: bool = True,
        log_response_body: bool = True,
        filter_pii: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.log_file = log_file
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.filter_pii = filter_pii

    async def before(self, context: RequestContext) -> RequestContext:
        """Log incoming request."""
        # Generate request ID for correlation
        request_id = self._generate_request_id(context.request)
        context.metadata["request_id"] = request_id
        context.state["request_start_time"] = time.time()

        # Prepare log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id,
            "type": "request",
            "message_type": context.request.get("message_type", "unknown"),
            "sender": context.request.get("sender", "unknown"),
            "client_id": context.client_id,
            "client_ip": context.client_ip,
        }

        if self.log_request_body:
            body = context.request.copy()
            if self.filter_pii:
                body = self._filter_pii(body)
            log_entry["body"] = body

        # Write to log file
        self._write_log(log_entry)

        logger.debug(f"Request logged: {request_id}")
        return context

    async def after(self, context: ResponseContext) -> ResponseContext:
        """Log outgoing response."""
        request_id = context.request.metadata.get("request_id", "unknown")
        start_time = context.state.get("request_start_time", time.time())
        duration_ms = (time.time() - start_time) * 1000

        # Prepare log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id,
            "type": "response",
            "duration_ms": round(duration_ms, 2),
            "success": context.response.get("success", True),
        }

        if self.log_response_body:
            body = context.response.copy()
            if self.filter_pii:
                body = self._filter_pii(body)
            log_entry["body"] = body

        # Write to log file
        self._write_log(log_entry)

        logger.debug(f"Response logged: {request_id} ({duration_ms:.2f}ms)")
        return context

    async def on_error(
        self, context: RequestContext, error: Exception
    ) -> Optional[Dict[str, Any]]:
        """Log errors."""
        request_id = context.metadata.get("request_id", "unknown")

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id,
            "type": "error",
            "error_type": type(error).__name__,
            "error_message": str(error),
        }

        self._write_log(log_entry)
        return None

    def _generate_request_id(self, request: Dict[str, Any]) -> str:
        """Generate unique request ID."""
        import uuid

        return str(uuid.uuid4())[:16]

    def _filter_pii(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter personally identifiable information."""
        # List of fields that might contain PII
        pii_fields = {"password", "token", "auth_token", "secret", "api_key"}

        filtered = data.copy()
        for key in filtered:
            if key.lower() in pii_fields:
                filtered[key] = "[FILTERED]"

        return filtered

    def _write_log(self, entry: Dict[str, Any]) -> None:
        """Write log entry to file."""
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write log entry: {e}")


# ============================================================================
# Example 2: JWT Authentication Middleware
# ============================================================================


class JWTAuthMiddleware(Middleware):
    """
    JWT token-based authentication middleware.

    Features:
    - JWT signature validation
    - Token expiration checking
    - Role-based access control (RBAC)
    - Token blacklisting

    Example:
        auth = JWTAuthMiddleware(
            secret_key="your-secret-key",
            required_roles=["player", "referee"],
            token_field="auth_token"
        )
        pipeline.add_middleware(auth, priority=80)
    """

    def __init__(
        self,
        secret_key: str,
        required: bool = True,
        required_roles: Optional[List[str]] = None,
        token_field: str = "auth_token",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.secret_key = secret_key
        self.required = required
        self.required_roles = required_roles or []
        self.token_field = token_field
        self._blacklist: Set[str] = set()

    async def before(self, context: RequestContext) -> RequestContext:
        """Validate JWT token."""
        # Extract token
        token = context.request.get(self.token_field)

        if not token:
            if self.required:
                context.set_response(
                    {
                        "error": "Missing authentication token",
                        "error_type": "AuthenticationError",
                        "required_field": self.token_field,
                    }
                )
            return context

        # Check blacklist
        if token in self._blacklist:
            context.set_response(
                {
                    "error": "Token has been revoked",
                    "error_type": "AuthenticationError",
                }
            )
            return context

        # Validate token
        try:
            payload = self._decode_jwt(token)

            # Check expiration
            if self._is_expired(payload):
                context.set_response(
                    {
                        "error": "Token has expired",
                        "error_type": "AuthenticationError",
                    }
                )
                return context

            # Check roles
            user_roles = payload.get("roles", [])
            if self.required_roles and not any(
                role in user_roles for role in self.required_roles
            ):
                context.set_response(
                    {
                        "error": "Insufficient permissions",
                        "error_type": "AuthorizationError",
                        "required_roles": self.required_roles,
                        "user_roles": user_roles,
                    }
                )
                return context

            # Store user info in context
            context.metadata["authenticated"] = True
            context.metadata["user_id"] = payload.get("user_id")
            context.metadata["roles"] = user_roles
            context.metadata["token_expires_at"] = payload.get("exp")

            logger.debug(
                f"Authentication successful: user_id={payload.get('user_id')}"
            )

        except Exception as e:
            logger.error(f"JWT validation error: {e}")
            context.set_response(
                {
                    "error": "Invalid authentication token",
                    "error_type": "AuthenticationError",
                }
            )

        return context

    def _decode_jwt(self, token: str) -> Dict[str, Any]:
        """
        Decode and validate JWT token.

        In production, use PyJWT library:
            import jwt
            return jwt.decode(token, self.secret_key, algorithms=["HS256"])

        This is a simplified example for demonstration.
        """
        # Simplified JWT decoding (in production, use PyJWT)
        try:
            # Split token
            header_b64, payload_b64, signature_b64 = token.split(".")

            # Decode payload (base64url)
            import base64

            payload_json = base64.urlsafe_b64decode(payload_b64 + "==")
            payload = json.loads(payload_json)

            # In production, verify signature here
            # expected_sig = hmac.new(secret, f"{header}.{payload}", sha256).digest()
            # if signature != expected_sig: raise InvalidSignature

            return payload

        except Exception as e:
            raise ValueError(f"Invalid JWT token: {e}")

    def _is_expired(self, payload: Dict[str, Any]) -> bool:
        """Check if token is expired."""
        exp = payload.get("exp")
        if not exp:
            return False

        now = datetime.utcnow().timestamp()
        return now > exp

    def revoke_token(self, token: str) -> None:
        """Add token to blacklist."""
        self._blacklist.add(token)
        logger.info("Token revoked")


# ============================================================================
# Example 3: Request Transform Middleware
# ============================================================================


class RequestTransformMiddleware(Middleware):
    """
    Transforms and enriches incoming requests.

    Features:
    - Add server-side timestamps
    - Normalize message formats
    - Add request metadata
    - Convert legacy formats

    Example:
        transformer = RequestTransformMiddleware(
            add_timestamps=True,
            normalize_case=True
        )
        pipeline.add_middleware(transformer, priority=85)
    """

    def __init__(
        self,
        add_timestamps: bool = True,
        normalize_case: bool = True,
        add_server_metadata: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.add_timestamps = add_timestamps
        self.normalize_case = normalize_case
        self.add_server_metadata = add_server_metadata

    async def before(self, context: RequestContext) -> RequestContext:
        """Transform incoming request."""
        request = context.request

        # Add server-side timestamp
        if self.add_timestamps:
            request["server_received_at"] = datetime.utcnow().isoformat()

        # Normalize message_type case (convert to lowercase)
        if self.normalize_case:
            if "message_type" in request:
                request["message_type"] = request["message_type"].lower()

        # Add server metadata
        if self.add_server_metadata:
            if "metadata" not in request:
                request["metadata"] = {}

            request["metadata"].update(
                {
                    "processed_by": "mcp_game_server",
                    "pipeline_version": "1.0.0",
                    "transform_applied": True,
                }
            )

        logger.debug("Request transformed")
        return context


# ============================================================================
# Example 4: Response Enhancer Middleware
# ============================================================================


class ResponseEnhancerMiddleware(Middleware):
    """
    Enhances outgoing responses with additional metadata.

    Features:
    - Add response timestamps
    - Add processing duration
    - Add API version
    - Add deprecation warnings

    Example:
        enhancer = ResponseEnhancerMiddleware(
            add_version=True,
            add_timing=True
        )
        pipeline.add_middleware(enhancer, priority=40)
    """

    def __init__(
        self,
        api_version: str = "1.0.0",
        add_version: bool = True,
        add_timing: bool = True,
        add_request_id: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.api_version = api_version
        self.add_version = add_version
        self.add_timing = add_timing
        self.add_request_id = add_request_id

    async def before(self, context: RequestContext) -> RequestContext:
        """Store timing info."""
        context.state["enhancer_start_time"] = time.time()
        return context

    async def after(self, context: ResponseContext) -> ResponseContext:
        """Enhance outgoing response."""
        response = context.response

        # Add API version
        if self.add_version:
            response["api_version"] = self.api_version

        # Add processing duration
        if self.add_timing:
            start_time = context.state.get("enhancer_start_time", time.time())
            duration_ms = (time.time() - start_time) * 1000
            response["processing_time_ms"] = round(duration_ms, 2)

        # Add request ID for correlation
        if self.add_request_id:
            request_id = context.request.metadata.get("request_id")
            if request_id:
                response["request_id"] = request_id

        # Add server timestamp
        response["server_timestamp"] = datetime.utcnow().isoformat()

        logger.debug("Response enhanced")
        return context


# ============================================================================
# Example 5: Conditional Middleware
# ============================================================================


class ConditionalMiddleware(Middleware):
    """
    Runs middleware logic conditionally based on request properties.

    Features:
    - Run only for specific message types
    - Run only for specific senders
    - Run only during certain time windows
    - Custom condition functions

    Example:
        conditional = ConditionalMiddleware(
            condition=lambda ctx: ctx.request.get("message_type") == "game_started",
            middleware=CustomMiddleware()
        )
        pipeline.add_middleware(conditional, priority=70)
    """

    def __init__(
        self,
        condition: callable,
        middleware: Middleware,
        invert: bool = False,
        **kwargs,
    ):
        """
        Initialize conditional middleware.

        Args:
            condition: Function that takes RequestContext and returns bool
            middleware: Middleware to run if condition is True
            invert: If True, run middleware when condition is False
        """
        super().__init__(**kwargs)
        self.condition = condition
        self.middleware = middleware
        self.invert = invert

    async def before(self, context: RequestContext) -> RequestContext:
        """Run middleware.before() if condition is met."""
        should_run = self.condition(context)
        if self.invert:
            should_run = not should_run

        if should_run:
            context.state["conditional_ran"] = True
            return await self.middleware.before(context)

        context.state["conditional_ran"] = False
        return context

    async def after(self, context: ResponseContext) -> ResponseContext:
        """Run middleware.after() if condition was met."""
        if context.state.get("conditional_ran", False):
            return await self.middleware.after(context)

        return context

    async def on_error(
        self, context: RequestContext, error: Exception
    ) -> Optional[Dict[str, Any]]:
        """Run middleware.on_error() if condition was met."""
        if context.state.get("conditional_ran", False):
            return await self.middleware.on_error(context, error)

        return None


# ============================================================================
# Example Usage
# ============================================================================


async def example_usage():
    """
    Demonstrates how to use custom middleware.
    """
    from src.middleware import MiddlewarePipeline

    # Create pipeline
    pipeline = MiddlewarePipeline(
        timeout_seconds=30.0,
        error_handling="continue",
    )

    # Example 1: Add request logger
    request_logger = RequestLoggerMiddleware(
        log_file="custom_requests.jsonl",
        log_request_body=True,
        log_response_body=True,
        filter_pii=True,
    )
    pipeline.add_middleware(request_logger, priority=90)

    # Example 2: Add JWT authentication (disabled for this example)
    # jwt_auth = JWTAuthMiddleware(
    #     secret_key="your-secret-key-here",
    #     required=True,
    #     required_roles=["player", "referee"],
    # )
    # pipeline.add_middleware(jwt_auth, priority=80)

    # Example 3: Add request transformer
    transformer = RequestTransformMiddleware(
        add_timestamps=True,
        normalize_case=True,
        add_server_metadata=True,
    )
    pipeline.add_middleware(transformer, priority=85)

    # Example 4: Add response enhancer
    enhancer = ResponseEnhancerMiddleware(
        api_version="1.0.0",
        add_version=True,
        add_timing=True,
        add_request_id=True,
    )
    pipeline.add_middleware(enhancer, priority=40)

    # Example 5: Add conditional middleware
    # Only log game_started messages
    game_started_logger = ConditionalMiddleware(
        condition=lambda ctx: ctx.request.get("message_type") == "game_started",
        middleware=RequestLoggerMiddleware(log_file="game_started.jsonl"),
    )
    pipeline.add_middleware(game_started_logger, priority=75)

    # Test with sample request
    async def test_handler(request):
        return {"success": True, "message": "Processed successfully"}

    request = {
        "message_type": "game_started",
        "sender": "player:P01",
        "game_id": "game_001",
        "timestamp": datetime.utcnow().isoformat(),
    }

    response = await pipeline.execute(request, handler=test_handler)
    print("Response:", json.dumps(response, indent=2))


if __name__ == "__main__":
    import asyncio

    asyncio.run(example_usage())
