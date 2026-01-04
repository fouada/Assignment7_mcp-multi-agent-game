"""
Final Coverage Push: 82% → 85%
================================

Highly targeted tests using correct APIs to cover specific missing lines
in the highest-impact modules.

Target modules:
- src/agents/referee.py (71.30% → 85%)
- src/agents/strategies/classic.py (74.10% → 85%)
- src/observability/health.py (75.75% → 85%)
"""

from unittest.mock import Mock

import pytest

from src.agents.referee import RefereeAgent
from src.agents.strategies.base import StrategyConfig
from src.agents.strategies.classic import PatternStrategy, RandomStrategy
from src.common.config import Config
from src.game.odd_even import GameRole
from src.observability.health import HealthMonitor

# ==============================================================================
# Simple Targeted Tests for Remaining Coverage
# ==============================================================================


class TestRefereeSimple:
    """Simple referee tests for remaining coverage."""

    def test_referee_with_custom_league_id(self):
        """Test referee with custom league_id."""
        referee = RefereeAgent(
            referee_id="REF1",
            league_id="custom_league",
            port=9500,
        )

        assert referee.league_id == "custom_league"

    def test_referee_with_custom_move_timeout(self):
        """Test referee with custom move timeout."""
        referee = RefereeAgent(
            referee_id="REF2",
            port=9501,
            move_timeout=30.0,
        )

        assert referee.move_timeout == 30.0

    def test_referee_with_custom_league_manager_url(self):
        """Test referee with custom league manager URL."""
        referee = RefereeAgent(
            referee_id="REF3",
            port=9502,
            league_manager_url="http://custom-league:8000/mcp",
        )

        assert referee.league_manager_url == "http://custom-league:8000/mcp"

    def test_referee_default_values(self):
        """Test referee uses default values correctly."""
        referee = RefereeAgent(referee_id="REF4", port=9503)

        # Test defaults
        assert referee.referee_id == "REF4"
        assert referee.port == 9503
        assert len(referee._sessions) == 0
        assert len(referee._player_connections) == 0


class TestStrategyVariations:
    """Test strategy variations for coverage."""

    @pytest.mark.asyncio
    async def test_random_strategy_multiple_calls(self):
        """Test random strategy called multiple times."""
        config = StrategyConfig(min_value=1, max_value=10)
        strategy = RandomStrategy(config)

        # Call multiple times
        moves = []
        for i in range(10):
            move = await strategy.decide_move(
                game_id=f"game_{i}",
                round_number=i + 1,
                my_role=GameRole.ODD,
                my_score=i,
                opponent_score=i - 1,
                history=[],
            )
            moves.append(move)

        # All should be valid
        assert all(1 <= m <= 10 for m in moves)
        assert len(moves) == 10

    @pytest.mark.asyncio
    async def test_pattern_strategy_with_consistent_opponent(self):
        """Test pattern strategy with consistent opponent behavior."""
        strategy = PatternStrategy()

        # Opponent always plays odd
        history = []
        for i in range(8):
            history.append({
                "opponent_move": 2 * i + 1,  # Always odd
                "my_move": 2 * i + 2,  # Always even
                "result": "win" if i % 2 == 0 else "loss"
            })

        move = await strategy.decide_move(
            game_id="test",
            round_number=9,
            my_role=GameRole.EVEN,
            my_score=4,
            opponent_score=4,
            history=history,
        )

        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_pattern_strategy_reset(self):
        """Test pattern strategy reset functionality."""
        strategy = PatternStrategy()

        # Use strategy
        await strategy.decide_move(
            game_id="test",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[],
        )

        # Reset
        strategy.reset()

        # Should work after reset
        move = await strategy.decide_move(
            game_id="test2",
            round_number=1,
            my_role=GameRole.EVEN,
            my_score=0,
            opponent_score=0,
            history=[],
        )

        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_random_strategy_with_score_variations(self):
        """Test random strategy with various score combinations."""
        strategy = RandomStrategy()

        # Test with different scores
        scores = [(0, 0), (5, 3), (10, 10), (2, 8)]

        for my_score, opp_score in scores:
            move = await strategy.decide_move(
                game_id="test",
                round_number=1,
                my_role=GameRole.ODD,
                my_score=my_score,
                opponent_score=opp_score,
                history=[],
            )

            assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_pattern_strategy_with_alternating_results(self):
        """Test pattern with alternating win/loss results."""
        strategy = PatternStrategy()

        history = []
        for i in range(6):
            history.append({
                "opponent_move": 5,
                "my_move": 4 + (i % 2),
                "result": "win" if i % 2 == 0 else "loss"
            })

        move = await strategy.decide_move(
            game_id="test",
            round_number=7,
            my_role=GameRole.ODD,
            my_score=3,
            opponent_score=3,
            history=history,
        )

        assert 1 <= move <= 10


class TestHealthMonitorSimple:
    """Simple health monitor tests."""

    def test_health_monitor_initialization(self):
        """Test health monitor initializes correctly."""
        monitor = HealthMonitor()

        # Should initialize without error
        assert monitor is not None

    @pytest.mark.asyncio
    async def test_health_monitor_with_custom_check(self):
        """Test adding custom health check."""
        monitor = HealthMonitor()

        async def custom_check():
            return {"status": "healthy"}

        # Create mock check
        check = Mock()
        check.check = custom_check
        check.name = "custom"

        # Add check
        monitor.add_check("custom", check)

        # Verify check was added
        assert "custom" in monitor._checks

    def test_health_monitor_remove_nonexistent_check(self):
        """Test removing check that doesn't exist."""
        monitor = HealthMonitor()

        # Should not raise error
        result = monitor.remove_check("nonexistent")

        assert result is False


class TestConfigurationCoverage:
    """Test configuration variations."""

    def test_config_default_instantiation(self):
        """Test Config creates with defaults."""
        config = Config()

        assert config is not None
        assert hasattr(config, "league_manager")
        assert hasattr(config, "game")

    def test_strategy_config_with_custom_values(self):
        """Test StrategyConfig with custom values."""
        config = StrategyConfig(
            min_value=5,
            max_value=15,
        )

        assert config.min_value == 5
        assert config.max_value == 15

    def test_strategy_config_defaults(self):
        """Test StrategyConfig default values."""
        config = StrategyConfig()

        assert config.min_value == 1
        assert config.max_value == 10


class TestStrategyBoundaryConditions:
    """Test strategies at boundary conditions."""

    @pytest.mark.asyncio
    async def test_strategy_at_min_value_boundary(self):
        """Test strategy when forced to minimum value."""
        config = StrategyConfig(min_value=1, max_value=1)
        strategy = RandomStrategy(config)

        move = await strategy.decide_move(
            game_id="test",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[],
        )

        assert move == 1

    @pytest.mark.asyncio
    async def test_strategy_at_max_value_boundary(self):
        """Test strategy with max value only."""
        config = StrategyConfig(min_value=10, max_value=10)
        strategy = RandomStrategy(config)

        move = await strategy.decide_move(
            game_id="test",
            round_number=1,
            my_role=GameRole.EVEN,
            my_score=0,
            opponent_score=0,
            history=[],
        )

        assert move == 10

    @pytest.mark.asyncio
    async def test_pattern_with_very_long_history(self):
        """Test pattern strategy with long history."""
        strategy = PatternStrategy()

        # Create long history
        history = []
        for i in range(50):
            history.append({
                "opponent_move": (i % 10) + 1,
                "my_move": ((i + 1) % 10) + 1,
                "result": "win" if i % 3 == 0 else "loss"
            })

        move = await strategy.decide_move(
            game_id="test",
            round_number=51,
            my_role=GameRole.ODD,
            my_score=17,
            opponent_score=33,
            history=history,
        )

        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_strategy_with_tied_scores(self):
        """Test strategy behavior with tied scores."""
        strategy = RandomStrategy()

        for tied_score in [0, 5, 10, 15]:
            move = await strategy.decide_move(
                game_id=f"test_{tied_score}",
                round_number=10,
                my_role=GameRole.ODD,
                my_score=tied_score,
                opponent_score=tied_score,
                history=[],
            )

            assert 1 <= move <= 10


class TestStrategyStatsAndState:
    """Test strategy statistics and state management."""

    @pytest.mark.asyncio
    async def test_strategy_get_stats_after_use(self):
        """Test getting stats after strategy use."""
        strategy = RandomStrategy()

        # Use strategy
        for i in range(5):
            await strategy.decide_move(
                game_id="test",
                round_number=i + 1,
                my_role=GameRole.ODD,
                my_score=i,
                opponent_score=i,
                history=[],
            )

        # Get stats
        stats = strategy.get_stats()

        assert isinstance(stats, dict)

    @pytest.mark.asyncio
    async def test_pattern_strategy_state_persistence(self):
        """Test pattern strategy maintains state."""
        strategy = PatternStrategy()

        # First call
        await strategy.decide_move(
            game_id="test",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[{"opponent_move": 3}],
        )

        # Second call - state should persist
        move = await strategy.decide_move(
            game_id="test",
            round_number=2,
            my_role=GameRole.ODD,
            my_score=1,
            opponent_score=0,
            history=[
                {"opponent_move": 3},
                {"opponent_move": 7},
            ],
        )

        assert 1 <= move <= 10


class TestMultipleGameScenarios:
    """Test strategies across multiple games."""

    @pytest.mark.asyncio
    async def test_strategy_across_different_games(self):
        """Test strategy used for different games."""
        strategy = RandomStrategy()

        # Use for multiple games
        game_ids = ["game1", "game2", "game3", "game4", "game5"]

        for game_id in game_ids:
            move = await strategy.decide_move(
                game_id=game_id,
                round_number=1,
                my_role=GameRole.EVEN,
                my_score=0,
                opponent_score=0,
                history=[],
            )

            assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_pattern_strategy_different_roles(self):
        """Test pattern strategy as both ODD and EVEN."""
        strategy = PatternStrategy()

        # Play as ODD
        move_odd = await strategy.decide_move(
            game_id="test_odd",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[],
        )

        # Play as EVEN
        move_even = await strategy.decide_move(
            game_id="test_even",
            round_number=1,
            my_role=GameRole.EVEN,
            my_score=0,
            opponent_score=0,
            history=[],
        )

        assert 1 <= move_odd <= 10
        assert 1 <= move_even <= 10
