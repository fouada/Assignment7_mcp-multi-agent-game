"""
Comprehensive tests for AnalyticsEngine to increase coverage.
"""

from src.visualization.analytics import (
    AnalyticsEngine,
    CounterfactualAnalysis,
    GameState,
    MatchupMatrix,
    OpponentModel,
    StrategyAnalytics,
    get_analytics_engine,
)


class TestAnalyticsEngineCore:
    """Test core analytics engine functionality."""

    def test_singleton_pattern(self):
        """Test that analytics engine is a singleton."""
        engine1 = get_analytics_engine()
        engine2 = get_analytics_engine()
        assert engine1 is engine2

    def test_register_player_basic(self):
        """Test basic player registration."""
        engine = AnalyticsEngine()
        engine.reset()

        engine.register_player("P1", "random")
        assert "P1" in engine.player_strategies
        assert engine.player_strategies["P1"] == "random"

    def test_register_player_multiple(self):
        """Test registering multiple players."""
        engine = AnalyticsEngine()
        engine.reset()

        for i in range(10):
            engine.register_player(f"P{i}", "adaptive")

        assert len(engine.player_strategies) == 10
        assert all(engine.player_strategies[f"P{i}"] == "adaptive" for i in range(10))

    def test_update_strategy_performance(self):
        """Test updating strategy performance."""
        engine = AnalyticsEngine()
        engine.reset()
        engine.register_player("P1", "random")

        engine.update_strategy_performance("P1", "random", won=True, score=5)
        engine.update_strategy_performance("P1", "random", won=False, score=3)

        assert len(engine.strategy_performance["random"]) == 2

    def test_record_match_outcome(self):
        """Test recording match outcomes."""
        engine = AnalyticsEngine()
        engine.reset()

        engine.register_player("P1", "random")
        engine.register_player("P2", "adaptive")

        engine.record_match_outcome(
            player_a="P1",
            player_b="P2",
            winner="P1",
            score_a=5,
            score_b=3,
            moves_a=[1, 2, 3],
            moves_b=[2, 3, 4]
        )

        assert ("P1", "P2") in engine.matchup_matrix or ("P2", "P1") in engine.matchup_matrix

    def test_get_opponent_model(self):
        """Test getting opponent model."""
        engine = AnalyticsEngine()
        engine.reset()

        engine.register_player("P1", "random")
        engine.register_player("P2", "adaptive")

        engine.record_match_outcome(
            player_a="P1",
            player_b="P2",
            winner="P1",
            score_a=5,
            score_b=3,
            moves_a=[1, 2, 3],
            moves_b=[2, 3, 4]
        )

        model = engine.get_opponent_model("P1", "P2")
        assert model is not None
        assert isinstance(model, OpponentModel)

    def test_get_opponent_model_nonexistent(self):
        """Test getting opponent model for nonexistent player."""
        engine = AnalyticsEngine()
        engine.reset()

        model = engine.get_opponent_model("P1", "P2")
        assert model is None


class TestStrategyAnalytics:
    """Test strategy analytics functionality."""

    def test_get_strategy_analytics(self):
        """Test getting strategy analytics."""
        engine = AnalyticsEngine()
        engine.reset()

        engine.register_player("P1", "random")
        engine.register_player("P2", "random")

        for _ in range(5):
            engine.update_strategy_performance("P1", "random", won=True, score=5)
            engine.update_strategy_performance("P2", "random", won=False, score=3)

        analytics = engine.get_strategy_analytics("random")
        assert analytics is not None
        assert isinstance(analytics, StrategyAnalytics)
        assert analytics.strategy_name == "random"

    def test_get_all_strategy_analytics(self):
        """Test getting all strategy analytics."""
        engine = AnalyticsEngine()
        engine.reset()

        engine.register_player("P1", "random")
        engine.register_player("P2", "adaptive")
        engine.register_player("P3", "nash")

        engine.update_strategy_performance("P1", "random", won=True, score=5)
        engine.update_strategy_performance("P2", "adaptive", won=True, score=5)
        engine.update_strategy_performance("P3", "nash", won=True, score=5)

        all_analytics = engine.get_all_strategy_analytics()
        assert len(all_analytics) == 3
        assert all(isinstance(a, StrategyAnalytics) for a in all_analytics)

    def test_get_strategy_comparison(self):
        """Test strategy comparison."""
        engine = AnalyticsEngine()
        engine.reset()

        engine.register_player("P1", "random")
        engine.register_player("P2", "adaptive")

        for _ in range(5):
            engine.update_strategy_performance("P1", "random", won=True, score=5)
            engine.update_strategy_performance("P2", "adaptive", won=False, score=3)

        comparison = engine.get_strategy_comparison(["random", "adaptive"])
        assert "random" in comparison
        assert "adaptive" in comparison


class TestMatchupMatrix:
    """Test matchup matrix functionality."""

    def test_get_matchup_matrix(self):
        """Test getting matchup matrix."""
        engine = AnalyticsEngine()
        engine.reset()

        engine.register_player("P1", "random")
        engine.register_player("P2", "adaptive")

        engine.record_match_outcome(
            player_a="P1",
            player_b="P2",
            winner="P1",
            score_a=5,
            score_b=3,
            moves_a=[1, 2, 3],
            moves_b=[2, 3, 4]
        )

        matrix = engine.get_matchup_matrix()
        assert isinstance(matrix, MatchupMatrix)
        assert len(matrix.players) == 2

    def test_get_head_to_head_stats(self):
        """Test getting head-to-head stats."""
        engine = AnalyticsEngine()
        engine.reset()

        engine.register_player("P1", "random")
        engine.register_player("P2", "adaptive")

        for _ in range(5):
            engine.record_match_outcome(
                player_a="P1",
                player_b="P2",
                winner="P1",
                score_a=5,
                score_b=3,
                moves_a=[1, 2, 3],
                moves_b=[2, 3, 4]
            )

        stats = engine.get_head_to_head_stats("P1", "P2")
        assert stats is not None
        assert stats["total_matches"] == 5


class TestCounterfactualAnalysis:
    """Test counterfactual analysis functionality."""

    def test_analyze_counterfactual_basic(self):
        """Test basic counterfactual analysis."""
        engine = AnalyticsEngine()
        engine.reset()

        engine.register_player("P1", "random")

        analysis = engine.analyze_counterfactual(
            player_id="P1",
            actual_move=5,
            opponent_move=3,
            actual_won=True
        )

        assert isinstance(analysis, CounterfactualAnalysis)
        assert analysis.player_id == "P1"

    def test_get_counterfactual_summary(self):
        """Test getting counterfactual summary."""
        engine = AnalyticsEngine()
        engine.reset()

        engine.register_player("P1", "random")

        for move in range(1, 6):
            engine.analyze_counterfactual(
                player_id="P1",
                actual_move=move,
                opponent_move=3,
                actual_won=(move + 3) % 2 == 1
            )

        summary = engine.get_counterfactual_summary("P1")
        assert summary is not None
        assert "total_analyses" in summary


class TestReplaySystem:
    """Test replay system functionality."""

    def test_capture_game_state(self):
        """Test capturing game state."""
        engine = AnalyticsEngine()
        engine.reset()

        state = GameState(
            round_number=1,
            player_scores={"P1": 5, "P2": 3},
            active_matches=[],
            recent_events=[]
        )

        engine.capture_game_state(state)
        assert len(engine.replay_history) == 1

    def test_get_replay_history(self):
        """Test getting replay history."""
        engine = AnalyticsEngine()
        engine.reset()

        for i in range(10):
            state = GameState(
                round_number=i,
                player_scores={"P1": i, "P2": i + 1},
                active_matches=[],
                recent_events=[]
            )
            engine.capture_game_state(state)

        history = engine.get_replay_history(0, 5)
        assert len(history) <= 6  # 0 to 5 inclusive

    def test_get_replay_at_round(self):
        """Test getting replay at specific round."""
        engine = AnalyticsEngine()
        engine.reset()

        for i in range(10):
            state = GameState(
                round_number=i,
                player_scores={"P1": i, "P2": i + 1},
                active_matches=[],
                recent_events=[]
            )
            engine.capture_game_state(state)

        replay = engine.get_replay_at_round(5)
        assert replay is not None
        assert replay.round_number == 5


class TestPerformanceMetrics:
    """Test performance metrics functionality."""

    def test_get_performance_summary(self):
        """Test getting performance summary."""
        engine = AnalyticsEngine()
        engine.reset()

        engine.register_player("P1", "random")
        engine.register_player("P2", "adaptive")

        for _ in range(10):
            engine.update_strategy_performance("P1", "random", won=True, score=5)
            engine.update_strategy_performance("P2", "adaptive", won=False, score=3)

        summary = engine.get_performance_summary()
        assert "total_players" in summary
        assert "total_strategies" in summary

    def test_get_top_performers(self):
        """Test getting top performers."""
        engine = AnalyticsEngine()
        engine.reset()

        for i in range(5):
            engine.register_player(f"P{i}", "random")
            for _ in range(i + 1):
                engine.update_strategy_performance(f"P{i}", "random", won=True, score=5)

        top = engine.get_top_performers(n=3)
        assert len(top) <= 3


class TestDataExport:
    """Test data export functionality."""

    def test_export_analytics_data(self):
        """Test exporting analytics data."""
        engine = AnalyticsEngine()
        engine.reset()

        engine.register_player("P1", "random")
        engine.update_strategy_performance("P1", "random", won=True, score=5)

        data = engine.export_analytics_data()
        assert "player_strategies" in data
        assert "strategy_performance" in data

    def test_import_analytics_data(self):
        """Test importing analytics data."""
        engine = AnalyticsEngine()
        engine.reset()

        data = {
            "player_strategies": {"P1": "random"},
            "strategy_performance": {},
            "matchup_matrix": {},
            "opponent_models": {}
        }

        engine.import_analytics_data(data)
        assert "P1" in engine.player_strategies


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_register_same_player_twice(self):
        """Test registering the same player twice."""
        engine = AnalyticsEngine()
        engine.reset()

        engine.register_player("P1", "random")
        engine.register_player("P1", "adaptive")  # Should update

        assert engine.player_strategies["P1"] == "adaptive"

    def test_record_match_with_draw(self):
        """Test recording a match with a draw."""
        engine = AnalyticsEngine()
        engine.reset()

        engine.register_player("P1", "random")
        engine.register_player("P2", "adaptive")

        engine.record_match_outcome(
            player_a="P1",
            player_b="P2",
            winner=None,  # Draw
            score_a=5,
            score_b=5,
            moves_a=[1, 2, 3],
            moves_b=[2, 3, 4]
        )

        stats = engine.get_head_to_head_stats("P1", "P2")
        assert stats is not None

    def test_empty_analytics(self):
        """Test analytics with no data."""
        engine = AnalyticsEngine()
        engine.reset()

        analytics = engine.get_strategy_analytics("nonexistent")
        assert analytics is None

        all_analytics = engine.get_all_strategy_analytics()
        assert len(all_analytics) == 0

    def test_reset_clears_all_data(self):
        """Test that reset clears all data."""
        engine = AnalyticsEngine()
        engine.reset()

        engine.register_player("P1", "random")
        engine.update_strategy_performance("P1", "random", won=True, score=5)

        engine.reset()

        assert len(engine.player_strategies) == 0
        assert len(engine.strategy_performance) == 0
        assert len(engine.matchup_matrix) == 0

