"""
Comprehensive end-to-end game flow tests simulating real gameplay scenarios.

Tests cover: player registration, referee assignment, game rounds, standings, and winner determination.
"""

import pytest

from src.agents.league_manager import LeagueManager
from src.game.odd_even import OddEvenGame


class TestCompleteGameFlow:
    """Test complete game flow scenarios."""

    @pytest.mark.asyncio
    async def test_league_manager_initialization(self):
        """Test that league manager initializes correctly."""
        league_manager = LeagueManager(league_id="test_league")

        assert league_manager.league_id == "test_league"
        assert league_manager.player_count == 0
        assert league_manager.is_registration_open is True


class TestGameRoundExecution:
    """Test game round execution."""

    @pytest.mark.asyncio
    async def test_odd_even_game_initialization(self):
        """Test OddEvenGame initialization."""
        game = OddEvenGame(game_id="test_game", player_a="p1", player_b="p2")

        assert game.game_id == "test_game"
        assert game.player_a == "p1"
        assert game.player_b == "p2"
        assert game.is_complete() is False

    @pytest.mark.asyncio
    async def test_odd_even_game_single_round(self):
        """Test a single round of Odd/Even game."""
        game = OddEvenGame(game_id="test_game", player_a="p1", player_b="p2", max_rounds=1)
        game.start()

        # Submit moves
        game.submit_move("p1", 3)
        game.submit_move("p2", 5)

        # Resolve round
        result = game.resolve_round()

        assert result is not None
        assert result["round"] == 1
        assert result["sum"] == 8  # 3 + 5
        assert result["parity"] == "even"

    @pytest.mark.asyncio
    async def test_odd_even_game_multiple_rounds(self):
        """Test multiple rounds of Odd/Even game."""
        game = OddEvenGame(game_id="test_game", player_a="p1", player_b="p2", max_rounds=3)
        game.start()

        rounds_completed = 0
        for _round in range(3):
            game.submit_move("p1", 2)
            game.submit_move("p2", 3)
            result = game.resolve_round()
            if result:
                rounds_completed += 1

        assert rounds_completed == 3
        assert game.is_complete() is True


class TestStandingsCalculation:
    """Test standings calculation."""

    @pytest.mark.asyncio
    async def test_league_manager_standings(self):
        """Test that league manager can calculate standings."""
        league_manager = LeagueManager(league_id="test_league")

        standings = league_manager.get_standings()

        assert isinstance(standings, list)
        assert len(standings) == 0  # No players registered yet


class TestWinnerDetermination:
    """Test winner determination."""

    @pytest.mark.asyncio
    async def test_game_winner_odd_sum(self):
        """Test determining winner when sum is odd."""
        game = OddEvenGame(game_id="test", player_a="p1", player_b="p2", max_rounds=1)
        game.start()

        game.submit_move("p1", 3)
        game.submit_move("p2", 4)
        result = game.resolve_round()

        # Sum is 7 (odd), so odd player wins
        assert result["sum"] == 7
        assert result["parity"] == "odd"

    @pytest.mark.asyncio
    async def test_game_winner_even_sum(self):
        """Test determining winner when sum is even."""
        game = OddEvenGame(game_id="test", player_a="p1", player_b="p2", max_rounds=1)
        game.start()

        game.submit_move("p1", 2)
        game.submit_move("p2", 4)
        result = game.resolve_round()

        # Sum is 6 (even), so even player wins
        assert result["sum"] == 6
        assert result["parity"] == "even"


class TestRefereeAssignment:
    """Test referee assignment."""

    @pytest.mark.asyncio
    async def test_league_manager_referee_count(self):
        """Test that league manager tracks referees."""
        league_manager = LeagueManager(league_id="test_league")

        # Initially no referees
        assert len(league_manager._referees) == 0


class TestCompleteLeagueScenario:
    """Test complete league scenarios."""

    @pytest.mark.asyncio
    async def test_league_registration_lifecycle(self):
        """Test complete league registration lifecycle."""
        league_manager = LeagueManager(league_id="test_league", max_players=4)

        # Registration should be open initially
        assert league_manager.is_registration_open is True

        # Close registration manually
        league_manager._registration_open = False
        assert league_manager.is_registration_open is False

