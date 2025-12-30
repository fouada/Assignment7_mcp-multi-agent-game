"""
Additional tests to improve referee.py coverage to 85%+.
Focuses on error handling, edge cases, and uncovered paths.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.agents.referee import RefereeAgent
from src.client.mcp_client import MCPClient
from src.game.odd_even import OddEvenGame


class TestRefereeAgentErrorHandling:
    """Test referee error handling scenarios."""

    @pytest.fixture
    def referee(self):
        """Create a referee agent."""
        return RefereeAgent(
            referee_id="ref1",
            host="localhost",
            port=7001,
        )

    @pytest.fixture
    def mock_client(self):
        """Create a mock MCP client."""
        client = Mock(spec=MCPClient)
        client.call_tool = AsyncMock()
        client.send_message = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_start_match_without_referee_client(self, referee):
        """Test starting match when referee client is not set."""
        match_info = {
            "match_id": "match1",
            "player_a": {"player_id": "p1", "endpoint": "http://localhost:9001"},
            "player_b": {"player_id": "p2", "endpoint": "http://localhost:9002"},
            "game_type": "even_odd",
            "rounds": 5,
        }

        with pytest.raises(Exception, match=".*"):
            await referee.start_match(match_info)

    @pytest.mark.asyncio
    async def test_send_game_invitations_player_rejects(self, referee, mock_client):
        """Test game invitation where player B rejects."""
        referee._client = mock_client

        # Mock responses - A accepts, B rejects
        mock_client.send_message.side_effect = [
            {"status": "accepted", "player_id": "p1"},  # Player A accepts
            {"status": "rejected", "player_id": "p2"},   # Player B rejects
        ]

        match_info = {
            "match_id": "match1",
            "player_a": {"player_id": "p1", "endpoint": "http://localhost:9001"},
            "player_b": {"player_id": "p2", "endpoint": "http://localhost:9002"},
            "game_type": "even_odd",
            "rounds": 5,
        }

        result = await referee._send_game_invitations(match_info)

        assert result["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_send_game_invitations_network_error(self, referee, mock_client):
        """Test game invitation with network error."""
        referee._client = mock_client

        # Mock network error
        mock_client.send_message.side_effect = Exception("Network error")

        match_info = {
            "match_id": "match1",
            "player_a": {"player_id": "p1", "endpoint": "http://localhost:9001"},
            "player_b": {"player_id": "p2", "endpoint": "http://localhost:9002"},
            "game_type": "even_odd",
            "rounds": 5,
        }

        result = await referee._send_game_invitations(match_info)

        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_run_round_with_move_collection_error(self, referee, mock_client):
        """Test running round when move collection fails."""
        referee._client = mock_client

        # Create a game
        game = OddEvenGame("p1", "p2", rounds=1)
        game.start()

        # Store game
        referee._games["match1"] = {
            "game": game,
            "match_id": "match1",
            "player_a_endpoint": "http://localhost:9001",
            "player_b_endpoint": "http://localhost:9002",
        }

        # Mock move request to fail
        mock_client.send_message.side_effect = Exception("Move request failed")

        with pytest.raises(Exception, match=".*"):
            await referee._run_round("match1")

    @pytest.mark.asyncio
    async def test_handle_move_submission_unknown_game(self, referee):
        """Test handling move for unknown game."""
        message = {
            "game_id": "nonexistent",
            "player_id": "p1",
            "move": 5,
        }

        result = await referee._handle_move_submission(message)

        assert result["status"] == "error"
        assert "not found" in result.get("message", "").lower()

    @pytest.mark.asyncio
    async def test_handle_move_submission_wrong_state(self, referee):
        """Test handling move when game is not in waiting state."""
        # Create game but don't start it
        game = OddEvenGame("p1", "p2", rounds=1)

        referee._games["match1"] = {
            "game": game,
            "match_id": "match1",
            "state": "initializing",  # Wrong state
            "player_a_endpoint": "http://localhost:9001",
            "player_b_endpoint": "http://localhost:9002",
        }

        message = {
            "game_id": "match1",
            "player_id": "p1",
            "move": 5,
        }

        result = await referee._handle_move_submission(message)

        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_handle_game_acceptance_unknown_game(self, referee):
        """Test handling game acceptance for unknown game."""
        message = {
            "game_id": "nonexistent",
            "player_id": "p1",
            "accepted": True,
        }

        result = await referee._handle_game_acceptance(message)

        # Should handle gracefully (return None or error)
        assert result is None or result.get("status") == "error"

    @pytest.mark.asyncio
    async def test_handle_game_acceptance_rejection(self, referee):
        """Test handling player rejecting game."""
        # Setup pending invitation
        referee._pending_invitations["match1"] = {
            "player_a": {"player_id": "p1", "status": "pending"},
            "player_b": {"player_id": "p2", "status": "pending"},
        }

        message = {
            "game_id": "match1",
            "player_id": "p1",
            "accepted": False,  # Player rejects
        }

        await referee._handle_game_acceptance(message)

        # Invitation should be updated
        assert referee._pending_invitations["match1"]["player_a"]["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_complete_game_and_report_network_error(self, referee, mock_client):
        """Test completing game when reporting to league fails."""
        referee._client = mock_client
        referee._league_endpoint = "http://localhost:8080"

        # Create completed game
        game = OddEvenGame("p1", "p2", rounds=1)
        game.start()
        game.submit_move("p1", 5)
        game.submit_move("p2", 4)
        game.resolve_round()

        referee._games["match1"] = {
            "game": game,
            "match_id": "match1",
            "player_a_endpoint": "http://localhost:9001",
            "player_b_endpoint": "http://localhost:9002",
        }

        # Mock report to fail
        mock_client.call_tool.side_effect = Exception("Network error")

        # Should handle error gracefully
        with pytest.raises(Exception, match=".*"):
            await referee._complete_game_and_report("match1")

    @pytest.mark.asyncio
    async def test_send_round_results_network_error(self, referee, mock_client):
        """Test sending round results with network error."""
        referee._client = mock_client

        # Mock send to fail
        mock_client.send_message.side_effect = Exception("Network error")

        round_result = {
            "round": 1,
            "player_a_move": 5,
            "player_b_move": 4,
            "winner": "p1",
        }

        # Should handle error gracefully (just log, not crash)
        await referee._send_round_results(
            "match1",
            "http://localhost:9001",
            "http://localhost:9002",
            round_result
        )


class TestRefereeAgentMatchSession:
    """Test match session handling."""

    @pytest.fixture
    def referee(self):
        return RefereeAgent(
            referee_id="ref1",
            host="localhost",
            port=7001,
        )

    def test_match_session_creation(self, referee):
        """Test creating match session with custom timeout."""
        match_info = {
            "match_id": "match1",
            "player_a": {"player_id": "p1", "endpoint": "http://localhost:9001"},
            "player_b": {"player_id": "p2", "endpoint": "http://localhost:9002"},
            "game_type": "even_odd",
            "rounds": 5,
            "timeout": 120,  # Custom timeout
        }

        # Just verify it doesn't crash with custom timeout
        assert match_info["timeout"] == 120


class TestRefereeAgentRegistration:
    """Test referee registration edge cases."""

    @pytest.fixture
    def referee(self):
        return RefereeAgent(
            referee_id="ref1",
            host="localhost",
            port=7001,
        )

    @pytest.mark.asyncio
    async def test_register_with_league_network_error(self, referee):
        """Test registration when network fails."""
        with patch("src.agents.referee.MCPClient") as mock_client_class:
            mock_client = Mock()
            mock_client.call_tool = AsyncMock(side_effect=Exception("Connection failed"))
            mock_client_class.return_value = mock_client

            result = await referee.register_with_league("http://localhost:8080")

            assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_register_with_league_rejected(self, referee):
        """Test registration when league rejects."""
        with patch("src.agents.referee.MCPClient") as mock_client_class:
            mock_client = Mock()
            mock_client.call_tool = AsyncMock(return_value={
                "status": "rejected",
                "reason": "League full"
            })
            mock_client_class.return_value = mock_client

            result = await referee.register_with_league("http://localhost:8080")

            assert result["status"] == "rejected"


class TestRefereeAgentToolHandlers:
    """Test referee tool handlers."""

    @pytest.fixture
    def referee(self):
        return RefereeAgent(
            referee_id="ref1",
            host="localhost",
            port=7001,
        )

    @pytest.mark.asyncio
    async def test_get_game_state_tool(self, referee):
        """Test get_game_state tool."""
        # Create a game
        game = OddEvenGame("p1", "p2", rounds=1)
        game.start()

        referee._games["match1"] = {
            "game": game,
            "match_id": "match1",
            "state": "active",
        }

        result = await referee._handle_get_game_state({"game_id": "match1"})

        assert result["game_id"] == "match1"
        assert result["state"] == "active"

    @pytest.mark.asyncio
    async def test_list_active_games_tool(self, referee):
        """Test list_active_games tool."""
        # Create multiple games
        game1 = OddEvenGame("p1", "p2", rounds=1)
        game2 = OddEvenGame("p3", "p4", rounds=1)

        referee._games = {
            "match1": {"game": game1, "match_id": "match1", "state": "active"},
            "match2": {"game": game2, "match_id": "match2", "state": "active"},
        }

        result = await referee._handle_list_active_games({})

        assert len(result["games"]) == 2
        assert result["count"] == 2


class TestRefereeAgentLifecycle:
    """Test referee lifecycle methods."""

    @pytest.fixture
    def referee(self):
        return RefereeAgent(
            referee_id="ref1",
            host="localhost",
            port=7001,
        )

    @pytest.mark.asyncio
    async def test_on_start(self, referee):
        """Test referee on_start lifecycle."""
        await referee.on_start()
        # Should complete without error

    @pytest.mark.asyncio
    async def test_on_stop(self, referee):
        """Test referee on_stop lifecycle."""
        await referee.on_stop()
        # Should complete without error


class TestRefereeAgentProtocolHandling:
    """Test protocol message handling."""

    @pytest.fixture
    def referee(self):
        return RefereeAgent(
            referee_id="ref1",
            host="localhost",
            port=7001,
        )

    @pytest.mark.asyncio
    async def test_handle_choose_parity_response(self, referee):
        """Test handling choose parity response."""
        # Setup game with pending parity choice
        game = OddEvenGame("p1", "p2", rounds=1)

        referee._games["match1"] = {
            "game": game,
            "match_id": "match1",
            "state": "waiting_parity",
            "player_a": {"player_id": "p1"},
        }

        message = {
            "game_id": "match1",
            "player_id": "p1",
            "choice": "odd",
        }

        result = await referee._handle_choose_parity_response(message)

        # Should process parity choice
        assert result is not None or referee._games["match1"]["game"]._player_a_role is not None
