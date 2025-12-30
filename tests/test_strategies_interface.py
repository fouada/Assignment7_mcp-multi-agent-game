"""
Simple additional tests to incrementally improve coverage.
"""

import pytest

from src.agents.strategies.base import StrategyConfig
from src.agents.strategies.classic import PatternStrategy, RandomStrategy
from src.agents.strategies.game_theory import (
    AdaptiveBayesianStrategy,
    BestResponseStrategy,
    FictitiousPlayStrategy,
    NashEquilibriumStrategy,
    RegretMatchingStrategy,
    ThompsonSamplingStrategy,
    UCBStrategy,
)
from src.game.odd_even import GameRole


class TestStrategyBasicOperations:
    """Test basic operations on all strategies."""

    def test_all_strategies_have_name(self):
        """Test all strategies have a name property."""
        strategies = [
            RandomStrategy(),
            PatternStrategy(),
            NashEquilibriumStrategy(),
            BestResponseStrategy(),
            AdaptiveBayesianStrategy(),
            FictitiousPlayStrategy(),
            RegretMatchingStrategy(),
            UCBStrategy(),
            ThompsonSamplingStrategy(),
        ]

        for strategy in strategies:
            stats = strategy.get_stats()
            assert "strategy" in stats or "name" in stats

    def test_all_strategies_can_reset(self):
        """Test all strategies can reset without error."""
        strategies = [
            RandomStrategy(),
            PatternStrategy(),
            NashEquilibriumStrategy(),
            BestResponseStrategy(),
            AdaptiveBayesianStrategy(),
            FictitiousPlayStrategy(),
            RegretMatchingStrategy(),
            UCBStrategy(),
            ThompsonSamplingStrategy(),
        ]

        for strategy in strategies:
            strategy.reset()  # Should not raise

    @pytest.mark.asyncio
    async def test_all_strategies_work_with_minimal_config(self):
        """Test all strategies work with minimal configuration."""
        config = StrategyConfig(min_value=1, max_value=50)
        strategies = [
            RandomStrategy(config),
            PatternStrategy(config),
            NashEquilibriumStrategy(config),
            BestResponseStrategy(config),
            AdaptiveBayesianStrategy(config),
            FictitiousPlayStrategy(config),
            RegretMatchingStrategy(config),
            UCBStrategy(config),
            ThompsonSamplingStrategy(config),
        ]

        for strategy in strategies:
            move = await strategy.decide_move(
                game_id="test",
                round_number=1,
                my_role=GameRole.ODD,
                my_score=0,
                opponent_score=0,
                history=[],
            )
            assert 1 <= move <= 50


class TestStrategyWithRoundProgression:
    """Test strategies over multiple rounds."""

    @pytest.mark.asyncio
    async def test_nash_over_100_rounds(self):
        """Test Nash strategy over 100 rounds."""
        strategy = NashEquilibriumStrategy()
        history = []

        for i in range(100):
            move = await strategy.decide_move(
                game_id="long_game",
                round_number=i + 1,
                my_role=GameRole.ODD if i % 2 == 0 else GameRole.EVEN,
                my_score=i // 2,
                opponent_score=(100 - i) // 2,
                history=history,
            )
            history.append(
                {"opponent_move": 25, "my_move": move, "result": "win" if i % 3 == 0 else "loss"}
            )

        assert len(history) == 100

    @pytest.mark.asyncio
    async def test_all_game_theory_strategies_long_game(self):
        """Test all game theory strategies over long game."""
        strategies = {
            "nash": NashEquilibriumStrategy(),
            "best_response": BestResponseStrategy(),
            "adaptive": AdaptiveBayesianStrategy(),
            "fictitious": FictitiousPlayStrategy(),
            "regret": RegretMatchingStrategy(),
            "ucb": UCBStrategy(),
            "thompson": ThompsonSamplingStrategy(),
        }

        for name, strategy in strategies.items():
            history = []
            for i in range(50):
                move = await strategy.decide_move(
                    game_id=f"game_{name}",
                    round_number=i + 1,
                    my_role=GameRole.ODD,
                    my_score=i // 5,
                    opponent_score=(50 - i) // 5,
                    history=history,
                )
                opponent_move = 20 + (i % 15)
                result = "win" if (move + opponent_move) % 2 == 1 else "loss"
                history.append({"opponent_move": opponent_move, "my_move": move, "result": result})

            assert len(history) == 50


class TestStrategyEdgeCaseRoundNumbers:
    """Test strategies with edge case round numbers."""

    @pytest.mark.asyncio
    async def test_strategies_at_round_1(self):
        """Test all strategies at round 1."""
        strategies = [
            NashEquilibriumStrategy(),
            BestResponseStrategy(),
            AdaptiveBayesianStrategy(),
            FictitiousPlayStrategy(),
            RegretMatchingStrategy(),
            UCBStrategy(),
            ThompsonSamplingStrategy(),
        ]

        for strategy in strategies:
            move = await strategy.decide_move("test", 1, GameRole.ODD, 0, 0, [])
            assert 1 <= move <= 50

    @pytest.mark.asyncio
    async def test_strategies_at_round_1000(self):
        """Test all strategies at very high round number."""
        strategies = [
            NashEquilibriumStrategy(),
            BestResponseStrategy(),
            AdaptiveBayesianStrategy(),
            FictitiousPlayStrategy(),
            RegretMatchingStrategy(),
            UCBStrategy(),
            ThompsonSamplingStrategy(),
        ]

        # Build a long history
        history = [
            {
                "opponent_move": (i % 30) + 10,
                "my_move": (i % 20) + 15,
                "result": ["win", "loss", "draw"][i % 3],
            }
            for i in range(100)  # Sample history, not full 1000 rounds
        ]

        for strategy in strategies:
            move = await strategy.decide_move("test", 1000, GameRole.ODD, 500, 500, history)
            assert 1 <= move <= 50
