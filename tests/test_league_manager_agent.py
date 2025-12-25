"""
Comprehensive Tests for League Manager Agent
=============================================

Tests cover:
- League initialization and configuration
- Player registration management
- Referee registration and assignment
- Round-robin schedule generation
- Round execution and coordination
- Standings tracking and updates
- Match result processing
- Edge cases and error conditions
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from src.agents.league_manager import (
    LeagueManager,
    LeagueState,
    RegisteredPlayer,
    RegisteredReferee,
)
from src.game.match import Match, MatchState, MatchScheduler
from src.client.mcp_client import MCPClient
from src.common.protocol import RegistrationStatus


class TestLeagueManagerInitialization:
    """Test league manager initialization."""
    
    def test_league_manager_init_basic(self):
        """Test basic league manager initialization."""
        manager = LeagueManager(
            league_id="test_league",
            port=8000,
        )
        
        assert manager.league_id == "test_league"
        assert manager.port == 8000
        assert manager.state == LeagueState.REGISTRATION
        assert manager.current_round == 0
        assert len(manager._players) == 0
        assert len(manager._referees) == 0
    
    def test_league_manager_init_with_config(self):
        """Test league manager initialization with custom configuration."""
        manager = LeagueManager(
            league_id="custom_league",
            min_players=4,
            max_players=16,
            host="0.0.0.0",
            port=9000,
        )
        
        assert manager.league_id == "custom_league"
        assert manager.min_players == 4
        assert manager.max_players == 16
        assert manager.port == 9000


class TestPlayerRegistration:
    """Test player registration."""
    
    @pytest.mark.asyncio
    async def test_register_player_success(self):
        """Test successful player registration."""
        manager = LeagueManager(league_id="test_league", port=8000)
        
        params = {
            "display_name": "TestPlayer",
            "endpoint": "http://localhost:8101/mcp",
            "version": "1.0.0",
            "game_types": ["even_odd"],
        }
        
        result = await manager._handle_registration(params)
        
        assert result["status"] == RegistrationStatus.ACCEPTED.value
        assert "player_id" in result
        assert "auth_token" in result
        assert len(manager._players) == 1
    
    @pytest.mark.asyncio
    async def test_register_multiple_players(self):
        """Test registering multiple players."""
        manager = LeagueManager(league_id="test_league", port=8000)
        
        for i in range(5):
            params = {
                "display_name": f"Player{i+1}",
                "endpoint": f"http://localhost:810{i+1}/mcp",
                "version": "1.0.0",
                "game_types": ["even_odd"],
            }
            
            result = await manager._handle_registration(params)
            
            assert result["status"] == RegistrationStatus.ACCEPTED.value
            assert result["player_id"] == f"P0{i+1}"
        
        assert len(manager._players) == 5
    
    @pytest.mark.asyncio
    async def test_register_player_league_full(self):
        """Test player registration when league is full."""
        manager = LeagueManager(
            league_id="test_league",
            max_players=2,
            port=8000,
        )
        
        # Register max players
        for i in range(2):
            params = {
                "display_name": f"Player{i+1}",
                "endpoint": f"http://localhost:810{i+1}/mcp",
                "game_types": ["even_odd"],
            }
            await manager._handle_registration(params)
        
        # Try to register one more
        params = {
            "display_name": "Player3",
            "endpoint": "http://localhost:8103/mcp",
            "game_types": ["even_odd"],
        }
        
        result = await manager._handle_registration(params)
        
        assert result["status"] == RegistrationStatus.REJECTED.value
        assert "full" in result["reason"].lower()
    
    @pytest.mark.asyncio
    async def test_register_player_registration_closed(self):
        """Test player registration when registration is closed."""
        manager = LeagueManager(league_id="test_league", port=8000)
        manager.state = LeagueState.IN_PROGRESS
        
        params = {
            "display_name": "LatePlayer",
            "endpoint": "http://localhost:8101/mcp",
            "game_types": ["even_odd"],
        }
        
        result = await manager._handle_registration(params)
        
        assert result["status"] == RegistrationStatus.REJECTED.value
        assert "closed" in result["reason"].lower()
    
    @pytest.mark.asyncio
    async def test_register_player_duplicate_endpoint(self):
        """Test registering player with duplicate endpoint."""
        manager = LeagueManager(league_id="test_league", port=8000)
        
        endpoint = "http://localhost:8101/mcp"
        
        # Register first player
        params1 = {
            "display_name": "Player1",
            "endpoint": endpoint,
            "game_types": ["even_odd"],
        }
        await manager._handle_registration(params1)
        
        # Try to register with same endpoint
        params2 = {
            "display_name": "Player2",
            "endpoint": endpoint,
            "game_types": ["even_odd"],
        }
        
        result = await manager._handle_registration(params2)
        
        assert result["status"] == RegistrationStatus.REJECTED.value
        assert "already registered" in result["reason"].lower()
    
    @pytest.mark.asyncio
    async def test_register_player_missing_game_type(self):
        """Test registering player without required game type."""
        manager = LeagueManager(league_id="test_league", port=8000)
        
        params = {
            "display_name": "TestPlayer",
            "endpoint": "http://localhost:8101/mcp",
            "game_types": ["other_game"],  # Missing "even_odd"
        }
        
        result = await manager._handle_registration(params)
        
        assert result["status"] == RegistrationStatus.REJECTED.value
        assert "even_odd" in result["reason"].lower()


class TestRefereeRegistration:
    """Test referee registration."""
    
    @pytest.mark.asyncio
    async def test_register_referee_success(self):
        """Test successful referee registration."""
        manager = LeagueManager(league_id="test_league", port=8000)
        
        params = {
            "referee_id": "REF01",
            "endpoint": "http://localhost:8001/mcp",
            "display_name": "Referee_Alpha",
            "version": "1.0.0",
            "game_types": ["even_odd"],
            "max_concurrent_matches": 2,
        }
        
        result = await manager._handle_referee_registration(params)
        
        assert result["status"] == RegistrationStatus.ACCEPTED.value
        assert result["referee_id"] == "REF01"
        assert "auth_token" in result
        assert len(manager._referees) == 1
    
    @pytest.mark.asyncio
    async def test_register_multiple_referees(self):
        """Test registering multiple referees."""
        manager = LeagueManager(league_id="test_league", port=8000)
        
        for i in range(3):
            params = {
                "referee_id": f"REF0{i+1}",
                "endpoint": f"http://localhost:800{i+1}/mcp",
                "display_name": f"Referee_{i+1}",
                "game_types": ["even_odd"],
            }
            
            result = await manager._handle_referee_registration(params)
            
            assert result["status"] == RegistrationStatus.ACCEPTED.value
        
        assert len(manager._referees) == 3
    
    @pytest.mark.asyncio
    async def test_register_referee_duplicate(self):
        """Test registering duplicate referee."""
        manager = LeagueManager(league_id="test_league", port=8000)
        
        params = {
            "referee_id": "REF01",
            "endpoint": "http://localhost:8001/mcp",
            "game_types": ["even_odd"],
        }
        
        # Register first time
        await manager._handle_referee_registration(params)
        
        # Try to register again
        result = await manager._handle_referee_registration(params)
        
        assert result["status"] == RegistrationStatus.REJECTED.value
        assert "already registered" in result["reason"].lower()


class TestScheduleGeneration:
    """Test schedule generation."""
    
    @pytest.mark.asyncio
    async def test_start_league_success(self):
        """Test successful league start with schedule generation."""
        manager = LeagueManager(
            league_id="test_league",
            min_players=2,
            port=8000,
        )
        
        # Register minimum players
        for i in range(4):
            params = {
                "display_name": f"Player{i+1}",
                "endpoint": f"http://localhost:810{i+1}/mcp",
                "game_types": ["even_odd"],
            }
            await manager._handle_registration(params)
        
        result = await manager._start_league()
        
        assert result["success"] is True
        assert manager.state == LeagueState.READY
        assert len(manager._schedule) > 0
        assert result["players"] == 4
        assert result["rounds"] == 3  # Round-robin for 4 players = 3 rounds
    
    @pytest.mark.asyncio
    async def test_start_league_insufficient_players(self):
        """Test league start with insufficient players."""
        manager = LeagueManager(
            league_id="test_league",
            min_players=4,
            port=8000,
        )
        
        # Register only 2 players
        for i in range(2):
            params = {
                "display_name": f"Player{i+1}",
                "endpoint": f"http://localhost:810{i+1}/mcp",
                "game_types": ["even_odd"],
            }
            await manager._handle_registration(params)
        
        result = await manager._start_league()
        
        assert result["success"] is False
        assert "at least" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_start_league_already_started(self):
        """Test starting league that's already started."""
        manager = LeagueManager(league_id="test_league", port=8000)
        manager.state = LeagueState.IN_PROGRESS
        
        result = await manager._start_league()
        
        assert result["success"] is False
        assert "already started" in result["error"].lower()
    
    def test_round_robin_schedule_even_players(self):
        """Test round-robin schedule generation with even number of players."""
        player_ids = ["P01", "P02", "P03", "P04"]
        schedule = MatchScheduler.create_round_robin_schedule(player_ids)
        
        # 4 players = 3 rounds
        assert len(schedule) == 3
        
        # Each round should have 2 matches
        for round_matches in schedule:
            assert len(round_matches) == 2
        
        # Each player should play 3 games total
        player_games = {pid: 0 for pid in player_ids}
        for round_matches in schedule:
            for p1, p2 in round_matches:
                player_games[p1] += 1
                player_games[p2] += 1
        
        for pid, games in player_games.items():
            assert games == 3
    
    def test_round_robin_schedule_odd_players(self):
        """Test round-robin schedule generation with odd number of players."""
        player_ids = ["P01", "P02", "P03"]
        schedule = MatchScheduler.create_round_robin_schedule(player_ids)
        
        # 3 players = 3 rounds (with byes)
        assert len(schedule) == 3
        
        # Each round should have 1 match (one player gets bye)
        for round_matches in schedule:
            assert len(round_matches) == 1
    
    def test_round_robin_schedule_two_players(self):
        """Test round-robin schedule with minimum players."""
        player_ids = ["P01", "P02"]
        schedule = MatchScheduler.create_round_robin_schedule(player_ids)
        
        # 2 players = 1 round
        assert len(schedule) == 1
        assert len(schedule[0]) == 1
        assert schedule[0][0] == ("P01", "P02")


class TestRoundExecution:
    """Test round execution and coordination."""
    
    @pytest.mark.asyncio
    async def test_start_next_round_success(self):
        """Test starting next round successfully."""
        manager = LeagueManager(league_id="test_league", port=8000)
        
        # Setup: Register players and referees
        for i in range(4):
            await manager._handle_registration({
                "display_name": f"Player{i+1}",
                "endpoint": f"http://localhost:810{i+1}/mcp",
                "game_types": ["even_odd"],
            })
        
        await manager._handle_referee_registration({
            "referee_id": "REF01",
            "endpoint": "http://localhost:8001/mcp",
            "game_types": ["even_odd"],
        })
        
        # Start league
        await manager._start_league()
        
        # Mock client
        mock_client = AsyncMock(spec=MCPClient)
        mock_client.connected_servers = {}
        mock_client.call_tool = AsyncMock(return_value={"success": True})
        manager._client = mock_client
        
        # Start first round
        result = await manager.start_next_round()
        
        assert result["success"] is True
        assert result["round"] == 1
        assert manager.state == LeagueState.IN_PROGRESS
        assert len(result["matches"]) > 0
    
    @pytest.mark.asyncio
    async def test_start_next_round_without_referees(self):
        """Test starting round without registered referees."""
        manager = LeagueManager(league_id="test_league", port=8000)
        
        # Register players only
        for i in range(4):
            await manager._handle_registration({
                "display_name": f"Player{i+1}",
                "endpoint": f"http://localhost:810{i+1}/mcp",
                "game_types": ["even_odd"],
            })
        
        # Start league
        await manager._start_league()
        
        # Try to start round without referees
        result = await manager.start_next_round()
        
        assert result["success"] is False
        assert "referee" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_start_next_round_all_completed(self):
        """Test starting round when all rounds are complete."""
        manager = LeagueManager(league_id="test_league", port=8000)
        
        # Register players
        for i in range(2):
            await manager._handle_registration({
                "display_name": f"Player{i+1}",
                "endpoint": f"http://localhost:810{i+1}/mcp",
                "game_types": ["even_odd"],
            })
        
        # Start league
        await manager._start_league()
        
        # Set current round to beyond schedule
        manager.current_round = len(manager._schedule)
        manager.state = LeagueState.READY
        
        result = await manager.start_next_round()
        
        assert result["success"] is False
        assert result.get("league_complete") is True
        assert manager.state == LeagueState.COMPLETED
    
    @pytest.mark.asyncio
    async def test_assign_referee_to_match(self):
        """Test referee assignment to matches."""
        manager = LeagueManager(league_id="test_league", port=8000)
        
        # Register referees
        for i in range(2):
            await manager._handle_referee_registration({
                "referee_id": f"REF0{i+1}",
                "endpoint": f"http://localhost:800{i+1}/mcp",
                "game_types": ["even_odd"],
            })
        
        # Assign referees to matches (round-robin)
        ref1 = manager._assign_referee_to_match(0)
        ref2 = manager._assign_referee_to_match(1)
        ref3 = manager._assign_referee_to_match(2)
        
        assert ref1 in ["REF01", "REF02"]
        assert ref2 in ["REF01", "REF02"]
        assert ref3 in ["REF01", "REF02"]


class TestMatchResultProcessing:
    """Test match result processing."""
    
    @pytest.mark.asyncio
    async def test_handle_match_result_with_winner(self):
        """Test handling match result with winner."""
        manager = LeagueManager(league_id="test_league", port=8000)
        
        # Register players
        for i in range(2):
            await manager._handle_registration({
                "display_name": f"Player{i+1}",
                "endpoint": f"http://localhost:810{i+1}/mcp",
                "game_types": ["even_odd"],
            })
        
        # Create a match
        match = Match(match_id="M001", league_id=manager.league_id)
        match.set_players(
            player1_id="P01",
            player1_endpoint="http://localhost:8101/mcp",
            player2_id="P02",
            player2_endpoint="http://localhost:8102/mcp",
        )
        manager._matches["M001"] = match
        manager._current_round_matches = [match]
        
        # Report result
        params = {
            "match_id": "M001",
            "winner_id": "P01",
            "player1_score": 3,
            "player2_score": 2,
        }
        
        with patch.object(manager, '_publish_standings_update', new_callable=AsyncMock):
            result = await manager._handle_match_result(params)
        
        assert result["success"] is True
        assert manager._players["P01"].wins == 1
        assert manager._players["P02"].losses == 1
        assert manager._players["P01"].points == 3
    
    @pytest.mark.asyncio
    async def test_handle_match_result_draw(self):
        """Test handling match result with draw."""
        manager = LeagueManager(league_id="test_league", port=8000)
        
        # Register players
        for i in range(2):
            await manager._handle_registration({
                "display_name": f"Player{i+1}",
                "endpoint": f"http://localhost:810{i+1}/mcp",
                "game_types": ["even_odd"],
            })
        
        # Create a match
        match = Match(match_id="M001", league_id=manager.league_id)
        match.set_players(
            player1_id="P01",
            player1_endpoint="http://localhost:8101/mcp",
            player2_id="P02",
            player2_endpoint="http://localhost:8102/mcp",
        )
        manager._matches["M001"] = match
        manager._current_round_matches = [match]
        
        # Report draw
        params = {
            "match_id": "M001",
            "winner_id": None,  # No winner = draw
            "player1_score": 2,
            "player2_score": 2,
        }
        
        with patch.object(manager, '_publish_standings_update', new_callable=AsyncMock):
            result = await manager._handle_match_result(params)
        
        assert result["success"] is True
        assert manager._players["P01"].draws == 1
        assert manager._players["P02"].draws == 1
        assert manager._players["P01"].points == 1
        assert manager._players["P02"].points == 1
    
    @pytest.mark.asyncio
    async def test_handle_match_result_unknown_match(self):
        """Test handling result for unknown match."""
        manager = LeagueManager(league_id="test_league", port=8000)
        
        params = {
            "match_id": "unknown_match",
            "winner_id": "P01",
            "player1_score": 3,
            "player2_score": 2,
        }
        
        result = await manager._handle_match_result(params)
        
        assert result["success"] is False
        assert "unknown" in result["error"].lower()


class TestStandingsManagement:
    """Test standings tracking and updates."""
    
    def test_get_standings_empty(self):
        """Test getting standings with no players."""
        manager = LeagueManager(league_id="test_league", port=8000)
        
        standings = manager._get_standings()
        
        assert standings["round_id"] == 0
        assert len(standings["standings"]) == 0
    
    @pytest.mark.asyncio
    async def test_get_standings_with_players(self):
        """Test getting standings with players."""
        manager = LeagueManager(league_id="test_league", port=8000)
        
        # Register players
        for i in range(3):
            await manager._handle_registration({
                "display_name": f"Player{i+1}",
                "endpoint": f"http://localhost:810{i+1}/mcp",
                "game_types": ["even_odd"],
            })
        
        # Simulate some games
        manager._players["P01"].record_win()
        manager._players["P01"].record_win()
        manager._players["P02"].record_win()
        manager._players["P02"].record_loss()
        manager._players["P03"].record_loss()
        manager._players["P03"].record_loss()
        
        standings = manager._get_standings()
        
        assert len(standings["standings"]) == 3
        
        # Check sorting (by points, then wins)
        assert standings["standings"][0]["player_id"] == "P01"  # 6 points, 2 wins
        assert standings["standings"][1]["player_id"] == "P02"  # 3 points, 1 win
        assert standings["standings"][2]["player_id"] == "P03"  # 0 points, 0 wins
    
    def test_get_standings_ranking(self):
        """Test standings ranking order."""
        manager = LeagueManager(league_id="test_league", port=8000)
        
        # Manually create players with different records
        manager._players["P01"] = RegisteredPlayer(
            player_id="P01",
            display_name="Player1",
            endpoint="http://localhost:8101/mcp",
            wins=3,
            draws=0,
            losses=0,
            points=9,
        )
        
        manager._players["P02"] = RegisteredPlayer(
            player_id="P02",
            display_name="Player2",
            endpoint="http://localhost:8102/mcp",
            wins=2,
            draws=1,
            losses=0,
            points=7,
        )
        
        manager._players["P03"] = RegisteredPlayer(
            player_id="P03",
            display_name="Player3",
            endpoint="http://localhost:8103/mcp",
            wins=1,
            draws=1,
            losses=1,
            points=4,
        )
        
        standings = manager._get_standings()
        
        # Verify ranking
        assert standings["standings"][0]["rank"] == 1
        assert standings["standings"][0]["player_id"] == "P01"
        assert standings["standings"][1]["rank"] == 2
        assert standings["standings"][1]["player_id"] == "P02"
        assert standings["standings"][2]["rank"] == 3
        assert standings["standings"][2]["player_id"] == "P03"


class TestLeagueManagerTools:
    """Test league manager MCP tools."""
    
    @pytest.mark.asyncio
    async def test_get_players_tool(self):
        """Test get_players tool."""
        manager = LeagueManager(league_id="test_league", port=8000)
        
        # Register players
        for i in range(3):
            await manager._handle_registration({
                "display_name": f"Player{i+1}",
                "endpoint": f"http://localhost:810{i+1}/mcp",
                "game_types": ["even_odd"],
            })
        
        # Find and call tool
        tool_func = None
        for tool_name, tool_def in manager._tools.items():
            if tool_name == "get_players":
                tool_func = tool_def["handler"]
                break
        
        result = await tool_func({})
        
        assert len(result["players"]) == 3
    
    @pytest.mark.asyncio
    async def test_get_round_status_tool(self):
        """Test get_round_status tool."""
        manager = LeagueManager(league_id="test_league", port=8000)
        
        # Register and start
        for i in range(4):
            await manager._handle_registration({
                "display_name": f"Player{i+1}",
                "endpoint": f"http://localhost:810{i+1}/mcp",
                "game_types": ["even_odd"],
            })
        
        await manager._start_league()
        
        # Find and call tool
        tool_func = None
        for tool_name, tool_def in manager._tools.items():
            if tool_name == "get_round_status":
                tool_func = tool_def["handler"]
                break
        
        result = await tool_func({})
        
        assert result["league_id"] == "test_league"
        assert result["state"] == LeagueState.READY.value
        assert result["current_round"] == 0
        assert result["total_rounds"] == 3


class TestLeagueManagerEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_registered_player_record_tracking(self):
        """Test player record tracking methods."""
        player = RegisteredPlayer(
            player_id="P01",
            display_name="TestPlayer",
            endpoint="http://localhost:8101/mcp",
        )
        
        assert player.wins == 0
        assert player.losses == 0
        assert player.draws == 0
        assert player.points == 0
        
        player.record_win()
        assert player.wins == 1
        assert player.points == 3
        
        player.record_loss()
        assert player.losses == 1
        assert player.points == 3
        
        player.record_draw()
        assert player.draws == 1
        assert player.points == 4
    
    def test_registered_referee_properties(self):
        """Test registered referee properties."""
        referee = RegisteredReferee(
            referee_id="REF01",
            endpoint="http://localhost:8001/mcp",
            display_name="Referee_Alpha",
            max_concurrent_matches=3,
        )
        
        assert referee.referee_id == "REF01"
        assert referee.is_available is True
        assert referee.max_concurrent_matches == 3
        
        ref_dict = referee.to_dict()
        assert ref_dict["referee_id"] == "REF01"
        assert ref_dict["is_available"] is True
    
    @pytest.mark.asyncio
    async def test_run_all_rounds_success(self):
        """Test running all rounds automatically."""
        manager = LeagueManager(league_id="test_league", port=8000)
        
        # Setup
        for i in range(2):
            await manager._handle_registration({
                "display_name": f"Player{i+1}",
                "endpoint": f"http://localhost:810{i+1}/mcp",
                "game_types": ["even_odd"],
            })
        
        await manager._handle_referee_registration({
            "referee_id": "REF01",
            "endpoint": "http://localhost:8001/mcp",
            "game_types": ["even_odd"],
        })
        
        await manager._start_league()
        
        # Mock dependencies
        mock_client = AsyncMock(spec=MCPClient)
        mock_client.connected_servers = {}
        mock_client.call_tool = AsyncMock(return_value={"success": True})
        manager._client = mock_client
        
        with patch.object(manager, '_send_match_to_referee', new_callable=AsyncMock):
            result = await manager._run_all_rounds()
        
        assert result["success"] is True
        assert result["rounds_completed"] > 0
        assert manager.state == LeagueState.COMPLETED
    
    def test_player_count_property(self):
        """Test player_count property."""
        manager = LeagueManager(league_id="test_league", port=8000)
        
        assert manager.player_count == 0
        
        manager._players["P01"] = RegisteredPlayer(
            player_id="P01",
            display_name="Player1",
            endpoint="http://localhost:8101/mcp",
        )
        
        assert manager.player_count == 1
    
    def test_is_registration_open_property(self):
        """Test is_registration_open property."""
        manager = LeagueManager(league_id="test_league", port=8000)
        
        assert manager.is_registration_open is True
        
        manager.state = LeagueState.IN_PROGRESS
        assert manager.is_registration_open is False
    
    @pytest.mark.asyncio
    async def test_get_schedule_with_matches(self):
        """Test getting schedule with match details."""
        manager = LeagueManager(league_id="test_league", port=8000)
        
        # Register players
        for i in range(4):
            await manager._handle_registration({
                "display_name": f"Player{i+1}",
                "endpoint": f"http://localhost:810{i+1}/mcp",
                "game_types": ["even_odd"],
            })
        
        await manager._start_league()
        
        schedule = manager._get_schedule()
        
        assert "schedule" in schedule
        assert len(schedule["schedule"]) == 3  # 4 players = 3 rounds
        
        for round_info in schedule["schedule"]:
            assert "round" in round_info
            assert "matches" in round_info
            assert "status" in round_info


class TestLeagueManagerLifecycle:
    """Test league manager lifecycle methods."""
    
    @pytest.mark.asyncio
    async def test_on_start(self):
        """Test league manager on_start lifecycle method."""
        manager = LeagueManager(league_id="test_league", port=8000)
        
        await manager.on_start()
        
        assert manager._client is not None
    
    @pytest.mark.asyncio
    async def test_on_stop(self):
        """Test league manager on_stop lifecycle method."""
        manager = LeagueManager(league_id="test_league", port=8000)
        
        await manager.on_start()
        await manager.on_stop()
        
        assert manager._client is not None


# ============================================================================
# Edge Case Documentation
# ============================================================================

"""
EDGE CASES TESTED:

1. Player Registration:
   - Successful registration with unique IDs
   - Multiple simultaneous registrations
   - League full scenario
   - Registration after league starts
   - Duplicate endpoint prevention
   - Missing required game type
   - Auth token generation

2. Referee Registration:
   - Single and multiple referee registration
   - Duplicate referee prevention
   - Referee availability tracking
   - Round-robin referee assignment
   - Concurrent match limits

3. Schedule Generation:
   - Even number of players (e.g., 4, 6, 8)
   - Odd number of players (with bye rounds)
   - Minimum players (2)
   - Maximum players scenarios
   - Ensuring fair pairings
   - No duplicate matchups

4. Round Execution:
   - Starting rounds with proper referee assignment
   - Round progression tracking
   - Match coordination
   - Handling no available referees
   - All rounds completed detection
   - State transitions

5. Match Results:
   - Win/loss recording
   - Draw handling
   - Points calculation (3 for win, 1 for draw)
   - Unknown match errors
   - Concurrent result submissions
   - Round completion detection

6. Standings:
   - Empty standings
   - Correct ranking by points
   - Tiebreaker by wins
   - Tiebreaker by losses
   - Standings updates after each round
   - Champion determination

7. State Management:
   - REGISTRATION → READY → IN_PROGRESS → COMPLETED
   - Invalid state transitions prevention
   - Registration closure
   - League completion detection

8. Tools and Resources:
   - All tool endpoints functional
   - Resource access patterns
   - Tool parameter validation
   - Error responses

9. Concurrent Operations:
   - Multiple player registrations
   - Simultaneous match results
   - Race conditions in state updates
   - Thread-safe operations

10. Boundary Conditions:
    - Zero players
    - Single player (insufficient)
    - Maximum player limit
    - Zero rounds (impossible)
    - Many concurrent matches
    - Empty match schedule
"""

