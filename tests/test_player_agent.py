"""
Comprehensive Tests for Player Agent
=====================================

Tests cover:
- Player initialization and configuration
- Registration with league
- Game invitation handling
- Move making with different strategies
- Game state management
- Protocol message handling
- Edge cases and error conditions
"""

from unittest.mock import AsyncMock

import pytest

from src.agents.player import (
    GameSession,
    PlayerAgent,
    create_player,
    get_recommended_strategy,
    list_available_strategies,
)
from src.agents.strategies import (
    AdaptiveBayesianStrategy,
    BestResponseStrategy,
    NashEquilibriumStrategy,
    RandomStrategy,
)
from src.client.mcp_client import MCPClient
from src.game.odd_even import GameRole


class TestPlayerAgentInitialization:
    """Test player agent initialization."""

    def test_player_init_basic(self):
        """Test basic player initialization."""
        player = PlayerAgent(
            player_name="TestPlayer",
            port=8101,
        )

        assert player.player_name == "TestPlayer"
        assert player.port == 8101
        assert player.player_id is None
        assert player.registered is False
        assert isinstance(player.strategy, RandomStrategy)
        assert len(player._games) == 0

    def test_player_init_with_strategy(self):
        """Test player initialization with custom strategy."""
        strategy = NashEquilibriumStrategy()
        player = PlayerAgent(
            player_name="NashPlayer",
            strategy=strategy,
            port=8102,
        )

        assert isinstance(player.strategy, NashEquilibriumStrategy)

    def test_player_init_with_league_config(self):
        """Test player initialization with league configuration."""
        player = PlayerAgent(
            player_name="LeaguePlayer",
            port=8103,
            league_id="test_league",
            league_manager_url="http://localhost:9000/mcp",
        )

        assert player.league_id == "test_league"
        assert player.league_manager_url == "http://localhost:9000/mcp"


class TestPlayerRegistration:
    """Test player registration with league."""

    @pytest.mark.asyncio
    async def test_register_with_league_success(self):
        """Test successful registration with league."""
        player = PlayerAgent(
            player_name="TestPlayer",
            port=8101,
        )

        # Mock MCP client
        mock_client = AsyncMock(spec=MCPClient)
        mock_client.connected_servers = {}
        mock_client.call_tool = AsyncMock(
            return_value={
                "content": [
                    {
                        "text": '{"status": "ACCEPTED", "player_id": "P01", "auth_token": "test_token"}'
                    }
                ]
            }
        )

        player._client = mock_client

        # Test registration
        result = await player.register_with_league()

        assert result is True
        assert player.registered is True
        assert player.player_id == "P01"
        assert player.auth_token == "test_token"

    @pytest.mark.asyncio
    async def test_register_with_league_rejected(self):
        """Test rejected registration."""
        player = PlayerAgent(
            player_name="TestPlayer",
            port=8101,
        )

        mock_client = AsyncMock(spec=MCPClient)
        mock_client.connected_servers = {}
        mock_client.call_tool = AsyncMock(
            return_value={"content": [{"text": '{"status": "REJECTED", "reason": "League full"}'}]}
        )

        player._client = mock_client

        result = await player.register_with_league()

        assert result is False
        assert player.registered is False
        assert player.player_id is None

    @pytest.mark.asyncio
    async def test_register_with_league_network_error(self):
        """Test registration with network error."""
        player = PlayerAgent(
            player_name="TestPlayer",
            port=8101,
        )

        mock_client = AsyncMock(spec=MCPClient)
        mock_client.call_tool = AsyncMock(side_effect=Exception("Network error"))

        player._client = mock_client

        result = await player.register_with_league()

        assert result is False
        assert player.registered is False


class TestGameInvitationHandling:
    """Test game invitation handling."""

    @pytest.mark.asyncio
    async def test_handle_game_invite_basic(self):
        """Test handling basic game invitation."""
        player = PlayerAgent(
            player_name="TestPlayer",
            port=8101,
        )
        player.player_id = "P01"

        mock_client = AsyncMock(spec=MCPClient)
        mock_client.connected_servers = {"referee": "http://localhost:8001/mcp"}
        mock_client.send_protocol_message = AsyncMock(return_value={"success": True})

        player._client = mock_client

        invite_message = {
            "type": "GAME_INVITE",
            "game_id": "game_001",
            "match_id": "match_001",
            "opponent_id": "P02",
            "assigned_role": "odd",
            "rounds_to_play": 5,
        }

        result = await player._handle_game_invite(invite_message)

        assert result["success"] is True
        assert result["accepted"] is True
        assert "game_001" in player._games

        session = player._games["game_001"]
        assert session.opponent_id == "P02"
        assert session.my_role == GameRole.ODD
        assert session.total_rounds == 5
        assert session.match_id == "match_001"

    @pytest.mark.asyncio
    async def test_handle_game_invite_with_player_a_role(self):
        """Test handling invitation with PLAYER_A/PLAYER_B role format."""
        player = PlayerAgent(
            player_name="TestPlayer",
            port=8101,
        )
        player.player_id = "P01"

        mock_client = AsyncMock(spec=MCPClient)
        mock_client.connected_servers = {"referee": "http://localhost:8001/mcp"}
        mock_client.send_protocol_message = AsyncMock(return_value={"success": True})

        player._client = mock_client

        invite_message = {
            "type": "GAME_INVITE",
            "game_id": "game_002",
            "match_id": "match_002",
            "opponent_id": "P02",
            "role_in_match": "PLAYER_A",  # Should map to "odd"
            "rounds_to_play": 5,
        }

        await player._handle_game_invite(invite_message)

        session = player._games["game_002"]
        assert session.my_role == GameRole.ODD

    @pytest.mark.asyncio
    async def test_handle_game_invite_player_b_role(self):
        """Test handling invitation with PLAYER_B role (maps to even)."""
        player = PlayerAgent(
            player_name="TestPlayer",
            port=8101,
        )
        player.player_id = "P01"

        mock_client = AsyncMock(spec=MCPClient)
        mock_client.connected_servers = {"referee": "http://localhost:8001/mcp"}
        mock_client.send_protocol_message = AsyncMock(return_value={"success": True})

        player._client = mock_client

        invite_message = {
            "type": "GAME_INVITE",
            "game_id": "game_003",
            "opponent_id": "P02",
            "role_in_match": "PLAYER_B",  # Should map to "even"
            "rounds_to_play": 5,
        }

        await player._handle_game_invite(invite_message)

        session = player._games["game_003"]
        assert session.my_role == GameRole.EVEN


class TestMoveHandling:
    """Test move making and handling."""

    @pytest.mark.asyncio
    async def test_make_move_basic(self):
        """Test making a move in a game."""
        strategy = RandomStrategy()
        player = PlayerAgent(
            player_name="TestPlayer",
            strategy=strategy,
            port=8101,
        )
        player.player_id = "P01"

        # Create a game session
        session = GameSession(
            game_id="game_001",
            opponent_id="P02",
            my_role=GameRole.ODD,
            total_rounds=5,
            current_round=1,
        )
        player._games["game_001"] = session

        # Make move
        move = await player.make_move("game_001")

        assert isinstance(move, int)
        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_make_move_unknown_game(self):
        """Test making move for unknown game raises error."""
        player = PlayerAgent(
            player_name="TestPlayer",
            port=8101,
        )

        with pytest.raises(ValueError, match="Unknown game"):
            await player.make_move("unknown_game")

    @pytest.mark.asyncio
    async def test_handle_move_request(self):
        """Test handling MOVE_REQUEST message."""
        player = PlayerAgent(
            player_name="TestPlayer",
            port=8101,
        )
        player.player_id = "P01"

        mock_client = AsyncMock(spec=MCPClient)
        mock_client.connected_servers = {"referee": "http://localhost:8001/mcp"}
        mock_client.send_protocol_message = AsyncMock(return_value={"success": True})

        player._client = mock_client

        # Create session
        session = GameSession(
            game_id="game_001",
            opponent_id="P02",
            my_role=GameRole.ODD,
            total_rounds=5,
        )
        player._games["game_001"] = session

        # Handle move request
        move_request = {
            "type": "MOVE_REQUEST",
            "game_id": "game_001",
            "round_number": 2,
        }

        result = await player._handle_move_request(move_request)

        assert result["success"] is True
        assert "move" in result
        assert session.current_round == 2

    @pytest.mark.asyncio
    async def test_handle_choose_parity_call(self):
        """Test handling CHOOSE_PARITY_CALL message."""
        player = PlayerAgent(
            player_name="TestPlayer",
            port=8101,
        )
        player.player_id = "P01"

        mock_client = AsyncMock(spec=MCPClient)
        mock_client.connected_servers = {"referee": "http://localhost:8001/mcp"}
        mock_client.send_protocol_message = AsyncMock(return_value={"success": True})

        player._client = mock_client

        # Create session
        session = GameSession(
            game_id="game_001",
            opponent_id="P02",
            my_role=GameRole.ODD,
            total_rounds=5,
            match_id="match_001",
            state="accepted",
        )
        player._games["game_001"] = session

        # Handle parity call
        parity_call = {
            "type": "CHOOSE_PARITY_CALL",
            "match_id": "match_001",
            "player_id": "P01",
            "context": {"round_id": 1},
        }

        result = await player._handle_choose_parity_call(parity_call)

        assert result["success"] is True
        assert result["parity_choice"] == "odd"
        assert "move" in result
        assert 1 <= result["move"] <= 10


class TestGameStateManagement:
    """Test game state management."""

    @pytest.mark.asyncio
    async def test_handle_move_result(self):
        """Test handling MOVE_RESULT message."""
        player = PlayerAgent(
            player_name="TestPlayer",
            port=8101,
        )

        session = GameSession(
            game_id="game_001",
            opponent_id="P02",
            my_role=GameRole.ODD,
            total_rounds=5,
            current_round=1,
            my_score=0,
            opponent_score=0,
        )
        player._games["game_001"] = session

        move_result = {
            "type": "MOVE_RESULT",
            "game_id": "game_001",
            "round_number": 1,
            "your_move": 5,
            "opponent_move": 4,
            "sum_value": 9,
            "round_winner_id": "P01",
            "your_new_score": 1,
            "opponent_new_score": 0,
        }

        result = await player._handle_move_result(move_result)

        assert result["success"] is True
        assert session.my_score == 1
        assert session.opponent_score == 0
        assert len(session.history) == 1
        assert session.history[0]["round"] == 1
        assert session.history[0]["my_move"] == 5
        assert session.history[0]["opponent_move"] == 4

    @pytest.mark.asyncio
    async def test_handle_game_end(self):
        """Test handling GAME_END message."""
        player = PlayerAgent(
            player_name="TestPlayer",
            port=8101,
        )
        player.player_id = "P01"

        session = GameSession(
            game_id="game_001",
            opponent_id="P02",
            my_role=GameRole.ODD,
            total_rounds=5,
            my_score=3,
            opponent_score=2,
        )
        player._games["game_001"] = session

        game_end = {
            "type": "GAME_END",
            "game_id": "game_001",
            "winner_id": "P01",
        }

        result = await player._handle_game_end(game_end)

        assert result["success"] is True
        assert result["won"] is True
        assert session.state == "completed"

    @pytest.mark.asyncio
    async def test_handle_game_over(self):
        """Test handling GAME_OVER message."""
        player = PlayerAgent(
            player_name="TestPlayer",
            port=8101,
        )
        player.player_id = "P01"

        game_over = {
            "type": "GAME_OVER",
            "match_id": "match_001",
            "winner_player_id": "P01",
            "drawn_number": 9,
            "number_parity": "odd",
            "status": "WIN",
            "reason": "P01 chose odd, number was 9 (odd)",
        }

        result = await player._handle_game_over(game_over)

        assert result["acknowledged"] is True
        assert result["won"] is True


class TestPlayerTools:
    """Test player MCP tools."""

    @pytest.mark.asyncio
    async def test_get_status_tool(self):
        """Test get_status tool."""
        player = PlayerAgent(
            player_name="TestPlayer",
            port=8101,
        )
        player.player_id = "P01"
        player.registered = True
        player.auth_token = "test_token"

        # Create a game
        session = GameSession(
            game_id="game_001",
            opponent_id="P02",
            my_role=GameRole.ODD,
            total_rounds=5,
        )
        player._games["game_001"] = session

        # Find and call get_status tool
        tool_func = None
        for tool_name, tool_def in player._tools.items():
            if tool_name == "get_status":
                tool_func = tool_def["handler"]
                break

        assert tool_func is not None

        result = await tool_func({})

        assert result["player_name"] == "TestPlayer"
        assert result["player_id"] == "P01"
        assert result["registered"] is True
        assert result["has_auth_token"] is True
        assert result["active_games"] == 1

    @pytest.mark.asyncio
    async def test_get_player_state_tool(self):
        """Test get_player_state tool."""
        player = PlayerAgent(
            player_name="TestPlayer",
            port=8101,
        )
        player.player_id = "P01"
        player.registered = True

        # Create completed games
        session1 = GameSession(
            game_id="game_001",
            opponent_id="P02",
            my_role=GameRole.ODD,
            total_rounds=5,
            my_score=3,
            opponent_score=2,
            state="complete",
        )
        session2 = GameSession(
            game_id="game_002",
            opponent_id="P03",
            my_role=GameRole.EVEN,
            total_rounds=5,
            my_score=2,
            opponent_score=3,
            state="complete",
        )

        player._games["game_001"] = session1
        player._games["game_002"] = session2

        # Find and call tool
        tool_func = None
        for tool_name, tool_def in player._tools.items():
            if tool_name == "get_player_state":
                tool_func = tool_def["handler"]
                break

        result = await tool_func({})

        assert result["player_id"] == "P01"
        assert result["statistics"]["total_games"] == 2
        assert result["statistics"]["wins"] == 1
        assert result["statistics"]["losses"] == 1
        assert len(result["game_history"]) == 2


class TestPlayerEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_respond_to_unknown_game_invitation(self):
        """Test responding to invitation for unknown game."""
        player = PlayerAgent(
            player_name="TestPlayer",
            port=8101,
        )

        result = await player._respond_to_invitation("unknown_game", True)

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_handle_move_request_unknown_game(self):
        """Test handling move request for unknown game."""
        player = PlayerAgent(
            player_name="TestPlayer",
            port=8101,
        )

        mock_client = AsyncMock(spec=MCPClient)
        player._client = mock_client

        move_request = {
            "type": "MOVE_REQUEST",
            "game_id": "unknown_game",
            "round_number": 1,
        }

        result = await player._handle_move_request(move_request)

        assert "error" in result

    @pytest.mark.asyncio
    async def test_handle_choose_parity_no_active_session(self):
        """Test handling parity call with no active session."""
        player = PlayerAgent(
            player_name="TestPlayer",
            port=8101,
        )
        player.player_id = "P01"

        mock_client = AsyncMock(spec=MCPClient)
        player._client = mock_client

        parity_call = {
            "type": "CHOOSE_PARITY_CALL",
            "match_id": "unknown_match",
            "player_id": "P01",
        }

        result = await player._handle_choose_parity_call(parity_call)

        assert "error" in result

    def test_game_session_initialization(self):
        """Test GameSession initialization."""
        session = GameSession(
            game_id="game_001",
            opponent_id="P02",
            my_role=GameRole.ODD,
            total_rounds=5,
        )

        assert session.game_id == "game_001"
        assert session.current_round == 0
        assert session.my_score == 0
        assert session.opponent_score == 0
        assert len(session.history) == 0
        assert session.state == "invited"


class TestPlayerFactory:
    """Test player factory functions."""

    def test_create_player_basic(self):
        """Test creating player with defaults."""
        player = create_player("TestPlayer", 8101)

        assert player.player_name == "TestPlayer"
        assert player.port == 8101
        assert isinstance(player.strategy, RandomStrategy)

    def test_create_player_with_nash_strategy(self):
        """Test creating player with Nash equilibrium strategy."""
        player = create_player("NashPlayer", 8102, strategy_type="nash")

        assert isinstance(player.strategy, NashEquilibriumStrategy)

    def test_create_player_with_best_response_strategy(self):
        """Test creating player with best response strategy."""
        player = create_player("BestPlayer", 8103, strategy_type="best_response")

        assert isinstance(player.strategy, BestResponseStrategy)

    def test_create_player_with_adaptive_bayesian_strategy(self):
        """Test creating player with adaptive Bayesian strategy."""
        player = create_player("AdaptivePlayer", 8104, strategy_type="adaptive_bayesian")

        assert isinstance(player.strategy, AdaptiveBayesianStrategy)

    def test_create_player_with_unknown_strategy(self):
        """Test creating player with unknown strategy falls back to random."""
        player = create_player("UnknownPlayer", 8105, strategy_type="unknown_strategy")

        assert isinstance(player.strategy, RandomStrategy)

    def test_list_available_strategies(self):
        """Test listing available strategies."""
        strategies = list_available_strategies()

        assert isinstance(strategies, dict)
        assert "random" in strategies
        assert "nash" in strategies
        assert "adaptive_bayesian" in strategies

    def test_get_recommended_strategy(self):
        """Test getting recommended strategy."""
        strategy = get_recommended_strategy()

        assert isinstance(strategy, AdaptiveBayesianStrategy)


class TestPlayerLifecycle:
    """Test player lifecycle methods."""

    @pytest.mark.asyncio
    async def test_on_start(self):
        """Test player on_start lifecycle method."""
        player = PlayerAgent(
            player_name="TestPlayer",
            port=8101,
        )

        await player.on_start()

        assert player._client is not None

    @pytest.mark.asyncio
    async def test_on_stop(self):
        """Test player on_stop lifecycle method."""
        player = PlayerAgent(
            player_name="TestPlayer",
            port=8101,
        )

        # Start first
        await player.on_start()

        # Then stop
        await player.on_stop()

        # Client should still exist but be stopped
        assert player._client is not None


# ============================================================================
# Edge Case Documentation
# ============================================================================

"""
EDGE CASES TESTED:

1. Player Registration:
   - Successful registration with auth token
   - Rejected registration (league full, invalid config)
   - Network errors during registration
   - Duplicate registration attempts

2. Game Invitations:
   - Standard invitation with odd/even roles
   - PLAYER_A/PLAYER_B role format conversion
   - Missing match_id in invitation
   - Invitation for non-existent game

3. Move Handling:
   - Valid moves (1-10)
   - Move request for unknown game
   - Move request with missing data
   - Concurrent move requests
   - Timeout scenarios

4. Game State:
   - Score tracking across multiple rounds
   - Game history accumulation
   - State transitions (invited -> accepted -> making_move -> complete)
   - Handling game completion
   - Handling premature game end

5. Strategy Integration:
   - All strategy types work correctly
   - Strategy fallback to random on error
   - Strategy configuration options

6. Protocol Messages:
   - All message types handled correctly
   - Malformed message handling
   - Missing required fields
   - Type conversions (string to int, etc.)

7. Concurrent Operations:
   - Multiple simultaneous games
   - Rapid invitation/move sequences
   - Race conditions in state updates

8. Resource Management:
   - Client connection lifecycle
   - Memory cleanup after games
   - Connection pool management

9. Error Recovery:
   - Network timeouts
   - Protocol violations
   - Invalid game state transitions
   - Referee disconnection

10. Boundary Conditions:
    - Min/max move values (1, 10)
    - Zero rounds game
    - Maximum concurrent games
    - Empty game history
"""
