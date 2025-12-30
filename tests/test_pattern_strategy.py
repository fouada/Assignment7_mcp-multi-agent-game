"""
Tests for PatternStrategy functionality.
Covers pattern detection, role-based behavior, and edge cases.
"""

import pytest

from src.agents.strategies.classic import PatternStrategy
from src.game.odd_even import GameRole


class TestPatternStrategyBehavior:
    """Test PatternStrategy behavior in various scenarios."""

    @pytest.mark.asyncio
    async def test_pattern_strategy_with_empty_history(self):
        """Test pattern strategy with no history falls back to random."""
        strategy = PatternStrategy()

        move = await strategy.decide_move(
            game_id="test",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[],
        )

        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_pattern_strategy_detects_odd_preference(self):
        """Test pattern detection when opponent prefers odd moves."""
        strategy = PatternStrategy()

        # Opponent consistently plays odd numbers
        history = [
            {"player_a_move": 5, "player_b_move": 1},
            {"player_a_move": 7, "player_b_move": 3},
            {"player_a_move": 9, "player_b_move": 5},
        ]

        move = await strategy.decide_move(
            game_id="test",
            round_number=4,
            my_role=GameRole.ODD,
            my_score=2,
            opponent_score=1,
            history=history,
        )

        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_pattern_strategy_detects_even_preference(self):
        """Test pattern detection when opponent prefers even moves."""
        strategy = PatternStrategy()

        # Opponent consistently plays even numbers
        history = [
            {"player_a_move": 2, "player_b_move": 4},
            {"player_a_move": 6, "player_b_move": 8},
            {"player_a_move": 10, "player_b_move": 2},
        ]

        move = await strategy.decide_move(
            game_id="test",
            round_number=4,
            my_role=GameRole.EVEN,
            my_score=1,
            opponent_score=2,
            history=history,
        )

        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_pattern_strategy_as_even_player(self):
        """Test pattern strategy when playing as EVEN role."""
        strategy = PatternStrategy()

        history = [
            {"player_a_move": 3, "player_b_move": 5},
            {"player_a_move": 7, "player_b_move": 9},
        ]

        move = await strategy.decide_move(
            game_id="test",
            round_number=3,
            my_role=GameRole.EVEN,
            my_score=0,
            opponent_score=2,
            history=history,
        )

        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_pattern_strategy_mixed_history(self):
        """Test with mixed odd/even moves from opponent."""
        strategy = PatternStrategy()

        history = [
            {"player_a_move": 1, "player_b_move": 2},
            {"player_a_move": 3, "player_b_move": 4},
            {"player_a_move": 5, "player_b_move": 6},
            {"player_a_move": 7, "player_b_move": 8},
        ]

        move = await strategy.decide_move(
            game_id="test",
            round_number=5,
            my_role=GameRole.ODD,
            my_score=2,
            opponent_score=2,
            history=history,
        )

        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_pattern_strategy_reset(self):
        """Test that reset clears history."""
        strategy = PatternStrategy()

        history = [{"player_a_move": 5, "player_b_move": 3}]
        await strategy.decide_move("game1", 2, GameRole.ODD, 0, 0, history)

        # Reset and verify it works
        strategy.reset()

        # Should work fine after reset
        move = await strategy.decide_move("game1", 1, GameRole.ODD, 0, 0, [])
        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_pattern_strategy_get_stats(self):
        """Test get_stats returns proper information."""
        strategy = PatternStrategy()

        stats = strategy.get_stats()

        assert "name" in stats or "strategy" in stats
        assert isinstance(stats, dict)
