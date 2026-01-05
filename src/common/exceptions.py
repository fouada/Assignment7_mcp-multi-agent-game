"""
Custom Exception Hierarchy
==========================

Comprehensive exception classes for the MCP Game System.
Supports error categorization, retry decisions, and structured error data.
"""

from enum import Enum
from typing import Any


class ErrorCategory(Enum):
    """Categories of errors for retry decisions."""

    TRANSIENT = "transient"  # Network issues, temporary overload - retry
    PERMANENT = "permanent"  # Missing file, permission denied - no retry
    TIMEOUT = "timeout"  # Response took too long - maybe retry
    VALIDATION = "validation"  # Invalid data - no retry
    PROTOCOL = "protocol"  # Protocol violation - no retry


class MCPError(Exception):
    """Base exception for all MCP-related errors."""

    category: ErrorCategory = ErrorCategory.PERMANENT
    retryable: bool = False
    error_code: str = "MCP_ERROR"

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "category": self.category.value,
            "retryable": self.retryable,
            "details": self.details,
        }

    def __str__(self) -> str:
        base = f"[{self.error_code}] {self.message}"
        if self.details:
            base += f" | Details: {self.details}"
        return base


# ============================================================================
# Connection Errors
# ============================================================================


class ConnectionError(MCPError):
    """Error establishing or maintaining connection."""

    category = ErrorCategory.TRANSIENT
    retryable = True
    error_code = "CONNECTION_ERROR"

    def __init__(self, message: str, host: str | None = None, port: int | None = None, **kwargs):
        details = kwargs.pop("details", {})
        if host:
            details["host"] = host
        if port:
            details["port"] = port
        super().__init__(message, details=details, **kwargs)


class ConnectionTimeoutError(ConnectionError):
    """Connection attempt timed out."""

    error_code = "CONNECTION_TIMEOUT"


class ConnectionRefusedError(ConnectionError):
    """Connection was refused by server."""

    error_code = "CONNECTION_REFUSED"


class HeartbeatFailedError(ConnectionError):
    """Server heartbeat check failed."""

    error_code = "HEARTBEAT_FAILED"


# ============================================================================
# Protocol Errors
# ============================================================================


class ProtocolError(MCPError):
    """Protocol-level errors."""

    category = ErrorCategory.PROTOCOL
    retryable = False
    error_code = "PROTOCOL_ERROR"


class InvalidProtocolVersionError(ProtocolError):
    """Protocol version mismatch."""

    error_code = "INVALID_PROTOCOL_VERSION"

    def __init__(self, expected: str, received: str, **kwargs):
        message = f"Protocol version mismatch. Expected '{expected}', got '{received}'"
        details = {"expected": expected, "received": received}
        super().__init__(message, details=details, **kwargs)


class InvalidMessageTypeError(ProtocolError):
    """Unknown or invalid message type."""

    error_code = "INVALID_MESSAGE_TYPE"


class MissingFieldError(ProtocolError):
    """Required field missing from message."""

    error_code = "MISSING_FIELD"

    def __init__(self, field: str, message_type: str | None = None, **kwargs):
        msg = f"Required field '{field}' is missing"
        if message_type:
            msg += f" in message type '{message_type}'"
        details = {"field": field, "message_type": message_type}
        super().__init__(msg, details=details, **kwargs)


class InvalidMessageFormatError(ProtocolError):
    """Message format is invalid."""

    error_code = "INVALID_MESSAGE_FORMAT"


# ============================================================================
# Validation Errors
# ============================================================================


class ValidationError(MCPError):
    """Data validation errors."""

    category = ErrorCategory.VALIDATION
    retryable = False
    error_code = "VALIDATION_ERROR"


class InvalidMoveError(ValidationError):
    """Invalid game move."""

    error_code = "INVALID_MOVE"

    def __init__(self, move: Any, reason: str, valid_range: tuple | None = None, **kwargs):
        message = f"Invalid move '{move}': {reason}"
        details = {"move": move, "reason": reason}
        if valid_range:
            details["valid_range"] = valid_range
        super().__init__(message, details=details, **kwargs)


class InvalidPlayerIdError(ValidationError):
    """Invalid or unknown player ID."""

    error_code = "INVALID_PLAYER_ID"


class InvalidGameStateError(ValidationError):
    """Game is in invalid state for operation."""

    error_code = "INVALID_GAME_STATE"


# ============================================================================
# Timeout Errors
# ============================================================================


class TimeoutError(MCPError):
    """Operation timed out."""

    category = ErrorCategory.TIMEOUT
    retryable = True
    error_code = "TIMEOUT_ERROR"

    def __init__(self, message: str, timeout_seconds: float | None = None, **kwargs):
        details = kwargs.pop("details", {})
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        super().__init__(message, details=details, **kwargs)


class MoveTimeoutError(TimeoutError):
    """Player took too long to make a move."""

    error_code = "MOVE_TIMEOUT"
    retryable = False  # Move timeouts are final


class ResponseTimeoutError(TimeoutError):
    """Server response timed out."""

    error_code = "RESPONSE_TIMEOUT"


# ============================================================================
# Game Errors
# ============================================================================


class GameError(MCPError):
    """Game logic errors."""

    category = ErrorCategory.PERMANENT
    retryable = False
    error_code = "GAME_ERROR"


class GameNotFoundError(GameError):
    """Game with specified ID not found."""

    error_code = "GAME_NOT_FOUND"


class GameAlreadyEndedError(GameError):
    """Operation on already ended game."""

    error_code = "GAME_ALREADY_ENDED"


class GameNotStartedError(GameError):
    """Operation on game that hasn't started."""

    error_code = "GAME_NOT_STARTED"


class NotPlayersTurnError(GameError):
    """Player tried to move out of turn."""

    error_code = "NOT_PLAYERS_TURN"


# ============================================================================
# Registration Errors
# ============================================================================


class RegistrationError(MCPError):
    """Player registration errors."""

    category = ErrorCategory.PERMANENT
    retryable = False
    error_code = "REGISTRATION_ERROR"


class AlreadyRegisteredError(RegistrationError):
    """Player already registered."""

    error_code = "ALREADY_REGISTERED"


class LeagueFullError(RegistrationError):
    """League has reached maximum players."""

    error_code = "LEAGUE_FULL"


class UnsupportedGameTypeError(RegistrationError):
    """Player doesn't support required game type."""

    error_code = "UNSUPPORTED_GAME_TYPE"


# ============================================================================
# Server Errors
# ============================================================================


class ServerError(MCPError):
    """Server-side errors."""

    category = ErrorCategory.TRANSIENT
    retryable = True
    error_code = "SERVER_ERROR"


class ServerOverloadedError(ServerError):
    """Server is overloaded."""

    error_code = "SERVER_OVERLOADED"


class ServerShuttingDownError(ServerError):
    """Server is shutting down."""

    retryable = False
    error_code = "SERVER_SHUTTING_DOWN"


# ============================================================================
# Circuit Breaker Errors
# ============================================================================


class CircuitBreakerError(MCPError):
    """Circuit breaker is open."""

    category = ErrorCategory.TRANSIENT
    retryable = False  # Wait for cooldown
    error_code = "CIRCUIT_BREAKER_OPEN"

    def __init__(self, server: str, cooldown_remaining: float | None = None, **kwargs):
        message = f"Circuit breaker open for server '{server}'"
        details: dict[str, Any] = {"server": server}
        if cooldown_remaining:
            details["cooldown_remaining_seconds"] = cooldown_remaining
            message += f", retry in {cooldown_remaining:.1f}s"
        super().__init__(message, details=details, **kwargs)


# ============================================================================
# LLM Errors
# ============================================================================


class LLMError(MCPError):
    """LLM-related errors."""

    category = ErrorCategory.TRANSIENT
    retryable = True
    error_code = "LLM_ERROR"


class LLMResponseError(LLMError):
    """Invalid response from LLM."""

    error_code = "LLM_RESPONSE_ERROR"


class LLMRateLimitError(LLMError):
    """LLM rate limit exceeded."""

    error_code = "LLM_RATE_LIMIT"


# ============================================================================
# Service/Dependency Errors
# ============================================================================


class ServiceNotFoundError(MCPError):
    """Service not found in service locator."""

    category = ErrorCategory.PERMANENT
    retryable = False
    error_code = "SERVICE_NOT_FOUND"


class DependencyResolutionError(MCPError):
    """Error resolving dependencies."""

    category = ErrorCategory.PERMANENT
    retryable = False
    error_code = "DEPENDENCY_RESOLUTION_ERROR"


# ============================================================================
# Utility Functions
# ============================================================================


def is_retryable(error: Exception) -> bool:
    """Check if an error is retryable."""
    if isinstance(error, MCPError):
        return error.retryable

    # Standard library errors
    import asyncio
    import socket

    transient_errors = (
        socket.timeout,
        asyncio.TimeoutError,
        OSError,  # Includes connection errors
    )

    return isinstance(error, transient_errors)


def get_error_category(error: Exception) -> ErrorCategory:
    """Get the category of an error."""
    if isinstance(error, MCPError):
        return error.category
    return ErrorCategory.PERMANENT
