"""
Dashboard Integration with Innovation Systems
==============================================

**Purpose:**
Connects the real-time interactive dashboard with the three core innovation systems:
1. Opponent Modeling Engine - Stream belief updates and predictions
2. Counterfactual Reasoning Engine - Stream regret analysis
3. Hierarchical Strategy Composition - Stream strategy decisions

**Architecture:**
- Event-driven integration using the existing event bus
- Non-blocking async updates to dashboard
- Hooks into key decision points in agents
- Aggregates data for visualization

**Innovation:**
First real-time visualization of internal agent reasoning:
- See what agents believe about opponents (live)
- Watch regret accumulation and strategy updates
- Observe strategy composition decisions
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime

from ..agents.strategies.counterfactual_reasoning import (
    CounterfactualReasoningEngine,
)
from ..agents.strategies.hierarchical_composition import CompositeStrategy
from ..agents.strategies.opponent_modeling import OpponentModel, OpponentModelingEngine
from ..common.logger import get_logger
from .dashboard import (
    CounterfactualVisualization,
    DashboardAPI,
    GameEvent,
    OpponentModelVisualization,
    StrategyPerformance,
    get_dashboard,
)

logger = get_logger(__name__)


# ============================================================================
# Integration Data Aggregation
# ============================================================================


@dataclass
class PlayerDashboardState:
    """Aggregated dashboard state for a single player."""

    player_id: str
    strategy_name: str

    # Performance metrics
    total_rounds: int = 0
    total_wins: int = 0
    total_score: float = 0.0
    win_rate: float = 0.0
    avg_score_per_round: float = 0.0

    # Opponent modeling state
    opponent_models: dict[str, OpponentModel] = field(default_factory=dict)
    recent_predictions: list[dict] = field(default_factory=list)

    # Counterfactual state
    recent_regrets: list[dict] = field(default_factory=list)
    cumulative_regret: dict[str, float] = field(default_factory=dict)

    # Strategy composition state
    strategy_tree: str | None = None
    component_usage: dict[str, int] = field(default_factory=dict)

    # History for charts
    round_history: list[int] = field(default_factory=list)
    score_history: list[float] = field(default_factory=list)
    win_rate_history: list[float] = field(default_factory=list)


@dataclass
class TournamentDashboardState:
    """Aggregated dashboard state for entire tournament."""

    tournament_id: str
    start_time: datetime
    current_round: int = 0
    total_rounds: int = 0

    # Player states
    players: dict[str, PlayerDashboardState] = field(default_factory=dict)

    # Match history
    matches: list[dict] = field(default_factory=list)

    # Real-time events
    event_buffer: list[GameEvent] = field(default_factory=list)
    max_buffer_size: int = 100


# ============================================================================
# Dashboard Integration Manager
# ============================================================================


class DashboardIntegration:
    """
    Manages integration between game engines and dashboard.

    **Responsibilities:**
    - Listen to game events via event bus
    - Aggregate data from innovation engines
    - Stream updates to dashboard via WebSocket
    - Maintain state for visualization

    **Usage:**
    ```python
    integration = DashboardIntegration()
    await integration.start()

    # Hooks are automatically registered with event bus
    # Dashboard receives real-time updates automatically
    ```
    """

    def __init__(self, dashboard: DashboardAPI | None = None):
        self.dashboard = dashboard or get_dashboard()
        self.tournament_state: TournamentDashboardState | None = None
        self.enabled = False

        # Track innovation engines per player
        self.opponent_modeling_engines: dict[str, OpponentModelingEngine] = {}
        self.cfr_engines: dict[str, CounterfactualReasoningEngine] = {}
        self.strategy_compositions: dict[str, CompositeStrategy] = {}

        logger.info("DashboardIntegration initialized")

    async def start(self, tournament_id: str, total_rounds: int):
        """Start dashboard integration for a tournament."""
        self.enabled = True

        # Initialize tournament state
        self.tournament_state = TournamentDashboardState(
            tournament_id=tournament_id, start_time=datetime.now(), total_rounds=total_rounds
        )

        # Start dashboard server (non-blocking)
        asyncio.create_task(self.dashboard.start_server())

        logger.info(f"Dashboard integration started for tournament {tournament_id}")

    async def stop(self):
        """Stop dashboard integration."""
        self.enabled = False
        logger.info("Dashboard integration stopped")

    # ========================================================================
    # Player Registration
    # ========================================================================

    def register_player(
        self,
        player_id: str,
        strategy_name: str,
        opponent_modeling_engine: OpponentModelingEngine | None = None,
        cfr_engine: CounterfactualReasoningEngine | None = None,
        strategy_composition: CompositeStrategy | None = None,
    ):
        """
        Register a player and their innovation engines with dashboard.

        This allows the dashboard to access internal agent state.
        """
        if not self.enabled:
            return

        # Create player state
        if self.tournament_state:
            self.tournament_state.players[player_id] = PlayerDashboardState(
                player_id=player_id, strategy_name=strategy_name
            )

        # Track engines
        if opponent_modeling_engine:
            self.opponent_modeling_engines[player_id] = opponent_modeling_engine

        if cfr_engine:
            self.cfr_engines[player_id] = cfr_engine

        if strategy_composition:
            self.strategy_compositions[player_id] = strategy_composition
            # Get strategy tree visualization
            tree = strategy_composition.get_composition_tree()
            if self.tournament_state:
                self.tournament_state.players[player_id].strategy_tree = tree

        logger.info(f"Registered player {player_id} with strategy {strategy_name}")

    # ========================================================================
    # Event Handlers - Game Events
    # ========================================================================

    async def on_round_start(self, round_num: int, matches: list[dict]):
        """Handle round start event."""
        if not self.enabled:
            return

        if self.tournament_state is None:
            return

        self.tournament_state.current_round = round_num

        # Create event
        event = GameEvent(
            timestamp=datetime.now().isoformat(),
            event_type="round_start",
            round=round_num,
            players=[],
            moves={},
            scores={},
            metadata={"matches": len(matches)},
        )

        # Stream to dashboard
        await self.dashboard.stream_event(event)

        logger.debug(f"Streamed round_start event for round {round_num}")

    async def on_move_decision(
        self, player_id: str, opponent_id: str, round_num: int, move: str, game_state: dict
    ):
        """Handle move decision event."""
        if not self.enabled:
            return

        # Create event
        event = GameEvent(
            timestamp=datetime.now().isoformat(),
            event_type="move",
            round=round_num,
            players=[player_id, opponent_id],
            moves={player_id: move},
            scores={},
            metadata={"game_state": game_state},
        )

        # Stream to dashboard
        await self.dashboard.stream_event(event)

        # Update opponent modeling visualization if available
        if player_id in self.opponent_modeling_engines:
            await self._update_opponent_model_viz(player_id, opponent_id)

        logger.debug(f"Streamed move event for player {player_id}")

    async def on_round_complete(
        self,
        round_num: int,
        player1_id: str,
        player2_id: str,
        moves: dict[str, str],
        scores: dict[str, float],
    ):
        """Handle round complete event."""
        if not self.enabled:
            return

        # Create event
        event = GameEvent(
            timestamp=datetime.now().isoformat(),
            event_type="round_end",
            round=round_num,
            players=[player1_id, player2_id],
            moves=moves,
            scores=scores,
            metadata={},
        )

        # Update player states
        if self.tournament_state is None:
            return

        for player_id in [player1_id, player2_id]:
            if player_id in self.tournament_state.players:
                state = self.tournament_state.players[player_id]
                state.total_rounds += 1
                state.total_score += scores.get(player_id, 0)
                state.avg_score_per_round = state.total_score / state.total_rounds

                # Update history
                state.round_history.append(round_num)
                state.score_history.append(scores.get(player_id, 0))

                # Calculate win rate
                if scores.get(player_id, 0) > scores.get(
                    player2_id if player_id == player1_id else player1_id, 0
                ):
                    state.total_wins += 1

                state.win_rate = (
                    state.total_wins / state.total_rounds if state.total_rounds > 0 else 0
                )
                state.win_rate_history.append(state.win_rate)

        # Stream to dashboard
        await self.dashboard.stream_event(event)

        # Update counterfactual visualization if available
        if player1_id in self.cfr_engines:
            await self._update_counterfactual_viz(player1_id, round_num)
        if player2_id in self.cfr_engines:
            await self._update_counterfactual_viz(player2_id, round_num)

        # Update strategy performance
        await self._update_strategy_performance()

        logger.debug(f"Streamed round_end event for round {round_num}")

    # ========================================================================
    # Opponent Modeling Integration
    # ========================================================================

    async def _update_opponent_model_viz(self, player_id: str, opponent_id: str):
        """Update opponent modeling visualization for a player."""
        engine = self.opponent_modeling_engines.get(player_id)
        if not engine:
            return

        # Get opponent model
        model = engine.models.get(opponent_id)
        if not model:
            return

        # Create visualization data
        # Convert move_distribution keys from int to str
        move_dist_str = {str(k): v for k, v in model.move_distribution.items()}

        viz = OpponentModelVisualization(  # type: ignore[call-arg]
            opponent_id=opponent_id,
            predicted_strategy=model.strategy_type,
            confidence=model.confidence,
            move_distribution=move_dist_str,
        )

        # Store additional metadata separately
        viz.metadata = {  # type: ignore[attr-defined]
            "determinism": model.determinism,
            "reactivity": model.reactivity,
            "adaptability": model.adaptability,
            "concept_drift": model.concept_drift_detected,
            "accuracy": model.prediction_accuracy,
        }

        # Update player state
        if self.tournament_state is None:
            return

        state = self.tournament_state.players[player_id]
        state.opponent_models[opponent_id] = model

        # Add to recent predictions
        state.recent_predictions.append(
            {
                "timestamp": datetime.now().isoformat(),
                "opponent_id": opponent_id,
                "predicted_strategy": model.strategy_type,
                "confidence": model.confidence,
            }
        )

        # Keep only last 20 predictions
        if len(state.recent_predictions) > 20:
            state.recent_predictions = state.recent_predictions[-20:]

        # Stream to dashboard (custom message)
        await self.dashboard.connection_manager.broadcast(
            {
                "type": "opponent_model_update",
                "player_id": player_id,
                "opponent_id": opponent_id,
                "data": {
                    "predicted_strategy": viz.predicted_strategy,
                    "confidence": viz.confidence,
                    "move_distribution": viz.move_distribution,
                    "metadata": viz.metadata,  # type: ignore[attr-defined]
                },
            }
        )

        logger.debug(f"Updated opponent model viz for {player_id} -> {opponent_id}")

    # ========================================================================
    # Counterfactual Reasoning Integration
    # ========================================================================

    async def _update_counterfactual_viz(self, player_id: str, round_num: int):
        """Update counterfactual reasoning visualization for a player."""
        engine = self.cfr_engines.get(player_id)
        if not engine:
            return

        # Get recent counterfactual analysis
        recent_cfs = [cf for cf in engine.counterfactual_history if cf.round == round_num]

        if not recent_cfs:
            return

        # Get actual move from last CF
        actual = recent_cfs[0]

        # Create visualization data
        viz = CounterfactualVisualization(  # type: ignore[call-arg]
            actual_move=str(actual.actual_move),  # Convert int to str
            actual_reward=actual.actual_reward,
            counterfactuals=[
                {
                    "move": cf.counterfactual_move,
                    "estimated_reward": cf.counterfactual_reward,
                    "regret": cf.regret,
                    "confidence": cf.confidence,
                }
                for cf in recent_cfs
            ],
            cumulative_regret={},  # Will populate from regret table
        )

        # Store metadata separately
        viz.metadata = {"round": round_num}  # type: ignore[attr-defined]

        # Get cumulative regrets from regret table (skip if no game state available)
        # infoset = engine._get_infoset(None)  # Would need actual game state
        # if infoset in engine.regret_table.cumulative_regret:
        #     viz.cumulative_regret = dict(engine.regret_table.cumulative_regret[infoset])

        # Update player state
        if self.tournament_state is None:
            return

        state = self.tournament_state.players[player_id]
        state.recent_regrets.append(
            {
                "timestamp": datetime.now().isoformat(),
                "round": round_num,
                "actual_move": viz.actual_move,
                "actual_reward": viz.actual_reward,
                "counterfactuals": viz.counterfactuals,
            }
        )

        # Keep only last 20 regrets
        if len(state.recent_regrets) > 20:
            state.recent_regrets = state.recent_regrets[-20:]

        # Update cumulative regret
        state.cumulative_regret = viz.cumulative_regret

        # Stream to dashboard
        await self.dashboard.connection_manager.broadcast(
            {
                "type": "counterfactual_update",
                "player_id": player_id,
                "round": round_num,
                "data": {
                    "actual_move": viz.actual_move,
                    "actual_reward": viz.actual_reward,
                    "counterfactuals": viz.counterfactuals,
                    "cumulative_regret": viz.cumulative_regret,
                },
            }
        )

        logger.debug(f"Updated counterfactual viz for {player_id} at round {round_num}")

    # ========================================================================
    # Strategy Performance Integration
    # ========================================================================

    async def _update_strategy_performance(self):
        """Update strategy performance metrics across all players."""
        if not self.enabled:
            return

        # Aggregate performance by strategy type
        strategy_stats: dict[str, dict[str, list]] = {}

        for _player_id, state in self.tournament_state.players.items():
            strategy_name = state.strategy_name

            if strategy_name not in strategy_stats:
                strategy_stats[strategy_name] = {"rounds": [], "win_rates": [], "avg_scores": []}

            # Aggregate data
            if state.round_history:
                strategy_stats[strategy_name]["rounds"].extend(state.round_history)
                strategy_stats[strategy_name]["win_rates"].extend(state.win_rate_history)
                strategy_stats[strategy_name]["avg_scores"].extend(state.score_history)

        # Create performance objects and stream to dashboard
        for strategy_name, stats in strategy_stats.items():
            if not stats["rounds"]:
                continue

            perf = StrategyPerformance(
                strategy_name=strategy_name,
                rounds=stats["rounds"],
                win_rates=stats["win_rates"],
                avg_scores=stats["avg_scores"],
            )

            # Stream to dashboard
            await self.dashboard.connection_manager.broadcast(
                {
                    "type": "strategy_performance_update",
                    "strategy_name": strategy_name,
                    "data": {
                        "rounds": perf.rounds,
                        "win_rates": perf.win_rates,
                        "avg_scores": perf.avg_scores,
                    },
                }
            )

        logger.debug("Updated strategy performance metrics")

    # ========================================================================
    # API Endpoints Data Providers
    # ========================================================================

    def get_tournament_state(self) -> dict:
        """Get current tournament state for API endpoint."""
        if not self.tournament_state:
            return {}

        return {
            "tournament_id": self.tournament_state.tournament_id,
            "start_time": self.tournament_state.start_time.isoformat(),
            "current_round": self.tournament_state.current_round,
            "total_rounds": self.tournament_state.total_rounds,
            "num_players": len(self.tournament_state.players),
            "matches_played": len(self.tournament_state.matches),
        }

    def get_player_standings(self) -> list[dict]:
        """Get current player standings sorted by win rate."""
        if not self.tournament_state:
            return []

        standings = []
        for player_id, state in self.tournament_state.players.items():
            standings.append(
                {
                    "player_id": player_id,
                    "strategy": state.strategy_name,
                    "total_rounds": state.total_rounds,
                    "total_wins": state.total_wins,
                    "win_rate": state.win_rate,
                    "total_score": state.total_score,
                    "avg_score": state.avg_score_per_round,
                }
            )

        # Sort by win rate (descending)
        def get_sort_key(x: dict) -> float:
            win_rate = x.get("win_rate")
            if win_rate is None:
                return 0.0
            return float(win_rate)

        standings.sort(key=get_sort_key, reverse=True)

        return standings

    def get_strategy_performance(self, strategy_name: str) -> dict | None:
        """Get performance data for a specific strategy."""
        if not self.tournament_state:
            return None

        # Find players using this strategy
        players_with_strategy = [
            state
            for state in self.tournament_state.players.values()
            if state.strategy_name == strategy_name
        ]

        if not players_with_strategy:
            return None

        # Aggregate data
        all_rounds = []
        all_win_rates = []
        all_scores = []

        for state in players_with_strategy:
            all_rounds.extend(state.round_history)
            all_win_rates.extend(state.win_rate_history)
            all_scores.extend(state.score_history)

        return {
            "strategy_name": strategy_name,
            "num_players": len(players_with_strategy),
            "rounds": all_rounds,
            "win_rates": all_win_rates,
            "avg_scores": all_scores,
        }

    def get_opponent_model(self, player_id: str, opponent_id: str) -> dict | None:
        """Get opponent model data for visualization."""
        if not self.tournament_state or player_id not in self.tournament_state.players:
            return None

        state = self.tournament_state.players[player_id]
        model = state.opponent_models.get(opponent_id)

        if not model:
            return None

        return {
            "opponent_id": opponent_id,
            "predicted_strategy": model.strategy_type,
            "confidence": model.confidence,
            "move_distribution": model.move_distribution,
            "determinism": model.determinism,
            "reactivity": model.reactivity,
            "adaptability": model.adaptability,
            "concept_drift": model.concept_drift_detected,
            "accuracy": model.prediction_accuracy,
        }

    def get_counterfactual_data(self, player_id: str, round_num: int | None = None) -> dict | None:
        """Get counterfactual reasoning data for visualization."""
        if not self.tournament_state or player_id not in self.tournament_state.players:
            return None

        state = self.tournament_state.players[player_id]

        if round_num is not None:
            # Get specific round
            regrets = [r for r in state.recent_regrets if r["round"] == round_num]
            if not regrets:
                return None
            return regrets[0]
        else:
            # Get most recent
            if not state.recent_regrets:
                return None

            return {
                "recent_regrets": state.recent_regrets[-5:],  # Last 5
                "cumulative_regret": state.cumulative_regret,
            }


# ============================================================================
# Global Integration Instance
# ============================================================================

_dashboard_integration: DashboardIntegration | None = None


def get_dashboard_integration() -> DashboardIntegration:
    """Get global dashboard integration instance (singleton)."""
    global _dashboard_integration
    if _dashboard_integration is None:
        _dashboard_integration = DashboardIntegration()
    return _dashboard_integration


def reset_dashboard_integration():
    """Reset global integration instance (for testing)."""
    global _dashboard_integration
    _dashboard_integration = None
