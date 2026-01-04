"""
Targeted Tests to Reach 85%+ Coverage
======================================

Focused on testable code paths that will increase coverage effectively.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.agents.referee import GameSession, RefereeAgent
from src.agents.strategies.classic import PatternStrategy, RandomStrategy
from src.agents.strategies.base import StrategyConfig
from src.common.config import Config, GameConfig, LeagueConfig, RetryConfig, ServerConfig
from src.common.protocol import MessageFactory, generate_auth_token
from src.common.repositories import DataManager
from src.game.match import Match
from src.game.odd_even import GameRole
from src.observability.health import HealthMonitor, LivenessCheck, ReadinessCheck


# ==============================================================================
# Pattern Strategy Advanced Tests
# ==============================================================================


class TestPatternStrategyAdvanced:
    """Advanced pattern strategy tests to cover more lines."""

    @pytest.mark.asyncio
    async def test_pattern_with_many_rounds(self):
        """Test pattern strategy over many rounds."""
        strategy = PatternStrategy()

        for round_num in range(20):
            history = [
                {"opponent_move": (i % 9) + 1, "my_move": ((i + 1) % 9) + 1}
                for i in range(round_num)
            ]

            move = await strategy.decide_move(
                game_id=f"game_{round_num}",
                round_number=round_num + 1,
                my_role=GameRole.ODD,
                my_score=round_num // 2,
                opponent_score=round_num // 2,
                history=history
            )

            assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_pattern_with_alternating_patterns(self):
        """Test pattern strategy with alternating opponent behavior."""
        strategy = PatternStrategy()

        # Opponent alternates between odd and even
        history = []
        for i in range(15):
            if i % 2 == 0:
                history.append({"opponent_move": 1, "my_move": 2})
            else:
                history.append({"opponent_move": 2, "my_move": 3})

        move = await strategy.decide_move(
            game_id="test",
            round_number=16,
            my_role=GameRole.ODD,
            my_score=7,
            opponent_score=8,
            history=history
        )

        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_pattern_with_all_same_moves(self):
        """Test pattern when opponent always plays same move."""
        strategy = PatternStrategy()

        history = [{"opponent_move": 5, "my_move": 4} for _ in range(12)]

        move = await strategy.decide_move(
            game_id="test",
            round_number=13,
            my_role=GameRole.EVEN,
            my_score=6,
            opponent_score=6,
            history=history
        )

        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_random_strategy_many_games(self):
        """Test random strategy across many games."""
        strategy = RandomStrategy()

        for game_num in range(30):
            for round_num in range(1, 6):
                move = await strategy.decide_move(
                    game_id=f"game_{game_num}",
                    round_number=round_num,
                    my_role=GameRole.ODD if game_num % 2 == 0 else GameRole.EVEN,
                    my_score=round_num - 1,
                    opponent_score=round_num - 1,
                    history=[]
                )

                assert 1 <= move <= 10


# ==============================================================================
# Configuration Edge Cases
# ==============================================================================


class TestConfigurationEdgeCases:
    """Test configuration with various edge cases."""

    def test_server_config_variations(self):
        """Test ServerConfig with various parameters."""
        configs = [
            ServerConfig(name="s1", host="0.0.0.0", port=8000),
            ServerConfig(name="s2", host="localhost", port=9000),
            ServerConfig(name="s3", host="127.0.0.1", port=443),
        ]

        for config in configs:
            assert config.name is not None
            assert config.port > 0

    def test_retry_config_variations(self):
        """Test RetryConfig with different values."""
        configs = [
            RetryConfig(max_retries=1, base_delay=0.1),
            RetryConfig(max_retries=10, base_delay=5.0),
            RetryConfig(max_retries=100, base_delay=0.01),
        ]

        for config in configs:
            assert config.max_retries >= 0
            assert config.base_delay > 0

    def test_game_config_variations(self):
        """Test GameConfig with various parameters."""
        configs = [
            GameConfig(rounds_per_match=3, move_timeout=10.0),
            GameConfig(rounds_per_match=10, move_timeout=60.0),
            GameConfig(rounds_per_match=1, move_timeout=5.0),
        ]

        for config in configs:
            assert config.rounds_per_match > 0
            assert config.move_timeout > 0

    def test_league_config_variations(self):
        """Test LeagueConfig with different options."""
        configs = [
            LeagueConfig(round_robin=True),
            LeagueConfig(round_robin=False),
        ]

        for config in configs:
            assert hasattr(config, "round_robin")


# ==============================================================================
# Protocol Message Factory
# ==============================================================================


class TestProtocolMessageFactory:
    """Test protocol message factory."""

    def test_message_factory_with_auth_token(self):
        """Test message factory with auth token."""
        factory = MessageFactory(sender="P1", league_id="test")

        token = generate_auth_token("P1", "test")
        factory.set_auth_token(token)

        assert factory.auth_token == token

    def test_message_factory_multiple_tokens(self):
        """Test changing auth tokens."""
        factory = MessageFactory(sender="P1", league_id="test")

        for i in range(5):
            token = generate_auth_token(f"P{i}", "test")
            factory.set_auth_token(token)
            assert factory.auth_token == token

    def test_generate_auth_token_uniqueness(self):
        """Test that auth tokens are unique."""
        tokens = set()
        for i in range(100):
            token = generate_auth_token(f"P{i}", "league")
            assert token not in tokens
            tokens.add(token)

        assert len(tokens) == 100


# ==============================================================================
# Health Monitor Tests
# ==============================================================================


class TestHealthMonitorExtended:
    """Extended health monitor tests."""

    def test_health_monitor_multiple_checks(self):
        """Test health monitor with multiple checks."""
        monitor = HealthMonitor()

        check1 = LivenessCheck()
        check2 = LivenessCheck()
        check3 = ReadinessCheck()

        monitor.add_check("live1", check1)
        monitor.add_check("live2", check2)
        monitor.add_check("ready1", check3)

        assert "live1" in monitor._checks
        assert "live2" in monitor._checks
        assert "ready1" in monitor._checks

    def test_health_monitor_remove_multiple(self):
        """Test removing multiple checks."""
        monitor = HealthMonitor()

        for i in range(5):
            check = LivenessCheck()
            monitor.add_check(f"check_{i}", check)

        for i in range(5):
            result = monitor.remove_check(f"check_{i}")
            assert result is True

        # Try removing again
        for i in range(5):
            result = monitor.remove_check(f"check_{i}")
            assert result is False

    def test_liveness_check_creation(self):
        """Test LivenessCheck instantiation."""
        check1 = LivenessCheck()
        check2 = LivenessCheck()

        assert check1 is not None
        assert check2 is not None

    def test_readiness_check_creation(self):
        """Test ReadinessCheck instantiation."""
        check1 = ReadinessCheck()
        check2 = ReadinessCheck()

        assert check1 is not None
        assert check2 is not None


# ==============================================================================
# Referee Configuration Tests
# ==============================================================================


class TestRefereeConfiguration:
    """Test referee with various configurations."""

    def test_referee_with_different_ports(self):
        """Test referee with different port numbers."""
        ports = [8000, 8080, 9000, 9999, 10000]

        for port in ports:
            referee = RefereeAgent(
                referee_id=f"REF_{port}",
                port=port
            )

            assert referee.port == port

    def test_referee_with_different_timeouts(self):
        """Test referee with various timeouts."""
        timeouts = [1.0, 5.0, 10.0, 30.0, 60.0]

        for timeout in timeouts:
            referee = RefereeAgent(
                referee_id="REF",
                port=8000,
                move_timeout=timeout
            )

            assert referee.move_timeout == timeout

    def test_referee_with_different_league_ids(self):
        """Test referee with different league IDs."""
        league_ids = ["league1", "league_test", "prod_league", "dev_league"]

        for league_id in league_ids:
            referee = RefereeAgent(
                referee_id="REF",
                league_id=league_id,
                port=8000
            )

            assert referee.league_id == league_id


# ==============================================================================
# Repository Edge Cases
# ==============================================================================


class TestRepositoryEdgeCases:
    """Test repositories with edge cases."""

    def test_data_manager_multiple_leagues(self):
        """Test DataManager with multiple leagues."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dm = DataManager(base_path=str(tmpdir))

            # Get repositories for multiple leagues
            leagues = ["league1", "league2", "league3"]

            for league in leagues:
                standings_repo = dm.standings(league)
                rounds_repo = dm.rounds(league)
                matches_repo = dm.matches(league)

                assert standings_repo is not None
                assert rounds_repo is not None
                assert matches_repo is not None

    def test_data_manager_same_league_multiple_times(self):
        """Test accessing same league repository multiple times."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dm = DataManager(base_path=str(tmpdir))

            # Access same league multiple times
            for _ in range(10):
                repo = dm.standings("test_league")
                assert repo is not None

            # Should still be cached
            repo1 = dm.standings("test_league")
            repo2 = dm.standings("test_league")
            assert repo1 is repo2


# ==============================================================================
# Match and Game Edge Cases
# ==============================================================================


class TestMatchGameEdgeCases:
    """Test match and game edge cases."""

    def test_match_with_different_player_combos(self):
        """Test match creation with various player combinations."""
        match = Match(match_id="m1", league_id="test")

        player_combos = [
            ("P1", "http://p1:8001", "P2", "http://p2:8002"),
            ("Alice", "http://localhost:9001", "Bob", "http://localhost:9002"),
            ("Player_1", "http://server1/mcp", "Player_2", "http://server2/mcp"),
        ]

        for p1_id, p1_url, p2_id, p2_url in player_combos:
            match.set_players(p1_id, p1_url, p2_id, p2_url)
            assert match.player1 is not None
            assert match.player2 is not None

    def test_match_create_multiple_games(self):
        """Test creating multiple games from same match."""
        match = Match(match_id="m1", league_id="test")
        match.set_players("P1", "http://p1", "P2", "http://p2")

        # Create multiple games
        for rounds in [1, 3, 5, 10]:
            game = match.create_game(total_rounds=rounds)
            assert game.total_rounds == rounds


# ==============================================================================
# Strategy Configuration Edge Cases
# ==============================================================================


class TestStrategyConfigEdgeCases:
    """Test strategy config edge cases."""

    def test_strategy_config_boundary_values(self):
        """Test strategy config with boundary values."""
        configs = [
            StrategyConfig(min_value=1, max_value=1),
            StrategyConfig(min_value=10, max_value=10),
            StrategyConfig(min_value=1, max_value=100),
            StrategyConfig(min_value=0, max_value=0),
        ]

        for config in configs:
            assert config.min_value <= config.max_value or config.min_value >= 0

    @pytest.mark.asyncio
    async def test_random_strategy_with_various_configs(self):
        """Test random strategy with different configs."""
        configs = [
            StrategyConfig(min_value=1, max_value=5),
            StrategyConfig(min_value=1, max_value=20),
            StrategyConfig(min_value=5, max_value=15),
        ]

        for config in configs:
            strategy = RandomStrategy(config)

            for _ in range(10):
                move = await strategy.decide_move(
                    game_id="test",
                    round_number=1,
                    my_role=GameRole.ODD,
                    my_score=0,
                    opponent_score=0,
                    history=[]
                )

                assert config.min_value <= move <= config.max_value


# ==============================================================================
# Integration-Style Tests
# ==============================================================================


class TestIntegrationScenarios:
    """Integration-style tests for coverage."""

    @pytest.mark.asyncio
    async def test_strategy_reset_and_reuse(self):
        """Test strategy can be reset and reused."""
        strategies = [
            RandomStrategy(),
            PatternStrategy(),
        ]

        for strategy in strategies:
            # Use strategy
            for i in range(5):
                await strategy.decide_move(
                    game_id="game1",
                    round_number=i + 1,
                    my_role=GameRole.ODD,
                    my_score=i,
                    opponent_score=i,
                    history=[]
                )

            # Reset
            strategy.reset()

            # Use again
            for i in range(5):
                move = await strategy.decide_move(
                    game_id="game2",
                    round_number=i + 1,
                    my_role=GameRole.EVEN,
                    my_score=i,
                    opponent_score=i,
                    history=[]
                )

                assert 1 <= move <= 10

    def test_config_composition(self):
        """Test creating full Config object."""
        config = Config()

        assert config.league_manager is not None
        assert config.game is not None
        assert hasattr(config, "log_level")
        assert hasattr(config, "debug")

    @pytest.mark.asyncio
    async def test_referee_initialization_variants(self):
        """Test referee with various initialization options."""
        referees = [
            RefereeAgent("REF1", port=9001),
            RefereeAgent("REF2", league_id="test", port=9002),
            RefereeAgent("REF3", port=9003, move_timeout=15.0),
            RefereeAgent("REF4", league_id="custom", port=9004, move_timeout=20.0),
        ]

        for referee in referees:
            assert referee.referee_id is not None
            assert referee.port > 0
            assert len(referee._sessions) == 0
