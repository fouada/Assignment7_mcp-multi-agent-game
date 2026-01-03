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

from dataclasses import dataclass, field
from datetime import datetime

from ..agents.strategies.counterfactual_reasoning import (
    CounterfactualReasoningEngine,
)
from ..agents.strategies.hierarchical_composition import CompositeStrategy
from ..agents.strategies.opponent_modeling import OpponentModel, OpponentModelingEngine
from ..common.logger import get_logger
from .analytics import AnalyticsEngine, get_analytics_engine
from .dashboard import (
    CounterfactualVisualization,
    DashboardAPI,
    GameEvent,
    OpponentModelVisualization,
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

    def __init__(
        self, dashboard: DashboardAPI | None = None, analytics_engine: AnalyticsEngine | None = None
    ):
        self.dashboard = dashboard or get_dashboard()
        self.analytics_engine = analytics_engine or get_analytics_engine()
        self.tournament_state: TournamentDashboardState | None = None
        self.enabled = False

        # Track innovation engines per player
        self.opponent_modeling_engines: dict[str, OpponentModelingEngine] = {}
        self.cfr_engines: dict[str, CounterfactualReasoningEngine] = {}
        self.strategy_compositions: dict[str, CompositeStrategy] = {}

        # Track moves for current round to accumulate both players' moves
        self.current_round_moves: dict[int, dict[str, str]] = {}  # round_num -> {player_id: move}

        logger.info("DashboardIntegration initialized with analytics engine")

    async def start(self, tournament_id: str, total_rounds: int):
        """Start dashboard integration for a tournament."""
        self.enabled = True

        # Initialize tournament state
        self.tournament_state = TournamentDashboardState(
            tournament_id=tournament_id, start_time=datetime.now(), total_rounds=total_rounds
        )

        # Dashboard server is already started by the launcher
        # No need to start it again here to avoid port conflicts

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

        # Register with analytics engine
        self.analytics_engine.register_player(player_id, strategy_name)

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

        # Accumulate moves for this round
        if round_num not in self.current_round_moves:
            self.current_round_moves[round_num] = {}

        self.current_round_moves[round_num][player_id] = str(move)

        # Check if we have both players' moves
        if len(self.current_round_moves[round_num]) >= 2:
            # Both players have moved - broadcast complete move event
            event = GameEvent(
                timestamp=datetime.now().isoformat(),
                event_type="move",
                round=round_num,
                players=[player_id, opponent_id],
                moves=self.current_round_moves[round_num].copy(),
                scores={},
                metadata={"game_state": game_state},
            )

            # Stream to dashboard
            await self.dashboard.stream_event(event)
            logger.debug(
                f"Streamed complete move event for round {round_num}: {self.current_round_moves[round_num]}"
            )
        else:
            # Only one player has moved so far
            logger.debug(
                f"Move recorded for {player_id} in round {round_num}, waiting for opponent"
            )

        # Update opponent modeling visualization if available
        if player_id in self.opponent_modeling_engines:
            await self._update_opponent_model_viz(player_id, opponent_id)

        logger.debug(f"Processed move for player {player_id}: {move}")

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

        # Update analytics engine
        await self.analytics_engine.on_round_complete(
            round_num, player1_id, player2_id, moves, scores
        )

        # Broadcast move event for dashboard to update last move
        move_event = GameEvent(
            timestamp=datetime.now().isoformat(),
            event_type="move",
            round=round_num,
            players=[player1_id, player2_id],
            moves=moves,
            scores={},
            metadata={},
        )
        await self.dashboard.stream_event(move_event)
        logger.debug(f"Streamed move event for round {round_num}: {moves}")

        # Create round end event with cumulative scores in metadata
        event = GameEvent(
            timestamp=datetime.now().isoformat(),
            event_type="round_end",
            round=round_num,
            players=[player1_id, player2_id],
            moves=moves,
            scores=scores,
            metadata={"cumulative_scores": scores},  # Include cumulative scores for dashboard
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

        # Clear accumulated moves for this round
        if round_num in self.current_round_moves:
            del self.current_round_moves[round_num]

        # Update counterfactual visualization if available
        if player1_id in self.cfr_engines:
            await self._update_counterfactual_viz(player1_id, round_num)
        if player2_id in self.cfr_engines:
            await self._update_counterfactual_viz(player2_id, round_num)

        # Update strategy performance with enriched analytics
        await self._update_strategy_performance_with_analytics()

        logger.debug(f"Streamed round_end event for round {round_num}")

    async def on_match_completed(self, event):
        """Handle match completed event to update matchup matrix."""
        if not self.enabled:
            logger.info("[Integration] 🔍 DEBUG: on_match_completed called but integration disabled")
            return

        logger.info(f"[Integration] 🔍 DEBUG: on_match_completed received match {event.match_id}")
        try:
            # Extract match data from event
            match_id = event.match_id
            winner = event.winner
            final_scores = event.final_scores
            total_rounds = event.total_rounds

            logger.info(f"[Integration] 🔍 DEBUG: Match {match_id}, winner={winner}, scores={final_scores}, rounds={total_rounds}")

            # Get player IDs from final_scores
            if len(final_scores) >= 2:
                players = list(final_scores.keys())
                player1_id = players[0]
                player2_id = players[1]

                # Auto-register players if not already registered
                for player_id in [player1_id, player2_id]:
                    if player_id not in self.analytics_engine.player_strategies:
                        # Try to get strategy from dashboard's tournament states
                        strategy_name = "Unknown"
                        if hasattr(self.dashboard, 'tournament_states') and self.dashboard.tournament_states:
                            # Get the first (likely only) tournament state
                            for tournament_id, state in self.dashboard.tournament_states.items():
                                standings = state.standings if hasattr(state, 'standings') else []
                                for standing in standings:
                                    if isinstance(standing, dict):
                                        pid = standing.get('player_id') or standing.get('player')
                                    else:
                                        pid = getattr(standing, 'player_id', None) or getattr(standing, 'player', None)

                                    if pid == player_id:
                                        if isinstance(standing, dict):
                                            strategy_name = standing.get('strategy', 'Unknown')
                                        else:
                                            strategy_name = getattr(standing, 'strategy', 'Unknown')
                                        break

                                if strategy_name != "Unknown":
                                    break

                        logger.info(f"[Integration] 🔧 Auto-registering player {player_id} with strategy '{strategy_name}'")
                        self.analytics_engine.register_player(player_id, strategy_name)

                logger.info(f"[Integration] 🔍 DEBUG: Calling analytics_engine.on_round_complete with players {player1_id} vs {player2_id}")

                # Update matchup matrix in analytics engine
                # Note: We use the total_rounds as the "current round"
                # since this is the cumulative result
                moves = {}  # Moves not available in match.completed event
                await self.analytics_engine.on_round_complete(
                    total_rounds, player1_id, player2_id, moves, final_scores
                )

                logger.info(f"[Integration] ✅ Successfully updated analytics for match {match_id}")

                # Broadcast matchup matrix update
                from dataclasses import asdict, is_dataclass
                matchup_data = self.analytics_engine.get_matchup_matrix()

                logger.info(f"[Integration] 🔍 DEBUG: Broadcasting matchup matrix, players={matchup_data.players}, matrix_size={len(matchup_data.matrix)}")

                # Convert dataclass or Pydantic model to dict
                if is_dataclass(matchup_data):
                    matchup_dict = asdict(matchup_data)
                elif hasattr(matchup_data, 'model_dump'):
                    matchup_dict = matchup_data.model_dump()
                elif hasattr(matchup_data, 'dict'):
                    matchup_dict = matchup_data.dict()
                else:
                    matchup_dict = matchup_data

                # Convert tuple keys to string keys for JSON serialization
                if 'matrix' in matchup_dict and isinstance(matchup_dict['matrix'], dict):
                    matchup_dict['matrix'] = {
                        f"{k[0]}_vs_{k[1]}" if isinstance(k, tuple) else k: v
                        for k, v in matchup_dict['matrix'].items()
                    }

                logger.info(f"[Integration] 🔍 DEBUG: About to broadcast matchup_matrix_update with {len(matchup_dict.get('matrix', {}))} matchups")

                await self.dashboard.connection_manager.broadcast({
                    "type": "matchup_matrix_update",
                    "data": matchup_dict
                })

                logger.info(f"[Integration] ✅ Successfully broadcasted matchup matrix update")

                logger.info(f"Updated matchup matrix for match {match_id}: {player1_id} vs {player2_id}, winner: {winner}")

        except Exception as e:
            logger.error(f"Error handling match completed event: {e}", exc_info=True)

    async def on_opponent_model_update(self, event):
        """Handle opponent model update event from strategies."""
        if not self.enabled:
            logger.info("[Integration] 🔍 DEBUG: on_opponent_model_update called but integration disabled")
            return

        logger.info(f"[Integration] 🔍 DEBUG: on_opponent_model_update received event from {event.player_id}")
        try:
            # Extract data from event
            player_id = event.player_id
            opponent_id = event.opponent_id
            confidence = event.confidence
            predicted_strategy = event.predicted_strategy
            belief_distribution = event.belief_distribution
            accuracy = event.accuracy

            logger.info(f"[Integration] 🔍 DEBUG: belief_distribution = {belief_distribution}")

            # Extract mean and std from belief distribution (handle both 'std' and 'std_dev')
            mean_belief = belief_distribution.get('mean', 0.5)
            std_dev_belief = belief_distribution.get('std', belief_distribution.get('std_dev', 0.0))

            # Update analytics engine
            await self.analytics_engine.on_opponent_model_update(
                player_id=player_id,
                opponent_id=opponent_id,
                confidence=confidence,
                accuracy=accuracy,
                predicted_strategy=predicted_strategy,
                beliefs=belief_distribution,
            )

            # Broadcast to dashboard
            await self.dashboard.connection_manager.broadcast(
                {
                    "type": "opponent_model_update",
                    "player_id": player_id,
                    "opponent_id": opponent_id,
                    "data": {
                        "confidence": confidence,
                        "mean_belief": mean_belief,
                        "std_dev_belief": std_dev_belief,
                        "predicted_strategy": predicted_strategy,
                        "belief_distribution": belief_distribution,
                    },
                }
            )

            logger.info(f"✓ Processed opponent model update: {player_id} -> {opponent_id} (confidence: {confidence:.2f}, mean: {mean_belief:.2f})")

        except Exception as e:
            logger.error(f"Error handling opponent model update event: {e}", exc_info=True)

    async def on_counterfactual_analysis(self, event):
        """Handle counterfactual analysis event from strategies."""
        if not self.enabled:
            logger.info("[Integration] 🔍 DEBUG: on_counterfactual_analysis called but integration disabled")
            return

        logger.info(f"[Integration] 🔍 DEBUG: on_counterfactual_analysis received event from {event.player_id}")
        try:
            # Extract data from event
            player_id = event.player_id
            game_id = event.game_id
            round_number = event.round_number
            actual_move = event.actual_move
            actual_payoff = event.actual_payoff
            alternative_moves = event.alternative_moves
            regret = event.regret
            cumulative_regret = event.cumulative_regret

            logger.info(f"[Integration] 🔍 DEBUG: regret dict = {regret}, cumulative={cumulative_regret}")

            # Convert regret dict to counterfactuals format for analytics engine
            # Analytics expects: list[dict] with "move" and "regret" keys
            counterfactuals_list = []
            cumulative_regret_dict = {}

            if regret:
                for move, reg_val in regret.items():
                    move_str = str(move)
                    counterfactuals_list.append({
                        "move": move_str,
                        "regret": float(reg_val)
                    })
                    cumulative_regret_dict[move_str] = float(reg_val)

            # Update analytics engine with correct signature
            await self.analytics_engine.on_counterfactual_update(
                player_id=player_id,
                actual_move=str(actual_move),
                counterfactuals=counterfactuals_list,
                cumulative_regret=cumulative_regret_dict,
            )

            # Broadcast to dashboard
            await self.dashboard.connection_manager.broadcast(
                {
                    "type": "counterfactual_update",
                    "player_id": player_id,
                    "game_id": game_id,
                    "data": {
                        "round_number": round_number,
                        "actual_move": str(actual_move),
                        "actual_payoff": actual_payoff,
                        "counterfactuals": counterfactuals_list,
                        "cumulative_regret": cumulative_regret,
                    },
                }
            )

            logger.info(f"✓ Processed counterfactual analysis: {player_id} round {round_number}, cumulative_regret: {cumulative_regret:.2f}")

        except Exception as e:
            logger.error(f"Error handling counterfactual analysis event: {e}", exc_info=True)

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

        # Update analytics engine
        await self.analytics_engine.on_opponent_model_update(
            player_id=player_id,
            opponent_id=opponent_id,
            confidence=model.confidence,
            accuracy=model.prediction_accuracy,
            predicted_strategy=model.strategy_type,
            beliefs={str(k): v for k, v in model.move_distribution.items()},
        )

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

        # Prepare counterfactuals list
        counterfactuals_list = [
            {
                "move": cf.counterfactual_move,
                "estimated_reward": cf.counterfactual_reward,
                "regret": cf.regret,
                "confidence": cf.confidence,
            }
            for cf in recent_cfs
        ]

        # Get cumulative regret (try to extract from regret table)
        cumulative_regret = {}
        try:
            # Access regret table if available
            if hasattr(engine, "regret_table") and hasattr(
                engine.regret_table, "cumulative_regret"
            ):
                # Get first infoset's regret as a representative
                if engine.regret_table.cumulative_regret:
                    first_infoset = list(engine.regret_table.cumulative_regret.keys())[0]
                    cumulative_regret = {
                        str(k): float(v)
                        for k, v in engine.regret_table.cumulative_regret[first_infoset].items()
                    }
        except Exception as e:
            logger.debug(f"Could not extract cumulative regret: {e}")
            cumulative_regret = {}

        # Update analytics engine
        await self.analytics_engine.on_counterfactual_update(
            player_id=player_id,
            actual_move=str(actual.actual_move),
            counterfactuals=counterfactuals_list,
            cumulative_regret=cumulative_regret,
        )

        # Create visualization data
        viz = CounterfactualVisualization(  # type: ignore[call-arg]
            actual_move=str(actual.actual_move),  # Convert int to str
            actual_reward=actual.actual_reward,
            counterfactuals=counterfactuals_list,
            cumulative_regret=cumulative_regret,
        )

        # Store metadata separately
        viz.metadata = {"round": round_num}  # type: ignore[attr-defined]

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

    async def _update_strategy_performance_with_analytics(self):
        """Update strategy performance metrics using analytics engine."""
        if not self.enabled:
            return

        # Get all strategy analytics from analytics engine
        all_analytics = self.analytics_engine.get_all_strategy_analytics()

        for analytics in all_analytics:
            # Stream enriched data to dashboard
            await self.dashboard.connection_manager.broadcast(
                {
                    "type": "strategy_performance_update",
                    "strategy_name": analytics.strategy_name,
                    "data": {
                        "rounds": analytics.rounds,
                        "win_rates": analytics.win_rates,
                        "avg_scores": analytics.avg_scores,
                        "cumulative_scores": analytics.cumulative_scores,
                        "learning_rate": analytics.learning_rate,
                        "consistency": analytics.consistency,
                        "improvement_trend": analytics.improvement_trend,
                        "total_matches": analytics.total_matches,
                        "win_rate": analytics.win_rate,
                    },
                }
            )

        # Also broadcast matchup matrix
        matchup_matrix = self.analytics_engine.get_matchup_matrix()
        await self.dashboard.connection_manager.broadcast(
            {
                "type": "matchup_matrix_update",
                "data": {
                    "players": matchup_matrix.players,
                    "matrix": {f"{k[0]}_vs_{k[1]}": v for k, v in matchup_matrix.matrix.items()},
                    "total_matches": matchup_matrix.total_matches,
                    "finished_matches": matchup_matrix.finished_matches,
                    "pending_matches": matchup_matrix.pending_matches,
                },
            }
        )

        logger.debug("Updated strategy performance metrics with analytics")

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
