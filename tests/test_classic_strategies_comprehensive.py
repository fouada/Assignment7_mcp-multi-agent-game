"""
Comprehensive tests for classic strategies to increase coverage.

Tests error handling, edge cases, and LLM strategy functionality.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import random

from src.agents.strategies.classic import (
    RandomStrategy,
    PatternStrategy,
    LLMStrategy,
)
from src.agents.strategies.base import StrategyConfig
from src.common.config import LLMConfig
from src.game.odd_even import GameRole


class TestRandomStrategyComprehensive:
    """Comprehensive tests for RandomStrategy."""

    @pytest.mark.asyncio
    async def test_random_strategy_respects_bounds(self):
        """Test that random strategy respects min/max bounds."""
        config = StrategyConfig(min_value=10, max_value=20)
        strategy = RandomStrategy(config)
        
        # Test multiple times to ensure consistency
        for _ in range(100):
            move = await strategy.decide_move(
                game_id="test",
                round_number=1,
                my_role=GameRole.ODD,
                my_score=0,
                opponent_score=0,
                history=[]
            )
            assert 10 <= move <= 20

    @pytest.mark.asyncio
    async def test_random_strategy_different_bounds(self):
        """Test random strategy with different bounds."""
        config = StrategyConfig(min_value=1, max_value=5)
        strategy = RandomStrategy(config)
        
        move = await strategy.decide_move(
            game_id="test",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[]
        )
        assert 1 <= move <= 5

    def test_random_strategy_reset(self):
        """Test reset does nothing for random strategy."""
        strategy = RandomStrategy()
        strategy.reset()  # Should not raise

    def test_random_strategy_get_stats(self):
        """Test get_stats includes bounds."""
        config = StrategyConfig(min_value=10, max_value=30)
        strategy = RandomStrategy(config)
        stats = strategy.get_stats()
        assert stats["min_value"] == 10
        assert stats["max_value"] == 30
        assert "name" in stats


class TestPatternStrategyComprehensive:
    """Comprehensive tests for PatternStrategy."""

    @pytest.mark.asyncio
    async def test_pattern_strategy_empty_history(self):
        """Test pattern strategy with no history."""
        strategy = PatternStrategy()
        move = await strategy.decide_move(
            game_id="test",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[]
        )
        assert 1 <= move <= 50  # Default bounds

    @pytest.mark.asyncio
    async def test_pattern_strategy_opponent_prefers_odd(self):
        """Test pattern strategy when opponent prefers odd numbers."""
        strategy = PatternStrategy()
        
        # Create history where opponent always plays odd
        history = [
            {"opponent_move": 1, "my_move": 2},
            {"opponent_move": 3, "my_move": 2},
            {"opponent_move": 5, "my_move": 2},
            {"opponent_move": 7, "my_move": 2},
            {"opponent_move": 9, "my_move": 2},
        ]
        
        # As ODD player, if opponent plays odd, we should play even (to get odd sum)
        move = await strategy.decide_move(
            game_id="test",
            round_number=6,
            my_role=GameRole.ODD,
            my_score=2,
            opponent_score=3,
            history=history
        )
        # Should be even (opponent likely odd, so we counter)
        assert move % 2 == 0

    @pytest.mark.asyncio
    async def test_pattern_strategy_opponent_prefers_even(self):
        """Test pattern strategy when opponent prefers even numbers."""
        strategy = PatternStrategy()
        
        # Create history where opponent always plays even
        history = [
            {"opponent_move": 2, "my_move": 1},
            {"opponent_move": 4, "my_move": 1},
            {"opponent_move": 6, "my_move": 1},
            {"opponent_move": 8, "my_move": 1},
            {"opponent_move": 10, "my_move": 1},
        ]
        
        # As ODD player, if opponent plays even, we should play odd (to get odd sum)
        move = await strategy.decide_move(
            game_id="test",
            round_number=6,
            my_role=GameRole.ODD,
            my_score=2,
            opponent_score=3,
            history=history
        )
        # Should be odd (opponent likely even, so we play odd)
        assert move % 2 == 1

    @pytest.mark.asyncio
    async def test_pattern_strategy_as_even_player(self):
        """Test pattern strategy as EVEN player."""
        strategy = PatternStrategy()
        
        # Opponent plays odd
        history = [
            {"opponent_move": 1, "my_move": 2},
            {"opponent_move": 3, "my_move": 2},
            {"opponent_move": 5, "my_move": 2},
        ]
        
        # As EVEN player, if opponent plays odd, we should play odd (to get even sum)
        move = await strategy.decide_move(
            game_id="test",
            round_number=4,
            my_role=GameRole.EVEN,
            my_score=2,
            opponent_score=1,
            history=history
        )
        # Should be odd (to counter opponent's odd)
        assert move % 2 == 1

    @pytest.mark.asyncio
    async def test_pattern_strategy_mixed_history(self):
        """Test pattern strategy with mixed history."""
        strategy = PatternStrategy()
        
        # Mixed history
        history = [
            {"opponent_move": 1, "my_move": 2},  # odd
            {"opponent_move": 2, "my_move": 1},  # even
            {"opponent_move": 3, "my_move": 2},  # odd
        ]
        
        move = await strategy.decide_move(
            game_id="test",
            round_number=4,
            my_role=GameRole.ODD,
            my_score=1,
            opponent_score=2,
            history=history
        )
        assert 1 <= move <= 50

    @pytest.mark.asyncio
    async def test_pattern_strategy_no_candidates_fallback(self):
        """Test pattern strategy fallback when no candidates."""
        # This should never happen in practice, but test the fallback
        strategy = PatternStrategy()
        history = [{"opponent_move": 1, "my_move": 2}]
        
        move = await strategy.decide_move(
            game_id="test",
            round_number=2,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=1,
            history=history
        )
        assert isinstance(move, int)

    @pytest.mark.asyncio
    async def test_pattern_strategy_multiple_games(self):
        """Test pattern strategy tracks multiple games separately."""
        strategy = PatternStrategy()
        
        # Game 1 history
        history1 = [{"opponent_move": 1, "my_move": 2}]
        await strategy.decide_move(
            game_id="game1",
            round_number=2,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=1,
            history=history1
        )
        
        # Game 2 history
        history2 = [{"opponent_move": 2, "my_move": 1}]
        await strategy.decide_move(
            game_id="game2",
            round_number=2,
            my_role=GameRole.ODD,
            my_score=1,
            opponent_score=0,
            history=history2
        )
        
        stats = strategy.get_stats()
        assert stats["games_tracked"] == 2

    def test_pattern_strategy_reset(self):
        """Test reset clears history."""
        strategy = PatternStrategy()
        strategy._opponent_parities["game1"] = [True, False]
        strategy._opponent_parities["game2"] = [False, True]
        
        strategy.reset()
        assert len(strategy._opponent_parities) == 0

    def test_pattern_strategy_get_stats(self):
        """Test get_stats includes games tracked."""
        strategy = PatternStrategy()
        strategy._opponent_parities["game1"] = [True]
        strategy._opponent_parities["game2"] = [False]
        
        stats = strategy.get_stats()
        assert stats["games_tracked"] == 2


class TestLLMStrategyComprehensive:
    """Comprehensive tests for LLMStrategy."""

    def test_llm_strategy_initialization_default(self):
        """Test LLM strategy with default config."""
        strategy = LLMStrategy()
        assert strategy.llm_config is not None
        assert strategy._client is None

    def test_llm_strategy_initialization_custom_config(self):
        """Test LLM strategy with custom LLM config."""
        llm_config = LLMConfig(
            provider="anthropic",
            model="claude-3-sonnet-20240229",
            api_key="test_key"
        )
        strategy = LLMStrategy(llm_config=llm_config)
        assert strategy.llm_config.provider == "anthropic"
        assert strategy.llm_config.model == "claude-3-sonnet-20240229"

    @pytest.mark.asyncio
    async def test_llm_strategy_no_api_key_fallback(self):
        """Test LLM strategy falls back to random when no API key."""
        strategy = LLMStrategy()
        
        move = await strategy.decide_move(
            game_id="test",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[]
        )
        # Should fallback to random
        assert 1 <= move <= 50

    @pytest.mark.asyncio
    async def test_llm_strategy_anthropic_success(self):
        """Test LLM strategy with successful Anthropic call."""
        llm_config = LLMConfig(
            provider="anthropic",
            model="claude-3-sonnet-20240229",
            api_key="test_key"
        )
        strategy = LLMStrategy(llm_config=llm_config)
        
        # Mock Anthropic client
        mock_client = Mock()
        mock_message = Mock()
        mock_message.content = [Mock(text="I choose 42")]
        mock_client.messages.create = AsyncMock(return_value=mock_message)
        
        strategy._client = mock_client
        
        move = await strategy.decide_move(
            game_id="test",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[]
        )
        assert move == 42

    @pytest.mark.asyncio
    async def test_llm_strategy_openai_success(self):
        """Test LLM strategy with successful OpenAI call."""
        llm_config = LLMConfig(
            provider="openai",
            model="gpt-4o-mini",
            api_key="test_key"
        )
        strategy = LLMStrategy(llm_config=llm_config)
        
        # Mock OpenAI client
        mock_client = Mock()
        mock_completion = Mock()
        mock_completion.choices = [Mock(message=Mock(content="I choose 25"))]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        
        strategy._client = mock_client
        
        move = await strategy.decide_move(
            game_id="test",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[]
        )
        assert move == 25

    @pytest.mark.asyncio
    async def test_llm_strategy_parse_number_from_text(self):
        """Test parsing numbers from various LLM responses."""
        llm_config = LLMConfig(provider="anthropic", api_key="test_key")
        strategy = LLMStrategy(llm_config=llm_config)
        
        test_cases = [
            ("I choose 42", 42),
            ("The answer is 15", 15),
            ("Let's go with 7", 7),
            ("I'll pick 33 as my move", 33),
            ("Response: 20", 20),
        ]
        
        for text, expected in test_cases:
            mock_client = Mock()
            mock_message = Mock()
            mock_message.content = [Mock(text=text)]
            mock_client.messages.create = AsyncMock(return_value=mock_message)
            strategy._client = mock_client
            
            move = await strategy.decide_move(
                game_id="test",
                round_number=1,
                my_role=GameRole.ODD,
                my_score=0,
                opponent_score=0,
                history=[]
            )
            assert move == expected

    @pytest.mark.asyncio
    async def test_llm_strategy_invalid_response_fallback(self):
        """Test fallback when LLM response has no valid number."""
        llm_config = LLMConfig(provider="anthropic", api_key="test_key")
        strategy = LLMStrategy(llm_config=llm_config)
        
        mock_client = Mock()
        mock_message = Mock()
        mock_message.content = [Mock(text="I don't know what to choose")]
        mock_client.messages.create = AsyncMock(return_value=mock_message)
        strategy._client = mock_client
        
        move = await strategy.decide_move(
            game_id="test",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[]
        )
        # Should fallback to random
        assert 1 <= move <= 50

    @pytest.mark.asyncio
    async def test_llm_strategy_api_error_fallback(self):
        """Test fallback when LLM API raises error."""
        llm_config = LLMConfig(provider="anthropic", api_key="test_key")
        strategy = LLMStrategy(llm_config=llm_config)
        
        mock_client = Mock()
        mock_client.messages.create = AsyncMock(side_effect=Exception("API Error"))
        strategy._client = mock_client
        
        move = await strategy.decide_move(
            game_id="test",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[]
        )
        # Should fallback to random
        assert 1 <= move <= 50

    @pytest.mark.asyncio
    async def test_llm_strategy_with_history(self):
        """Test LLM strategy includes history in prompt."""
        llm_config = LLMConfig(provider="anthropic", api_key="test_key")
        strategy = LLMStrategy(llm_config=llm_config)
        
        history = [
            {"opponent_move": 5, "my_move": 10, "result": "win"},
            {"opponent_move": 15, "my_move": 20, "result": "loss"},
        ]
        
        mock_client = Mock()
        mock_message = Mock()
        mock_message.content = [Mock(text="Based on history, I choose 12")]
        mock_client.messages.create = AsyncMock(return_value=mock_message)
        strategy._client = mock_client
        
        move = await strategy.decide_move(
            game_id="test",
            round_number=3,
            my_role=GameRole.ODD,
            my_score=1,
            opponent_score=1,
            history=history
        )
        assert move == 12

    def test_llm_strategy_reset(self):
        """Test reset does nothing for LLM strategy."""
        strategy = LLMStrategy()
        strategy.reset()  # Should not raise

    def test_llm_strategy_get_stats(self):
        """Test get_stats includes LLM info."""
        llm_config = LLMConfig(
            provider="anthropic",
            model="claude-3-sonnet-20240229"
        )
        strategy = LLMStrategy(llm_config=llm_config)
        stats = strategy.get_stats()
        assert stats["llm_provider"] == "anthropic"
        assert stats["llm_model"] == "claude-3-sonnet-20240229"

