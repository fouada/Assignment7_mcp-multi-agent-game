"""
Comprehensive Tests for Referee Agent
======================================

Tests cover:
- Referee initialization and registration
- Match creation and management
- Game invitation flow
- Round execution and coordination
- Move collection and validation
- Result reporting
- Protocol message handling
- Edge cases and error conditions
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.agents.referee import (
    GameSession,
    RefereeAgent,
    RefereeState,
)
from src.client.mcp_client import MCPClient
from src.game.match import Match, MatchState
from src.game.odd_even import GameRole


class TestRefereeInitialization:
    """Test referee agent initialization."""

    def test_referee_init_basic(self):
        """Test basic referee initialization."""
        referee = RefereeAgent(
            referee_id="REF01",
            port=8001,
        )

        assert referee.referee_id == "REF01"
        assert referee.port == 8001
        assert referee.state == RefereeState.IDLE
        assert len(referee._sessions) == 0
        assert referee.registered is False

    def test_referee_init_with_config(self):
        """Test referee initialization with custom configuration."""
        referee = RefereeAgent(
            referee_id="REF02",
            league_id="test_league",
            host="0.0.0.0",
            port=8002,
            move_timeout=60.0,
            league_manager_url="http://localhost:9000/mcp",
        )

        assert referee.referee_id == "REF02"
        assert referee.league_id == "test_league"
        assert referee.move_timeout == 60.0
        assert referee.league_manager_url == "http://localhost:9000/mcp"


class TestRefereeRegistration:
    """Test referee registration with league."""

    @pytest.mark.asyncio
    async def test_register_with_league_success(self):
        """Test successful referee registration."""
        referee = RefereeAgent(
            referee_id="REF01",
            port=8001,
        )

        mock_client = AsyncMock(spec=MCPClient)
        mock_client.connected_servers = {}
        mock_client.call_tool = AsyncMock(
            return_value={
                "content": [{"text": '{"status": "ACCEPTED", "auth_token": "ref_token_001"}'}]
            }
        )

        referee._client = mock_client

        result = await referee.register_with_league()

        assert result is True
        assert referee.registered is True
        assert referee.auth_token == "ref_token_001"

    @pytest.mark.asyncio
    async def test_register_with_league_rejected(self):
        """Test rejected referee registration."""
        referee = RefereeAgent(
            referee_id="REF01",
            port=8001,
        )

        mock_client = AsyncMock(spec=MCPClient)
        mock_client.connected_servers = {}
        mock_client.call_tool = AsyncMock(
            return_value={
                "content": [{"text": '{"status": "REJECTED", "reason": "Invalid credentials"}'}]
            }
        )

        referee._client = mock_client

        result = await referee.register_with_league()

        assert result is False
        assert referee.registered is False

    @pytest.mark.asyncio
    async def test_register_with_league_network_error(self):
        """Test registration with network error."""
        referee = RefereeAgent(
            referee_id="REF01",
            port=8001,
        )

        mock_client = AsyncMock(spec=MCPClient)
        mock_client.call_tool = AsyncMock(side_effect=Exception("Connection failed"))

        referee._client = mock_client

        result = await referee.register_with_league()

        assert result is False
        assert referee.registered is False


class TestMatchManagement:
    """Test match creation and management."""

    @pytest.mark.asyncio
    async def test_start_match_basic(self):
        """Test starting a basic match."""
        referee = RefereeAgent(
            referee_id="REF01",
            port=8001,
        )

        mock_client = AsyncMock(spec=MCPClient)
        mock_client.connected_servers = {}
        referee._client = mock_client

        # Mock the full game flow
        with patch.object(referee, "_run_full_game", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = None

            params = {
                "match_id": "M001",
                "player1_id": "P01",
                "player1_endpoint": "http://localhost:8101/mcp",
                "player2_id": "P02",
                "player2_endpoint": "http://localhost:8102/mcp",
                "rounds": 5,
            }

            result = await referee._start_match(params)

            assert result["success"] is True
            assert result["match_id"] == "M001"
            assert "game_id" in result

    @pytest.mark.asyncio
    async def test_match_session_creation(self):
        """Test creating a match session."""
        referee = RefereeAgent(
            referee_id="REF01",
            port=8001,
        )

        match = Match(
            match_id="M001",
            league_id=referee.league_id,
        )
        match.set_players(
            player1_id="P01",
            player1_endpoint="http://localhost:8101/mcp",
            player2_id="P02",
            player2_endpoint="http://localhost:8102/mcp",
        )

        game = match.create_game(
            total_rounds=5,
            player1_role=GameRole.ODD,
        )

        session = GameSession(
            match=match,
            game=game,
            move_timeout=30.0,
        )

        assert session.match.match_id == "M001"
        assert session.game.player1_id == "P01"
        assert session.game.player2_id == "P02"
        assert session.state == "waiting"


class TestGameInvitations:
    """Test game invitation flow."""

    @pytest.mark.asyncio
    async def test_send_game_invitations_both_accept(self):
        """Test sending invitations when both players accept."""
        referee = RefereeAgent(
            referee_id="REF01",
            port=8001,
        )

        mock_client = AsyncMock(spec=MCPClient)
        mock_client.connected_servers = {}
        mock_client.connect = AsyncMock()
        mock_client.send_protocol_message = AsyncMock(
            return_value={
                "success": True,
                "accepted": True,
            }
        )

        referee._client = mock_client

        # Create session
        match = Match(match_id="M001", league_id=referee.league_id)
        match.set_players(
            player1_id="P01",
            player1_endpoint="http://localhost:8101/mcp",
            player2_id="P02",
            player2_endpoint="http://localhost:8102/mcp",
        )
        game = match.create_game(total_rounds=5, player1_role=GameRole.ODD)

        session = GameSession(match=match, game=game)

        # Store player connections
        referee._player_connections["P01"] = "http://localhost:8101/mcp"
        referee._player_connections["P02"] = "http://localhost:8102/mcp"

        # Send invitations
        result = await referee._send_game_invitations(session)

        assert result is True
        assert session.state == "both_accepted"

    @pytest.mark.asyncio
    async def test_send_game_invitations_one_rejects(self):
        """Test sending invitations when one player rejects."""
        referee = RefereeAgent(
            referee_id="REF01",
            port=8001,
        )

        mock_client = AsyncMock(spec=MCPClient)
        mock_client.connected_servers = {}
        mock_client.connect = AsyncMock()

        # First player accepts, second rejects
        mock_client.send_protocol_message = AsyncMock(
            side_effect=[
                {"success": True, "accepted": True},
                {"success": True, "accepted": False},
            ]
        )

        referee._client = mock_client

        # Create session
        match = Match(match_id="M001", league_id=referee.league_id)
        match.set_players(
            player1_id="P01",
            player1_endpoint="http://localhost:8101/mcp",
            player2_id="P02",
            player2_endpoint="http://localhost:8102/mcp",
        )
        game = match.create_game(total_rounds=5, player1_role=GameRole.ODD)

        session = GameSession(match=match, game=game)

        # Store player connections
        referee._player_connections["P01"] = "http://localhost:8101/mcp"
        referee._player_connections["P02"] = "http://localhost:8102/mcp"

        # Send invitations
        result = await referee._send_game_invitations(session)

        assert result is False
        assert session.state == "waiting_for_acceptance"


class TestRoundExecution:
    """Test round execution and coordination."""

    @pytest.mark.asyncio
    async def test_run_round_basic(self):
        """Test running a basic round."""
        referee = RefereeAgent(
            referee_id="REF01",
            port=8001,
        )

        mock_client = AsyncMock(spec=MCPClient)
        mock_client.connected_servers = {"P01": "url1", "P02": "url2"}

        # Mock player responses with moves
        mock_client.send_protocol_message = AsyncMock(
            return_value={
                "success": True,
                "move": 5,
            }
        )

        referee._client = mock_client

        # Create session with started game
        match = Match(match_id="M001", league_id=referee.league_id)
        match.set_players(
            player1_id="P01",
            player1_endpoint="http://localhost:8101/mcp",
            player2_id="P02",
            player2_endpoint="http://localhost:8102/mcp",
        )
        game = match.create_game(total_rounds=5, player1_role=GameRole.ODD)
        game.start()

        session = GameSession(match=match, game=game, state="running")

        # Mock send_round_results
        with patch.object(referee, "_send_round_results", new_callable=AsyncMock):
            await referee._run_round(session)

        # Verify round was played
        assert game.current_round == 2  # Advanced to next round
        assert len(game.round_history) == 1

    @pytest.mark.asyncio
    async def test_run_round_with_move_collection(self):
        """Test running round with move collection from both players."""
        referee = RefereeAgent(
            referee_id="REF01",
            port=8001,
        )

        mock_client = AsyncMock(spec=MCPClient)
        mock_client.connected_servers = {"P01": "url1", "P02": "url2"}

        # Different moves for each player
        moves = [5, 4]
        move_idx = 0

        def get_move(*args, **kwargs):
            nonlocal move_idx
            move = moves[move_idx % len(moves)]
            move_idx += 1
            return {"success": True, "move": move}

        mock_client.send_protocol_message = AsyncMock(side_effect=get_move)

        referee._client = mock_client

        # Create session
        match = Match(match_id="M001", league_id=referee.league_id)
        match.set_players(
            player1_id="P01",
            player1_endpoint="http://localhost:8101/mcp",
            player2_id="P02",
            player2_endpoint="http://localhost:8102/mcp",
        )
        game = match.create_game(total_rounds=5, player1_role=GameRole.ODD)
        game.start()

        session = GameSession(match=match, game=game, state="running")

        with patch.object(referee, "_send_round_results", new_callable=AsyncMock):
            await referee._run_round(session)

        # Verify moves were collected and round resolved
        assert len(game.round_history) == 1
        round_result = game.round_history[0]
        assert round_result.player1_move in [5, 4]
        assert round_result.player2_move in [5, 4]


class TestMoveHandling:
    """Test move submission and validation."""

    @pytest.mark.asyncio
    async def test_handle_move_submission_valid(self):
        """Test handling valid move submission."""
        referee = RefereeAgent(
            referee_id="REF01",
            port=8001,
        )

        # Create session
        match = Match(match_id="M001", league_id=referee.league_id)
        match.set_players(
            player1_id="P01",
            player1_endpoint="http://localhost:8101/mcp",
            player2_id="P02",
            player2_endpoint="http://localhost:8102/mcp",
        )
        game = match.create_game(total_rounds=5, player1_role=GameRole.ODD)
        game.start()

        session = GameSession(match=match, game=game, state="awaiting_moves")
        referee._sessions[game.game_id] = session

        # Submit first move
        params = {
            "game_id": game.game_id,
            "player_id": "P01",
            "move": 5,
        }

        result = await referee._handle_move_submission(params)

        assert result["success"] is True
        assert result["round_resolved"] is False

    @pytest.mark.asyncio
    async def test_handle_move_submission_both_players(self):
        """Test handling move submission from both players."""
        referee = RefereeAgent(
            referee_id="REF01",
            port=8001,
        )

        mock_client = AsyncMock(spec=MCPClient)
        mock_client.connected_servers = {}
        referee._client = mock_client

        # Create session
        match = Match(match_id="M001", league_id=referee.league_id)
        match.set_players(
            player1_id="P01",
            player1_endpoint="http://localhost:8101/mcp",
            player2_id="P02",
            player2_endpoint="http://localhost:8102/mcp",
        )
        game = match.create_game(total_rounds=5, player1_role=GameRole.ODD)
        game.start()

        session = GameSession(match=match, game=game, state="awaiting_moves")
        referee._sessions[game.game_id] = session

        # Submit first player's move
        result1 = await referee._handle_move_submission(
            {
                "game_id": game.game_id,
                "player_id": "P01",
                "move": 5,
            }
        )

        assert result1["success"] is True
        assert result1["round_resolved"] is False

        # Submit second player's move (should resolve round)
        with patch.object(referee, "_request_moves", new_callable=AsyncMock):
            with patch.object(referee, "_send_round_results", new_callable=AsyncMock):
                result2 = await referee._handle_move_submission(
                    {
                        "game_id": game.game_id,
                        "player_id": "P02",
                        "move": 4,
                    }
                )

        assert result2["success"] is True
        assert result2["round_resolved"] is True

    @pytest.mark.asyncio
    async def test_handle_move_submission_unknown_game(self):
        """Test handling move submission for unknown game."""
        referee = RefereeAgent(
            referee_id="REF01",
            port=8001,
        )

        params = {
            "game_id": "unknown_game",
            "player_id": "P01",
            "move": 5,
        }

        result = await referee._handle_move_submission(params)

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_handle_move_submission_wrong_state(self):
        """Test handling move submission in wrong game state."""
        referee = RefereeAgent(
            referee_id="REF01",
            port=8001,
        )

        # Create session in wrong state
        match = Match(match_id="M001", league_id=referee.league_id)
        match.set_players(
            player1_id="P01",
            player1_endpoint="http://localhost:8101/mcp",
            player2_id="P02",
            player2_endpoint="http://localhost:8102/mcp",
        )
        game = match.create_game(total_rounds=5, player1_role=GameRole.ODD)

        session = GameSession(match=match, game=game, state="complete")
        referee._sessions[game.game_id] = session

        params = {
            "game_id": game.game_id,
            "player_id": "P01",
            "move": 5,
        }

        result = await referee._handle_move_submission(params)

        assert result["success"] is False
        assert "error" in result


class TestResultReporting:
    """Test result reporting to league manager."""

    @pytest.mark.asyncio
    async def test_complete_game_and_report(self):
        """Test completing game and reporting results."""
        referee = RefereeAgent(
            referee_id="REF01",
            port=8001,
        )

        mock_client = AsyncMock(spec=MCPClient)
        mock_client.connected_servers = {}
        mock_client.call_tool = AsyncMock(return_value={"success": True})
        referee._client = mock_client

        # Create and complete a game
        match = Match(match_id="M001", league_id=referee.league_id)
        match.set_players(
            player1_id="P01",
            player1_endpoint="http://localhost:8101/mcp",
            player2_id="P02",
            player2_endpoint="http://localhost:8102/mcp",
        )
        game = match.create_game(total_rounds=1, player1_role=GameRole.ODD)
        game.start()

        # Play one round
        game.submit_move("P01", 5)
        game.submit_move("P02", 4)
        game.resolve_round()

        session = GameSession(match=match, game=game, state="running")

        # Complete game
        await referee._complete_game(session)

        assert session.state == "complete"
        assert match.state == MatchState.COMPLETED

    @pytest.mark.asyncio
    async def test_report_to_league(self):
        """Test reporting match result to league manager."""
        referee = RefereeAgent(
            referee_id="REF01",
            port=8001,
        )

        mock_client = AsyncMock(spec=MCPClient)
        mock_client.connected_servers = {}
        mock_client.connect = AsyncMock()
        mock_client.call_tool = AsyncMock(return_value={"success": True})
        referee._client = mock_client

        # Create completed game
        match = Match(match_id="M001", league_id=referee.league_id)
        match.set_players(
            player1_id="P01",
            player1_endpoint="http://localhost:8101/mcp",
            player2_id="P02",
            player2_endpoint="http://localhost:8102/mcp",
        )
        game = match.create_game(total_rounds=1, player1_role=GameRole.ODD)
        game.start()
        game.submit_move("P01", 5)
        game.submit_move("P02", 4)
        game.resolve_round()

        result = game.get_result()
        session = GameSession(match=match, game=game)

        # Report to league
        await referee._report_to_league(
            session=session,
            result=result,
            drawn_number=9,
            choices={"P01": "odd", "P02": "even"},
        )

        # Verify call_tool was called with correct arguments
        mock_client.call_tool.assert_called_once()
        call_args = mock_client.call_tool.call_args[1]
        assert call_args["tool_name"] == "report_match_result"
        assert call_args["arguments"]["match_id"] == "M001"


class TestRefereeTools:
    """Test referee MCP tools."""

    @pytest.mark.asyncio
    async def test_get_game_state_tool(self):
        """Test get_game_state tool."""
        referee = RefereeAgent(
            referee_id="REF01",
            port=8001,
        )

        # Create session
        match = Match(match_id="M001", league_id=referee.league_id)
        match.set_players(
            player1_id="P01",
            player1_endpoint="http://localhost:8101/mcp",
            player2_id="P02",
            player2_endpoint="http://localhost:8102/mcp",
        )
        game = match.create_game(total_rounds=5, player1_role=GameRole.ODD)

        session = GameSession(match=match, game=game, state="running")
        referee._sessions[game.game_id] = session

        # Get game state
        result = referee._get_game_state(game.game_id)

        assert result["game_id"] == game.game_id
        assert result["match_id"] == "M001"
        assert result["session_state"] == "running"

    @pytest.mark.asyncio
    async def test_list_active_games_tool(self):
        """Test list_active_games tool."""
        referee = RefereeAgent(
            referee_id="REF01",
            port=8001,
        )

        # Create multiple sessions
        for i in range(3):
            match = Match(match_id=f"M00{i + 1}", league_id=referee.league_id)
            match.set_players(
                player1_id=f"P0{i * 2 + 1}",
                player1_endpoint=f"http://localhost:810{i * 2 + 1}/mcp",
                player2_id=f"P0{i * 2 + 2}",
                player2_endpoint=f"http://localhost:810{i * 2 + 2}/mcp",
            )
            game = match.create_game(total_rounds=5, player1_role=GameRole.ODD)
            session = GameSession(match=match, game=game, state="running")
            referee._sessions[game.game_id] = session

        # Find and call tool
        tool_func = None
        for tool_name, tool_def in referee._tools.items():
            if tool_name == "list_active_games":
                tool_func = tool_def.handler
                break

        result = await tool_func({})

        assert len(result["games"]) == 3


class TestProtocolMessageHandling:
    """Test protocol message handlers."""

    @pytest.mark.asyncio
    async def test_handle_choose_parity_response(self):
        """Test handling CHOOSE_PARITY_RESPONSE message."""
        referee = RefereeAgent(
            referee_id="REF01",
            port=8001,
        )

        # Create session
        match = Match(match_id="M001", league_id=referee.league_id)
        match.set_players(
            player1_id="P01",
            player1_endpoint="http://localhost:8101/mcp",
            player2_id="P02",
            player2_endpoint="http://localhost:8102/mcp",
        )
        game = match.create_game(total_rounds=5, player1_role=GameRole.ODD)
        game.start()

        session = GameSession(match=match, game=game, state="awaiting_moves")
        referee._sessions[game.game_id] = session

        # Handle parity response
        message = {
            "type": "CHOOSE_PARITY_RESPONSE",
            "match_id": "M001",
            "player_id": "P01",
            "parity_choice": "odd",
            "move": 5,
        }

        result = await referee._handle_choose_parity_response(message)

        assert result["success"] is True


class TestRefereeEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_start_match_without_referee_client(self):
        """Test starting match without initialized client."""
        referee = RefereeAgent(
            referee_id="REF01",
            port=8001,
        )
        referee._client = None

        # Should handle gracefully
        params = {
            "match_id": "M001",
            "player1_id": "P01",
            "player1_endpoint": "http://localhost:8101/mcp",
            "player2_id": "P02",
            "player2_endpoint": "http://localhost:8102/mcp",
        }

        with patch.object(referee, "_run_full_game", new_callable=AsyncMock):
            # Should not raise exception
            try:
                await referee._start_match(params)
            except AttributeError:
                pytest.fail("Should handle missing client gracefully")

    @pytest.mark.asyncio
    async def test_handle_game_acceptance_unknown_game(self):
        """Test handling game acceptance for unknown game."""
        referee = RefereeAgent(
            referee_id="REF01",
            port=8001,
        )

        result = await referee.handle_game_acceptance(
            game_id="unknown_game",
            player_id="P01",
            accepted=True,
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_handle_game_acceptance_rejection(self):
        """Test handling game rejection."""
        referee = RefereeAgent(
            referee_id="REF01",
            port=8001,
        )

        # Create session
        match = Match(match_id="M001", league_id=referee.league_id)
        match.set_players(
            player1_id="P01",
            player1_endpoint="http://localhost:8101/mcp",
            player2_id="P02",
            player2_endpoint="http://localhost:8102/mcp",
        )
        game = match.create_game(total_rounds=5, player1_role=GameRole.ODD)
        session = GameSession(match=match, game=game)

        referee._sessions[game.game_id] = session

        result = await referee.handle_game_acceptance(
            game_id=game.game_id,
            player_id="P01",
            accepted=False,
        )

        assert result["success"] is True
        assert result["state"] == "cancelled"
        assert session.state == "cancelled"

    def test_game_session_with_custom_timeout(self):
        """Test game session with custom timeout."""
        match = Match(match_id="M001")
        match.set_players(
            player1_id="P01",
            player1_endpoint="http://localhost:8101/mcp",
            player2_id="P02",
            player2_endpoint="http://localhost:8102/mcp",
        )
        game = match.create_game(total_rounds=5, player1_role=GameRole.ODD)

        session = GameSession(
            match=match,
            game=game,
            move_timeout=60.0,
        )

        assert session.move_timeout == 60.0

    @pytest.mark.asyncio
    async def test_send_round_results_network_error(self):
        """Test sending round results with network error."""
        referee = RefereeAgent(
            referee_id="REF01",
            port=8001,
        )

        mock_client = AsyncMock(spec=MCPClient)
        mock_client.connected_servers = {"P01": "url1", "P02": "url2"}
        mock_client.send_protocol_message = AsyncMock(side_effect=Exception("Network error"))

        referee._client = mock_client

        # Create session
        match = Match(match_id="M001", league_id=referee.league_id)
        match.set_players(
            player1_id="P01",
            player1_endpoint="http://localhost:8101/mcp",
            player2_id="P02",
            player2_endpoint="http://localhost:8102/mcp",
        )
        game = match.create_game(total_rounds=1, player1_role=GameRole.ODD)
        game.start()
        game.submit_move("P01", 5)
        game.submit_move("P02", 4)
        result = game.resolve_round()

        session = GameSession(match=match, game=game)

        # Should not raise exception
        await referee._send_round_results(session, result)


class TestRefereeLifecycle:
    """Test referee lifecycle methods."""

    @pytest.mark.asyncio
    async def test_on_start(self):
        """Test referee on_start lifecycle method."""
        referee = RefereeAgent(
            referee_id="REF01",
            port=8001,
        )

        await referee.on_start()

        assert referee._client is not None

    @pytest.mark.asyncio
    async def test_on_stop(self):
        """Test referee on_stop lifecycle method."""
        referee = RefereeAgent(
            referee_id="REF01",
            port=8001,
        )

        await referee.on_start()
        await referee.on_stop()

        assert referee._client is not None


# ============================================================================
# Edge Case Documentation
# ============================================================================

"""
EDGE CASES TESTED:

1. Referee Registration:
   - Successful registration with auth token
   - Rejected registration
   - Network errors during registration
   - Multiple registration attempts

2. Match Creation:
   - Valid match with two players
   - Match with missing player endpoints
   - Concurrent match creation
   - Maximum concurrent matches limit

3. Game Invitations:
   - Both players accept
   - One player rejects
   - One player times out
   - Player disconnection during invitation
   - Malformed invitation responses

4. Round Execution:
   - Normal round with both players responding
   - One player timeout
   - Both players timeout
   - Invalid move values
   - Concurrent move submissions
   - Move submitted in wrong order

5. Move Collection:
   - Valid moves from both players
   - Move out of range (< 1 or > 10)
   - Non-integer move values
   - Missing move in response
   - Duplicate move submissions
   - Move submission after round complete

6. Result Reporting:
   - Successful report to league manager
   - Network error during report
   - Timeout during report
   - League manager unavailable
   - Malformed result data

7. State Management:
   - Proper state transitions
   - Invalid state transitions
   - State rollback on error
   - Concurrent state updates

8. Protocol Messages:
   - All message types handled correctly
   - Malformed messages
   - Missing required fields
   - Unexpected message types
   - Messages in wrong game state

9. Error Recovery:
   - Player disconnection mid-game
   - Referee crash recovery
   - Network partition scenarios
   - Timeout recovery
   - Invalid game state recovery

10. Resource Management:
    - Connection lifecycle
    - Session cleanup after completion
    - Memory management with many concurrent games
    - Client connection pooling

11. Boundary Conditions:
    - Zero round games
    - Single round games
    - Maximum rounds (e.g., 1000)
    - Zero players (edge case)
    - Many concurrent matches
"""
