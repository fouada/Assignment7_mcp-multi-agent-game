"""
Additional tests to improve league_manager.py coverage to 85%+.
Focuses on uncovered dashboard streaming, error handling, and edge cases.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.agents.league_manager import (
    LeagueManager,
    LeagueState,
    RegisteredPlayer,
    RegisteredReferee,
)


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
                strategy_name="Nash"
            ),
            "player2": RegisteredPlayer(
                player_id="player2",
                display_name="Bob",
                endpoint="http://localhost:9002",
                strategy_name="Random"
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
    async def test_stream_tournament_update_in_progress_phase(
        self, league_manager, mock_dashboard
    ):
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

        # Add match
        match = Match(
            match_id="match1",
            game_type="even_odd",
            players=["player1", "player2"],
        )
        match.state = MatchState.IN_PROGRESS
        league_manager._matches = {"match1": match}
        league_manager._current_round = 1

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
        message = {
            "player_meta": {
                "display_name": "TestPlayer",
                "contact_endpoint": "http://localhost:9001",
                "version": "1.0.0",
                "game_types": ["even_odd"],
            }
        }

        result = await league_manager._handle_player_register_mcp_request(message)

        assert result["status"] == "registered"
        assert "player_id" in result

    @pytest.mark.asyncio
    async def test_handle_player_register_mcp_request_missing_fields(
        self, league_manager
    ):
        """Test MCP player registration with missing fields."""
        message = {
            "player_meta": {
                "display_name": "TestPlayer",
            }
        }

        result = await league_manager._handle_player_register_mcp_request(message)

        # Should still work with defaults
        assert result["status"] == "registered"

    @pytest.mark.asyncio
    async def test_handle_player_register_mcp_request_league_full(self, league_manager):
        """Test MCP player registration when league is full."""
        # Fill the league
        for i in range(4):
            league_manager._players[f"player{i}"] = RegisteredPlayer(
                player_id=f"player{i}",
                display_name=f"Player{i}",
                endpoint=f"http://localhost:900{i}",
            )

        message = {
            "player_meta": {
                "display_name": "LatePlayer",
                "contact_endpoint": "http://localhost:9999",
                "version": "1.0.0",
                "game_types": ["even_odd"],
            }
        }

        result = await league_manager._handle_player_register_mcp_request(message)

        assert result["status"] == "rejected"
        assert "full" in result.get("reason", "").lower()

    @pytest.mark.asyncio
    async def test_register_referee_when_league_completed(self, league_manager):
        """Test registering referee after league completes."""
        league_manager.state = LeagueState.COMPLETED

        referee_info = {
            "referee_id": "ref1",
            "endpoint": "http://localhost:7001",
            "display_name": "Referee One",
        }

        result = await league_manager._register_referee(referee_info)

        assert result["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_start_next_round_event_emission_with_error(self, league_manager):
        """Test round start with event emission error."""
        # Setup
        league_manager.state = LeagueState.IN_PROGRESS
        league_manager._schedule = [[("player1", "player2")]]
        league_manager._current_round = 0

        # Add players
        league_manager._players = {
            "player1": RegisteredPlayer(
                player_id="player1",
                display_name="Alice",
                endpoint="http://localhost:9001",
            ),
            "player2": RegisteredPlayer(
                player_id="player2",
                display_name="Bob",
                endpoint="http://localhost:9002",
            ),
        }

        # Add referee
        league_manager._referees = {
            "ref1": RegisteredReferee(
                referee_id="ref1",
                endpoint="http://localhost:7001",
                display_name="Referee",
            ),
        }

        # Mock event bus to raise error
        with patch("src.agents.league_manager.get_event_bus") as mock_get_bus:
            mock_bus = Mock()
            mock_bus.emit = AsyncMock(side_effect=Exception("Event error"))
            mock_get_bus.return_value = mock_bus

            # Should not crash even if event emission fails
            result = await league_manager.start_next_round()

            assert result["status"] in ["started", "complete"]

    @pytest.mark.asyncio
    async def test_run_all_rounds_with_mid_execution_failure(self, league_manager):
        """Test run_all_rounds with failure mid-execution."""
        # Setup league
        league_manager._players = {
            "player1": RegisteredPlayer(
                player_id="player1",
                display_name="Alice",
                endpoint="http://localhost:9001",
            ),
            "player2": RegisteredPlayer(
                player_id="player2",
                display_name="Bob",
                endpoint="http://localhost:9002",
            ),
        }

        league_manager._referees = {
            "ref1": RegisteredReferee(
                referee_id="ref1",
                endpoint="http://localhost:7001",
                display_name="Referee",
            ),
        }

        # Start league
        await league_manager.start_league()

        # Mock start_next_round to fail on second call
        original_start = league_manager.start_next_round
        call_count = [0]

        async def failing_start_next_round():
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("Round start failed")
            return await original_start()

        league_manager.start_next_round = failing_start_next_round

        # Should handle error gracefully
        with pytest.raises(Exception, match="Round start failed"):
            await league_manager.run_all_rounds()

    @pytest.mark.asyncio
    async def test_run_all_rounds_completes_league(self, league_manager):
        """Test that run_all_rounds sets league to completed."""
        # Setup league
        league_manager._players = {
            "player1": RegisteredPlayer(
                player_id="player1",
                display_name="Alice",
                endpoint="http://localhost:9001",
            ),
            "player2": RegisteredPlayer(
                player_id="player2",
                display_name="Bob",
                endpoint="http://localhost:9002",
            ),
        }

        league_manager._referees = {
            "ref1": RegisteredReferee(
                referee_id="ref1",
                endpoint="http://localhost:7001",
                display_name="Referee",
            ),
        }

        # Start league
        await league_manager.start_league()

        # Mock all rounds as complete immediately
        league_manager._current_round = len(league_manager._schedule)

        # Run all rounds
        result = await league_manager.run_all_rounds()

        # Verify league is completed
        assert league_manager.state == LeagueState.COMPLETED
        assert result["rounds_completed"] >= 0


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
        player_info = {
            "display_name": "TestPlayer",
            "endpoint": "http://localhost:9001",
            "version": "1.0.0",
        }

        result = await league_manager._register_player(player_info)

        assert result["status"] == "rejected"
        assert "game_types" in result.get("reason", "").lower() or "unsupported" in result.get("reason", "").lower()

    @pytest.mark.asyncio
    async def test_register_player_when_registration_closed(self, league_manager):
        """Test registering player when registration is closed."""
        league_manager.state = LeagueState.IN_PROGRESS

        player_info = {
            "display_name": "LatePlayer",
            "endpoint": "http://localhost:9001",
            "version": "1.0.0",
            "game_types": ["even_odd"],
        }

        result = await league_manager._register_player(player_info)

        assert result["status"] == "rejected"
        assert "closed" in result.get("reason", "").lower()

    @pytest.mark.asyncio
    async def test_register_duplicate_player_endpoint(self, league_manager):
        """Test registering player with duplicate endpoint."""
        # Register first player
        player1_info = {
            "display_name": "Player1",
            "endpoint": "http://localhost:9001",
            "version": "1.0.0",
            "game_types": ["even_odd"],
        }

        await league_manager._register_player(player1_info)

        # Try to register another player with same endpoint
        player2_info = {
            "display_name": "Player2",
            "endpoint": "http://localhost:9001",  # Same endpoint
            "version": "1.0.0",
            "game_types": ["even_odd"],
        }

        result = await league_manager._register_player(player2_info)

        assert result["status"] == "rejected"


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
        league_manager._players = {
            "player1": RegisteredPlayer(
                player_id="player1",
                display_name="Lonely",
                endpoint="http://localhost:9001",
            ),
        }

        result = await league_manager.start_league()

        assert result["status"] == "error"
        assert "insufficient" in result.get("message", "").lower()

    @pytest.mark.asyncio
    async def test_start_league_already_started(self, league_manager):
        """Test starting league that's already in progress."""
        league_manager.state = LeagueState.IN_PROGRESS

        result = await league_manager.start_league()

        assert result["status"] == "error"
        assert "already" in result.get("message", "").lower()


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
        result_data = {
            "match_id": "nonexistent",
            "winner_id": "player1",
            "player_a_score": 3,
            "player_b_score": 2,
        }

        result = await league_manager._handle_match_result(result_data)

        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_start_next_round_without_referees(self, league_manager):
        """Test starting round when no referees available."""
        # Setup league
        league_manager._players = {
            "player1": RegisteredPlayer(
                player_id="player1",
                display_name="Alice",
                endpoint="http://localhost:9001",
            ),
            "player2": RegisteredPlayer(
                player_id="player2",
                display_name="Bob",
                endpoint="http://localhost:9002",
            ),
        }

        # Start league
        await league_manager.start_league()

        # Remove all referees
        league_manager._referees = {}

        # Try to start round
        result = await league_manager.start_next_round()

        # Should handle gracefully
        assert result["status"] in ["error", "complete"]
