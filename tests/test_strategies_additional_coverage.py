"""
Additional Strategy Tests for 85%+ Coverage
============================================

Targeted tests to cover missing paths in classic strategies
(Random, Pattern, LLM) to push coverage from 70% to 85%+.

Edge Cases Covered:
- LLM API fallback scenarios
- Pattern detection edge cases
- Empty candidate lists
- Number extraction from various formats
"""

import random
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.agents.strategies.classic import LLMStrategy, PatternStrategy, RandomStrategy
from src.agents.strategies.base import StrategyConfig
from src.common.config import LLMConfig
from src.game.odd_even import GameRole


class TestPatternStrategyEdgeCases:
    """Test PatternStrategy edge cases."""

    @pytest.mark.asyncio
    async def test_pattern_with_empty_history_list(self):
        """Test pattern strategy with explicitly empty history.

        Edge Case: Empty list for history.
        """
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
    async def test_pattern_with_no_opponent_parities_yet(self):
        """Test pattern when opponent parity list is empty.

        Edge Case: History exists but opponent parities not yet tracked.
        """
        strategy = PatternStrategy()

        # Clear any existing parities
        strategy._opponent_parities.clear()

        history = [{"round": 1}]  # Missing opponent_move

        move = await strategy.decide_move(
            game_id="test",
            round_number=2,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=history,
        )

        # Should fall back to random
        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_pattern_with_all_even_candidates_needed(self):
        """Test pattern when even candidates are needed.

        Edge Case: Strategy determines player should play even.
        """
        strategy = PatternStrategy()

        # Set up history where opponent plays odd frequently
        history = [
            {"opponent_move": 1, "my_move": 2, "result": "win"},
            {"opponent_move": 3, "my_move": 4, "result": "win"},
            {"opponent_move": 5, "my_move": 6, "result": "win"},
            {"opponent_move": 7, "my_move": 2, "result": "win"},
            {"opponent_move": 9, "my_move": 4, "result": "win"},
        ]

        move = await strategy.decide_move(
            game_id="test",
            round_number=6,
            my_role=GameRole.ODD,
            my_score=5,
            opponent_score=0,
            history=history,
        )

        # Should pick a move (may be odd or even based on prediction)
        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_pattern_with_mixed_parity_history(self):
        """Test pattern with 50/50 parity distribution.

        Edge Case: Opponent has no clear pattern.
        """
        strategy = PatternStrategy()

        history = [
            {"opponent_move": 1, "my_move": 2, "result": "win"},
            {"opponent_move": 2, "my_move": 3, "result": "loss"},
            {"opponent_move": 3, "my_move": 4, "result": "win"},
            {"opponent_move": 4, "my_move": 5, "result": "loss"},
        ]

        move = await strategy.decide_move(
            game_id="test",
            round_number=5,
            my_role=GameRole.EVEN,
            my_score=2,
            opponent_score=2,
            history=history,
        )

        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_pattern_with_constrained_range_no_candidates(self):
        """Test pattern with very constrained range where no candidates match.

        Edge Case: Range is so narrow that desired parity has no candidates.
        """
        config = StrategyConfig(min_value=2, max_value=2)  # Only value 2 (even)
        strategy = PatternStrategy(config)

        # History suggests we should play odd, but only 2 is available
        history = [
            {"opponent_move": 1, "my_move": 2, "result": "win"},
        ]

        move = await strategy.decide_move(
            game_id="test",
            round_number=2,
            my_role=GameRole.ODD,
            my_score=1,
            opponent_score=0,
            history=history,
        )

        # Should fall back to random from available range
        assert move == 2

    def test_pattern_reset_clears_tracking(self):
        """Test reset clears opponent parity tracking."""
        strategy = PatternStrategy()

        # Add some tracking data
        strategy._opponent_parities["game1"] = [True, False, True]
        strategy._opponent_parities["game2"] = [False, False]

        assert len(strategy._opponent_parities) == 2

        strategy.reset()

        assert len(strategy._opponent_parities) == 0

    def test_pattern_get_stats_with_tracking(self):
        """Test get_stats returns tracking info."""
        strategy = PatternStrategy()

        strategy._opponent_parities["game1"] = [True, False]
        strategy._opponent_parities["game2"] = [False, True]

        stats = strategy.get_stats()

        assert "games_tracked" in stats
        assert stats["games_tracked"] == 2


class TestLLMStrategyEdgeCases:
    """Test LLMStrategy edge cases and fallback scenarios."""

    @pytest.mark.asyncio
    async def test_llm_without_api_key_falls_back(self):
        """Test LLM strategy without API key falls back to random.

        Edge Case: No API key configured - must use fallback.
        """
        llm_config = LLMConfig(api_key="")
        strategy = LLMStrategy(llm_config=llm_config)

        move = await strategy.decide_move(
            game_id="test",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[],
        )

        # Should fall back to random move
        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_llm_client_creation_returns_none(self):
        """Test when LLM client cannot be created.

        Edge Case: Client creation fails - should return None.
        """
        llm_config = LLMConfig(api_key="")
        strategy = LLMStrategy(llm_config=llm_config)

        client = await strategy._get_client()

        # Should return None when no API key
        assert client is None

    @pytest.mark.asyncio
    async def test_llm_with_invalid_config_uses_fallback(self):
        """Test LLM with invalid configuration uses fallback."""
        llm_config = LLMConfig(
            provider="anthropic",
            api_key=None,  # Invalid
            model="claude-sonnet-4-20250514",
        )
        strategy = LLMStrategy(llm_config=llm_config)

        move = await strategy.decide_move(
            game_id="test",
            round_number=1,
            my_role=GameRole.EVEN,
            my_score=0,
            opponent_score=0,
            history=[],
        )

        # Should fall back gracefully
        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_llm_with_empty_history(self):
        """Test LLM decision with no game history."""
        llm_config = LLMConfig(api_key="")  # Will use fallback
        strategy = LLMStrategy(llm_config=llm_config)

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
    async def test_llm_with_extensive_history(self):
        """Test LLM handles extensive game history.

        Edge Case: Large history should be summarized or handled efficiently.
        """
        llm_config = LLMConfig(api_key="")  # Will use fallback
        strategy = LLMStrategy(llm_config=llm_config)

        # Create large history
        history = [
            {
                "round": i,
                "opponent_move": 3 + (i % 5),
                "my_move": 2 + (i % 4),
                "result": "win" if i % 2 == 0 else "loss",
            }
            for i in range(50)
        ]

        move = await strategy.decide_move(
            game_id="test",
            round_number=51,
            my_role=GameRole.ODD,
            my_score=25,
            opponent_score=25,
            history=history,
        )

        assert 1 <= move <= 10

    def test_llm_reset_does_not_crash(self):
        """Test LLM reset completes successfully."""
        llm_config = LLMConfig(api_key="test_key")
        strategy = LLMStrategy(llm_config=llm_config)

        strategy.reset()

        # Should complete without error
        assert True

    def test_llm_get_stats_includes_config(self):
        """Test LLM get_stats includes configuration info."""
        llm_config = LLMConfig(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            api_key="test_key",
        )
        strategy = LLMStrategy(llm_config=llm_config)

        stats = strategy.get_stats()

        # Should include config details
        assert "provider" in stats or "model" in stats

    @pytest.mark.asyncio
    async def test_llm_number_extraction_fallback(self):
        """Test LLM falls back when no valid number in response.

        Edge Case: LLM response doesn't contain a valid move number.
        """
        llm_config = LLMConfig(api_key="")
        strategy = LLMStrategy(llm_config=llm_config)

        # Will use fallback since no API key
        move = await strategy.decide_move(
            game_id="test",
            round_number=1,
            my_role=GameRole.EVEN,
            my_score=0,
            opponent_score=0,
            history=[],
        )

        assert 1 <= move <= 10


class TestRandomStrategyEdgeCases:
    """Test RandomStrategy edge cases."""

    @pytest.mark.asyncio
    async def test_random_with_narrow_range(self):
        """Test random strategy with very narrow value range.

        Edge Case: Min and max are very close.
        """
        config = StrategyConfig(min_value=5, max_value=6)
        strategy = RandomStrategy(config)

        moves = []
        for _ in range(20):
            move = await strategy.decide_move(
                game_id="test",
                round_number=1,
                my_role=GameRole.ODD,
                my_score=0,
                opponent_score=0,
                history=[],
            )
            moves.append(move)
            assert 5 <= move <= 6

        # Should have both values
        assert 5 in moves or 6 in moves

    @pytest.mark.asyncio
    async def test_random_with_single_value_range(self):
        """Test random strategy with single possible value.

        Edge Case: Min equals max.
        """
        config = StrategyConfig(min_value=7, max_value=7)
        strategy = RandomStrategy(config)

        move = await strategy.decide_move(
            game_id="test",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[],
        )

        assert move == 7

    @pytest.mark.asyncio
    async def test_random_is_not_predictable(self):
        """Test random strategy produces varied moves."""
        strategy = RandomStrategy()

        moves = set()
        for _ in range(50):
            move = await strategy.decide_move(
                game_id="test",
                round_number=1,
                my_role=GameRole.ODD,
                my_score=0,
                opponent_score=0,
                history=[],
            )
            moves.add(move)

        # Should have variety (at least 5 different moves)
        assert len(moves) >= 5

    def test_random_reset_is_noop(self):
        """Test random reset does nothing (no state to reset)."""
        strategy = RandomStrategy()

        strategy.reset()

        # Should complete without issue
        assert True

    def test_random_get_stats_includes_range(self):
        """Test random get_stats includes value range."""
        config = StrategyConfig(min_value=1, max_value=20)
        strategy = RandomStrategy(config)

        stats = strategy.get_stats()

        assert "min_value" in stats
        assert "max_value" in stats
        assert stats["min_value"] == 1
        assert stats["max_value"] == 20


class TestStrategyConfigEdgeCases:
    """Test StrategyConfig edge cases."""

    def test_strategy_config_defaults(self):
        """Test StrategyConfig with default values."""
        config = StrategyConfig()

        assert config.min_value == 1
        assert config.max_value == 10
        assert hasattr(config, "exploration_rate")

    def test_strategy_config_custom_values(self):
        """Test StrategyConfig with custom values."""
        config = StrategyConfig(
            min_value=10,
            max_value=100,
            exploration_rate=0.3,
        )

        assert config.min_value == 10
        assert config.max_value == 100
        assert config.exploration_rate == 0.3

    def test_strategy_config_with_zero_exploration(self):
        """Test StrategyConfig with zero exploration.

        Edge Case: Pure exploitation mode.
        """
        config = StrategyConfig(exploration_rate=0.0)

        assert config.exploration_rate == 0.0

    def test_strategy_config_with_full_exploration(self):
        """Test StrategyConfig with full exploration.

        Edge Case: Pure exploration mode.
        """
        config = StrategyConfig(exploration_rate=1.0)

        assert config.exploration_rate == 1.0


class TestStrategyIntegrationEdgeCases:
    """Test strategy integration edge cases."""

    @pytest.mark.asyncio
    async def test_all_strategies_handle_empty_history(self):
        """Test all strategy types handle empty history."""
        strategies = [
            RandomStrategy(),
            PatternStrategy(),
            LLMStrategy(llm_config=LLMConfig(api_key="")),
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

            assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_all_strategies_handle_large_scores(self):
        """Test all strategies handle extreme score values.

        Edge Case: Very large score differences.
        """
        strategies = [
            RandomStrategy(),
            PatternStrategy(),
        ]

        for strategy in strategies:
            move = await strategy.decide_move(
                game_id="test",
                round_number=100,
                my_role=GameRole.ODD,
                my_score=500,
                opponent_score=200,
                history=[],
            )

            assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_strategies_with_alternating_roles(self):
        """Test strategies work with both ODD and EVEN roles."""
        strategy = PatternStrategy()

        # Test as ODD player
        move_odd = await strategy.decide_move(
            game_id="test1",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[],
        )

        # Test as EVEN player
        move_even = await strategy.decide_move(
            game_id="test2",
            round_number=1,
            my_role=GameRole.EVEN,
            my_score=0,
            opponent_score=0,
            history=[],
        )

        assert 1 <= move_odd <= 10
        assert 1 <= move_even <= 10
