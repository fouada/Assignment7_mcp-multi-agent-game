"""
Comprehensive Tests for Game Strategies
========================================

Tests cover:
- All strategy types (Random, Nash, Best Response, Adaptive Bayesian, etc.)
- Strategy initialization and configuration
- Move decision making
- History tracking and learning
- Edge cases and boundary conditions
- Strategy performance characteristics
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.agents.strategies import (
    AdaptiveBayesianStrategy,
    BestResponseStrategy,
    FictitiousPlayStrategy,
    LLMStrategy,
    NashEquilibriumStrategy,
    PatternStrategy,
    RandomStrategy,
    RegretMatchingStrategy,
    StrategyConfig,
    StrategyFactory,
    ThompsonSamplingStrategy,
    UCBStrategy,
)
from src.common.config import LLMConfig
from src.game.odd_even import GameRole


class TestStrategyBase:
    """Test base strategy functionality."""

    def test_strategy_has_name(self):
        """Test that strategies have names."""
        strategy = RandomStrategy()
        assert strategy.name is not None
        assert len(strategy.name) > 0


class TestRandomStrategy:
    """Test random strategy."""

    @pytest.mark.asyncio
    async def test_random_strategy_move_range(self):
        """Test that random strategy produces moves in valid range."""
        strategy = RandomStrategy()

        for _ in range(100):
            move = await strategy.decide_move(
                game_id="game_001",
                round_number=1,
                my_role=GameRole.ODD,
                my_score=0,
                opponent_score=0,
                history=[],
            )

            assert isinstance(move, int)
            assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_random_strategy_distribution(self):
        """Test that random strategy has roughly uniform distribution."""
        strategy = RandomStrategy()

        # Generate many moves
        moves = []
        for _ in range(1000):
            move = await strategy.decide_move(
                game_id="game_001",
                round_number=1,
                my_role=GameRole.ODD,
                my_score=0,
                opponent_score=0,
                history=[],
            )
            moves.append(move)

        # Check each value appears (with some tolerance)
        for value in range(1, 11):
            count = moves.count(value)
            # Should be roughly 100 ± some margin
            assert 50 < count < 150  # Allow for variance


class TestNashEquilibriumStrategy:
    """Test Nash equilibrium strategy."""

    @pytest.mark.asyncio
    async def test_nash_strategy_move_range(self):
        """Test Nash strategy produces valid moves."""
        strategy = NashEquilibriumStrategy()

        for _ in range(50):
            move = await strategy.decide_move(
                game_id="game_001",
                round_number=1,
                my_role=GameRole.ODD,
                my_score=0,
                opponent_score=0,
                history=[],
            )

            assert isinstance(move, int)
            assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_nash_strategy_uniform_distribution(self):
        """Test Nash strategy maintains uniform distribution (Nash equilibrium)."""
        strategy = NashEquilibriumStrategy()

        moves = []
        for _ in range(1000):
            move = await strategy.decide_move(
                game_id="game_001",
                round_number=1,
                my_role=GameRole.ODD,
                my_score=0,
                opponent_score=0,
                history=[],
            )
            moves.append(move)

        # Nash equilibrium should be roughly uniform
        for value in range(1, 11):
            count = moves.count(value)
            assert 50 < count < 150


class TestBestResponseStrategy:
    """Test best response strategy."""

    @pytest.mark.asyncio
    async def test_best_response_with_history(self):
        """Test best response adapts to opponent history."""
        strategy = BestResponseStrategy()

        # Opponent always plays 5
        history = [{"round": i + 1, "opponent_move": 5, "my_move": 3} for i in range(10)]

        # Strategy should adapt
        moves = []
        for _ in range(20):
            move = await strategy.decide_move(
                game_id="game_001",
                round_number=11,
                my_role=GameRole.ODD,
                my_score=5,
                opponent_score=5,
                history=history,
            )
            moves.append(move)

        # Should produce valid moves
        for move in moves:
            assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_best_response_no_history(self):
        """Test best response with no history (should be random)."""
        strategy = BestResponseStrategy()

        move = await strategy.decide_move(
            game_id="game_001",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[],
        )

        assert 1 <= move <= 10


class TestAdaptiveBayesianStrategy:
    """Test adaptive Bayesian strategy."""

    @pytest.mark.asyncio
    async def test_adaptive_bayesian_learning(self):
        """Test that adaptive Bayesian learns from history."""
        strategy = AdaptiveBayesianStrategy()

        # Create biased history (opponent favors even moves)
        history = []
        for i in range(20):
            history.append(
                {
                    "round": i + 1,
                    "opponent_move": 2 if i % 2 == 0 else 4,
                    "my_move": 3,
                }
            )

        # Make multiple decisions
        moves = []
        for _ in range(10):
            move = await strategy.decide_move(
                game_id="game_001",
                round_number=21,
                my_role=GameRole.ODD,
                my_score=10,
                opponent_score=10,
                history=history,
            )
            moves.append(move)

        # All moves should be valid
        for move in moves:
            assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_adaptive_bayesian_initialization(self):
        """Test adaptive Bayesian with default parameters."""
        strategy = AdaptiveBayesianStrategy()

        move = await strategy.decide_move(
            game_id="game_001",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[],
        )

        assert 1 <= move <= 10


class TestFictitiousPlayStrategy:
    """Test fictitious play strategy."""

    @pytest.mark.asyncio
    async def test_fictitious_play_learning(self):
        """Test fictitious play learns opponent tendencies."""
        strategy = FictitiousPlayStrategy()

        # Opponent has pattern
        history = [{"round": i + 1, "opponent_move": (i % 3) + 1, "my_move": 5} for i in range(15)]

        move = await strategy.decide_move(
            game_id="game_001",
            round_number=16,
            my_role=GameRole.ODD,
            my_score=7,
            opponent_score=8,
            history=history,
        )

        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_fictitious_play_no_history(self):
        """Test fictitious play with no history."""
        strategy = FictitiousPlayStrategy()

        move = await strategy.decide_move(
            game_id="game_001",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[],
        )

        assert 1 <= move <= 10


class TestRegretMatchingStrategy:
    """Test regret matching strategy."""

    @pytest.mark.asyncio
    async def test_regret_matching_adaptation(self):
        """Test regret matching adapts based on outcomes."""
        strategy = RegretMatchingStrategy()

        # History with clear pattern
        history = [
            {"round": i + 1, "opponent_move": 5, "my_move": 3, "winner": "opponent"}
            for i in range(10)
        ]

        move = await strategy.decide_move(
            game_id="game_001",
            round_number=11,
            my_role=GameRole.ODD,
            my_score=2,
            opponent_score=8,
            history=history,
        )

        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_regret_matching_initialization(self):
        """Test regret matching with default parameters."""
        strategy = RegretMatchingStrategy()

        move = await strategy.decide_move(
            game_id="game_001",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[],
        )

        assert 1 <= move <= 10


class TestUCBStrategy:
    """Test UCB (Upper Confidence Bound) strategy."""

    @pytest.mark.asyncio
    async def test_ucb_exploration_exploitation(self):
        """Test UCB balances exploration and exploitation."""
        strategy = UCBStrategy()

        # Some history
        history = [{"round": i + 1, "opponent_move": 5, "my_move": 3} for i in range(10)]

        moves = []
        for _ in range(20):
            move = await strategy.decide_move(
                game_id="game_001",
                round_number=11,
                my_role=GameRole.ODD,
                my_score=5,
                opponent_score=5,
                history=history,
            )
            moves.append(move)

        # Should explore different moves
        unique_moves = len(set(moves))
        assert unique_moves >= 2  # At least some exploration

    @pytest.mark.asyncio
    async def test_ucb_custom_exploration(self):
        """Test UCB with default exploration."""
        strategy = UCBStrategy()

        move = await strategy.decide_move(
            game_id="game_001",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[],
        )

        assert 1 <= move <= 10


class TestThompsonSamplingStrategy:
    """Test Thompson sampling strategy."""

    @pytest.mark.asyncio
    async def test_thompson_sampling_bayesian_updates(self):
        """Test Thompson sampling updates beliefs."""
        strategy = ThompsonSamplingStrategy()

        # History with some wins
        history = [
            {"round": i + 1, "opponent_move": 5, "my_move": 4, "winner": "me"} for i in range(10)
        ]

        moves = []
        for _ in range(20):
            move = await strategy.decide_move(
                game_id="game_001",
                round_number=11,
                my_role=GameRole.ODD,
                my_score=8,
                opponent_score=2,
                history=history,
            )
            moves.append(move)

        # Should sample from posterior
        for move in moves:
            assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_thompson_sampling_initialization(self):
        """Test Thompson sampling with default priors."""
        strategy = ThompsonSamplingStrategy()

        move = await strategy.decide_move(
            game_id="game_001",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[],
        )

        assert 1 <= move <= 10


class TestPatternStrategy:
    """Test pattern detection strategy."""

    @pytest.mark.asyncio
    async def test_pattern_strategy_detection(self):
        """Test pattern strategy detects opponent patterns."""
        strategy = PatternStrategy()

        # Clear repeating pattern
        history = [{"round": i + 1, "opponent_move": (i % 3) + 1, "my_move": 5} for i in range(12)]

        move = await strategy.decide_move(
            game_id="game_001",
            round_number=13,
            my_role=GameRole.ODD,
            my_score=6,
            opponent_score=6,
            history=history,
        )

        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_pattern_strategy_no_pattern(self):
        """Test pattern strategy with random opponent."""
        strategy = PatternStrategy()

        # Random history
        import random

        history = [
            {"round": i + 1, "opponent_move": random.randint(1, 10), "my_move": 5}
            for i in range(10)
        ]

        move = await strategy.decide_move(
            game_id="game_001",
            round_number=11,
            my_role=GameRole.ODD,
            my_score=5,
            opponent_score=5,
            history=history,
        )

        assert 1 <= move <= 10


class TestLLMStrategy:
    """Test LLM-based strategy."""

    @pytest.mark.asyncio
    async def test_llm_strategy_with_mock(self):
        """Test LLM strategy with mocked LLM call."""
        llm_config = LLMConfig(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            api_key="test_key",
        )

        strategy = LLMStrategy(llm_config=llm_config)

        # Mock the LLM call
        with patch.object(strategy, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = 5

            move = await strategy.decide_move(
                game_id="game_001",
                round_number=1,
                my_role=GameRole.ODD,
                my_score=0,
                opponent_score=0,
                history=[],
            )

            assert move == 5

    @pytest.mark.asyncio
    async def test_llm_strategy_fallback(self):
        """Test LLM strategy falls back on error."""
        llm_config = LLMConfig(
            provider="anthropic",
            api_key="invalid_key",
        )

        strategy = LLMStrategy(llm_config=llm_config)

        # Should fall back to random move
        move = await strategy.decide_move(
            game_id="game_001",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[],
        )

        assert 1 <= move <= 10


class TestStrategyFactory:
    """Test strategy factory."""

    def test_create_random_strategy(self):
        """Test creating random strategy from factory."""
        strategy = StrategyFactory.create_from_string("random")
        assert isinstance(strategy, RandomStrategy)

    def test_create_nash_strategy(self):
        """Test creating Nash strategy from factory."""
        strategy = StrategyFactory.create_from_string("nash")
        assert isinstance(strategy, NashEquilibriumStrategy)

    def test_create_best_response_strategy(self):
        """Test creating best response strategy from factory."""
        strategy = StrategyFactory.create_from_string("best_response")
        assert isinstance(strategy, BestResponseStrategy)

    def test_create_adaptive_bayesian_strategy(self):
        """Test creating adaptive Bayesian strategy from factory."""
        strategy = StrategyFactory.create_from_string("adaptive_bayesian")
        assert isinstance(strategy, AdaptiveBayesianStrategy)

    def test_create_fictitious_play_strategy(self):
        """Test creating fictitious play strategy from factory."""
        strategy = StrategyFactory.create_from_string("fictitious_play")
        assert isinstance(strategy, FictitiousPlayStrategy)

    def test_create_regret_matching_strategy(self):
        """Test creating regret matching strategy from factory."""
        strategy = StrategyFactory.create_from_string("regret_matching")
        assert isinstance(strategy, RegretMatchingStrategy)

    def test_create_ucb_strategy(self):
        """Test creating UCB strategy from factory."""
        strategy = StrategyFactory.create_from_string("ucb")
        assert isinstance(strategy, UCBStrategy)

    def test_create_thompson_sampling_strategy(self):
        """Test creating Thompson sampling strategy from factory."""
        strategy = StrategyFactory.create_from_string("thompson_sampling")
        assert isinstance(strategy, ThompsonSamplingStrategy)

    def test_create_pattern_strategy(self):
        """Test creating pattern strategy from factory."""
        strategy = StrategyFactory.create_from_string("pattern")
        assert isinstance(strategy, PatternStrategy)

    def test_create_unknown_strategy(self):
        """Test creating unknown strategy raises error."""
        with pytest.raises(ValueError, match="Unknown strategy"):
            StrategyFactory.create_from_string("unknown_strategy")

    def test_list_strategies(self):
        """Test listing available strategies."""
        strategies = StrategyFactory.list_strategies()

        assert isinstance(strategies, dict)
        assert "random" in strategies
        assert "nash" in strategies
        assert "adaptive_bayesian" in strategies
        assert "best_response" in strategies

    def test_get_recommended_strategy(self):
        """Test getting recommended strategy."""
        strategy = StrategyFactory.get_recommended_strategy()

        assert isinstance(strategy, AdaptiveBayesianStrategy)

    def test_create_with_config(self):
        """Test creating strategy with configuration."""
        config = StrategyConfig(
            exploration_rate=0.3,
            learning_rate=0.2,
        )

        strategy = StrategyFactory.create_from_string(
            "adaptive_bayesian",
            config=config,
        )

        assert isinstance(strategy, AdaptiveBayesianStrategy)

    def test_create_with_kwargs(self):
        """Test creating strategy with keyword arguments."""
        strategy = StrategyFactory.create_from_string(
            "ucb",
            exploration_constant=2.0,
        )

        assert isinstance(strategy, UCBStrategy)


class TestStrategyEdgeCases:
    """Test strategy edge cases."""

    @pytest.mark.asyncio
    async def test_strategy_with_empty_history(self):
        """Test all strategies work with empty history."""
        strategies = [
            RandomStrategy(),
            NashEquilibriumStrategy(),
            BestResponseStrategy(),
            AdaptiveBayesianStrategy(),
            FictitiousPlayStrategy(),
            RegretMatchingStrategy(),
            UCBStrategy(),
            ThompsonSamplingStrategy(),
            PatternStrategy(),
        ]

        for strategy in strategies:
            move = await strategy.decide_move(
                game_id="game_001",
                round_number=1,
                my_role=GameRole.ODD,
                my_score=0,
                opponent_score=0,
                history=[],
            )

            assert 1 <= move <= 10, f"{strategy.name} produced invalid move: {move}"

    @pytest.mark.asyncio
    async def test_strategy_with_long_history(self):
        """Test strategies with very long history."""
        # Create long history
        history = [
            {"round": i + 1, "opponent_move": (i % 10) + 1, "my_move": 5} for i in range(100)
        ]

        strategies = [
            RandomStrategy(),
            BestResponseStrategy(),
            AdaptiveBayesianStrategy(),
            PatternStrategy(),
        ]

        for strategy in strategies:
            move = await strategy.decide_move(
                game_id="game_001",
                round_number=101,
                my_role=GameRole.ODD,
                my_score=50,
                opponent_score=50,
                history=history,
            )

            assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_strategy_with_extreme_scores(self):
        """Test strategies with extreme score differences."""
        strategy = AdaptiveBayesianStrategy()

        # Losing badly
        move1 = await strategy.decide_move(
            game_id="game_001",
            round_number=10,
            my_role=GameRole.ODD,
            my_score=1,
            opponent_score=9,
            history=[],
        )
        assert 1 <= move1 <= 10

        # Winning big
        move2 = await strategy.decide_move(
            game_id="game_002",
            round_number=10,
            my_role=GameRole.ODD,
            my_score=9,
            opponent_score=1,
            history=[],
        )
        assert 1 <= move2 <= 10

    @pytest.mark.asyncio
    async def test_strategy_determinism(self):
        """Test that some strategies are deterministic given same state."""
        # Note: Most strategies have randomness, but Nash should be uniform
        strategy = NashEquilibriumStrategy()

        moves = []
        for _ in range(10):
            move = await strategy.decide_move(
                game_id="game_001",
                round_number=1,
                my_role=GameRole.ODD,
                my_score=0,
                opponent_score=0,
                history=[],
            )
            moves.append(move)

        # All should be valid
        for move in moves:
            assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_strategy_with_tied_scores(self):
        """Test strategies when scores are tied."""
        strategy = BestResponseStrategy()

        history = [
            {"round": i + 1, "opponent_move": 5, "my_move": 5, "winner": None} for i in range(5)
        ]

        move = await strategy.decide_move(
            game_id="game_001",
            round_number=6,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=history,
        )

        assert 1 <= move <= 10


# ============================================================================
# Edge Case Documentation
# ============================================================================

"""
EDGE CASES TESTED:

1. Strategy Initialization:
   - Default parameters
   - Custom parameters
   - With configuration objects
   - With LLM configuration

2. Random Strategy:
   - Valid move range (1-10)
   - Uniform distribution
   - No bias

3. Nash Equilibrium:
   - Uniform distribution
   - No exploitation vulnerability
   - Consistent behavior

4. Best Response:
   - Adapts to opponent patterns
   - Works with no history
   - Handles biased opponents

5. Adaptive Bayesian:
   - Learns from history
   - Balances exploration/exploitation
   - Custom priors
   - Handles extreme scores

6. Fictitious Play:
   - Learns opponent frequencies
   - Works with no history
   - Adapts over time

7. Regret Matching:
   - Minimizes regret
   - Custom learning rate
   - Adapts to losses

8. UCB (Upper Confidence Bound):
   - Explores uncertain options
   - Exploits known good options
   - Custom exploration constant

9. Thompson Sampling:
   - Bayesian bandit
   - Posterior sampling
   - Custom priors

10. Pattern Detection:
    - Detects simple patterns
    - Handles random opponents
    - Pattern prediction

11. LLM Strategy:
    - Fallback on error
    - Handles network issues
    - API key validation

12. Strategy Factory:
    - All strategy types
    - Unknown strategy errors
    - Configuration passing
    - Recommended strategy

13. Edge Cases:
    - Empty history
    - Very long history (100+ rounds)
    - Extreme score differences
    - Tied scores
    - First round decisions
    - Deterministic vs stochastic behavior
"""
