"""
Simple Tests to Push Coverage to 85%+
======================================

Targeted tests for specific uncovered lines in files close to 85%.
"""


import pytest

from src.common.protocol import AgentState, Timeouts
from src.middleware.pipeline import MiddlewarePipeline

# ==============================================================================
# Middleware Pipeline Tests (Lines 179, 197, 261, etc.)
# ==============================================================================


class TestMiddlewarePipelineAdditional:
    """Additional middleware pipeline tests for missing lines."""

    @pytest.mark.asyncio
    async def test_enable_nonexistent_middleware(self):
        """Test enable_middleware with non-existent middleware returns False."""
        pipeline = MiddlewarePipeline()

        # Try to enable middleware that doesn't exist
        result = pipeline.enable_middleware("nonexistent_middleware")

        assert result is False  # Line 179

    @pytest.mark.asyncio
    async def test_disable_nonexistent_middleware(self):
        """Test disable_middleware with non-existent middleware returns False."""
        pipeline = MiddlewarePipeline()

        # Try to disable middleware that doesn't exist
        result = pipeline.disable_middleware("nonexistent_middleware")

        assert result is False  # Line 197

    # Note: Skipping error handling test as it requires more complex setup
    # The middleware pipeline error handling (lines 261-265) is tested
    # in other test files with proper middleware implementations


# ==============================================================================
# Protocol - Timeouts Tests (Line 61)
# ==============================================================================


class TestTimeoutsDefault:
    """Test Timeouts.get_timeout() returns DEFAULT for unknown types."""

    def test_unknown_type_returns_default(self):
        """Unknown message type should return DEFAULT timeout."""
        result = Timeouts.get_timeout("COMPLETELY_UNKNOWN_TYPE")
        assert result == Timeouts.DEFAULT  # Line 61

    def test_none_returns_default(self):
        """None type should return DEFAULT timeout."""
        result = Timeouts.get_timeout(None)
        assert result == Timeouts.DEFAULT

    def test_empty_string_returns_default(self):
        """Empty string should return DEFAULT timeout."""
        result = Timeouts.get_timeout("")
        assert result == Timeouts.DEFAULT

    def test_random_string_returns_default(self):
        """Random string should return DEFAULT timeout."""
        result = Timeouts.get_timeout("xyz123abc")
        assert result == Timeouts.DEFAULT


# ==============================================================================
# Protocol - AgentState Transitions (Lines 176-183)
# ==============================================================================


class TestAgentStateTransitions:
    """Test AgentState.can_transition() for all state combinations."""

    def test_init_to_registered(self):
        """INIT can transition to REGISTERED."""
        assert AgentState.can_transition(AgentState.INIT, AgentState.REGISTERED) is True

    def test_init_to_shutdown(self):
        """INIT can transition to SHUTDOWN."""
        assert AgentState.can_transition(AgentState.INIT, AgentState.SHUTDOWN) is True

    def test_init_to_active_invalid(self):
        """INIT cannot transition to ACTIVE."""
        assert AgentState.can_transition(AgentState.INIT, AgentState.ACTIVE) is False

    def test_init_to_suspended_invalid(self):
        """INIT cannot transition to SUSPENDED."""
        assert AgentState.can_transition(AgentState.INIT, AgentState.SUSPENDED) is False

    def test_registered_to_active(self):
        """REGISTERED can transition to ACTIVE."""
        assert AgentState.can_transition(AgentState.REGISTERED, AgentState.ACTIVE) is True

    def test_registered_to_shutdown(self):
        """REGISTERED can transition to SHUTDOWN."""
        assert AgentState.can_transition(AgentState.REGISTERED, AgentState.SHUTDOWN) is True

    def test_active_to_suspended(self):
        """ACTIVE can transition to SUSPENDED."""
        assert AgentState.can_transition(AgentState.ACTIVE, AgentState.SUSPENDED) is True

    def test_active_to_shutdown(self):
        """ACTIVE can transition to SHUTDOWN."""
        assert AgentState.can_transition(AgentState.ACTIVE, AgentState.SHUTDOWN) is True

    def test_suspended_to_active(self):
        """SUSPENDED can transition to ACTIVE."""
        assert AgentState.can_transition(AgentState.SUSPENDED, AgentState.ACTIVE) is True

    def test_suspended_to_shutdown(self):
        """SUSPENDED can transition to SHUTDOWN."""
        assert AgentState.can_transition(AgentState.SUSPENDED, AgentState.SHUTDOWN) is True

    def test_shutdown_terminal_no_transitions(self):
        """SHUTDOWN is terminal - no outgoing transitions."""
        for target in [AgentState.INIT, AgentState.REGISTERED, AgentState.ACTIVE,
                      AgentState.SUSPENDED, AgentState.SHUTDOWN]:
            assert AgentState.can_transition(AgentState.SHUTDOWN, target) is False


# ==============================================================================
# Simple Protocol Tests
# ==============================================================================


class TestProtocolSimple:
    """Simple protocol tests for coverage."""

    def test_timeout_all_message_types(self):
        """Test get_timeout with all known message types."""
        types = [
            "REFEREE_REGISTER_REQUEST", "REFEREE_REGISTER_RESPONSE",
            "LEAGUE_REGISTER_REQUEST", "LEAGUE_REGISTER_RESPONSE",
            "GAME_JOIN_ACK", "GAME_INVITE_RESPONSE",
            "CHOOSE_PARITY", "CHOOSE_PARITY_CALL", "CHOOSE_PARITY_RESPONSE",
            "MOVE_REQUEST", "MOVE_RESPONSE",
            "GAME_OVER", "GAME_END",
            "MATCH_RESULT_REPORT", "LEAGUE_QUERY"
        ]

        for msg_type in types:
            timeout = Timeouts.get_timeout(msg_type)
            assert timeout > 0
            assert isinstance(timeout, float)
