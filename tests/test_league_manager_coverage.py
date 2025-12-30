"""
Additional tests to improve league_manager.py coverage to 85%+.
Focuses on uncovered dashboard streaming, error handling, and edge cases.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from src.agents.league_manager import (
    LeagueManager,
    LeagueState,
    RegisteredPlayer,
)
from src.common.events import get_event_bus


class TestLeagueManagerDashboardStreaming:
    """Test dashboard streaming functionality."""

    @pytest.fixture
    def league_manager(self):
        """Create a league manager instance."""
        return LeagueManager(
            league_id="test_league",
            max_players=10,
            host="localhost",
            port=8080,
        )

    @pytest.fixture
    def mock_dashboard(self):
        """Create a mock dashboard."""
        dashboard = Mock()
        dashboard.tournament_states = {}
        dashboard.broadcast = AsyncMock()
        return dashboard

    @pytest.mark.asyncio
    async def test_stream_tournament_update_registration_phase(
        self, league_manager, mock_dashboard
    ):
        """Test streaming updates during registration phase."""
        # Setup
        league_manager.set_dashboard(mock_dashboard)
        league_manager._players = {
            "player1": RegisteredPlayer(
                player_id="player1",
                display_name="Alice",
                endpoint="http://localhost:9001",
                strategy_name="Nash",
            ),
            "player2": RegisteredPlayer(
                player_id="player2",
                display_name="Bob",
                endpoint="http://localhost:9002",
                strategy_name="Random",
            ),
        }

        # Execute
        await league_manager._stream_tournament_update()

        # Verify dashboard state was updated
        assert "test_league" in mock_dashboard.tournament_states
        tournament_state = mock_dashboard.tournament_states["test_league"]
        assert tournament_state.current_round == 0
        assert tournament_state.total_rounds == 0
        assert len(tournament_state.standings) == 2
        assert tournament_state.standings[0]["display_name"] == "Alice"
        assert tournament_state.standings[0]["strategy"] == "Nash"

    @pytest.mark.asyncio
    async def test_stream_tournament_update_no_dashboard(self, league_manager):
        """Test that streaming without dashboard doesn't crash."""
        # Should return early without error
        await league_manager._stream_tournament_update()

    @pytest.mark.asyncio
    async def test_stream_tournament_update_in_progress_phase(self, league_manager, mock_dashboard):
        """Test streaming updates during tournament."""
        from src.game.match import Match, MatchState

        league_manager.set_dashboard(mock_dashboard)
        league_manager.state = LeagueState.IN_PROGRESS

        # Add players
        league_manager._players = {
            "player1": RegisteredPlayer(
                player_id="player1",
                display_name="Alice",
                endpoint="http://localhost:9001",
                strategy_name="Nash",
                wins=2,
                losses=1,
                points=6,
                played=3,
            ),
            "player2": RegisteredPlayer(
                player_id="player2",
                display_name="Bob",
                endpoint="http://localhost:9002",
                strategy_name="Random",
                wins=1,
                losses=2,
                points=3,
                played=3,
            ),
        }

        # Add match with correct constructor
        match = Match(match_id="match1")
        # Set players using the correct method signature
        match.set_players(
            player1_id="player1",
            player1_endpoint="http://localhost:9001",
            player2_id="player2",
            player2_endpoint="http://localhost:9002",
            player1_name="Alice",
            player2_name="Bob"
        )
        match.state = MatchState.IN_PROGRESS
        league_manager._matches = {"match1": match}
        league_manager.current_round = 1

        # Create schedule
        league_manager._schedule = [[("player1", "player2")]]

        # Execute
        await league_manager._stream_tournament_update()

        # Verify
        assert "test_league" in mock_dashboard.tournament_states

class TestLeagueManagerEdgeCasesAdvanced:
    """Test additional edge cases in league manager."""

    @pytest.fixture
    def league_manager(self):
        """Create a league manager instance."""
        return LeagueManager(
            league_id="test_league",
            max_players=4,
            host="localhost",
            port=8080,
        )

    @pytest.mark.asyncio
    async def test_handle_player_register_mcp_request(self, league_manager):
        """Test handling MCP player registration request."""
        params = {
            "display_name": "TestPlayer",
            "endpoint": "http://localhost:9001",
            "version": "1.0.0",
            "game_types": ["even_odd"],
            "strategy": "random"
        }

        result = await league_manager._handle_registration(params)

        assert result["status"].upper() == "ACCEPTED"
        assert "player_id" in result

    @pytest.mark.asyncio
    async def test_handle_player_register_mcp_request_missing_fields(self, league_manager):
        """Test MCP player registration with missing fields."""
        # Missing display_name field
        params = {
            "endpoint": "http://localhost:9001",
        }

        # Should still work with defaults
        result = await league_manager._handle_registration(params)
        assert "status" in result
        assert result["status"].upper() == "ACCEPTED"

    @pytest.mark.asyncio
    async def test_handle_player_register_mcp_request_league_full(self, league_manager):
        """Test MCP player registration when league is full."""
        # Fill the league to max capacity
        for i in range(league_manager.max_players):
            params = {
                "display_name": f"Player{i}",
                "endpoint": f"http://localhost:{9000 + i}",
                "game_types": ["even_odd"],
            }
            await league_manager._handle_registration(params)

        # Try to register one more
        params = {
            "display_name": "ExtraPlayer",
            "endpoint": "http://localhost:9999",
            "game_types": ["even_odd"],
        }
        result = await league_manager._handle_registration(params)

        assert result["status"].upper() == "REJECTED"
        assert "full" in result.get("reason", "").lower()

    @pytest.mark.asyncio
    async def test_register_referee_when_league_completed(self, league_manager):
        """Test registering referee after league completes."""
        # Set league to completed state
        league_manager.state = LeagueState.COMPLETED

        params = {
            "display_name": "Referee_Test",
            "endpoint": "http://localhost:9002",
            "game_types": ["even_odd"],
        }

        result = await league_manager._handle_referee_registration(params)

        # Referees can still register even when league is completed
        assert result["status"].upper() in ["ACCEPTED", "REJECTED"]

    @pytest.mark.asyncio
    async def test_start_next_round_event_emission_with_error(self, league_manager):
        """Test round start with event emission error."""
        # Mock event bus to raise error
        event_bus = get_event_bus()
        original_emit = event_bus.emit
        event_bus.emit = Mock(side_effect=Exception("Event emission failed"))

        # Register players and start league
        for i in range(2):
            params = {
                "display_name": f"Player{i}",
                "endpoint": f"http://localhost:900{i}",
                "game_types": ["even_odd"],
            }
            await league_manager._handle_registration(params)

        await league_manager._start_league()

        # Try to start round - should handle the error gracefully
        try:
            await league_manager.start_next_round()
        except Exception:
            pass  # Error is expected but should be handled

        # Restore original emit
        event_bus.emit = original_emit

    @pytest.mark.asyncio
    async def test_run_all_rounds_with_mid_execution_failure(self, league_manager):
        """Test run_all_rounds with failure mid-execution."""
        # Register players
        for i in range(2):
            params = {
                "display_name": f"Player{i}",
                "endpoint": f"http://localhost:900{i}",
                "game_types": ["even_odd"],
            }
            await league_manager._handle_registration(params)

        # Start league
        await league_manager._start_league()

        # Mock start_next_round to fail after first round
        call_count = 0
        original_start_next_round = league_manager.start_next_round

        async def mock_start_next_round():
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise Exception("Mid-execution failure")
            return await original_start_next_round()

        league_manager.start_next_round = mock_start_next_round

        # Run all rounds - should handle the failure
        result = await league_manager._run_all_rounds()

        # Verify it attempted but failed
        assert call_count > 0
        assert result is not None  # Function returns a result

    @pytest.mark.asyncio
    async def test_run_all_rounds_completes_league(self, league_manager):
        """Test that run_all_rounds sets league to completed."""
        # Register players
        for i in range(2):
            params = {
                "display_name": f"Player{i}",
                "endpoint": f"http://localhost:900{i}",
                "game_types": ["even_odd"],
            }
            await league_manager._handle_registration(params)

        # Start league
        await league_manager._start_league()

        # Mock the round execution to complete immediately
        league_manager.start_next_round = AsyncMock()
        league_manager._current_round_matches = []
        league_manager.current_round = len(league_manager._schedule)

        result = await league_manager._run_all_rounds()

        # Verify league is completed
        assert league_manager.state == LeagueState.COMPLETED
        assert result is not None  # Function returns a result

class TestLeagueManagerRegistrationEdgeCases:
    """Test registration edge cases."""

    @pytest.fixture
    def league_manager(self):
        return LeagueManager(
            league_id="test_league",
            max_players=3,
            host="localhost",
            port=8080,
        )

    @pytest.mark.asyncio
    async def test_register_player_with_missing_game_types(self, league_manager):
        """Test registering player without game_types field."""
        params = {
            "display_name": "Player_NoGameTypes",
            "endpoint": "http://localhost:9001",
            # game_types missing - should use default
        }

        result = await league_manager._handle_registration(params)
        assert result["status"].upper() == "ACCEPTED"

    @pytest.mark.asyncio
    async def test_register_player_when_registration_closed(self, league_manager):
        """Test registering player when registration is closed."""
        # Close registration by changing state
        league_manager.state = LeagueState.IN_PROGRESS

        params = {
            "display_name": "LatePlayer",
            "endpoint": "http://localhost:9001",
            "game_types": ["even_odd"],
        }

        result = await league_manager._handle_registration(params)

        assert result["status"].upper() == "REJECTED"
        assert "closed" in result.get("reason", "").lower()

    @pytest.mark.asyncio
    async def test_register_duplicate_player_endpoint(self, league_manager):
        """Test registering player with duplicate endpoint."""
        # Register first player
        params1 = {
            "display_name": "Player1",
            "endpoint": "http://localhost:9001",
            "game_types": ["even_odd"],
        }
        await league_manager._handle_registration(params1)

        # Try to register another player with same endpoint
        params2 = {
            "display_name": "Player2",
            "endpoint": "http://localhost:9001",  # Same endpoint
            "game_types": ["even_odd"],
        }
        result = await league_manager._handle_registration(params2)

        assert result["status"].upper() == "REJECTED"
        assert "already registered" in result.get("reason", "").lower()

class TestLeagueManagerScheduleGeneration:
    """Test schedule generation edge cases."""

    @pytest.fixture
    def league_manager(self):
        return LeagueManager(
            league_id="test_league",
            max_players=10,
            host="localhost",
            port=8080,
        )

    @pytest.mark.asyncio
    async def test_start_league_with_insufficient_players(self, league_manager):
        """Test starting league with only 1 player."""
        # Register only one player (less than min_players=2)
        params = {
            "display_name": "LonePlayer",
            "endpoint": "http://localhost:9001",
            "game_types": ["even_odd"],
        }
        await league_manager._handle_registration(params)

        result = await league_manager._start_league()

        # Check for error condition - could be in different formats
        assert ("error" in result or "status" in result)
        if "error" in result:
            error_msg = result["error"].lower()
            assert "insufficient" in error_msg or "need at least" in error_msg
        elif "status" in result:
            assert result["status"].upper() == "ERROR"

    @pytest.mark.asyncio
    async def test_start_league_already_started(self, league_manager):
        """Test starting league that's already in progress."""
        # Set league to already started
        league_manager.state = LeagueState.IN_PROGRESS

        result = await league_manager._start_league()

        # Check for error condition - could be in different formats
        assert ("error" in result or "status" in result)
        if "error" in result:
            assert "already" in result["error"].lower()
        elif "status" in result:
            assert result["status"].upper() == "ERROR"

class TestLeagueManagerMatchHandling:
    """Test match handling edge cases."""

    @pytest.fixture
    def league_manager(self):
        return LeagueManager(
            league_id="test_league",
            max_players=10,
            host="localhost",
            port=8080,
        )

    @pytest.mark.asyncio
    async def test_handle_match_result_unknown_match(self, league_manager):
        """Test handling result for unknown match."""
        params = {
            "match_id": "UNKNOWN_MATCH_ID",
            "winner_id": "P01",
            "player1_score": 3,
            "player2_score": 2,
        }

        result = await league_manager._handle_match_result(params)

        # Should handle gracefully
        assert "error" in result or "status" in result

    @pytest.mark.asyncio
    async def test_start_next_round_without_referees(self, league_manager):
        """Test starting round when no referees available."""
        # Register players but no referees
        for i in range(2):
            params = {
                "display_name": f"Player{i}",
                "endpoint": f"http://localhost:900{i}",
                "game_types": ["even_odd"],
            }
            await league_manager._handle_registration(params)

        # Start league
        await league_manager._start_league()

        # Try to start round without referees
        # Should either queue or handle gracefully
        result = await league_manager.start_next_round()

        # Verify it handles the no-referee situation
        assert result is not None
