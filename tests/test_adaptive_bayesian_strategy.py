"""
Final targeted tests to reach 85% coverage.
Focuses on specific uncovered paths in high-value files.
"""

import pytest

from src.agents.strategies.base import GameRole, StrategyConfig
from src.agents.strategies.game_theory import AdaptiveBayesianStrategy


class TestAdaptiveBayesianStrategyEdgeCases:
    """Test AdaptiveBayesianStrategy edge cases to cover missing lines."""

    @pytest.mark.asyncio
    async def test_adaptive_bayesian_deterministic_mode(self):
        """Test deterministic mode (line 148)."""
        strategy = AdaptiveBayesianStrategy()
        strategy.deterministic = True

        # Play a few rounds to establish history
        history = [
            {"player_a_move": 5, "player_b_move": 3},  # Odd sum
            {"player_a_move": 7, "player_b_move": 5},  # Even sum
        ]

        move = await strategy.decide_move(
            "game1",
            round_number=3,
            my_role=GameRole.ODD,
            my_score=1,
            opponent_score=1,
            history=history,
        )
        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_adaptive_bayesian_confidence_high_std(self):
        """Test confidence calculation with very low std (line 240)."""
        strategy = AdaptiveBayesianStrategy()

        # Create a belief with very low std by having many observations
        belief = strategy._get_belief("game1")
        belief.alpha = 100.0
        belief.beta = 10.0  # Very biased with lots of data -> low std

        confidence = belief.confidence_in_bias()
        assert isinstance(confidence, float)
        assert 0 <= confidence <= 1

    @pytest.mark.asyncio
    async def test_adaptive_bayesian_belief_reset(self):
        """Test belief reset (lines 247-248)."""
        strategy = AdaptiveBayesianStrategy()

        # Get a belief and modify it
        belief = strategy._get_belief("game1")
        belief.alpha = 10.0
        belief.beta = 5.0

        # Reset it
        belief.reset()
        assert belief.alpha == 1.0
        assert belief.beta == 1.0

    @pytest.mark.asyncio
    async def test_adaptive_bayesian_multiple_games(self):
        """Test strategy across multiple games."""
        strategy = AdaptiveBayesianStrategy()

        # Game 1
        history1 = [{"player_a_move": 5, "player_b_move": 3}]
        move1 = await strategy.decide_move(
            "game1", 2, GameRole.ODD, 0, 0, history1
        )
        assert 1 <= move1 <= 10

        # Game 2 (different game_id)
        history2 = [{"player_a_move": 2, "player_b_move": 4}]
        move2 = await strategy.decide_move(
            "game2", 2, GameRole.EVEN, 0, 0, history2
        )
        assert 1 <= move2 <= 10

        # Verify separate beliefs
        assert "game1" in strategy._beliefs
        assert "game2" in strategy._beliefs

