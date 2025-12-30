"""
Comprehensive end-to-end game flow tests.
Simulates complete game scenarios: player registration, referee assignment,
game rounds, standings calculation, and winner determination.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.league_manager import LeagueManager
from src.agents.player import PlayerAgent
from src.agents.referee import RefereeAgent
from src.agents.strategies.classic import RandomStrategy
from src.game.odd_even import OddEvenGame, GameRole
from src.common.config_loader import ConfigLoader


class TestCompleteGameFlow:
    """Test complete game flow from start to finish."""

    @pytest.mark.asyncio
    async def test_full_league_cycle_two_players(self):
        """Test complete league cycle with two players."""
        # Initialize league manager
        league_manager = LeagueManager(league_id="test_league")
        
        # Register two players
        player1_info = await league_manager.register_player(
            player_id="player1",
            name="Alice",
            endpoint="http://localhost:8001",
            supported_games=["even_odd"]
        )
        assert player1_info is not None
        assert player1_info["player_id"] == "player1"
        
        player2_info = await league_manager.register_player(
            player_id="player2",
            name="Bob",
            endpoint="http://localhost:8002",
            supported_games=["even_odd"]
        )
        assert player2_info is not None
        assert player2_info["player_id"] == "player2"
        
        # Verify player count
        assert league_manager.player_count == 2
        
        # Register a referee
        referee_info = await league_manager.register_referee(
            referee_id="ref1",
            endpoint="http://localhost:9001",
            supported_games=["even_odd"]
        )
        assert referee_info is not None
        
        # Start the league (generates schedule)
        result = await league_manager.start_league()
        assert result["status"] == "started"
        assert len(result["schedule"]) > 0
        
        # Get standings (should be initialized)
        standings = league_manager.get_standings()
        assert len(standings) == 2
        assert any(p["player_id"] == "player1" for p in standings)
        assert any(p["player_id"] == "player2" for p in standings)

    @pytest.mark.asyncio
    async def test_player_registration_validation(self):
        """Test player registration with validation."""
        league_manager = LeagueManager(league_id="test_league")
        
        # Valid registration
        result = await league_manager.register_player(
            player_id="player1",
            name="Alice",
            endpoint="http://localhost:8001",
            supported_games=["even_odd"]
        )
        assert result["player_id"] == "player1"
        
        # Duplicate registration should be handled
        result2 = await league_manager.register_player(
            player_id="player1",
            name="Alice Again",
            endpoint="http://localhost:8001",
            supported_games=["even_odd"]
        )
        # Should either reject or update existing

    @pytest.mark.asyncio
    async def test_multiple_players_registration(self):
        """Test registering multiple players."""
        league_manager = LeagueManager(league_id="multi_player_league")
        
        players = []
        for i in range(4):
            player_info = await league_manager.register_player(
                player_id=f"player{i+1}",
                name=f"Player {i+1}",
                endpoint=f"http://localhost:800{i+1}",
                supported_games=["even_odd"]
            )
            players.append(player_info)
        
        assert league_manager.player_count == 4
        
        # Start league with 4 players
        result = await league_manager.start_league()
        assert result["status"] == "started"
        
        # Verify schedule has matches for all players
        schedule = result["schedule"]
        assert len(schedule) > 0


class TestGameRoundExecution:
    """Test game round execution and results."""

    def test_odd_even_game_single_round(self):
        """Test a single round of odd-even game."""
        game = OddEvenGame(
            game_id="test_game",
            player_a_id="player1",
            player_b_id="player2",
            rounds=1
        )
        
        # Start game
        game.start()
        assert game.is_active
        
        # Submit moves
        game.submit_move("player1", 5)  # Odd
        game.submit_move("player2", 4)  # Even
        
        # Resolve round
        result = game.resolve_round()
        assert result is not None
        assert "winner" in result
        assert result["sum"] == 9  # Odd sum
        
        # Game should be complete after 1 round
        assert game.is_complete

    def test_odd_even_game_multiple_rounds(self):
        """Test multiple rounds of odd-even game."""
        game = OddEvenGame(
            game_id="test_game",
            player_a_id="player1",
            player_b_id="player2",
            rounds=3
        )
        
        game.start()
        
        # Round 1
        game.submit_move("player1", 5)
        game.submit_move("player2", 4)
        result1 = game.resolve_round()
        assert result1["round"] == 1
        
        # Round 2
        game.submit_move("player1", 2)
        game.submit_move("player2", 3)
        result2 = game.resolve_round()
        assert result2["round"] == 2
        
        # Round 3
        game.submit_move("player1", 7)
        game.submit_move("player2", 8)
        result3 = game.resolve_round()
        assert result3["round"] == 3
        
        # Game should be complete
        assert game.is_complete
        
        # Get final result
        final_result = game.get_result()
        assert final_result is not None
        assert "winner" in final_result

    def test_game_role_assignment(self):
        """Test that players are assigned ODD/EVEN roles."""
        game = OddEvenGame(
            game_id="test_game",
            player_a_id="player1",
            player_b_id="player2",
            rounds=1
        )
        
        game.start()
        
        # Check role assignment
        role_a = game.get_player_role("player1")
        role_b = game.get_player_role("player2")
        
        assert role_a in [GameRole.ODD, GameRole.EVEN]
        assert role_b in [GameRole.ODD, GameRole.EVEN]
        assert role_a != role_b  # Different roles


class TestStandingsCalculation:
    """Test standings calculation and ranking."""

    @pytest.mark.asyncio
    async def test_standings_after_matches(self):
        """Test standings calculation after multiple matches."""
        league_manager = LeagueManager(league_id="standings_test")
        
        # Register players
        await league_manager.register_player(
            "player1", "Alice", "http://localhost:8001", ["even_odd"]
        )
        await league_manager.register_player(
            "player2", "Bob", "http://localhost:8002", ["even_odd"]
        )
        await league_manager.register_player(
            "player3", "Charlie", "http://localhost:8003", ["even_odd"]
        )
        
        # Start league
        await league_manager.start_league()
        
        # Simulate match results
        await league_manager.handle_match_result(
            match_id="match1",
            winner_id="player1",
            loser_id="player2",
            score={"player1": 3, "player2": 2}
        )
        
        await league_manager.handle_match_result(
            match_id="match2",
            winner_id="player1",
            loser_id="player3",
            score={"player1": 3, "player3": 1}
        )
        
        # Get standings
        standings = league_manager.get_standings()
        
        # Player1 should be first (2 wins)
        assert standings[0]["player_id"] == "player1"
        assert standings[0]["wins"] >= 2

    @pytest.mark.asyncio
    async def test_standings_ranking_order(self):
        """Test that standings are properly ranked."""
        league_manager = LeagueManager(league_id="ranking_test")
        
        # Register players
        for i in range(4):
            await league_manager.register_player(
                f"player{i+1}",
                f"Player {i+1}",
                f"http://localhost:800{i+1}",
                ["even_odd"]
            )
        
        await league_manager.start_league()
        
        # Simulate different win records
        # Player1: 3 wins
        await league_manager.handle_match_result(
            "m1", "player1", "player2", {"player1": 3, "player2": 0}
        )
        await league_manager.handle_match_result(
            "m2", "player1", "player3", {"player1": 3, "player3": 0}
        )
        await league_manager.handle_match_result(
            "m3", "player1", "player4", {"player1": 3, "player4": 0}
        )
        
        # Player2: 1 win
        await league_manager.handle_match_result(
            "m4", "player2", "player3", {"player2": 3, "player3": 0}
        )
        
        standings = league_manager.get_standings()
        
        # Verify ranking order (by wins/points)
        assert standings[0]["player_id"] == "player1"  # Most wins
        assert standings[0]["wins"] > standings[1]["wins"]


class TestWinnerDetermination:
    """Test winner determination logic."""

    @pytest.mark.asyncio
    async def test_determine_league_winner(self):
        """Test determining the overall league winner."""
        league_manager = LeagueManager(league_id="winner_test")
        
        # Register players
        await league_manager.register_player(
            "player1", "Winner", "http://localhost:8001", ["even_odd"]
        )
        await league_manager.register_player(
            "player2", "Runner-up", "http://localhost:8002", ["even_odd"]
        )
        
        await league_manager.start_league()
        
        # Player1 wins
        await league_manager.handle_match_result(
            "final", "player1", "player2", {"player1": 3, "player2": 1}
        )
        
        standings = league_manager.get_standings()
        winner = standings[0]
        
        assert winner["player_id"] == "player1"
        assert winner["wins"] > 0

    def test_game_winner_odd_sum(self):
        """Test winner determination for odd sum."""
        game = OddEvenGame("test", "p1", "p2", rounds=1)
        game.start()
        
        # Assuming p1 is ODD player
        game.submit_move("p1", 5)  # Odd
        game.submit_move("p2", 4)  # Even
        
        result = game.resolve_round()
        
        # Sum is 9 (odd), so ODD player wins
        assert result["sum"] == 9
        assert result["winner"] is not None

    def test_game_winner_even_sum(self):
        """Test winner determination for even sum."""
        game = OddEvenGame("test", "p1", "p2", rounds=1)
        game.start()
        
        game.submit_move("p1", 4)  # Even
        game.submit_move("p2", 6)  # Even
        
        result = game.resolve_round()
        
        # Sum is 10 (even), so EVEN player wins
        assert result["sum"] == 10
        assert result["winner"] is not None


class TestRefereeAssignment:
    """Test referee assignment and management."""

    @pytest.mark.asyncio
    async def test_referee_registration(self):
        """Test referee registration."""
        league_manager = LeagueManager(league_id="ref_test")
        
        referee_info = await league_manager.register_referee(
            referee_id="ref1",
            endpoint="http://localhost:9001",
            supported_games=["even_odd"]
        )
        
        assert referee_info is not None
        assert referee_info["referee_id"] == "ref1"

    @pytest.mark.asyncio
    async def test_multiple_referee_registration(self):
        """Test registering multiple referees."""
        league_manager = LeagueManager(league_id="multi_ref_test")
        
        for i in range(3):
            ref_info = await league_manager.register_referee(
                referee_id=f"ref{i+1}",
                endpoint=f"http://localhost:900{i+1}",
                supported_games=["even_odd"]
            )
            assert ref_info["referee_id"] == f"ref{i+1}"


class TestCompleteLeagueScenario:
    """Test complete league scenario from start to finish."""

    @pytest.mark.asyncio
    async def test_complete_mini_tournament(self):
        """Test a complete mini tournament scenario."""
        # Setup
        league_manager = LeagueManager(league_id="mini_tournament")
        
        # Phase 1: Registration
        players = []
        for i in range(3):
            player = await league_manager.register_player(
                player_id=f"player{i+1}",
                name=f"Player {i+1}",
                endpoint=f"http://localhost:800{i+1}",
                supported_games=["even_odd"]
            )
            players.append(player)
        
        referee = await league_manager.register_referee(
            referee_id="ref1",
            endpoint="http://localhost:9001",
            supported_games=["even_odd"]
        )
        
        # Phase 2: Start League
        league_start = await league_manager.start_league()
        assert league_start["status"] == "started"
        
        # Phase 3: Simulate matches
        matches = [
            ("match1", "player1", "player2", {"player1": 3, "player2": 2}),
            ("match2", "player1", "player3", {"player1": 3, "player3": 1}),
            ("match3", "player2", "player3", {"player2": 3, "player3": 0}),
        ]
        
        for match_id, winner, loser, score in matches:
            await league_manager.handle_match_result(match_id, winner, loser, score)
        
        # Phase 4: Get Final Standings
        final_standings = league_manager.get_standings()
        
        assert len(final_standings) == 3
        assert final_standings[0]["player_id"] == "player1"  # Winner
        
        # Phase 5: Verify winner has most wins
        winner = final_standings[0]
        assert winner["wins"] >= 2

    @pytest.mark.asyncio
    async def test_league_with_round_robin(self):
        """Test league with round-robin format."""
        league_manager = LeagueManager(league_id="round_robin_test")
        
        # Register 4 players
        for i in range(4):
            await league_manager.register_player(
                f"player{i+1}",
                f"Player {i+1}",
                f"http://localhost:800{i+1}",
                ["even_odd"]
            )
        
        # Start league
        result = await league_manager.start_league()
        
        # In round-robin with 4 players, each plays 3 matches
        # Total matches = 4 * 3 / 2 = 6 matches
        schedule = result.get("schedule", [])
        
        # Verify schedule structure
        assert len(schedule) > 0

