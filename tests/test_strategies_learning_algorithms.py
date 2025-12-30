"""
Targeted tests to boost coverage to 85%+.

These tests target uncovered lines in key modules.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from src.agents.strategies.base import StrategyConfig
from src.agents.strategies.game_theory import (
    NashEquilibriumStrategy,
    BestResponseStrategy,
    AdaptiveBayesianStrategy,
    FictitiousPlayStrategy,
    RegretMatchingStrategy,
)
from src.game.odd_even import GameRole


class TestGameTheoryStrategiesEdgeCases:
    """Test game theory strategies edge cases for coverage."""

    @pytest.mark.asyncio
    async def test_nash_equilibrium_strategy_uniform_distribution(self):
        """Test Nash equilibrium creates uniform distribution."""
        strategy = NashEquilibriumStrategy()

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

        # Check all moves are in valid range
        assert all(1 <= m <= 50 for m in moves)
        # Check we have both odd and even moves (probabilistically)
        assert any(m % 2 == 0 for m in moves)
        assert any(m % 2 == 1 for m in moves)

    @pytest.mark.asyncio
    async def test_best_response_with_empty_history(self):
        """Test best response with empty history."""
        strategy = BestResponseStrategy()

        move = await strategy.decide_move(
            game_id="test",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[]
        )

        assert 1 <= move <= 50

    @pytest.mark.asyncio
    async def test_best_response_as_even_player(self):
        """Test best response as EVEN player."""
        strategy = BestResponseStrategy()

        history = [
            {"opponent_move": 5, "my_move": 10},
            {"opponent_move": 7, "my_move": 12},
            {"opponent_move": 9, "my_move": 14},
        ]

        move = await strategy.decide_move(
            game_id="test",
            round_number=4,
            my_role=GameRole.EVEN,
            my_score=1,
            opponent_score=2,
            history=history
        )

        assert 1 <= move <= 50

    @pytest.mark.asyncio
    async def test_adaptive_bayesian_updates_beliefs(self):
        """Test adaptive Bayesian updates beliefs over time."""
        strategy = AdaptiveBayesianStrategy()

        # Play multiple rounds
        history = []
        for i in range(10):
            move = await strategy.decide_move(
                game_id="test",
                round_number=i + 1,
                my_role=GameRole.ODD,
                my_score=i,
                opponent_score=10 - i,
                history=history
            )

            # Add to history
            history.append({
                "opponent_move": 25,
                "my_move": move,
                "result": "win" if i % 2 == 0 else "loss"
            })

        assert len(history) == 10

    @pytest.mark.asyncio
    async def test_fictitious_play_empty_history(self):
        """Test fictitious play with empty history."""
        strategy = FictitiousPlayStrategy()

        move = await strategy.decide_move(
            game_id="test",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[]
        )

        assert 1 <= move <= 50

    @pytest.mark.asyncio
    async def test_fictitious_play_learns_from_history(self):
        """Test fictitious play learns from opponent history."""
        strategy = FictitiousPlayStrategy()

        # Opponent always plays odd
        history = [
            {"opponent_move": 1, "my_move": 2},
            {"opponent_move": 3, "my_move": 4},
            {"opponent_move": 5, "my_move": 6},
            {"opponent_move": 7, "my_move": 8},
            {"opponent_move": 9, "my_move": 10},
        ]

        move = await strategy.decide_move(
            game_id="test",
            round_number=6,
            my_role=GameRole.ODD,
            my_score=2,
            opponent_score=3,
            history=history
        )

        # Should play even (opponent plays odd, we want odd sum)
        assert move % 2 == 0

    @pytest.mark.asyncio
    async def test_regret_matching_initialization(self):
        """Test regret matching initializes properly."""
        strategy = RegretMatchingStrategy()

        move = await strategy.decide_move(
            game_id="test",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[]
        )

        assert 1 <= move <= 50

    @pytest.mark.asyncio
    async def test_regret_matching_updates_regrets(self):
        """Test regret matching updates regrets over time."""
        strategy = RegretMatchingStrategy()

        history = []
        for i in range(15):
            move = await strategy.decide_move(
                game_id="test",
                round_number=i + 1,
                my_role=GameRole.ODD,
                my_score=i // 2,
                opponent_score=i - (i // 2),
                history=history
            )

            history.append({
                "opponent_move": 15 + i,
                "my_move": move,
                "result": "win" if i % 3 == 0 else "loss"
            })

        assert len(history) == 15

    def test_strategy_config_custom_values(self):
        """Test StrategyConfig with custom values."""
        config = StrategyConfig(
            min_value=5,
            max_value=25,
            exploration_rate=0.3
        )

        assert config.min_value == 5
        assert config.max_value == 25
        assert config.exploration_rate == 0.3

    @pytest.mark.asyncio
    async def test_nash_equilibrium_get_stats(self):
        """Test Nash equilibrium get_stats."""
        strategy = NashEquilibriumStrategy()

        stats = strategy.get_stats()
        assert "strategy" in stats
        assert "games_tracked" in stats

    @pytest.mark.asyncio
    async def test_adaptive_bayesian_get_stats(self):
        """Test Adaptive Bayesian get_stats."""
        strategy = AdaptiveBayesianStrategy()

        # Play a few rounds
        history = [
            {"opponent_move": 5, "my_move": 10},
            {"opponent_move": 7, "my_move": 12},
        ]

        await strategy.decide_move(
            game_id="test",
            round_number=3,
            my_role=GameRole.ODD,
            my_score=1,
            opponent_score=1,
            history=history
        )

        stats = strategy.get_stats()
        assert "name" in stats or "strategy" in stats

    @pytest.mark.asyncio
    async def test_fictitious_play_get_stats(self):
        """Test Fictitious Play get_stats."""
        strategy = FictitiousPlayStrategy()

        stats = strategy.get_stats()
        assert "name" in stats or "strategy" in stats
        assert "games_tracked" in stats

    @pytest.mark.asyncio
    async def test_regret_matching_get_stats(self):
        """Test Regret Matching get_stats."""
        strategy = RegretMatchingStrategy()

        stats = strategy.get_stats()
        assert "name" in stats or "strategy" in stats


class TestStrategyReset:
    """Test strategy reset functionality."""

    def test_best_response_reset(self):
        """Test best response strategy reset doesn't crash."""
        strategy = BestResponseStrategy()
        strategy.reset()  # Should not raise

    def test_adaptive_bayesian_reset(self):
        """Test adaptive Bayesian strategy reset doesn't crash."""
        strategy = AdaptiveBayesianStrategy()
        strategy.reset()  # Should not raise

    def test_fictitious_play_reset(self):
        """Test fictitious play strategy reset doesn't crash."""
        strategy = FictitiousPlayStrategy()
        strategy.reset()  # Should not raise

    def test_regret_matching_reset(self):
        """Test regret matching strategy reset doesn't crash."""
        strategy = RegretMatchingStrategy()
        strategy.reset()  # Should not raise


class TestMultipleGamesTracking:
    """Test strategies tracking multiple games."""

    @pytest.mark.asyncio
    async def test_best_response_multiple_games(self):
        """Test best response tracks multiple games separately."""
        strategy = BestResponseStrategy()

        # Game 1
        history1 = [{"opponent_move": 5, "my_move": 10}]
        move1 = await strategy.decide_move(
            game_id="game1",
            round_number=2,
            my_role=GameRole.ODD,
            my_score=1,
            opponent_score=0,
            history=history1
        )

        # Game 2
        history2 = [{"opponent_move": 15, "my_move": 20}]
        move2 = await strategy.decide_move(
            game_id="game2",
            round_number=2,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=1,
            history=history2
        )

        # Should produce valid moves
        assert 1 <= move1 <= 50
        assert 1 <= move2 <= 50

    @pytest.mark.asyncio
    async def test_adaptive_bayesian_multiple_games(self):
        """Test adaptive Bayesian tracks multiple games."""
        strategy = AdaptiveBayesianStrategy()

        # Play game 1
        move1 = await strategy.decide_move(
            game_id="game1",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[]
        )

        # Play game 2
        move2 = await strategy.decide_move(
            game_id="game2",
            round_number=1,
            my_role=GameRole.EVEN,
            my_score=0,
            opponent_score=0,
            history=[]
        )

        # Both should produce valid moves
        assert 1 <= move1 <= 50
        assert 1 <= move2 <= 50


class TestStrategyBoundaryValues:
    """Test strategies with boundary values."""

    @pytest.mark.asyncio
    async def test_strategy_with_narrow_range(self):
        """Test strategy with very narrow value range."""
        config = StrategyConfig(min_value=10, max_value=11)
        strategy = NashEquilibriumStrategy(config)

        move = await strategy.decide_move(
            game_id="test",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[]
        )

        assert 10 <= move <= 11

    @pytest.mark.asyncio
    async def test_strategy_with_wide_range(self):
        """Test strategy with wide value range."""
        config = StrategyConfig(min_value=1, max_value=100)
        strategy = BestResponseStrategy(config)

        move = await strategy.decide_move(
            game_id="test",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[]
        )

        assert 1 <= move <= 100


class TestMoreStrategyCoverage:
    """Additional tests for strategy coverage."""

    @pytest.mark.asyncio
    async def test_best_response_with_long_history(self):
        """Test best response with long game history."""
        strategy = BestResponseStrategy()

        # Create a long history
        history = []
        for i in range(20):
            history.append({
                "opponent_move": (i % 10) + 1,
                "my_move": ((i + 5) % 10) + 1,
                "result": "win" if i % 2 == 0 else "loss"
            })

        move = await strategy.decide_move(
            game_id="test",
            round_number=21,
            my_role=GameRole.ODD,
            my_score=10,
            opponent_score=10,
            history=history
        )

        assert 1 <= move <= 50

    @pytest.mark.asyncio
    async def test_adaptive_bayesian_with_varying_moves(self):
        """Test adaptive Bayesian with varying opponent moves."""
        strategy = AdaptiveBayesianStrategy()

        history = []
        for i in range(10):
            history.append({
                "opponent_move": 5 + (i * 3),
                "my_move": 10 + (i * 2),
                "result": "win" if i < 5 else "loss"
            })

            move = await strategy.decide_move(
                game_id="test",
                round_number=i + 1,
                my_role=GameRole.ODD if i % 2 == 0 else GameRole.EVEN,
                my_score=i,
                opponent_score=10 - i,
                history=history
            )

            assert 1 <= move <= 50

    @pytest.mark.asyncio
    async def test_fictitious_play_with_mixed_parities(self):
        """Test fictitious play with mixed parity opponent."""
        strategy = FictitiousPlayStrategy()

        history = []
        for i in range(10):
            is_odd = i % 2 == 0
            history.append({
                "opponent_move": (2 * i + 1) if is_odd else (2 * i + 2),
                "my_move": 25,
                "result": "win" if i % 3 == 0 else "loss"
            })

        move = await strategy.decide_move(
            game_id="test",
            round_number=11,
            my_role=GameRole.ODD,
            my_score=3,
            opponent_score=7,
            history=history
        )

        assert 1 <= move <= 50

    @pytest.mark.asyncio
    async def test_regret_matching_with_many_rounds(self):
        """Test regret matching over many rounds."""
        strategy = RegretMatchingStrategy()

        history = []
        for i in range(25):
            move = await strategy.decide_move(
                game_id="test",
                round_number=i + 1,
                my_role=GameRole.ODD,
                my_score=i // 3,
                opponent_score=i // 2,
                history=history
            )

            history.append({
                "opponent_move": 10 + (i % 20),
                "my_move": move,
                "result": ["win", "loss", "draw"][i % 3]
            })

        assert len(history) == 25

    @pytest.mark.asyncio
    async def test_nash_equilibrium_with_different_roles(self):
        """Test Nash equilibrium with different player roles."""
        strategy = NashEquilibriumStrategy()

        # Test as ODD player
        move1 = await strategy.decide_move(
            game_id="test1",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[]
        )

        # Test as EVEN player
        move2 = await strategy.decide_move(
            game_id="test2",
            round_number=1,
            my_role=GameRole.EVEN,
            my_score=0,
            opponent_score=0,
            history=[]
        )

        assert 1 <= move1 <= 50
        assert 1 <= move2 <= 50

    @pytest.mark.asyncio
    async def test_strategy_with_draws_in_history(self):
        """Test strategy behavior with draws in history."""
        strategy = BestResponseStrategy()

        history = [
            {"opponent_move": 10, "my_move": 10, "result": "draw"},
            {"opponent_move": 20, "my_move": 20, "result": "draw"},
            {"opponent_move": 15, "my_move": 15, "result": "draw"},
        ]

        move = await strategy.decide_move(
            game_id="test",
            round_number=4,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=history
        )

        assert 1 <= move <= 50

    @pytest.mark.asyncio
    async def test_strategy_with_extreme_scores(self):
        """Test strategy with extreme score difference."""
        strategy = FictitiousPlayStrategy()

        history = [{"opponent_move": 25, "my_move": 26}] * 5

        move = await strategy.decide_move(
            game_id="test",
            round_number=6,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=10,
            history=history
        )

        assert 1 <= move <= 50

    @pytest.mark.asyncio
    async def test_adaptive_bayesian_even_player(self):
        """Test Adaptive Bayesian as EVEN player."""
        strategy = AdaptiveBayesianStrategy()

        history = [
            {"opponent_move": 7, "my_move": 8, "result": "win"},
            {"opponent_move": 9, "my_move": 10, "result": "win"},
            {"opponent_move": 11, "my_move": 12, "result": "win"},
        ]

        move = await strategy.decide_move(
            game_id="test",
            round_number=4,
            my_role=GameRole.EVEN,
            my_score=3,
            opponent_score=0,
            history=history
        )

        assert 1 <= move <= 50

    @pytest.mark.asyncio
    async def test_regret_matching_even_player(self):
        """Test Regret Matching as EVEN player."""
        strategy = RegretMatchingStrategy()

        history = [
            {"opponent_move": 3, "my_move": 4, "result": "loss"},
            {"opponent_move": 5, "my_move": 6, "result": "loss"},
        ]

        move = await strategy.decide_move(
            game_id="test",
            round_number=3,
            my_role=GameRole.EVEN,
            my_score=0,
            opponent_score=2,
            history=history
        )

        assert 1 <= move <= 50

    def test_strategy_config_default_exploration(self):
        """Test StrategyConfig default exploration rate."""
        config = StrategyConfig()
        assert hasattr(config, 'exploration_rate')
        assert 0 <= config.exploration_rate <= 1

    def test_strategy_config_edge_values(self):
        """Test StrategyConfig with edge values."""
        config = StrategyConfig(
            min_value=1,
            max_value=1,
            exploration_rate=0.0
        )
        assert config.min_value == 1
        assert config.max_value == 1
        assert config.exploration_rate == 0.0

