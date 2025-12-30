"""
Tests for RandomStrategy functionality.
Covers random move generation, bounds checking, and statistics.
"""

import pytest

from src.agents.strategies.classic import RandomStrategy
from src.agents.strategies.base import StrategyConfig
from src.game.odd_even import GameRole


class TestRandomStrategyBehavior:
    """Test RandomStrategy behavior and edge cases."""

    @pytest.mark.asyncio
    async def test_random_strategy_respects_default_bounds(self):
        """Test that random strategy respects default min/max bounds."""
        strategy = RandomStrategy()

        moves = []
        for _ in range(50):
            move = await strategy.decide_move(
                game_id="test",
                round_number=1,
                my_role=GameRole.ODD,
                my_score=0,
                opponent_score=0,
                history=[]
            )
            moves.append(move)

        # All moves should be in default range [1, 10]
        assert all(1 <= move <= 10 for move in moves)

    @pytest.mark.asyncio
    async def test_random_strategy_with_custom_config(self):
        """Test random strategy with custom configuration."""
        config = StrategyConfig(min_value=5, max_value=15)
        strategy = RandomStrategy(config=config)

        moves = []
        for _ in range(30):
            move = await strategy.decide_move(
                game_id="test",
                round_number=1,
                my_role=GameRole.EVEN,
                my_score=0,
                opponent_score=0,
                history=[]
            )
            moves.append(move)

        # All moves should be in custom range [5, 15]
        assert all(5 <= move <= 15 for move in moves)

    @pytest.mark.asyncio
    async def test_random_strategy_with_narrow_range(self):
        """Test random strategy with very narrow range."""
        config = StrategyConfig(min_value=7, max_value=9)
        strategy = RandomStrategy(config=config)

        moves = []
        for _ in range(20):
            move = await strategy.decide_move(
                game_id="test",
                round_number=1,
                my_role=GameRole.ODD,
                my_score=0,
                opponent_score=0,
                history=[]
            )
            moves.append(move)

        # All moves should be in narrow range [7, 9]
        assert all(7 <= move <= 9 for move in moves)
        # Should have variety despite narrow range
        assert len(set(moves)) >= 2

    @pytest.mark.asyncio
    async def test_random_strategy_with_game_history(self):
        """Test that random strategy ignores game history."""
        strategy = RandomStrategy()

        history = [
            {"player_a_move": 5, "player_b_move": 3},
            {"player_a_move": 7, "player_b_move": 9},
        ]

        move = await strategy.decide_move(
            game_id="test",
            round_number=3,
            my_role=GameRole.ODD,
            my_score=1,
            opponent_score=1,
            history=history
        )

        # Should still generate valid move regardless of history
        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_random_strategy_multiple_games(self):
        """Test random strategy across multiple games."""
        strategy = RandomStrategy()

        # Game 1
        move1 = await strategy.decide_move("game1", 1, GameRole.ODD, 0, 0, [])
        assert 1 <= move1 <= 10

        # Game 2
        move2 = await strategy.decide_move("game2", 1, GameRole.EVEN, 0, 0, [])
        assert 1 <= move2 <= 10

        # Game 1 again
        move3 = await strategy.decide_move("game1", 2, GameRole.ODD, 0, 0, [])
        assert 1 <= move3 <= 10

    def test_random_strategy_reset(self):
        """Test that reset works without errors."""
        strategy = RandomStrategy()
        
        # Reset should work without issues
        strategy.reset()

    def test_random_strategy_get_stats(self):
        """Test get_stats returns proper information."""
        strategy = RandomStrategy()
        
        stats = strategy.get_stats()
        
        assert isinstance(stats, dict)
        assert "name" in stats or "strategy" in stats
        assert "min_value" in stats
        assert "max_value" in stats


class TestRandomStrategyStatistics:
    """Test RandomStrategy statistics and distribution."""

    @pytest.mark.asyncio
    async def test_random_strategy_produces_variety(self):
        """Test that random strategy produces variety in moves."""
        strategy = RandomStrategy()

        moves = []
        for _ in range(100):
            move = await strategy.decide_move(
                game_id="test",
                round_number=1,
                my_role=GameRole.ODD,
                my_score=0,
                opponent_score=0,
                history=[]
            )
            moves.append(move)

        # Should have reasonable variety (at least 5 different values in 100 moves)
        unique_moves = set(moves)
        assert len(unique_moves) >= 5

    @pytest.mark.asyncio
    async def test_random_strategy_both_odd_and_even(self):
        """Test that random strategy produces both odd and even moves."""
        strategy = RandomStrategy()

        moves = []
        for _ in range(100):
            move = await strategy.decide_move(
                game_id="test",
                round_number=1,
                my_role=GameRole.ODD,
                my_score=0,
                opponent_score=0,
                history=[]
            )
            moves.append(move)

        # Should have both odd and even numbers
        has_odd = any(move % 2 == 1 for move in moves)
        has_even = any(move % 2 == 0 for move in moves)
        
        assert has_odd
        assert has_even

