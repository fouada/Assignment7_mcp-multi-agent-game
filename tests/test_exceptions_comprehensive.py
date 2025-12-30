"""
Comprehensive tests for exception classes to increase coverage.

Tests all exception types, their properties, and utility functions.
"""

import pytest
import asyncio
import socket

from src.common.exceptions import (
    MCPError,
    ErrorCategory,
    ConnectionError,
    ConnectionTimeoutError,
    ConnectionRefusedError,
    HeartbeatFailedError,
    ProtocolError,
    InvalidProtocolVersionError,
    InvalidMessageTypeError,
    MissingFieldError,
    InvalidMessageFormatError,
    ValidationError,
    InvalidMoveError,
    InvalidPlayerIdError,
    InvalidGameStateError,
    TimeoutError,
    MoveTimeoutError,
    ResponseTimeoutError,
    GameError,
    GameNotFoundError,
    GameAlreadyEndedError,
    GameNotStartedError,
    NotPlayersTurnError,
    RegistrationError,
    AlreadyRegisteredError,
    LeagueFullError,
    UnsupportedGameTypeError,
    ServerError,
    ServerOverloadedError,
    ServerShuttingDownError,
    CircuitBreakerError,
    LLMError,
    LLMResponseError,
    LLMRateLimitError,
    is_retryable,
    get_error_category,
)


class TestErrorCategory:
    """Test ErrorCategory enum."""

    def test_error_categories(self):
        """Test all error category values."""
        assert ErrorCategory.TRANSIENT.value == "transient"
        assert ErrorCategory.PERMANENT.value == "permanent"
        assert ErrorCategory.TIMEOUT.value == "timeout"
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.PROTOCOL.value == "protocol"


class TestMCPError:
    """Test base MCPError class."""

    def test_mcp_error_basic(self):
        """Test basic MCPError creation."""
        error = MCPError("Test error")
        assert str(error) == "[MCP_ERROR] Test error"
        assert error.message == "Test error"
        assert error.details == {}
        assert error.cause is None

    def test_mcp_error_with_details(self):
        """Test MCPError with details."""
        error = MCPError("Test error", details={"key": "value"})
        assert error.details == {"key": "value"}
        assert "Details: {'key': 'value'}" in str(error)

    def test_mcp_error_with_cause(self):
        """Test MCPError with cause."""
        cause = ValueError("Original error")
        error = MCPError("Test error", cause=cause)
        assert error.cause is cause

    def test_mcp_error_to_dict(self):
        """Test MCPError to_dict method."""
        error = MCPError("Test error", details={"key": "value"})
        error_dict = error.to_dict()
        assert error_dict["error_code"] == "MCP_ERROR"
        assert error_dict["message"] == "Test error"
        assert error_dict["category"] == "permanent"
        assert error_dict["retryable"] is False
        assert error_dict["details"] == {"key": "value"}


class TestConnectionErrors:
    """Test connection-related errors."""

    def test_connection_error_basic(self):
        """Test basic ConnectionError."""
        error = ConnectionError("Connection failed")
        assert error.error_code == "CONNECTION_ERROR"
        assert error.category == ErrorCategory.TRANSIENT
        assert error.retryable is True

    def test_connection_error_with_host_port(self):
        """Test ConnectionError with host and port."""
        error = ConnectionError("Connection failed", host="localhost", port=8080)
        assert error.details["host"] == "localhost"
        assert error.details["port"] == 8080

    def test_connection_error_with_existing_details(self):
        """Test ConnectionError with existing details."""
        error = ConnectionError(
            "Connection failed",
            host="localhost",
            port=8080,
            details={"extra": "info"}
        )
        assert error.details["host"] == "localhost"
        assert error.details["port"] == 8080
        assert error.details["extra"] == "info"

    def test_connection_timeout_error(self):
        """Test ConnectionTimeoutError."""
        error = ConnectionTimeoutError("Connection timed out")
        assert error.error_code == "CONNECTION_TIMEOUT"
        assert error.retryable is True

    def test_connection_refused_error(self):
        """Test ConnectionRefusedError."""
        error = ConnectionRefusedError("Connection refused")
        assert error.error_code == "CONNECTION_REFUSED"
        assert error.retryable is True

    def test_heartbeat_failed_error(self):
        """Test HeartbeatFailedError."""
        error = HeartbeatFailedError("Heartbeat failed")
        assert error.error_code == "HEARTBEAT_FAILED"
        assert error.retryable is True


class TestProtocolErrors:
    """Test protocol-related errors."""

    def test_protocol_error(self):
        """Test basic ProtocolError."""
        error = ProtocolError("Protocol violation")
        assert error.error_code == "PROTOCOL_ERROR"
        assert error.category == ErrorCategory.PROTOCOL
        assert error.retryable is False

    def test_invalid_protocol_version_error(self):
        """Test InvalidProtocolVersionError."""
        error = InvalidProtocolVersionError("1.0", "2.0")
        assert error.error_code == "INVALID_PROTOCOL_VERSION"
        assert "Expected '1.0', got '2.0'" in error.message
        assert error.details["expected"] == "1.0"
        assert error.details["received"] == "2.0"

    def test_invalid_message_type_error(self):
        """Test InvalidMessageTypeError."""
        error = InvalidMessageTypeError("Invalid message type")
        assert error.error_code == "INVALID_MESSAGE_TYPE"

    def test_missing_field_error_basic(self):
        """Test MissingFieldError without message type."""
        error = MissingFieldError("player_id")
        assert error.error_code == "MISSING_FIELD"
        assert "Required field 'player_id' is missing" in error.message
        assert error.details["field"] == "player_id"

    def test_missing_field_error_with_message_type(self):
        """Test MissingFieldError with message type."""
        error = MissingFieldError("player_id", message_type="register_request")
        assert "in message type 'register_request'" in error.message
        assert error.details["message_type"] == "register_request"

    def test_invalid_message_format_error(self):
        """Test InvalidMessageFormatError."""
        error = InvalidMessageFormatError("Invalid format")
        assert error.error_code == "INVALID_MESSAGE_FORMAT"


class TestValidationErrors:
    """Test validation-related errors."""

    def test_validation_error(self):
        """Test basic ValidationError."""
        error = ValidationError("Validation failed")
        assert error.error_code == "VALIDATION_ERROR"
        assert error.category == ErrorCategory.VALIDATION
        assert error.retryable is False

    def test_invalid_move_error_basic(self):
        """Test InvalidMoveError without valid_range."""
        error = InvalidMoveError(100, "Out of range")
        assert error.error_code == "INVALID_MOVE"
        assert "Invalid move '100': Out of range" in error.message
        assert error.details["move"] == 100
        assert error.details["reason"] == "Out of range"

    def test_invalid_move_error_with_range(self):
        """Test InvalidMoveError with valid_range."""
        error = InvalidMoveError(100, "Out of range", valid_range=(1, 50))
        assert error.details["valid_range"] == (1, 50)

    def test_invalid_player_id_error(self):
        """Test InvalidPlayerIdError."""
        error = InvalidPlayerIdError("Invalid player")
        assert error.error_code == "INVALID_PLAYER_ID"

    def test_invalid_game_state_error(self):
        """Test InvalidGameStateError."""
        error = InvalidGameStateError("Game not started")
        assert error.error_code == "INVALID_GAME_STATE"


class TestTimeoutErrors:
    """Test timeout-related errors."""

    def test_timeout_error_basic(self):
        """Test basic TimeoutError."""
        error = TimeoutError("Operation timed out")
        assert error.error_code == "TIMEOUT_ERROR"
        assert error.category == ErrorCategory.TIMEOUT
        assert error.retryable is True

    def test_timeout_error_with_timeout_seconds(self):
        """Test TimeoutError with timeout_seconds."""
        error = TimeoutError("Operation timed out", timeout_seconds=30.0)
        assert error.details["timeout_seconds"] == 30.0

    def test_timeout_error_with_existing_details(self):
        """Test TimeoutError with existing details."""
        error = TimeoutError(
            "Operation timed out",
            timeout_seconds=30.0,
            details={"operation": "move"}
        )
        assert error.details["timeout_seconds"] == 30.0
        assert error.details["operation"] == "move"

    def test_move_timeout_error(self):
        """Test MoveTimeoutError."""
        error = MoveTimeoutError("Move timed out")
        assert error.error_code == "MOVE_TIMEOUT"
        assert error.retryable is False  # Move timeouts are final

    def test_response_timeout_error(self):
        """Test ResponseTimeoutError."""
        error = ResponseTimeoutError("Response timed out")
        assert error.error_code == "RESPONSE_TIMEOUT"
        assert error.retryable is True


class TestGameErrors:
    """Test game-related errors."""

    def test_game_error(self):
        """Test basic GameError."""
        error = GameError("Game error")
        assert error.error_code == "GAME_ERROR"
        assert error.category == ErrorCategory.PERMANENT
        assert error.retryable is False

    def test_game_not_found_error(self):
        """Test GameNotFoundError."""
        error = GameNotFoundError("Game not found")
        assert error.error_code == "GAME_NOT_FOUND"

    def test_game_already_ended_error(self):
        """Test GameAlreadyEndedError."""
        error = GameAlreadyEndedError("Game already ended")
        assert error.error_code == "GAME_ALREADY_ENDED"

    def test_game_not_started_error(self):
        """Test GameNotStartedError."""
        error = GameNotStartedError("Game not started")
        assert error.error_code == "GAME_NOT_STARTED"

    def test_not_players_turn_error(self):
        """Test NotPlayersTurnError."""
        error = NotPlayersTurnError("Not your turn")
        assert error.error_code == "NOT_PLAYERS_TURN"


class TestRegistrationErrors:
    """Test registration-related errors."""

    def test_registration_error(self):
        """Test basic RegistrationError."""
        error = RegistrationError("Registration failed")
        assert error.error_code == "REGISTRATION_ERROR"
        assert error.category == ErrorCategory.PERMANENT
        assert error.retryable is False

    def test_already_registered_error(self):
        """Test AlreadyRegisteredError."""
        error = AlreadyRegisteredError("Already registered")
        assert error.error_code == "ALREADY_REGISTERED"

    def test_league_full_error(self):
        """Test LeagueFullError."""
        error = LeagueFullError("League is full")
        assert error.error_code == "LEAGUE_FULL"

    def test_unsupported_game_type_error(self):
        """Test UnsupportedGameTypeError."""
        error = UnsupportedGameTypeError("Unsupported game type")
        assert error.error_code == "UNSUPPORTED_GAME_TYPE"


class TestServerErrors:
    """Test server-related errors."""

    def test_server_error(self):
        """Test basic ServerError."""
        error = ServerError("Server error")
        assert error.error_code == "SERVER_ERROR"
        assert error.category == ErrorCategory.TRANSIENT
        assert error.retryable is True

    def test_server_overloaded_error(self):
        """Test ServerOverloadedError."""
        error = ServerOverloadedError("Server overloaded")
        assert error.error_code == "SERVER_OVERLOADED"
        assert error.retryable is True

    def test_server_shutting_down_error(self):
        """Test ServerShuttingDownError."""
        error = ServerShuttingDownError("Server shutting down")
        assert error.error_code == "SERVER_SHUTTING_DOWN"
        assert error.retryable is False


class TestCircuitBreakerError:
    """Test circuit breaker errors."""

    def test_circuit_breaker_error_basic(self):
        """Test CircuitBreakerError without cooldown."""
        error = CircuitBreakerError("server1")
        assert error.error_code == "CIRCUIT_BREAKER_OPEN"
        assert error.category == ErrorCategory.TRANSIENT
        assert error.retryable is False
        assert "Circuit breaker open for server 'server1'" in error.message
        assert error.details["server"] == "server1"

    def test_circuit_breaker_error_with_cooldown(self):
        """Test CircuitBreakerError with cooldown."""
        error = CircuitBreakerError("server1", cooldown_remaining=5.5)
        assert error.details["cooldown_remaining_seconds"] == 5.5
        assert "retry in 5.5s" in error.message


class TestLLMErrors:
    """Test LLM-related errors."""

    def test_llm_error(self):
        """Test basic LLMError."""
        error = LLMError("LLM error")
        assert error.error_code == "LLM_ERROR"
        assert error.category == ErrorCategory.TRANSIENT
        assert error.retryable is True

    def test_llm_response_error(self):
        """Test LLMResponseError."""
        error = LLMResponseError("Invalid response")
        assert error.error_code == "LLM_RESPONSE_ERROR"

    def test_llm_rate_limit_error(self):
        """Test LLMRateLimitError."""
        error = LLMRateLimitError("Rate limit exceeded")
        assert error.error_code == "LLM_RATE_LIMIT"


class TestUtilityFunctions:
    """Test utility functions."""

    def test_is_retryable_mcp_error_true(self):
        """Test is_retryable with retryable MCPError."""
        error = ConnectionError("Connection failed")
        assert is_retryable(error) is True

    def test_is_retryable_mcp_error_false(self):
        """Test is_retryable with non-retryable MCPError."""
        error = ValidationError("Validation failed")
        assert is_retryable(error) is False

    def test_is_retryable_socket_timeout(self):
        """Test is_retryable with socket.timeout."""
        error = socket.timeout("Socket timeout")
        assert is_retryable(error) is True

    def test_is_retryable_asyncio_timeout(self):
        """Test is_retryable with asyncio.TimeoutError."""
        error = asyncio.TimeoutError()
        assert is_retryable(error) is True

    def test_is_retryable_os_error(self):
        """Test is_retryable with OSError."""
        error = OSError("OS error")
        assert is_retryable(error) is True

    def test_is_retryable_other_error(self):
        """Test is_retryable with non-retryable standard error."""
        error = ValueError("Value error")
        assert is_retryable(error) is False

    def test_get_error_category_mcp_error(self):
        """Test get_error_category with MCPError."""
        error = ConnectionError("Connection failed")
        assert get_error_category(error) == ErrorCategory.TRANSIENT

    def test_get_error_category_other_error(self):
        """Test get_error_category with standard error."""
        error = ValueError("Value error")
        assert get_error_category(error) == ErrorCategory.PERMANENT

