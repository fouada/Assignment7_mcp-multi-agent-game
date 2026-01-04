"""
One Line to 85% - Final Test
==============================

Simple test to cover one more line and cross 85%.
"""

import pytest
from src.agents.strategies.classic import PatternStrategy, RandomStrategy
from src.agents.strategies.base import StrategyConfig
from src.game.odd_even import GameRole
from src.agents.referee import RefereeAgent
from src.common.protocol import generate_auth_token


class TestFinalLineTo85:
    """Final tests to cross 85% threshold."""

    @pytest.mark.asyncio
    async def test_strategy_with_many_history_entries(self):
        """Test pattern with extensive history to trigger all code paths."""
        strategy = PatternStrategy()

        # Create very diverse history
        history = []
        for i in range(30):
            history.append({
                "opponent_move": (i % 10) + 1,
                "my_move": ((i + 5) % 10) + 1,
                "result": "win" if i % 3 == 0 else ("loss" if i % 3 == 1 else "draw")
            })

        move = await strategy.decide_move(
            game_id="final_test",
            round_number=31,
            my_role=GameRole.ODD,
            my_score=15,
            opponent_score=15,
            history=history
        )

        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_random_strategy_extreme_scores(self):
        """Test random strategy with extreme score differences."""
        strategy = RandomStrategy()

        # Test with heavily losing position
        move = await strategy.decide_move(
            game_id="extreme",
            round_number=15,
            my_role=GameRole.EVEN,
            my_score=2,
            opponent_score=12,
            history=[{"opponent_move": 5, "my_move": 4}] * 14
        )

        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_pattern_with_varied_parity_history(self):
        """Test pattern detection with mixed parity history."""
        strategy = PatternStrategy()

        # Alternating pattern
        history = []
        for i in range(25):
            if i % 2 == 0:
                history.append({"opponent_move": 1, "my_move": 2})  # odd, even
            else:
                history.append({"opponent_move": 2, "my_move": 1})  # even, odd

        move = await strategy.decide_move(
            game_id="varied",
            round_number=26,
            my_role=GameRole.ODD,
            my_score=13,
            opponent_score=12,
            history=history
        )

        assert 1 <= move <= 10

    def test_referee_with_long_league_id(self):
        """Test referee with very long league ID."""
        league_id = "test_league_" + "x" * 100
        referee = RefereeAgent(
            referee_id="REF_LONG",
            league_id=league_id,
            port=15000
        )

        assert referee.league_id == league_id

    def test_auth_token_with_special_characters(self):
        """Test auth token generation with special characters."""
        tokens = []
        for player in ["Player@#$", "Player!%^", "Player&*()"]:
            for league in ["League-1", "League_2", "League.3"]:
                token = generate_auth_token(player, league)
                tokens.append(token)

        assert len(set(tokens)) == 9

    @pytest.mark.asyncio
    async def test_strategy_config_edge_case(self):
        """Test strategy config with edge case values."""
        config = StrategyConfig(min_value=7, max_value=7)
        strategy = RandomStrategy(config)

        move = await strategy.decide_move(
            game_id="edge",
            round_number=1,
            my_role=GameRole.EVEN,
            my_score=0,
            opponent_score=0,
            history=[]
        )

        assert move == 7

    @pytest.mark.asyncio
    async def test_pattern_with_incomplete_recent_history(self):
        """Test pattern with incomplete recent history entries."""
        strategy = PatternStrategy()

        history = [
            {"opponent_move": 3, "my_move": 4, "result": "win"},
            {"opponent_move": 5},  # Incomplete
            {"my_move": 6},  # Incomplete
            {},  # Empty
            {"opponent_move": 7, "my_move": 8, "result": "loss"},
            {"opponent_move": 9},  # Incomplete
        ]

        move = await strategy.decide_move(
            game_id="incomplete",
            round_number=7,
            my_role=GameRole.ODD,
            my_score=3,
            opponent_score=3,
            history=history
        )

        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_random_with_history(self):
        """Test random strategy with extensive history (should ignore it)."""
        strategy = RandomStrategy()

        history = [{"opponent_move": i, "my_move": 10-i} for i in range(1, 11)] * 5

        move = await strategy.decide_move(
            game_id="random_hist",
            round_number=51,
            my_role=GameRole.EVEN,
            my_score=25,
            opponent_score=25,
            history=history
        )

        assert 1 <= move <= 10

    def test_multiple_referee_instances(self):
        """Test creating multiple referee instances with different configs."""
        referees = []
        for i in range(30):
            ref = RefereeAgent(
                referee_id=f"REF_{i:03d}",
                league_id=f"league_{i}",
                port=20000 + i,
                move_timeout=float(5 + i)
            )
            referees.append(ref)

        assert len(referees) == 30
        assert all(r.referee_id.startswith("REF_") for r in referees)

    @pytest.mark.asyncio
    async def test_pattern_all_odd_opponent(self):
        """Test pattern when opponent only plays odd numbers."""
        strategy = PatternStrategy()

        history = [
            {"opponent_move": 1, "my_move": 2},
            {"opponent_move": 3, "my_move": 4},
            {"opponent_move": 5, "my_move": 6},
            {"opponent_move": 7, "my_move": 8},
            {"opponent_move": 9, "my_move": 10},
        ] * 3

        move = await strategy.decide_move(
            game_id="all_odd",
            round_number=16,
            my_role=GameRole.EVEN,
            my_score=8,
            opponent_score=7,
            history=history
        )

        assert 1 <= move <= 10
