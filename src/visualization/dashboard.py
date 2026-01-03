"""
Real-Time Interactive Dashboard - Innovation #4
================================================

**Complex Problem Solved:**
How to visualize and analyze complex multi-agent interactions in real-time?
Traditional game systems lack observability into agent decision-making.

**Original Solution:**
- Real-time WebSocket streaming of game events
- Interactive strategy performance visualization
- Opponent modeling visualization (belief updates)
- Counterfactual analysis visualization
- Tournament replay with time-travel debugging
- Multi-agent coordination graphs

**Research Contribution:**
- First real-time dashboard for multi-agent game theory research
- Visualizes internal agent state (beliefs, regrets, strategy distributions)
- Enables interactive "what-if" analysis
- Publication-quality visualizations

**Innovation:**
Like mission control for NASA, but for multi-agent AI research.
"""

import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from ..common.logger import get_logger

# Import comprehensive dashboard HTML
# Note: COMPREHENSIVE_DASHBOARD_HTML available in comprehensive_dashboard.py if needed
USE_COMPREHENSIVE = False

logger = get_logger(__name__)


# ============================================================================
# Dashboard Data Models
# ============================================================================


@dataclass
class GameEvent:
    """Real-time game event for dashboard streaming."""

    timestamp: str
    event_type: str  # "round_start", "move", "round_end", "game_end"
    round: int
    players: list[str]
    moves: dict[str, str]
    scores: dict[str, float]
    metadata: dict


@dataclass
class StrategyPerformance:
    """Strategy performance metrics over time."""

    strategy_name: str
    rounds: list[int]
    win_rates: list[float]
    avg_scores: list[float]
    opponent_types: dict[str, int]  # Opponent strategy -> count


@dataclass
class OpponentModelVisualization:
    """Opponent modeling data for visualization."""

    opponent_id: str
    round: int
    predicted_strategy: str
    confidence: float
    move_distribution: dict[str, float]
    determinism: float
    reactivity: float
    adaptability: float


@dataclass
class CounterfactualVisualization:
    """Counterfactual analysis for visualization."""

    round: int
    actual_move: str
    actual_reward: float
    counterfactuals: list[dict]  # {move, reward, regret}
    cumulative_regret: dict[str, float]


@dataclass
class TournamentState:
    """Complete tournament state for dashboard."""

    tournament_id: str
    game_type: str
    players: list[str]
    current_round: int
    total_rounds: int
    standings: list[dict]  # {player, score, wins, losses}
    recent_matches: list[dict]
    active_matches: list[dict]


# ============================================================================
# WebSocket Connection Manager
# ============================================================================


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.

    **Features:**
    - Multiple concurrent connections
    - Broadcast to all clients
    - Per-client filtering
    - Connection pooling
    """

    def __init__(self):
        self.active_connections: set[WebSocket] = set()
        self.connection_metadata: dict[WebSocket, dict] = {}

    async def connect(self, websocket: WebSocket, client_info: dict[Any, Any] | None = None):  # type: ignore[name-defined]
        """Accept new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.connection_metadata[websocket] = client_info or {}
        logger.info(f"WebSocket connected: {len(self.active_connections)} active connections")

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        self.active_connections.discard(websocket)
        self.connection_metadata.pop(websocket, None)
        logger.info(f"WebSocket disconnected: {len(self.active_connections)} active connections")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        disconnected = set()

        for connection in self.active_connections:
            try:
                # Test JSON serialization before sending
                import json

                try:
                    json.dumps(message)
                except TypeError as json_err:
                    logger.error(f"Message not JSON serializable before send: {json_err}")
                    logger.error(f"Message type: {message.get('type')}")
                    logger.error(
                        f"Message data keys: {message.get('data', {}).keys() if isinstance(message.get('data'), dict) else 'not a dict'}"
                    )
                    raise

                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


# ============================================================================
# Dashboard API
# ============================================================================


class DashboardAPI:
    """
    FastAPI application for interactive dashboard.

    **Endpoints:**
    - GET /: Dashboard UI
    - WS /ws: Real-time event stream
    - GET /api/tournament/{id}: Tournament state
    - GET /api/strategy/{name}/performance: Strategy metrics
    - GET /api/opponent_model/{player_id}/{opponent_id}: Opponent model
    - GET /api/counterfactual/{player_id}/{round}: Counterfactual analysis
    - GET /api/replay/{tournament_id}: Tournament replay data
    """

    def __init__(self):
        self.app = FastAPI(title="MCP Game League Dashboard", version="1.0.0")
        self.connection_manager = ConnectionManager()

        # Data storage
        self.tournament_states: dict[str, TournamentState] = {}
        self.game_events: dict[str, list[GameEvent]] = {}
        self.strategy_performance: dict[str, StrategyPerformance] = {}
        self.opponent_models: dict[str, dict[str, OpponentModelVisualization]] = {}
        self.counterfactuals: dict[str, dict[int, CounterfactualVisualization]] = {}

        # Server state
        self._server_task: asyncio.Task | None = None
        self._server = None

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Configure API routes."""

        @self.app.get("/")
        async def dashboard_home():
            """Serve dashboard UI."""
            return HTMLResponse(content=self._get_dashboard_html())

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket for real-time updates."""
            from datetime import datetime

            await self.connection_manager.connect(websocket)

            def convert_datetimes(obj):
                """Recursively convert datetime objects to ISO format strings"""
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: convert_datetimes(v) for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [convert_datetimes(item) for item in obj]
                return obj

            # Send current tournament state on connect (for page refreshes)
            try:
                # Send all active tournament states
                for tournament_id, state in self.tournament_states.items():
                    state_dict = asdict(state)
                    serializable_state = convert_datetimes(state_dict)

                    await self.connection_manager.send_personal_message(
                        {
                            "type": "tournament_state",
                            "tournament_id": tournament_id,
                            "data": serializable_state,
                        },
                        websocket,
                    )
                logger.info(
                    f"Sent {len(self.tournament_states)} tournament states to new connection"
                )
            except Exception as e:
                logger.error(f"Failed to send initial state: {e}")

            try:
                while True:
                    # Keep connection alive
                    await websocket.receive_text()
                    # Echo back for ping/pong
                    await self.connection_manager.send_personal_message(
                        {"type": "pong", "timestamp": datetime.now().isoformat()}, websocket
                    )
            except WebSocketDisconnect:
                self.connection_manager.disconnect(websocket)

        @self.app.get("/api/tournament/{tournament_id}")
        async def get_tournament_state(tournament_id: str):
            """Get current tournament state."""
            from datetime import datetime

            def convert_datetimes(obj):
                """Recursively convert datetime objects to ISO format strings"""
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: convert_datetimes(v) for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [convert_datetimes(item) for item in obj]
                return obj

            state = self.tournament_states.get(tournament_id)
            if not state:
                return {"error": "Tournament not found"}
            return convert_datetimes(asdict(state))

        @self.app.get("/api/strategy/{strategy_name}/performance")
        async def get_strategy_performance(strategy_name: str):
            """Get strategy performance metrics."""
            from datetime import datetime

            def convert_datetimes(obj):
                """Recursively convert datetime objects to ISO format strings"""
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: convert_datetimes(v) for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [convert_datetimes(item) for item in obj]
                return obj

            perf = self.strategy_performance.get(strategy_name)
            if not perf:
                return {"error": "Strategy not found"}
            return convert_datetimes(asdict(perf))

        @self.app.get("/api/opponent_model/{player_id}/{opponent_id}")
        async def get_opponent_model(player_id: str, opponent_id: str):
            """Get opponent model visualization data."""
            from datetime import datetime

            def convert_datetimes(obj):
                """Recursively convert datetime objects to ISO format strings"""
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: convert_datetimes(v) for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [convert_datetimes(item) for item in obj]
                return obj

            models = self.opponent_models.get(player_id, {})
            model = models.get(opponent_id)
            if not model:
                return {"error": "Opponent model not found"}
            return convert_datetimes(asdict(model))

        @self.app.get("/api/counterfactual/{player_id}/{round}")
        async def get_counterfactual(player_id: str, round: int):
            """Get counterfactual analysis for specific round."""
            from datetime import datetime

            def convert_datetimes(obj):
                """Recursively convert datetime objects to ISO format strings"""
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: convert_datetimes(v) for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [convert_datetimes(item) for item in obj]
                return obj

            cfs = self.counterfactuals.get(player_id, {})
            cf = cfs.get(round)
            if not cf:
                return {"error": "Counterfactual data not found"}
            return convert_datetimes(asdict(cf))

        @self.app.get("/api/events/{tournament_id}")
        async def get_events(tournament_id: str, limit: int = 100):
            """Get recent game events."""
            events = self.game_events.get(tournament_id, [])
            return [asdict(e) for e in events[-limit:]]

        @self.app.get("/api/replay/{tournament_id}")
        async def get_replay_data(tournament_id: str):
            """Get complete replay data for tournament."""
            events = self.game_events.get(tournament_id, [])
            state = self.tournament_states.get(tournament_id)

            return {
                "tournament": asdict(state) if state else None,
                "events": [asdict(e) for e in events],
                "total_rounds": len(events),
            }

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "active_connections": len(self.connection_manager.active_connections),
                "tournaments": len(self.tournament_states),
            }

        # Advanced Analytics Endpoints
        @self.app.get("/api/analytics/strategies")
        async def get_all_strategies_analytics():
            """Get analytics for all strategies."""
            from .analytics import get_analytics_engine

            engine = get_analytics_engine()
            all_analytics = engine.get_all_strategy_analytics()

            return {
                "strategies": [
                    {
                        "strategy_name": a.strategy_name,
                        "time_series": {
                            "rounds": a.rounds,
                            "win_rates": a.win_rates,
                            "avg_scores": a.avg_scores,
                            "cumulative_scores": a.cumulative_scores,
                        },
                        "metrics": {
                            "total_matches": a.total_matches,
                            "win_rate": a.win_rate,
                            "learning_rate": a.learning_rate,
                            "consistency": a.consistency,
                            "improvement_trend": a.improvement_trend,
                        },
                    }
                    for a in all_analytics
                ]
            }

        @self.app.get("/api/analytics/strategy/{strategy_name}")
        async def get_strategy_analytics_detailed(strategy_name: str):
            """Get detailed analytics for a specific strategy."""
            from .analytics import get_analytics_engine

            engine = get_analytics_engine()
            analytics = engine.get_strategy_analytics(strategy_name)

            if not analytics:
                return {"error": "Strategy not found"}

            return {
                "strategy_name": analytics.strategy_name,
                "player_ids": analytics.player_ids,
                "time_series": {
                    "rounds": analytics.rounds,
                    "win_rates": analytics.win_rates,
                    "avg_scores": analytics.avg_scores,
                    "cumulative_scores": analytics.cumulative_scores,
                },
                "statistics": {
                    "total_matches": analytics.total_matches,
                    "total_wins": analytics.total_wins,
                    "total_draws": analytics.total_draws,
                    "total_losses": analytics.total_losses,
                    "win_rate": analytics.win_rate,
                    "avg_score_per_match": analytics.avg_score_per_match,
                },
                "learning_metrics": {
                    "learning_rate": analytics.learning_rate,
                    "consistency": analytics.consistency,
                    "improvement_trend": analytics.improvement_trend,
                },
                "opponent_matchups": analytics.opponent_win_rates,
            }

        @self.app.get("/api/analytics/opponent_models/{player_id}")
        async def get_player_opponent_models(player_id: str):
            """Get all opponent models for a player."""
            from .analytics import get_analytics_engine

            engine = get_analytics_engine()
            models = engine.get_all_opponent_models(player_id)

            return {
                "player_id": player_id,
                "opponent_models": {
                    opp_id: {
                        "opponent_id": model.opponent_id,
                        "current_confidence": model.current_confidence,
                        "current_accuracy": model.current_accuracy,
                        "predicted_strategy": model.predicted_strategy,
                        "convergence_round": model.convergence_round,
                        "time_series": {
                            "rounds": model.rounds,
                            "confidence_history": model.confidence_history,
                            "accuracy_history": model.accuracy_history,
                        },
                        "prediction_count": model.prediction_count,
                        "correct_predictions": model.correct_predictions,
                    }
                    for opp_id, model in models.items()
                },
            }

        @self.app.get("/api/analytics/counterfactual/{player_id}")
        async def get_player_counterfactual(player_id: str):
            """Get counterfactual analytics for a player."""
            from .analytics import get_analytics_engine

            engine = get_analytics_engine()
            cf = engine.get_counterfactual_analytics(player_id)

            if not cf:
                return {"error": "Player not found"}

            return {
                "player_id": cf.player_id,
                "time_series": {
                    "rounds": cf.rounds,
                    "regret_by_action": cf.regret_by_action,
                    "entropy_history": cf.entropy_history,
                },
                "cumulative_regret": cf.cumulative_regret_by_action,
                "strategy_distribution": cf.strategy_distribution_history[-1]
                if cf.strategy_distribution_history
                else {},
                "metrics": {
                    "total_regret_minimized": cf.total_regret_minimized,
                    "strategy_stability": cf.strategy_stability,
                    "nash_equilibrium_distance": cf.nash_equilibrium_distance,
                },
            }

        @self.app.get("/api/analytics/matchup_matrix")
        async def get_matchup_matrix():
            """Get complete matchup matrix."""
            from .analytics import get_analytics_engine

            engine = get_analytics_engine()
            matrix = engine.get_matchup_matrix()

            return {
                "players": matrix.players,
                "matchups": {
                    f"{k[0]}_vs_{k[1]}": {
                        "player_a": v["player_a"],
                        "player_b": v["player_b"],
                        "total_matches": v["total_matches"],
                        "player_a_wins": v["player_a_wins"],
                        "player_b_wins": v["player_b_wins"],
                        "draws": v["draws"],
                        "avg_score_a": v["total_score_a"] / v["total_matches"]
                        if v["total_matches"] > 0
                        else 0,
                        "avg_score_b": v["total_score_b"] / v["total_matches"]
                        if v["total_matches"] > 0
                        else 0,
                        "recent_matches": v["match_history"][-5:],  # Last 5 matches
                    }
                    for k, v in matrix.matrix.items()
                },
                "summary": {
                    "total_matches": matrix.total_matches,
                    "finished_matches": matrix.finished_matches,
                    "pending_matches": matrix.pending_matches,
                },
            }

        @self.app.get("/api/analytics/replay/history")
        async def get_replay_history(start_round: int = 0, end_round: int | None = None):
            """Get replay history for a range of rounds."""
            from .analytics import get_analytics_engine

            engine = get_analytics_engine()
            history = engine.get_replay_history(start_round, end_round)

            return {
                "start_round": start_round,
                "end_round": end_round or engine.current_round,
                "snapshots": [
                    {
                        "round": snap.round_number,
                        "timestamp": snap.timestamp,
                        "standings": snap.standings,
                        "active_matches_count": len(snap.active_matches),
                        "completed_matches_count": len(snap.completed_matches),
                    }
                    for snap in history
                ],
                "total_snapshots": len(history),
            }

        @self.app.get("/api/analytics/export")
        async def export_analytics():
            """Export all analytics data for research."""
            from .analytics import get_analytics_engine

            engine = get_analytics_engine()
            return engine.export_for_research()

        @self.app.post("/api/league/start")
        async def start_league():
            """Start the league tournament (proxy to league manager)."""
            try:
                import httpx

                # Call league manager's start_league tool via MCP
                response = await httpx.AsyncClient().post(
                    "http://localhost:8000/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {
                            "name": "start_league",
                            "arguments": {}
                        },
                        "id": 1
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                result = response.json()

                if result.get("result", {}).get("success"):
                    logger.info("[Dashboard] Tournament started successfully")
                    return {
                        "success": True,
                        "message": "Tournament started successfully",
                        "data": result.get("result", {})
                    }
                else:
                    error_msg = result.get("result", {}).get("error", "Unknown error")
                    logger.error(f"[Dashboard] Start failed: {error_msg}")
                    return {"success": False, "error": error_msg}

            except Exception as e:
                logger.error(f"[Dashboard] Error starting tournament: {e}", exc_info=True)
                return {"success": False, "error": str(e)}

        @self.app.post("/api/league/run_round")
        async def run_round():
            """Run the next round (proxy to league manager)."""
            try:
                import httpx

                # Call league manager's start_next_round tool via MCP
                response = await httpx.AsyncClient().post(
                    "http://localhost:8000/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {
                            "name": "start_next_round",
                            "arguments": {}
                        },
                        "id": 1
                    },
                    timeout=30.0  # Longer timeout for round execution
                )
                response.raise_for_status()
                result = response.json()

                if result.get("result", {}).get("success"):
                    logger.info("[Dashboard] Round started successfully")
                    return {
                        "success": True,
                        "message": "Round started successfully",
                        "data": result.get("result", {})
                    }
                else:
                    error_msg = result.get("result", {}).get("error", "Unknown error")
                    logger.error(f"[Dashboard] Run round failed: {error_msg}")
                    return {"success": False, "error": error_msg}

            except Exception as e:
                logger.error(f"[Dashboard] Error running round: {e}", exc_info=True)
                return {"success": False, "error": str(e)}

        @self.app.post("/api/league/reset")
        async def reset_league():
            """Reset the league tournament (proxy to league manager)."""
            try:
                import httpx

                # Call league manager's reset_league tool via MCP
                response = await httpx.AsyncClient().post(
                    "http://localhost:8000/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {
                            "name": "reset_league",
                            "arguments": {}
                        },
                        "id": 1
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                result = response.json()

                if result.get("result", {}).get("success"):
                    # Clear dashboard data
                    self.tournament_states.clear()
                    self.game_events.clear()
                    self.strategy_performance.clear()
                    self.opponent_models.clear()
                    self.counterfactuals.clear()

                    # Clear analytics engine
                    from .analytics import get_analytics_engine
                    engine = get_analytics_engine()
                    engine.reset()

                    logger.info("[Dashboard] Tournament reset successful")
                    return {"success": True, "message": "Tournament reset successfully"}
                else:
                    error_msg = result.get("result", {}).get("error", "Unknown error")
                    logger.error(f"[Dashboard] Reset failed: {error_msg}")
                    return {"success": False, "error": error_msg}

            except Exception as e:
                logger.error(f"[Dashboard] Error resetting tournament: {e}", exc_info=True)
                return {"success": False, "error": str(e)}

    async def stream_event(self, event: GameEvent):
        """Stream event to all connected clients."""
        message = {"type": "game_event", "data": asdict(event)}
        await self.connection_manager.broadcast(message)

        # Store event
        tournament_id = event.metadata.get("tournament_id", "default")
        if tournament_id not in self.game_events:
            self.game_events[tournament_id] = []
        self.game_events[tournament_id].append(event)

    async def update_tournament_state(self, state: TournamentState):
        """Update and broadcast tournament state."""
        self.tournament_states[state.tournament_id] = state

        message = {"type": "tournament_update", "data": asdict(state)}
        await self.connection_manager.broadcast(message)

    async def update_strategy_performance(self, perf: StrategyPerformance):
        """Update strategy performance metrics."""
        self.strategy_performance[perf.strategy_name] = perf

        message = {"type": "strategy_performance", "data": asdict(perf)}
        await self.connection_manager.broadcast(message)

    async def update_opponent_model(self, player_id: str, model: OpponentModelVisualization):
        """Update opponent model visualization."""
        if player_id not in self.opponent_models:
            self.opponent_models[player_id] = {}
        self.opponent_models[player_id][model.opponent_id] = model

        message = {
            "type": "opponent_model_update",
            "data": {"player_id": player_id, "model": asdict(model)},
        }
        await self.connection_manager.broadcast(message)

    async def update_counterfactual(self, player_id: str, cf: CounterfactualVisualization):
        """Update counterfactual analysis."""
        if player_id not in self.counterfactuals:
            self.counterfactuals[player_id] = {}
        self.counterfactuals[player_id][cf.round] = cf

        message = {
            "type": "counterfactual_update",
            "data": {"player_id": player_id, "counterfactual": asdict(cf)},
        }
        await self.connection_manager.broadcast(message)

    async def broadcast_match_update(self, match_data: dict):
        """Broadcast live match state to all connected clients."""
        message = {"type": "match_update", "data": match_data}
        await self.connection_manager.broadcast(message)
        logger.debug(f"Broadcasted match update: {match_data.get('match_id', 'unknown')}")

    async def broadcast_tournament_complete(self, winner_data: dict):
        """Broadcast tournament completion with winner data."""
        message = {"type": "tournament_complete", "data": {"winner": winner_data}}
        await self.connection_manager.broadcast(message)
        logger.info(f"Tournament complete! Winner: {winner_data.get('player_id', 'unknown')}")

    async def start_server(self, host: str = "127.0.0.1", port: int = 8050):
        """
        Start the dashboard server with Uvicorn.

        This is a blocking call that runs the server until interrupted.
        Use start_server_background() for non-blocking operation.

        Args:
            host: Host to bind to (default: 127.0.0.1 for localhost only)
            port: Port to listen on (default: 8050)

        Note:
            For security, defaults to localhost. Use "0.0.0.0" to bind to all
            interfaces if needed for remote access (not recommended for production).
        """
        import uvicorn

        logger.info(f"Starting dashboard server on {host}:{port}")
        config = uvicorn.Config(self.app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        self._server = server
        await server.serve()

    async def start_server_background(self, host: str = "127.0.0.1", port: int = 8050):
        """
        Start server in background task (non-blocking).

        This allows the dashboard to run alongside other components.

        Args:
            host: Host to bind to (default: 127.0.0.1 for localhost only)
            port: Port to listen on (default: 8050)

        Note:
            For security, defaults to localhost. Use "0.0.0.0" to bind to all
            interfaces if needed for remote access (not recommended for production).

        Args:
            host: Host to bind to (default: 0.0.0.0 for all interfaces)
            port: Port to listen on (default: 8050)
        """
        import uvicorn

        logger.info(f"Starting dashboard server in background on {host}:{port}")
        config = uvicorn.Config(self.app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        self._server = server

        # Start server in background task
        self._server_task = asyncio.create_task(server.serve())

        # Wait a moment for server to start
        await asyncio.sleep(1)
        logger.info(f"✓ Dashboard started at http://{host}:{port}")

    async def stop_server(self):
        """Stop the dashboard server gracefully."""
        if self._server:
            logger.info("Stopping dashboard server...")
            self._server.should_exit = True
            if self._server_task:
                try:
                    await asyncio.wait_for(self._server_task, timeout=5.0)
                except TimeoutError:
                    logger.warning("Dashboard server shutdown timed out")
                    self._server_task.cancel()
            logger.info("✓ Dashboard server stopped")

    def _get_dashboard_html(self) -> str:
        """Generate enhanced dashboard HTML with player strategies."""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>MCP Game League - Enhanced Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0e27;
            color: #e0e0e0;
            overflow-x: hidden;
        }

        /* Header */
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            position: sticky;
            top: 0;
            z-index: 1000;
        }
        .header h1 {
            color: white;
            font-size: 28px;
            font-weight: 600;
        }
        .connection-status {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            margin-left: 20px;
        }
        .connected { background: #10b981; color: white; }
        .disconnected { background: #ef4444; color: white; }

        /* Main Container */
        .container {
            max-width: 1800px;
            margin: 0 auto;
            padding: 20px;
        }

        /* Card Styles */
        .card {
            background: #1a1f3a;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            border: 1px solid #2a2f4a;
            margin-bottom: 20px;
        }
        .card h2 {
            font-size: 22px;
            margin-bottom: 20px;
            color: #667eea;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        /* Enhanced Standings Table */
        .standings-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        .standings-table thead {
            background: rgba(102, 126, 234, 0.2);
        }
        .standings-table th {
            padding: 15px;
            text-align: left;
            font-weight: 600;
            color: #667eea;
            border-bottom: 2px solid #667eea;
        }
        .standings-table td {
            padding: 15px;
            border-bottom: 1px solid #2a2f4a;
        }
        .standings-table tr:hover {
            background: rgba(102, 126, 234, 0.1);
        }
        .rank-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 35px;
            height: 35px;
            border-radius: 50%;
            font-weight: bold;
            font-size: 16px;
        }
        .rank-1 {
            background: linear-gradient(135deg, #ffd700, #ffed4e);
            color: #000;
        }
        .rank-2 {
            background: linear-gradient(135deg, #c0c0c0, #e8e8e8);
            color: #000;
        }
        .rank-3 {
            background: linear-gradient(135deg, #cd7f32, #e89547);
            color: #fff;
        }
        .rank-other {
            background: rgba(255,255,255,0.1);
            color: #a0aec0;
        }
        .player-cell {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .player-avatar {
            width: 45px;
            height: 45px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea, #764ba2);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 16px;
        }
        .player-details {
            flex: 1;
        }
        .player-name {
            font-weight: 600;
            font-size: 16px;
            margin-bottom: 4px;
        }
        .strategy-badge {
            font-size: 11px;
            color: #fff;
            background: linear-gradient(135deg, #667eea, #764ba2);
            padding: 3px 10px;
            border-radius: 12px;
            display: inline-block;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .last-move-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 40px;
            height: 40px;
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
            font-size: 22px;
            font-weight: 700;
            border-radius: 8px;
            padding: 5px 12px;
            box-shadow: 0 2px 8px rgba(16, 185, 129, 0.4);
            animation: fadeInScale 0.3s ease;
        }
        @keyframes fadeInScale {
            from {
                opacity: 0;
                transform: scale(0.8);
            }
            to {
                opacity: 1;
                transform: scale(1);
            }
        }
        .score-cell {
            font-size: 24px;
            font-weight: 700;
            color: #667eea;
        }
        .wins-cell {
            color: #10b981;
            font-weight: 600;
        }
        .draws-cell {
            color: #f59e0b;
            font-weight: 600;
        }
        .losses-cell {
            color: #ef4444;
            font-weight: 600;
        }
        .winrate-cell {
            font-weight: 600;
        }
        .metric {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #2a2f4a;
        }
        .metric:last-child { border-bottom: none; }
        .metric-label { color: #a0aec0; }
        .metric-value {
            font-weight: 600;
            color: #e0e0e0;
            font-size: 18px;
        }
        .chart {
            height: 300px;
            background: #0f1321;
            border-radius: 8px;
            padding: 10px;
        }
        .event-log {
            max-height: 400px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 12px;
        }
        .event {
            padding: 8px;
            margin: 4px 0;
            background: #0f1321;
            border-radius: 4px;
            border-left: 3px solid #667eea;
        }
        .timestamp {
            color: #10b981;
            margin-right: 10px;
        }
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            background: #667eea;
            color: white;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: background 0.2s;
        }
        button:hover { background: #5568d3; }
        button:disabled {
            background: #4a5568;
            cursor: not-allowed;
        }

        /* Game Arena Styles */
        .full-width {
            grid-column: 1 / -1;
        }
        .matches-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 20px;
        }
        .match-card {
            background: linear-gradient(135deg, #1a1f3a 0%, #2a2f4a 100%);
            border-radius: 12px;
            padding: 20px;
            border: 2px solid transparent;
            transition: all 0.3s ease;
        }
        .match-card.active {
            border-color: #667eea;
            box-shadow: 0 0 20px rgba(102, 126, 234, 0.3);
        }
        .match-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .match-id {
            font-weight: 600;
            color: #667eea;
        }
        .round-badge {
            background: rgba(102, 126, 234, 0.2);
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            color: #a0aec0;
        }
        .player-slot {
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 15px;
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            margin: 10px 0;
        }
        .player-avatar {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea, #764ba2);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 18px;
            flex-shrink: 0;
        }
        .player-info {
            flex: 1;
        }
        .player-name {
            font-weight: 600;
            margin-bottom: 4px;
        }
        .strategy-badge {
            font-size: 12px;
            color: #a0aec0;
            background: rgba(255,255,255,0.1);
            padding: 2px 8px;
            border-radius: 4px;
            display: inline-block;
            margin-right: 4px;
        }
        .role-badge {
            font-size: 12px;
            padding: 2px 8px;
            border-radius: 4px;
            display: inline-block;
            font-weight: 600;
        }
        .role-badge.ODD {
            background: rgba(236, 72, 153, 0.2);
            color: #ec4899;
        }
        .role-badge.EVEN {
            background: rgba(59, 130, 246, 0.2);
            color: #3b82f6;
        }
        .move-display {
            font-size: 36px;
            font-weight: bold;
            color: #667eea;
            animation: pulse 1s ease-in-out;
            min-width: 50px;
            text-align: center;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.2); }
        }
        .vs-divider {
            text-align: center;
            font-weight: bold;
            color: #a0aec0;
            font-size: 18px;
            padding: 10px 0;
        }
        .score-section {
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }
        .score-display {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }
        .score-label {
            color: #a0aec0;
            font-size: 14px;
        }
        .score-value {
            font-weight: 600;
            font-size: 18px;
            color: #667eea;
        }
        .score-bar {
            height: 8px;
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
            overflow: hidden;
        }
        .score-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            transition: width 0.5s ease;
        }

        /* Round History Styles */
        .round-history {
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }
        .round-history-title {
            font-size: 14px;
            font-weight: 600;
            color: #a0aec0;
            margin-bottom: 10px;
        }
        .round-history-items {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .round-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            background: rgba(255,255,255,0.03);
            border-radius: 6px;
            font-size: 13px;
            border-left: 3px solid transparent;
        }
        .round-label {
            font-weight: 600;
            color: #667eea;
            min-width: 30px;
        }
        .round-moves {
            color: #a0aec0;
        }
        .round-moves.winner {
            color: #10b981;
            font-weight: 600;
        }
        .round-plus, .round-equals {
            color: #667eea;
            font-weight: 600;
        }
        .round-sum {
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 4px;
        }
        .round-sum.odd {
            background: rgba(239, 68, 68, 0.2);
            color: #f87171;
        }
        .round-sum.even {
            background: rgba(59, 130, 246, 0.2);
            color: #60a5fa;
        }
        .round-winner {
            color: #10b981;
            font-weight: 600;
            margin-left: auto;
        }

        /* Strategy Evolution Tabs */
        .tabs {
            display: flex;
            gap: 5px;
            margin-bottom: 20px;
            border-bottom: 2px solid rgba(255,255,255,0.1);
        }
        .tab-btn {
            padding: 10px 20px;
            background: transparent;
            border: none;
            border-bottom: 3px solid transparent;
            color: #a0aec0;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
        }
        .tab-btn:hover {
            color: #e0e0e0;
            background: rgba(255,255,255,0.05);
        }
        .tab-btn.active {
            color: #667eea;
            border-bottom-color: #667eea;
        }
        .tab-content {
            min-height: 400px;
        }
        .tab-content.hidden {
            display: none;
        }

        /* Tournament Bracket/Flow Styles */
        .tournament-controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .view-btn {
            padding: 10px 20px;
            background: rgba(255,255,255,0.1);
            border: 2px solid rgba(102, 126, 234, 0.3);
            border-radius: 6px;
            color: #a0aec0;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
        }
        .view-btn:hover {
            background: rgba(102, 126, 234, 0.2);
            border-color: #667eea;
            color: #e0e0e0;
        }
        .view-btn.active {
            background: linear-gradient(135deg, #667eea, #764ba2);
            border-color: #667eea;
            color: white;
        }
        .tournament-view {
            min-height: 400px;
        }
        .tournament-view.hidden {
            display: none;
        }

        /* Matchup Matrix Styles */
        .matchup-matrix {
            width: 100%;
            border-collapse: collapse;
            overflow-x: auto;
            display: block;
        }
        .matchup-matrix table {
            width: 100%;
            border-collapse: collapse;
        }
        .matchup-matrix th,
        .matchup-matrix td {
            padding: 12px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
            min-width: 80px;
        }
        .matchup-matrix th {
            background: rgba(102, 126, 234, 0.2);
            font-weight: 600;
            color: #667eea;
            position: sticky;
            top: 0;
            z-index: 10;
        }
        .matchup-matrix th:first-child {
            position: sticky;
            left: 0;
            z-index: 11;
            background: rgba(102, 126, 234, 0.3);
        }
        .matchup-matrix td:first-child {
            background: rgba(102, 126, 234, 0.15);
            font-weight: 600;
            position: sticky;
            left: 0;
            z-index: 9;
        }
        .matrix-cell {
            cursor: pointer;
            transition: all 0.2s;
            position: relative;
        }
        .matrix-cell:hover {
            background: rgba(255,255,255,0.15);
            transform: scale(1.05);
        }
        .matrix-cell.win {
            background: rgba(34, 197, 94, 0.2);
            color: #22c55e;
            font-weight: 600;
        }
        .matrix-cell.loss {
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
        }
        .matrix-cell.draw {
            background: rgba(234, 179, 8, 0.2);
            color: #eab308;
        }
        .matrix-cell.pending {
            background: rgba(148, 163, 184, 0.2);
            color: #94a3b8;
        }

        /* Head-to-Head Stats */
        .h2h-stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        .h2h-card {
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        .h2h-card h4 {
            margin-bottom: 10px;
            color: #667eea;
            font-size: 16px;
        }
        .h2h-stat {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .h2h-stat:last-child {
            border-bottom: none;
        }
        .h2h-label {
            color: #a0aec0;
            font-size: 14px;
        }
        .h2h-value {
            color: #e0e0e0;
            font-weight: 600;
            font-size: 14px;
        }

        /* Replay Controls & Timeline Styles */
        .replay-section {
            background: linear-gradient(135deg, #1a1f3a 0%, #252a4a 100%);
            border: 2px solid rgba(102, 126, 234, 0.3);
        }
        .replay-controls {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .playback-buttons {
            display: flex;
            gap: 10px;
            justify-content: center;
            align-items: center;
        }
        .playback-buttons button {
            width: 50px;
            height: 50px;
            padding: 0;
            background: linear-gradient(135deg, #667eea, #764ba2);
            border: none;
            border-radius: 8px;
            color: white;
            cursor: pointer;
            font-size: 20px;
            transition: all 0.2s;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
        }
        .playback-buttons button:hover {
            transform: scale(1.1);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.5);
        }
        .playback-buttons button:active {
            transform: scale(0.95);
        }
        #play-pause-btn {
            width: 60px;
            height: 60px;
            font-size: 24px;
            background: linear-gradient(135deg, #22c55e, #16a34a);
        }
        #play-pause-btn.playing {
            background: linear-gradient(135deg, #ef4444, #dc2626);
        }

        /* Timeline Scrubber */
        .timeline-scrubber {
            display: flex;
            flex-direction: column;
            gap: 10px;
            padding: 15px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
        }
        .timeline-info {
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: #a0aec0;
            font-size: 14px;
            font-weight: 500;
        }
        .timeline-label {
            color: #667eea;
            font-weight: 600;
        }
        .timeline-slider {
            width: 100%;
            height: 8px;
            -webkit-appearance: none;
            appearance: none;
            background: linear-gradient(to right, #667eea 0%, rgba(102, 126, 234, 0.3) 100%);
            outline: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .timeline-slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 20px;
            height: 20px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            cursor: pointer;
            border-radius: 50%;
            box-shadow: 0 0 10px rgba(102, 126, 234, 0.5);
            transition: all 0.2s;
        }
        .timeline-slider::-webkit-slider-thumb:hover {
            width: 24px;
            height: 24px;
            box-shadow: 0 0 15px rgba(102, 126, 234, 0.8);
        }
        .timeline-slider::-moz-range-thumb {
            width: 20px;
            height: 20px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            cursor: pointer;
            border-radius: 50%;
            border: none;
            box-shadow: 0 0 10px rgba(102, 126, 234, 0.5);
        }
        .timeline-markers {
            height: 4px;
            position: relative;
            margin-top: -8px;
        }

        /* Playback Options */
        .playback-options {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }
        .speed-control {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .speed-control label {
            color: #a0aec0;
            font-size: 14px;
            font-weight: 500;
        }
        .speed-control select {
            padding: 8px 12px;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(102, 126, 234, 0.3);
            border-radius: 6px;
            color: white;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .speed-control select:hover {
            background: rgba(255,255,255,0.15);
            border-color: #667eea;
        }
        .replay-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .action-btn {
            padding: 8px 16px;
            background: rgba(102, 126, 234, 0.2);
            border: 1px solid rgba(102, 126, 234, 0.3);
            border-radius: 6px;
            color: #e0e0e0;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .action-btn:hover {
            background: rgba(102, 126, 234, 0.3);
            border-color: #667eea;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }

        /* Replay Status */
        .replay-status {
            display: flex;
            justify-content: space-between;
            padding: 10px 15px;
            background: rgba(0,0,0,0.2);
            border-radius: 6px;
            font-size: 13px;
        }
        #replay-status-text {
            color: #a0aec0;
        }
        #replay-status-text.playing {
            color: #22c55e;
            font-weight: 600;
        }
        #snapshots-count {
            color: #667eea;
            font-weight: 500;
        }

        /* Winner Celebration Modal */
        .winner-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.9);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 10000;
            animation: fadeIn 0.5s ease;
        }
        .winner-modal.hidden {
            display: none;
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        .winner-content {
            background: linear-gradient(135deg, #1a1f3a 0%, #2a2f4a 100%);
            padding: 60px 40px;
            border-radius: 20px;
            text-align: center;
            position: relative;
            max-width: 600px;
            border: 3px solid #ffd700;
            box-shadow: 0 0 50px rgba(255, 215, 0, 0.5);
            animation: scaleIn 0.5s ease;
        }
        @keyframes scaleIn {
            from { transform: scale(0.5); opacity: 0; }
            to { transform: scale(1); opacity: 1; }
        }
        .confetti-container {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            pointer-events: none;
        }
        .confetti-piece {
            position: absolute;
            width: 10px;
            height: 10px;
            background: #ffd700;
            top: -10px;
            animation: confettiFall 3s linear infinite;
        }
        @keyframes confettiFall {
            to {
                transform: translateY(120vh) rotate(360deg);
                opacity: 0;
            }
        }
        .winner-trophy {
            font-size: 80px;
            animation: bounce 1s ease infinite;
        }
        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-20px); }
        }
        .winner-title {
            color: #ffd700;
            font-size: 48px;
            margin: 20px 0;
            text-shadow: 0 0 20px rgba(255, 215, 0, 0.5);
            animation: glow 2s ease-in-out infinite;
        }
        @keyframes glow {
            0%, 100% { text-shadow: 0 0 20px rgba(255, 215, 0, 0.5); }
            50% { text-shadow: 0 0 40px rgba(255, 215, 0, 0.8); }
        }
        .winner-avatar-large {
            width: 150px;
            height: 150px;
            margin: 20px auto;
            border-radius: 50%;
            background: linear-gradient(135deg, #ffd700, #ffed4e);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 80px;
            box-shadow: 0 0 30px rgba(255, 215, 0, 0.6);
            animation: rotate 3s linear infinite;
        }
        @keyframes rotate {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        .winner-name {
            font-size: 36px;
            color: #e0e0e0;
            margin: 20px 0;
            font-weight: 700;
        }
        .winner-strategy {
            font-size: 18px;
            color: #a0aec0;
            margin-bottom: 30px;
            padding: 10px 20px;
            background: rgba(255, 215, 0, 0.1);
            border-radius: 20px;
            display: inline-block;
        }
        .winner-stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin: 30px 0;
        }
        .winner-stat-box {
            background: rgba(255, 215, 0, 0.1);
            padding: 20px;
            border-radius: 12px;
            border: 2px solid rgba(255, 215, 0, 0.3);
        }
        .winner-stat-box .stat-value {
            font-size: 36px;
            font-weight: 700;
            color: #ffd700;
            margin-bottom: 8px;
        }
        .winner-stat-box .stat-label {
            font-size: 14px;
            color: #a0aec0;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .close-winner-btn {
            margin-top: 30px;
            padding: 15px 40px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            border: none;
            border-radius: 30px;
            color: white;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        .close-winner-btn:hover {
            transform: scale(1.1);
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.5);
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>
            🎮 MCP Game League - Real-Time Dashboard
            <span id="status" class="connection-status disconnected">Disconnected</span>
        </h1>
    </div>

    <div class="container">
        <div class="controls">
            <button onclick="connectWebSocket()">Connect</button>
            <button onclick="startTournament()" style="background: #27ae60;">🚀 Start Tournament</button>
            <button onclick="runRound()" style="background: #3498db;">▶️ Run Round</button>
            <button onclick="clearData()" style="background: #e74c3c;">🔄 Reset Tournament</button>
            <button onclick="exportData()">Export Data</button>
        </div>

        <div class="grid">
            <div class="card">
                <h2>📊 Tournament Overview</h2>
                <div class="metric">
                    <span class="metric-label">Game Type</span>
                    <span class="metric-value" id="game-type">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Current Round</span>
                    <span class="metric-value" id="current-round">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Active Players</span>
                    <span class="metric-value" id="active-players">-</span>
                </div>
            </div>

            <div class="card">
                <h2>🏆 Player Standings & Strategies</h2>
                <table class="standings-table">
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Player & Strategy</th>
                            <th>Last Move</th>
                            <th>Points</th>
                            <th>W</th>
                            <th>D</th>
                            <th>L</th>
                            <th>Matches</th>
                            <th>Win %</th>
                        </tr>
                    </thead>
                    <tbody id="standings-tbody">
                        <tr>
                            <td colspan="6" style="text-align: center; color: #a0aec0; padding: 40px;">
                                Waiting for tournament data...
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Real-Time Game Arena -->
        <div class="card full-width">
            <h2>🎮 Live Game Arena</h2>
            <div id="active-matches" class="matches-grid">
                <p style="color: #a0aec0; text-align: center; padding: 40px;">No active matches</p>
            </div>
        </div>

        <!-- Strategy Evolution Visualization -->
        <div class="card full-width">
            <h2>🧠 Strategy Learning Evolution</h2>
            <div class="tabs">
                <button class="tab-btn active" onclick="showEvolutionTab('beliefs')">Bayesian Beliefs</button>
                <button class="tab-btn" onclick="showEvolutionTab('confidence')">Confidence</button>
                <button class="tab-btn" onclick="showEvolutionTab('regret')">Regret Analysis</button>
                <button class="tab-btn" onclick="showEvolutionTab('learning')">Learning Curve</button>
            </div>
            <div id="evolution-beliefs" class="tab-content">
                <div id="beliefs-chart" class="chart"></div>
            </div>
            <div id="evolution-confidence" class="tab-content hidden">
                <div id="confidence-chart" class="chart"></div>
            </div>
            <div id="evolution-regret" class="tab-content hidden">
                <div id="regret-chart-evolution" class="chart"></div>
            </div>
            <div id="evolution-learning" class="tab-content hidden">
                <div id="learning-chart" class="chart"></div>
            </div>
        </div>

        <!-- Tournament Bracket/Flow Visualization -->
        <div class="card full-width">
            <h2>🏆 Tournament Flow & Standings</h2>
            <div class="tournament-controls">
                <button class="view-btn active" onclick="showTournamentView('matrix')">Matchup Matrix</button>
                <button class="view-btn" onclick="showTournamentView('standings')">Standings Race</button>
                <button class="view-btn" onclick="showTournamentView('stats')">Head-to-Head Stats</button>
            </div>
            <div id="tournament-matrix" class="tournament-view">
                <div id="matchup-matrix"></div>
            </div>
            <div id="tournament-standings" class="tournament-view hidden">
                <div id="standings-race-chart" class="chart"></div>
            </div>
            <div id="tournament-stats" class="tournament-view hidden">
                <div id="head-to-head-stats"></div>
            </div>
        </div>

        <!-- Replay Controls & Timeline -->
        <div class="card full-width replay-section">
            <h2>⏯️ Tournament Replay</h2>

            <div class="replay-controls">
                <div class="playback-buttons">
                    <button onclick="replayJumpStart()" title="Jump to Start">⏮️</button>
                    <button onclick="replayStepBack()" title="Step Back">⏪</button>
                    <button id="play-pause-btn" onclick="replayTogglePlay()" title="Play/Pause">▶️</button>
                    <button onclick="replayStepForward()" title="Step Forward">⏩</button>
                    <button onclick="replayJumpEnd()" title="Jump to End">⏭️</button>
                </div>

                <div class="timeline-scrubber">
                    <div class="timeline-info">
                        <span id="current-round-display" class="timeline-label">Round 0</span>
                        <span id="total-rounds-display" class="timeline-label">/ 0</span>
                    </div>
                    <input type="range" id="timeline-slider" min="0" max="100" value="0"
                           oninput="replayScrub(this.value)" class="timeline-slider">
                    <div class="timeline-markers" id="timeline-markers"></div>
                </div>

                <div class="playback-options">
                    <div class="speed-control">
                        <label for="playback-speed">Speed:</label>
                        <select id="playback-speed" onchange="setPlaybackSpeed(this.value)">
                            <option value="0.25">0.25x</option>
                            <option value="0.5">0.5x</option>
                            <option value="1" selected>1x</option>
                            <option value="2">2x</option>
                            <option value="5">5x</option>
                            <option value="10">10x</option>
                        </select>
                    </div>

                    <div class="replay-actions">
                        <button onclick="captureSnapshot()" class="action-btn" title="Capture current state">
                            📸 Snapshot
                        </button>
                        <button onclick="compareSnapshots()" class="action-btn" title="Compare snapshots">
                            📊 Compare
                        </button>
                        <button onclick="exportReplay()" class="action-btn" title="Export replay data">
                            💾 Export
                        </button>
                    </div>
                </div>

                <div class="replay-status">
                    <span id="replay-status-text">Ready to replay</span>
                    <span id="snapshots-count">Snapshots: 0</span>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>📈 Strategy Performance Over Time</h2>
            <div id="performance-chart" class="chart"></div>
        </div>

        <div class="card">
            <h2>🎯 Opponent Model Confidence</h2>
            <div id="opponent-model-chart" class="chart"></div>
        </div>

        <div class="card">
            <h2>🔄 Counterfactual Regret Analysis</h2>
            <div id="regret-chart" class="chart"></div>
        </div>

        <div class="card">
            <h2>📝 Live Event Log</h2>
            <div id="event-log" class="event-log"></div>
        </div>
    </div>

    <!-- Winner Celebration Modal -->
    <div id="winner-modal" class="winner-modal hidden">
        <div class="winner-content">
            <div class="confetti-container" id="confetti-container"></div>
            <div class="winner-trophy">🏆</div>
            <h1 class="winner-title">Tournament Champion!</h1>
            <div class="winner-avatar-large" id="winner-avatar">🥇</div>
            <h2 class="winner-name" id="winner-name">Champion</h2>
            <div class="winner-strategy" id="winner-strategy">Strategy: Unknown</div>
            <div class="winner-stats-grid">
                <div class="winner-stat-box">
                    <div class="stat-value" id="winner-wins">0</div>
                    <div class="stat-label">Wins</div>
                </div>
                <div class="winner-stat-box">
                    <div class="stat-value" id="winner-points">0</div>
                    <div class="stat-label">Points</div>
                </div>
                <div class="winner-stat-box">
                    <div class="stat-value" id="winner-winrate">0%</div>
                    <div class="stat-label">Win Rate</div>
                </div>
            </div>
            <button class="close-winner-btn" onclick="closeWinnerModal()">Close</button>
        </div>
    </div>

    <script>
        let ws = null;
        let performanceData = {};
        let opponentModelData = {};
        let regretData = {};
        let events = [];
        let currentMatches = {}; // Store current match states by match_id
        let playerLastMoves = {}; // Store last move for each player

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host;
            ws = new WebSocket(`${protocol}//${host}/ws`);

            ws.onopen = () => {
                document.getElementById('status').textContent = 'Connected';
                document.getElementById('status').className = 'connection-status connected';
                addLog('Connected to dashboard');
            };

            ws.onclose = () => {
                document.getElementById('status').textContent = 'Disconnected';
                document.getElementById('status').className = 'connection-status disconnected';
                addLog('Disconnected from dashboard');
            };

            ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                handleMessage(message);
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                addLog('WebSocket error occurred', 'error');
            };

            // Send ping every 30 seconds
            setInterval(() => {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send('ping');
                }
            }, 30000);
        }

        function handleMessage(message) {
            switch (message.type) {
                case 'tournament_state':
                    // Handle initial state on reconnect
                    handleTournamentUpdate(message.data);
                    addLog('Tournament state restored');
                    break;
                case 'state_update':
                    // Handle events forwarded from state sync service
                    const eventType = message.event_type;
                    const eventData = message.data;

                    if (eventType === 'strategy.performance') {
                        handleStrategyPerformance(eventData);
                    } else if (eventType === 'opponent.model.update') {
                        handleOpponentModelUpdate(eventData);
                    } else if (eventType === 'counterfactual.analysis') {
                        handleCounterfactualUpdate(eventData);
                    } else if (eventType === 'tournament.completed') {
                        handleTournamentComplete(eventData);
                    }
                    break;
                case 'game_event':
                    handleGameEvent(message.data);
                    break;
                case 'tournament_update':
                    handleTournamentUpdate(message.data);
                    break;
                case 'strategy_performance':
                    handleStrategyPerformance(message.data);
                    break;
                case 'opponent_model_update':
                    handleOpponentModelUpdate(message.data);
                    break;
                case 'counterfactual_update':
                    handleCounterfactualUpdate(message.data);
                    break;
                case 'match_update':
                    handleMatchUpdate(message.data);
                    break;
                case 'matchup_matrix_update':
                    handleMatchupMatrixUpdate(message.data);
                    break;
                case 'tournament_complete':
                    handleTournamentComplete(message.data);
                    break;
            }
        }

        function handleGameEvent(data) {
            events.push(data);
            console.log('Game event received:', data); // Debug logging
            addLog(`Round ${data.round}: ${data.event_type}`);

            // Update game arena when moves are made
            if (data.event_type === 'move' || data.event_type === 'round_end') {
                // Create match display from game event data
                if (data.players && data.players.length >= 2) {
                    const matchId = `Round_${data.round}_${data.players[0]}_vs_${data.players[1]}`;

                    // Get or create match state
                    if (!currentMatches[matchId]) {
                        currentMatches[matchId] = {
                            match_id: matchId,
                            round: data.round,
                            total_rounds: data.round,
                            state: 'IN_PROGRESS',
                            player_a: {
                                id: data.players[0],
                                name: getPlayerDisplayName(data.players[0]),
                                strategy: getPlayerStrategy(data.players[0]),
                                role: 'ODD',
                                move: '',
                                score: 0
                            },
                            player_b: {
                                id: data.players[1],
                                name: getPlayerDisplayName(data.players[1]),
                                strategy: getPlayerStrategy(data.players[1]),
                                role: 'EVEN',
                                move: '',
                                score: 0
                            }
                        };
                    }

                    const match = currentMatches[matchId];

                    // Update moves and track last moves
                    if (data.moves) {
                        if (data.moves[data.players[0]]) {
                            match.player_a.move = data.moves[data.players[0]];
                            // Store last move for this player
                            playerLastMoves[data.players[0]] = data.moves[data.players[0]];
                            playerLastMoves[match.player_a.name] = data.moves[data.players[0]];
                        }
                        if (data.moves[data.players[1]]) {
                            match.player_b.move = data.moves[data.players[1]];
                            // Store last move for this player
                            playerLastMoves[data.players[1]] = data.moves[data.players[1]];
                            playerLastMoves[match.player_b.name] = data.moves[data.players[1]];
                        }
                    }

                    // Update scores - for round_end events, scores field contains cumulative scores
                    console.log('[DEBUG] Game event:', {
                        type: data.event_type,
                        scores: data.scores,
                        metadata: data.metadata,
                        players: data.players
                    });

                    // Only update scores on round_end events (scores are cumulative)
                    if (data.event_type === 'round_end' && data.scores && Object.keys(data.scores).length > 0) {
                        match.player_a.score = data.scores[data.players[0]] || 0;
                        match.player_b.score = data.scores[data.players[1]] || 0;
                        console.log('[DEBUG] Score updated:', match.player_a.score, '-', match.player_b.score);
                    }

                    // Update state
                    match.state = data.event_type === 'round_end' ? 'FINISHED' : 'IN_PROGRESS';

                    // Update game arena with all current matches
                    updateGameArena(Object.values(currentMatches));

                    // Refresh standings table to show updated last moves
                    const tbody = document.getElementById('standings-tbody');
                    if (tbody && tbody.innerHTML !== '<tr><td colspan="9" style="text-align: center; color: #a0aec0; padding: 40px;">No data yet</td></tr>') {
                        // Trigger standings refresh by calling handleTournamentUpdate with current data
                        // This will re-render the standings table with new last moves
                        const currentRound = document.getElementById('current-round').textContent;
                        const gameType = document.getElementById('game-type').textContent;
                        const activePlayers = document.getElementById('active-players').textContent;

                        // Extract current standings from table and re-render
                        const rows = tbody.querySelectorAll('tr');
                        if (rows.length > 0 && rows[0].querySelector('.player-name')) {
                            const standings = Array.from(rows).map(row => {
                                const playerName = row.querySelector('.player-name')?.textContent;
                                const strategy = row.querySelector('.strategy-badge')?.textContent;
                                const points = parseInt(row.querySelector('.score-cell')?.textContent || '0');
                                const wins = parseInt(row.querySelector('.wins-cell')?.textContent || '0');
                                const draws = parseInt(row.querySelector('.draws-cell')?.textContent || '0');
                                const losses = parseInt(row.querySelector('.losses-cell')?.textContent || '0');
                                const matches = parseInt(row.cells[7]?.textContent || '0');

                                return {
                                    player_id: playerName,
                                    display_name: playerName,
                                    strategy: strategy,
                                    points: points,
                                    wins: wins,
                                    draws: draws,
                                    losses: losses,
                                    total_matches: matches
                                };
                            });

                            updateStandingsTable(standings);
                        }
                    }

                    // Add to event log with move details
                    if (data.moves && Object.keys(data.moves).length > 0) {
                        const movesText = Object.entries(data.moves)
                            .filter(([_, move]) => move !== null && move !== undefined && move !== '')
                            .map(([player, move]) => `${getPlayerDisplayName(player)}: ${move}`)
                            .join(', ');
                        if (movesText) {
                            addLog(`🎲 Moves: ${movesText}`);
                        }
                    } else {
                        console.log('No moves in event data:', data);
                    }

                    // Clean up finished matches after a delay
                    if (data.event_type === 'round_end') {
                        setTimeout(() => {
                            delete currentMatches[matchId];
                            updateGameArena(Object.values(currentMatches));
                        }, 5000); // Keep for 5 seconds after round ends
                    }
                }
            }
        }

        // Helper function to get player display name from standings
        function getPlayerDisplayName(playerId) {
            const tbody = document.getElementById('standings-tbody');
            if (tbody) {
                const rows = tbody.querySelectorAll('tr');
                for (const row of rows) {
                    const nameDiv = row.querySelector('.player-name');
                    if (nameDiv && row.textContent.includes(playerId)) {
                        return nameDiv.textContent.trim();
                    }
                }
            }
            return playerId;
        }

        // Helper function to get player strategy from standings
        function getPlayerStrategy(playerId) {
            const tbody = document.getElementById('standings-tbody');
            if (tbody) {
                const rows = tbody.querySelectorAll('tr');
                for (const row of rows) {
                    if (row.textContent.includes(playerId)) {
                        const badge = row.querySelector('.strategy-badge');
                        if (badge) {
                            return badge.textContent.trim();
                        }
                    }
                }
            }
            return 'unknown';
        }

        function handleTournamentUpdate(data) {
            // Store tournament state globally for other functions to access
            window.tournamentState = data;

            document.getElementById('game-type').textContent = data.game_type || 'even_odd';
            document.getElementById('current-round').textContent =
                `${data.current_round || 0} / ${data.total_rounds || 0}`;

            // Calculate active players from standings (more reliable than players array)
            const activePlayers = data.standings ? data.standings.length : (data.players ? data.players.length : 0);
            document.getElementById('active-players').textContent = activePlayers;

            // Update enhanced standings table
            updateStandingsTable(data.standings || []);

            // Update active matches if present
            if (data.active_matches && data.active_matches.length > 0) {
                updateGameArena(data.active_matches);
            }

            // Update Standings Race chart if it's visible
            const standingsView = document.getElementById('tournament-standings');
            if (standingsView && !standingsView.classList.contains('hidden')) {
                createStandingsRace();
            }

            // Initialize learning evolution charts if we have player data
            if (data.standings && data.standings.length > 0) {
                // Trigger initial chart updates after a short delay to allow data to load
                setTimeout(() => {
                    updateBeliefsChart();
                    updateConfidenceEvolutionChart();
                    updateRegretEvolutionChart();
                    updateLearningCurve();
                }, 500);
            }
        }

        function updateStandingsTable(standings) {
            const tbody = document.getElementById('standings-tbody');

            if (!standings || standings.length === 0) {
                tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: #a0aec0; padding: 40px;">No data yet</td></tr>';
                return;
            }

            tbody.innerHTML = standings.map((player, index) => {
                const rank = index + 1;
                let rankClass = 'rank-other';
                if (rank === 1) rankClass = 'rank-1';
                else if (rank === 2) rankClass = 'rank-2';
                else if (rank === 3) rankClass = 'rank-3';

                const playerId = player.player_id || player.player || `Player ${rank}`;
                const playerName = player.display_name || player.player_name || playerId;
                const strategy = player.strategy || 'Unknown';
                const points = player.points || 0;
                const wins = player.wins || player.total_wins || 0;
                const draws = player.draws || 0;
                const losses = player.losses || 0;
                const matches = player.total_matches || player.matches_played || player.played || 0;
                const winRate = matches > 0
                    ? ((wins / matches) * 100).toFixed(1)
                    : '0.0';

                // Get last move for this player - prioritize standings data, then fall back to tracked moves
                const lastMove = player.last_move || playerLastMoves[playerId] || playerLastMoves[playerName] || null;
                const lastMoveDisplay = lastMove !== null && lastMove !== undefined && lastMove !== '-'
                    ? `<span class="last-move-badge">${lastMove}</span>`
                    : '<span style="color: #a0aec0;">-</span>';

                // Update playerLastMoves cache with standings data
                if (player.last_move) {
                    playerLastMoves[playerId] = player.last_move;
                    playerLastMoves[playerName] = player.last_move;
                }

                return `
                    <tr>
                        <td>
                            <div class="rank-badge ${rankClass}">${rank}</div>
                        </td>
                        <td>
                            <div class="player-cell">
                                <div class="player-avatar">${playerName.substring(0, 2).toUpperCase()}</div>
                                <div class="player-details">
                                    <div class="player-name">${playerName}</div>
                                    <span class="strategy-badge">${strategy}</span>
                                </div>
                            </div>
                        </td>
                        <td style="text-align: center; font-size: 20px; font-weight: bold;">${lastMoveDisplay}</td>
                        <td class="score-cell">${points}</td>
                        <td class="wins-cell">${wins}</td>
                        <td class="draws-cell">${draws}</td>
                        <td class="losses-cell">${losses}</td>
                        <td>${matches}</td>
                        <td class="winrate-cell">${winRate}%</td>
                    </tr>
                `;
            }).join('');
        }

        function handleStrategyPerformance(data) {
            performanceData[data.strategy_name] = data;
            updatePerformanceChart();
            // Also update learning evolution charts
            updateBeliefsChart();
            updateLearningCurve();
        }

        function handleOpponentModelUpdate(data) {
            // Handle both old format and new format
            if (data.model) {
                opponentModelData[data.player_id] = data.model;
            } else if (data.data) {
                // New format from analytics
                opponentModelData[data.player_id] = data.data;
            }
            updateOpponentModelChart();
            updateConfidenceEvolutionChart();
        }

        function handleCounterfactualUpdate(data) {
            // Handle both old format and new format
            if (data.counterfactual) {
                regretData[data.player_id] = data.counterfactual;
            } else if (data.data) {
                // New format from analytics
                regretData[data.player_id] = data.data;
            }
            updateRegretChart();
            updateRegretEvolutionChart();
        }

        function handleMatchupMatrixUpdate(data) {
            // Store matchup matrix data
            window.matchupMatrixData = data;
            // Always update matrix view to keep data fresh
            // (Even if not currently visible, it will be ready when user clicks the tab)
            createMatchupMatrix();

            // Also update head-to-head stats if it's visible or needs updating
            const statsView = document.getElementById('tournament-stats');
            if (statsView && !statsView.classList.contains('hidden')) {
                createHeadToHeadStats();
            }
        }

        function handleMatchUpdate(data) {
            // Update game arena with match data
            updateGameArena(data);
        }

        function updateGameArena(matchesData) {
            const container = document.getElementById('active-matches');

            // Handle both single match and array of matches
            const matches = Array.isArray(matchesData) ? matchesData : [matchesData];

            if (matches.length === 0 || (matches.length === 1 && !matches[0].match_id)) {
                container.innerHTML = '<p style="color: #a0aec0; text-align: center; padding: 40px;">No active matches</p>';
                return;
            }

            // Debug: Log match data to see round_history
            console.log('[DEBUG] Match data:', matches.map(m => ({
                match_id: m.match_id,
                round_history_count: m.round_history ? m.round_history.length : 0,
                round_history: m.round_history
            })));

            container.innerHTML = matches.map(match => {
                const player_a = match.player_a || {};
                const player_b = match.player_b || {};
                const totalScore = (player_a.score || 0) + (player_b.score || 0);
                const scorePercentage = totalScore > 0 ? ((player_a.score || 0) / totalScore * 100) : 50;

                // Generate round history HTML
                let roundHistoryHtml = '';
                if (match.round_history && match.round_history.length > 0) {
                    roundHistoryHtml = `
                        <div class="round-history">
                            <div class="round-history-title">Round Details:</div>
                            <div class="round-history-items">
                                ${match.round_history.map(round => {
                                    const sumParity = round.sum_is_odd ? 'ODD' : 'EVEN';
                                    const sumParityClass = round.sum_is_odd ? 'odd' : 'even';
                                    const isPlayer1Winner = round.winner_id === player_a.id;
                                    const isPlayer2Winner = round.winner_id === player_b.id;

                                    return `
                                        <div class="round-item">
                                            <span class="round-label">R${round.round_number}</span>
                                            <span class="round-moves ${isPlayer1Winner ? 'winner' : ''}">${player_a.name}: ${round.player1_move}</span>
                                            <span class="round-plus">+</span>
                                            <span class="round-moves ${isPlayer2Winner ? 'winner' : ''}">${player_b.name}: ${round.player2_move}</span>
                                            <span class="round-equals">=</span>
                                            <span class="round-sum ${sumParityClass}">${round.sum} (${sumParity})</span>
                                            <span class="round-winner">→ ${round.winner_name || 'Unknown'} ✓</span>
                                        </div>
                                    `;
                                }).join('')}
                            </div>
                        </div>
                    `;
                }

                return `
                    <div class="match-card ${match.state === 'IN_PROGRESS' ? 'active' : ''}">
                        <div class="match-header">
                            <span class="match-id">${match.match_id || 'Match'}</span>
                            <span class="round-badge">Tournament Round ${match.round || 0}/${match.total_rounds || 0}</span>
                            ${match.game_rounds ? `<span class="round-badge" style="background: #667eea;">Game Round ${match.game_round_current || 0}/${match.game_rounds}</span>` : ''}
                        </div>

                        <div class="player-slot">
                            <div class="player-avatar">${(player_a.id || 'P1').substring(0,2)}</div>
                            <div class="player-info">
                                <div class="player-name">${player_a.name || player_a.id || 'Player A'}</div>
                                <div>
                                    <span class="strategy-badge">${player_a.strategy || 'unknown'}</span>
                                    <span class="role-badge ${player_a.role || 'ODD'}">${player_a.role || 'ODD'}</span>
                                </div>
                            </div>
                            ${player_a.move ? `<div class="move-display" title="Current move">${player_a.move}</div>` :
                              (playerLastMoves[player_a.id] || playerLastMoves[player_a.name]) ?
                              `<div class="move-display" style="opacity: 0.6; font-size: 28px;" title="Last move">${playerLastMoves[player_a.id] || playerLastMoves[player_a.name]}</div>` :
                              ''}
                        </div>

                        <div class="vs-divider">VS</div>

                        <div class="player-slot">
                            <div class="player-avatar">${(player_b.id || 'P2').substring(0,2)}</div>
                            <div class="player-info">
                                <div class="player-name">${player_b.name || player_b.id || 'Player B'}</div>
                                <div>
                                    <span class="strategy-badge">${player_b.strategy || 'unknown'}</span>
                                    <span class="role-badge ${player_b.role || 'EVEN'}">${player_b.role || 'EVEN'}</span>
                                </div>
                            </div>
                            ${player_b.move ? `<div class="move-display" title="Current move">${player_b.move}</div>` :
                              (playerLastMoves[player_b.id] || playerLastMoves[player_b.name]) ?
                              `<div class="move-display" style="opacity: 0.6; font-size: 28px;" title="Last move">${playerLastMoves[player_b.id] || playerLastMoves[player_b.name]}</div>` :
                              ''}
                        </div>

                        <div class="score-section">
                            <div class="score-display">
                                <span class="score-label">Score:</span>
                                <span class="score-value">${player_a.score || 0} - ${player_b.score || 0}</span>
                            </div>
                            <div class="score-bar">
                                <div class="score-fill" style="width: ${scorePercentage}%"></div>
                            </div>
                        </div>

                        ${roundHistoryHtml}
                    </div>
                `;
            }).join('');
        }

        function updatePerformanceChart() {
            const traces = Object.values(performanceData).map(perf => ({
                x: perf.rounds,
                y: perf.win_rates,
                type: 'scatter',
                mode: 'lines+markers',
                name: perf.strategy_name,
                line: { width: 2 }
            }));

            const layout = {
                title: 'Win Rate Over Time',
                xaxis: { title: 'Round', color: '#a0aec0', gridcolor: '#2a2f4a' },
                yaxis: { title: 'Win Rate', color: '#a0aec0', gridcolor: '#2a2f4a' },
                plot_bgcolor: '#0f1321',
                paper_bgcolor: '#0f1321',
                font: { color: '#e0e0e0' },
                showlegend: true,
                legend: { bgcolor: '#1a1f3a', bordercolor: '#2a2f4a', borderwidth: 1 }
            };

            Plotly.newPlot('performance-chart', traces, layout, {responsive: true});
        }

        function updateOpponentModelChart() {
            const data = Object.values(opponentModelData);
            const trace = {
                x: data.map(m => m.opponent_id),
                y: data.map(m => m.confidence),
                type: 'bar',
                marker: { color: '#667eea' }
            };

            const layout = {
                title: 'Opponent Classification Confidence',
                xaxis: { title: 'Opponent', color: '#a0aec0' },
                yaxis: { title: 'Confidence', color: '#a0aec0', range: [0, 1] },
                plot_bgcolor: '#0f1321',
                paper_bgcolor: '#0f1321',
                font: { color: '#e0e0e0' }
            };

            Plotly.newPlot('opponent-model-chart', [trace], layout, {responsive: true});
        }

        function updateRegretChart() {
            const data = Object.values(regretData);
            if (data.length === 0) return;

            const latest = data[data.length - 1];
            const trace = {
                x: latest.counterfactuals.map(cf => cf.move),
                y: latest.counterfactuals.map(cf => cf.regret),
                type: 'bar',
                marker: {
                    color: latest.counterfactuals.map(cf => cf.regret > 0 ? '#ef4444' : '#10b981')
                }
            };

            const layout = {
                title: `Regret Analysis (Round ${latest.round})`,
                xaxis: { title: 'Alternative Move', color: '#a0aec0' },
                yaxis: { title: 'Regret', color: '#a0aec0' },
                plot_bgcolor: '#0f1321',
                paper_bgcolor: '#0f1321',
                font: { color: '#e0e0e0' }
            };

            Plotly.newPlot('regret-chart', [trace], layout, {responsive: true});
        }

        function addLog(message, level = 'info') {
            const logDiv = document.getElementById('event-log');
            const timestamp = new Date().toLocaleTimeString();
            const eventDiv = document.createElement('div');
            eventDiv.className = 'event';
            eventDiv.innerHTML = `<span class="timestamp">[${timestamp}]</span>${message}`;
            logDiv.appendChild(eventDiv);
            logDiv.scrollTop = logDiv.scrollHeight;
        }

        // Strategy Evolution Visualization Functions
        function showEvolutionTab(tabName) {
            // Hide all tab contents
            document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
            // Remove active class from all tabs
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));

            // Show selected tab content
            document.getElementById(`evolution-${tabName}`).classList.remove('hidden');
            // Activate clicked tab button
            event.target.classList.add('active');

            // Trigger chart update for the selected tab
            switch(tabName) {
                case 'beliefs':
                    updateBeliefsChart();
                    break;
                case 'confidence':
                    updateConfidenceEvolutionChart();
                    break;
                case 'regret':
                    updateRegretEvolutionChart();
                    break;
                case 'learning':
                    updateLearningCurve();
                    break;
            }
        }

        function updateBeliefsChart() {
            // Get player list from either WebSocket data OR tournament state
            let players = Object.keys(opponentModelData);

            // If no WebSocket data, try getting players from tournament state standings
            // Use display_name (Alice, Bob, etc.) not player_id (P01, P02, etc.)
            if (players.length === 0 && window.tournamentState && window.tournamentState.standings) {
                players = window.tournamentState.standings.map(s => s.display_name || s.player_id || s.player || s.name);
                console.log('[Beliefs] Using player names from standings:', players);
            }

            if (players.length === 0) {
                // Show placeholder
                Plotly.newPlot('beliefs-chart', [], {
                    title: 'Bayesian Belief Evolution - Waiting for data...',
                    xaxis: { title: 'Round' },
                    yaxis: { title: 'Belief Probability', range: [0, 1] },
                    template: 'plotly_dark',
                    paper_bgcolor: '#1a1f3a',
                    plot_bgcolor: '#1a1f3a'
                });
                return;
            }

            // Fetch detailed opponent model data from API
            Promise.all(players.map(pid =>
                fetch(`/api/analytics/opponent_models/${pid}`)
                    .then(r => r.json())
                    .catch(() => null)
            )).then(results => {
                const traces = [];

                results.forEach((data, idx) => {
                    if (!data || !data.opponent_models) return;

                    const playerId = players[idx];
                    Object.entries(data.opponent_models).forEach(([oppId, model]) => {
                        if (model.time_series && model.time_series.rounds.length > 0) {
                            traces.push({
                                x: model.time_series.rounds,
                                y: model.time_series.confidence_history,
                                name: `${playerId.substring(0, 8)} → ${oppId.substring(0, 8)} (${model.predicted_strategy})`,
                                mode: 'lines+markers',
                                line: { width: 2 },
                                marker: { size: 6 }
                            });
                        }
                    });
                });

                if (traces.length === 0) {
                    traces.push({
                        x: [1],
                        y: [0.5],
                        mode: 'markers',
                        name: 'No data yet',
                        marker: { size: 1, opacity: 0 }
                    });
                }

                Plotly.newPlot('beliefs-chart', traces, {
                    title: 'Opponent Model Confidence Evolution',
                    xaxis: { title: 'Round' },
                    yaxis: { title: 'Model Confidence', range: [0, 1] },
                    template: 'plotly_dark',
                    paper_bgcolor: '#1a1f3a',
                    plot_bgcolor: '#1a1f3a'
                });
            });
        }

        function updateConfidenceEvolutionChart() {
            // Get player list from tournament state standings
            let players = [];
            if (window.tournamentState && window.tournamentState.standings) {
                players = window.tournamentState.standings.map(s => s.display_name || s.player_id || s.player || s.name);
                console.log('[Confidence] Using player names from standings:', players);
            }

            if (players.length === 0) {
                Plotly.newPlot('confidence-chart', [], {
                    title: 'Opponent Model Confidence Evolution - Waiting for data...',
                    xaxis: { title: 'Round' },
                    yaxis: { title: 'Confidence', range: [0, 1] },
                    template: 'plotly_dark',
                    paper_bgcolor: '#1a1f3a',
                    plot_bgcolor: '#1a1f3a'
                });
                return;
            }

            // Fetch detailed opponent model analytics from API (same as Bayesian Beliefs)
            Promise.all(players.map(pid =>
                fetch(`/api/analytics/opponent_models/${pid}`)
                    .then(r => r.json())
                    .catch(() => null)
            )).then(results => {
                const traces = [];

                results.forEach((data, idx) => {
                    if (!data || !data.opponent_models) return;

                    const playerId = players[idx];
                    Object.entries(data.opponent_models).forEach(([oppId, model]) => {
                        if (model.time_series && model.time_series.rounds.length > 0) {
                            traces.push({
                                x: model.time_series.rounds,
                                y: model.time_series.confidence_history,
                                name: `${playerId.substring(0, 8)} → ${oppId.substring(0, 8)}`,
                                mode: 'lines+markers',
                                line: { width: 2 },
                                marker: { size: 6 }
                            });
                        }
                    });
                });

                if (traces.length === 0) {
                    traces.push({
                        x: [0],
                        y: [0.5],
                        mode: 'markers',
                        name: 'No data yet',
                        marker: { size: 1, opacity: 0 }
                    });
                }

                Plotly.newPlot('confidence-chart', traces, {
                    title: 'Opponent Model Confidence Evolution',
                    xaxis: { title: 'Round' },
                    yaxis: { title: 'Model Confidence', range: [0, 1] },
                    template: 'plotly_dark',
                    paper_bgcolor: '#1a1f3a',
                    plot_bgcolor: '#1a1f3a'
                });
            }).catch(error => {
                console.error('Failed to fetch confidence data:', error);
            });
        }

        function updateRegretEvolutionChart() {
            // Get player list from either WebSocket data OR tournament state
            let players = Object.keys(regretData);

            // If no WebSocket data, try getting players from tournament state standings
            // Use display_name (Alice, Bob, etc.) not player_id (P01, P02, etc.)
            if (players.length === 0 && window.tournamentState && window.tournamentState.standings) {
                players = window.tournamentState.standings.map(s => s.display_name || s.player_id || s.player || s.name);
                console.log('[Regret] Using player names from standings:', players);
            }

            if (players.length === 0) {
                Plotly.newPlot('regret-chart-evolution', [], {
                    title: 'Cumulative Regret Analysis (CFR) - Waiting for data...',
                    xaxis: { title: 'Round' },
                    yaxis: { title: 'Cumulative Regret' },
                    template: 'plotly_dark',
                    paper_bgcolor: '#1a1f3a',
                    plot_bgcolor: '#1a1f3a'
                });
                return;
            }

            // Fetch detailed counterfactual analytics from API
            Promise.all(players.map(pid =>
                fetch(`/api/analytics/counterfactual/${pid}`)
                    .then(r => r.json())
                    .catch(() => null)
            )).then(results => {
                const traces = [];
                let maxRound = 0;

                results.forEach((data, idx) => {
                    if (!data || !data.time_series) return;

                    const playerId = players[idx];
                    const regretByAction = data.time_series.regret_by_action || {};
                    const rounds = data.time_series.rounds || [];

                    if (rounds.length > 0) {
                        maxRound = Math.max(maxRound, ...rounds);
                    }

                    // Create trace for each action
                    Object.entries(regretByAction).forEach(([action, regrets]) => {
                        if (regrets.length > 0) {
                            traces.push({
                                x: rounds.slice(0, regrets.length),
                                y: regrets,
                                name: `${playerId.substring(0, 8)} - ${action}`,
                                mode: 'lines',
                                line: { width: 2 }
                            });
                        }
                    });
                });

                if (traces.length === 0) {
                    traces.push({
                        x: [1],
                        y: [0],
                        mode: 'markers',
                        name: 'No data yet',
                        marker: { size: 1, opacity: 0 }
                    });
                    maxRound = 1;
                }

                Plotly.newPlot('regret-chart-evolution', traces, {
                    title: 'Counterfactual Regret Minimization',
                    xaxis: { title: 'Round' },
                    yaxis: { title: 'Regret Value' },
                    shapes: [{
                        type: 'line',
                        x0: 0, x1: maxRound,
                        y0: 0, y1: 0,
                        line: { color: 'red', width: 1, dash: 'dot' }
                    }],
                    template: 'plotly_dark',
                    paper_bgcolor: '#1a1f3a',
                    plot_bgcolor: '#1a1f3a'
                });
            });
        }

        function updateLearningCurve() {
            // Fetch from analytics API
            console.log('[LearningCurve] Fetching strategies data...');
            fetch('/api/analytics/strategies')
                .then(r => r.json())
                .then(data => {
                    const strategies = data.strategies || [];
                    console.log('[LearningCurve] Strategies data:', strategies);

                    if (strategies.length === 0) {
                        Plotly.newPlot('learning-chart', [], {
                            title: 'Learning Curve (Win Rate Over Time) - Waiting for data...',
                            xaxis: { title: 'Round' },
                            yaxis: { title: 'Win Rate', range: [0, 1] },
                            template: 'plotly_dark',
                            paper_bgcolor: '#1a1f3a',
                            plot_bgcolor: '#1a1f3a'
                        });
                        return;
                    }

                    const traces = [];
                    let maxRound = 0;

                    strategies.forEach(strategy => {
                        const rounds = strategy.time_series.rounds || [];
                        const winRates = strategy.time_series.win_rates || [];
                        console.log(`[LearningCurve] Strategy ${strategy.strategy_name}: rounds=${rounds.length}, winRates=${winRates.length}`);

                        if (rounds.length > 0 && winRates.length > 0) {
                            maxRound = Math.max(maxRound, ...rounds);

                            // Main line
                            traces.push({
                                x: rounds,
                                y: winRates,
                                name: `${strategy.strategy_name} (${strategy.metrics.improvement_trend})`,
                                mode: 'lines+markers',
                                line: { width: 3, shape: 'spline' },
                                marker: { size: 6 }
                            });

                            // Trendline
                            if (rounds.length >= 2) {
                                const trendline = calculateTrendline(rounds, winRates);
                                traces.push({
                                    x: rounds,
                                    y: trendline,
                                    name: `${strategy.strategy_name} trend`,
                                    mode: 'lines',
                                    line: { dash: 'dash', width: 1 },
                                    showlegend: false,
                                    hoverinfo: 'skip',
                                    opacity: 0.5
                                });
                            }
                        }
                    });

                    console.log(`[LearningCurve] Total traces: ${traces.length}`);

                    if (traces.length === 0) {
                        traces.push({
                            x: [1],
                            y: [0.5],
                            mode: 'markers',
                            name: 'No data yet',
                            marker: { size: 1, opacity: 0 }
                        });
                        maxRound = 1;
                    }

                    Plotly.newPlot('learning-chart', traces, {
                        title: 'Strategy Learning Curves (Win Rate Evolution)',
                        xaxis: { title: 'Round' },
                        yaxis: { title: 'Win Rate', range: [0, 1] },
                        shapes: [{
                            type: 'line',
                            x0: 0, x1: maxRound,
                            y0: 0.5, y1: 0.5,
                            line: { color: 'yellow', width: 1, dash: 'dot' }
                        }],
                        template: 'plotly_dark',
                        paper_bgcolor: '#1a1f3a',
                        plot_bgcolor: '#1a1f3a',
                        annotations: [{
                            x: maxRound * 0.9,
                            y: 0.5,
                            text: 'Random baseline',
                            showarrow: false,
                            font: { color: 'yellow', size: 10 }
                        }]
                    });
                })
                .catch(error => {
                    console.error('[LearningCurve] Failed to fetch learning curve data:', error);
                });
        }

        function calculateTrendline(x, y) {
            // Simple linear regression
            const n = x.length;
            const sumX = x.reduce((a, b) => a + b, 0);
            const sumY = y.reduce((a, b) => a + b, 0);
            const sumXY = x.reduce((sum, xi, i) => sum + xi * y[i], 0);
            const sumX2 = x.reduce((sum, xi) => sum + xi * xi, 0);

            const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
            const intercept = (sumY - slope * sumX) / n;

            return x.map(xi => slope * xi + intercept);
        }

        // Tournament Bracket/Flow Visualization Functions
        function showTournamentView(viewName) {
            // Hide all tournament views
            document.querySelectorAll('.tournament-view').forEach(el => el.classList.add('hidden'));
            // Remove active class from all view buttons
            document.querySelectorAll('.view-btn').forEach(el => el.classList.remove('active'));

            // Show selected view
            document.getElementById(`tournament-${viewName}`).classList.remove('hidden');
            // Activate clicked button
            event.target.classList.add('active');

            // Trigger update for the selected view
            switch(viewName) {
                case 'matrix':
                    createMatchupMatrix();
                    break;
                case 'standings':
                    createStandingsRace();
                    break;
                case 'stats':
                    createHeadToHeadStats();
                    break;
            }
        }

        function createMatchupMatrix() {
            // Show loading message
            document.getElementById('matchup-matrix').innerHTML =
                '<p style="text-align: center; color: #a0aec0; padding: 40px;">Loading matchup matrix...</p>';

            // Use real data from analytics engine via WebSocket or fetch from API
            if (!window.matchupMatrixData || !window.matchupMatrixData.players) {
                // Fetch from API if not available
                console.log('[MatchupMatrix] Fetching from API...');
                fetch('/api/analytics/matchup_matrix')
                    .then(response => {
                        if (!response.ok) throw new Error('Failed to fetch');
                        return response.json();
                    })
                    .then(data => {
                        console.log('[MatchupMatrix] Fetched data:', data);
                        window.matchupMatrixData = data;
                        renderMatchupMatrix(data);
                    })
                    .catch(error => {
                        console.error('[MatchupMatrix] Failed to fetch:', error);
                        // Fallback to sample data
                        renderMatchupMatrixFallback();
                    });
            } else {
                console.log('[MatchupMatrix] Using cached data:', window.matchupMatrixData);
                renderMatchupMatrix(window.matchupMatrixData);
            }
        }

        function renderMatchupMatrix(data) {
            const players = data.players || [];
            // Check both 'matchups' and 'matrix' fields for compatibility
            const matchups = data.matchups || data.matrix || {};

            console.log('[MatchupMatrix] Rendering with players:', players, 'matchups:', matchups);

            if (players.length === 0) {
                document.getElementById('matchup-matrix').innerHTML =
                    '<p style="text-align: center; color: #a0aec0; padding: 40px;">No matchup data available yet</p>';
                return;
            }

            // Create player ID to display name mapping from tournament state
            const playerNames = {};
            if (window.tournamentState && window.tournamentState.standings) {
                window.tournamentState.standings.forEach(s => {
                    const playerId = s.player_id || s.player;
                    const displayName = s.display_name || s.player_name || playerId;
                    playerNames[playerId] = displayName;
                });
            }

            // Function to get display name (fallback to ID if not found)
            const getDisplayName = (playerId) => {
                return playerNames[playerId] || playerId;
            };

            // Build matrix
            const matrix = [];
            players.forEach(p1 => {
                const row = [];
                players.forEach(p2 => {
                    if (p1 === p2) {
                        row.push({ value: null, text: '-', cssClass: '', title: 'Same player' });
                    } else {
                        // Find matchup (keys are ordered, so try both combinations)
                        const key1 = `${p1}_vs_${p2}`;
                        const key2 = `${p2}_vs_${p1}`;
                        const matchup = matchups[key1] || matchups[key2];

                        if (matchup && matchup.total_matches > 0) {
                            // Determine result from p1's perspective
                            let wins, losses, draws;
                            if (matchup.player_a === p1) {
                                wins = matchup.player_a_wins;
                                losses = matchup.player_b_wins;
                            } else {
                                wins = matchup.player_b_wins;
                                losses = matchup.player_a_wins;
                            }
                            draws = matchup.draws;

                            // Determine cell style and text
                            let cssClass, text, title;
                            if (wins > losses) {
                                cssClass = 'matrix-cell win';
                                text = `W ${wins}-${losses}`;
                            } else if (losses > wins) {
                                cssClass = 'matrix-cell loss';
                                text = `L ${losses}-${wins}`;
                            } else {
                                cssClass = 'matrix-cell draw';
                                text = `D ${wins}-${losses}`;
                            }

                            if (draws > 0) {
                                text += ` (${draws}D)`;
                            }

                            title = `${p1} vs ${p2}: ${wins}W-${losses}L-${draws}D (${matchup.total_matches} matches)`;

                            row.push({
                                value: matchup,
                                text: text,
                                cssClass: cssClass,
                                title: title,
                                p1: p1,
                                p2: p2
                            });
                        } else {
                            row.push({
                                value: null,
                                text: '...',
                                cssClass: 'matrix-cell pending',
                                title: 'No matches played yet'
                            });
                        }
                    }
                });
                matrix.push(row);
            });

            // Render as interactive table
            const html = `
                <div class="matchup-matrix">
                    <table>
                        <thead>
                            <tr>
                                <th></th>
                                ${players.map(p => `<th>${getDisplayName(p)}</th>`).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            ${players.map((p1, i) => `
                                <tr>
                                    <td>${getDisplayName(p1)}</td>
                                    ${matrix[i].map((cell, j) => `
                                        <td class="${cell.cssClass}"
                                            ${cell.value ? `onclick="showMatchDetails('${cell.p1}', '${cell.p2}')"` : ''}
                                            title="${cell.title}">
                                            ${cell.text}
                                        </td>
                                    `).join('')}
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;

            document.getElementById('matchup-matrix').innerHTML = html;
        }

        function renderMatchupMatrixFallback() {
            // Fallback sample data
            const html = `
                <div class="matchup-matrix">
                    <p style="text-align: center; color: #a0aec0; padding: 40px;">
                        Loading matchup matrix...
                    </p>
                </div>
            `;
            document.getElementById('matchup-matrix').innerHTML = html;
        }

        function createStandingsRace() {
            // Use real tournament data if available
            if (!window.tournamentState || !window.tournamentState.standings) {
                // Fallback message
                document.getElementById('standings-race-chart').innerHTML =
                    '<p style="text-align: center; color: #a0aec0; padding: 40px;">No tournament data available yet</p>';
                return;
            }

            // Create player ID to display name mapping
            const playerNames = {};
            window.tournamentState.standings.forEach(s => {
                const playerId = s.player_id || s.player;
                const displayName = s.display_name || s.player_name || playerId;
                playerNames[playerId] = displayName;
            });

            // Get current standings snapshot
            const currentStandings = window.tournamentState.standings.map(s => ({
                player_id: s.player_id || s.player,
                display_name: playerNames[s.player_id || s.player],
                points: s.points || 0
            }));

            // For now, show current standings as a bar chart
            // TODO: Store standings history for animated progression
            const sorted = [...currentStandings].sort((a, b) => b.points - a.points);

            const data = [{
                x: sorted.map(p => p.points),
                y: sorted.map(p => p.display_name),
                type: 'bar',
                orientation: 'h',
                marker: {
                    color: sorted.map((_, i) => {
                        const colors = ['#667eea', '#48c9b0', '#f39c12', '#e74c3c'];
                        return colors[i % colors.length];
                    })
                },
                text: sorted.map(p => p.points.toString()),
                textposition: 'outside'
            }];

            const layout = {
                title: `Tournament Standings - Round ${window.tournamentState.current_round || 0}`,
                xaxis: {
                    title: 'Points',
                    range: [0, Math.max(...sorted.map(p => p.points), 10) + 2],
                    color: '#a0aec0',
                    gridcolor: '#2a2f4a'
                },
                yaxis: {
                    title: '',
                    color: '#a0aec0',
                    gridcolor: '#2a2f4a'
                },
                paper_bgcolor: '#0f1321',
                plot_bgcolor: '#0f1321',
                font: { color: '#e0e0e0' },
                height: 400,
                margin: { l: 100, r: 50, t: 60, b: 60 }
            };

            Plotly.newPlot('standings-race-chart', data, layout, {responsive: true});
        }

        function createHeadToHeadStats() {
            // Show loading message
            document.getElementById('head-to-head-stats').innerHTML = `
                <div style="text-align: center; color: #a0aec0; padding: 40px;">
                    Loading head-to-head statistics...
                </div>
            `;

            // Get actual matchup data from matchup matrix
            const matchupData = window.matchupMatrixData;

            if (!matchupData || !matchupData.matrix || Object.keys(matchupData.matrix).length === 0) {
                // Try to fetch from API if not in memory
                console.log('[H2H] Fetching matchup matrix from API...');
                fetch('/api/analytics/matchup_matrix')
                    .then(response => {
                        if (!response.ok) throw new Error('Failed to fetch');
                        return response.json();
                    })
                    .then(data => {
                        console.log('[H2H] Fetched matchup matrix:', data);
                        window.matchupMatrixData = data;
                        // Retry rendering with fetched data
                        renderHeadToHeadStats(data);
                    })
                    .catch(error => {
                        console.error('[H2H] Failed to fetch matchup matrix:', error);
                        document.getElementById('head-to-head-stats').innerHTML = `
                            <div style="text-align: center; color: #a0aec0; padding: 40px;">
                                No head-to-head statistics available yet.<br>
                                Complete some matches to see statistics.
                            </div>
                        `;
                    });
                return;
            }

            console.log('[H2H] Using cached matchup matrix:', matchupData);
            renderHeadToHeadStats(matchupData);
        }

        function renderHeadToHeadStats(matchupData) {
            console.log('[H2H] Rendering with matchupData:', matchupData);

            // Validate input
            if (!matchupData || !matchupData.matrix) {
                console.log('[H2H] No valid matchup data available');
                document.getElementById('head-to-head-stats').innerHTML = `
                    <div style="text-align: center; color: #a0aec0; padding: 40px;">
                        No head-to-head statistics available yet.<br>
                        Complete some matches to see statistics.
                    </div>
                `;
                return;
            }

            // Create player ID to display name mapping
            const playerNames = {};
            if (window.tournamentState && window.tournamentState.standings) {
                window.tournamentState.standings.forEach(s => {
                    const playerId = s.player_id || s.player;
                    const displayName = s.display_name || s.player_name || playerId;
                    playerNames[playerId] = displayName;
                });
            }

            // Function to get display name (fallback to ID if not found)
            const getDisplayName = (playerId) => {
                return playerNames[playerId] || playerId;
            };

            // Convert matchup matrix to h2h data
            const h2hData = [];
            const matrix = matchupData.matrix || {};
            for (const [key, matchup] of Object.entries(matrix)) {
                if (matchup.total_matches > 0) {
                    const player1 = matchup.player_a;
                    const player2 = matchup.player_b;
                    const p1Name = getDisplayName(player1);
                    const p2Name = getDisplayName(player2);

                    h2hData.push({
                        matchup: `${p1Name} vs ${p2Name}`,
                        stats: {
                            'Total Matches': matchup.total_matches,
                            [`${p1Name} Wins`]: matchup.player_a_wins,
                            [`${p2Name} Wins`]: matchup.player_b_wins,
                            'Draws': matchup.draws || 0,
                            'Avg Score Diff': matchup.avg_score_diff ? matchup.avg_score_diff.toFixed(1) : '0.0',
                            'Last Winner': matchup.last_winner ? getDisplayName(matchup.last_winner) : 'N/A'
                        }
                    });
                }
            }

            if (h2hData.length === 0) {
                document.getElementById('head-to-head-stats').innerHTML = `
                    <div style="text-align: center; color: #a0aec0; padding: 40px;">
                        No head-to-head statistics available yet.<br>
                        Complete some matches to see statistics.
                    </div>
                `;
                return;
            }

            const html = `
                <div class="h2h-stats-grid">
                    ${h2hData.map(h2h => `
                        <div class="h2h-card">
                            <h4>${h2h.matchup}</h4>
                            ${Object.entries(h2h.stats).map(([label, value]) => `
                                <div class="h2h-stat">
                                    <span class="h2h-label">${label}:</span>
                                    <span class="h2h-value">${value}</span>
                                </div>
                            `).join('')}
                        </div>
                    `).join('')}
                </div>
            `;

            document.getElementById('head-to-head-stats').innerHTML = html;
        }

        function showMatchDetails(player1, player2) {
            // Placeholder for showing detailed match information
            alert(`Match Details: ${player1} vs ${player2}\n\nThis would show:\n- Round by round scores\n- Move history\n- Strategy used\n- Key moments`);
        }

        // Replay Manager Class
        class ReplayManager {
            constructor() {
                this.history = [];
                this.currentIndex = 0;
                this.isPlaying = false;
                this.playbackSpeed = 1;
                this.playbackInterval = null;
                this.snapshots = [];
                this.initialized = false;
            }

            initialize() {
                // Generate sample replay data
                this.history = this.generateSampleHistory();
                this.initialized = true;
                this.updateUI();
                this.updateSliderMax();
                addLog(`Replay initialized with ${this.history.length} rounds`);
            }

            generateSampleHistory() {
                // Sample tournament history data
                const rounds = [];
                for (let i = 0; i < 10; i++) {
                    rounds.push({
                        round: i,
                        matches: [
                            {
                                match_id: `R${i}M1`,
                                player_a: { id: 'Player_1', name: 'Player_1', strategy: 'adaptive', role: 'ODD', move: Math.floor(Math.random() * 10) + 1, score: i },
                                player_b: { id: 'Player_2', name: 'Player_2', strategy: 'random', role: 'EVEN', move: Math.floor(Math.random() * 10) + 1, score: 10 - i },
                                state: 'FINISHED',
                                round: i + 1,
                                total_rounds: 5
                            }
                        ],
                        standings: [
                            { player_id: 'Player_1', score: i * 3, wins: i, losses: 0 },
                            { player_id: 'Player_2', score: (10 - i) * 3, wins: 10 - i, losses: i },
                            { player_id: 'Player_3', score: i * 2, wins: i, losses: 1 },
                            { player_id: 'Player_4', score: i, wins: 0, losses: i }
                        ],
                        timestamp: new Date(Date.now() - (10 - i) * 60000).toISOString()
                    });
                }
                return rounds;
            }

            loadHistory(data) {
                this.history = data.rounds || [];
                this.initialized = true;
                this.currentIndex = 0;
                this.updateSliderMax();
                this.updateUI();
            }

            updateSliderMax() {
                const slider = document.getElementById('timeline-slider');
                slider.max = Math.max(0, this.history.length - 1);
                document.getElementById('total-rounds-display').textContent = `/ ${this.history.length}`;
            }

            jumpTo(index) {
                if (!this.initialized) this.initialize();
                this.currentIndex = Math.max(0, Math.min(index, this.history.length - 1));
                this.updateDisplay();
            }

            stepForward() {
                if (!this.initialized) this.initialize();
                if (this.currentIndex < this.history.length - 1) {
                    this.currentIndex++;
                    this.updateDisplay();
                }
            }

            stepBack() {
                if (!this.initialized) this.initialize();
                if (this.currentIndex > 0) {
                    this.currentIndex--;
                    this.updateDisplay();
                }
            }

            togglePlay() {
                if (!this.initialized) this.initialize();

                this.isPlaying = !this.isPlaying;
                const btn = document.getElementById('play-pause-btn');
                const statusText = document.getElementById('replay-status-text');

                if (this.isPlaying) {
                    btn.textContent = '⏸️';
                    btn.classList.add('playing');
                    statusText.textContent = 'Playing...';
                    statusText.classList.add('playing');
                    this.startPlayback();
                } else {
                    btn.textContent = '▶️';
                    btn.classList.remove('playing');
                    statusText.textContent = 'Paused';
                    statusText.classList.remove('playing');
                    this.stopPlayback();
                }
            }

            startPlayback() {
                const intervalMs = 1000 / this.playbackSpeed;
                this.playbackInterval = setInterval(() => {
                    if (this.currentIndex < this.history.length - 1) {
                        this.stepForward();
                    } else {
                        this.togglePlay();  // Auto-pause at end
                        addLog('Replay finished');
                    }
                }, intervalMs);
            }

            stopPlayback() {
                if (this.playbackInterval) {
                    clearInterval(this.playbackInterval);
                    this.playbackInterval = null;
                }
            }

            updateDisplay() {
                const roundData = this.history[this.currentIndex];

                // Update all visualizations with historical data
                if (roundData.matches && roundData.matches.length > 0) {
                    updateGameArena(roundData.matches);
                }

                // Update UI elements
                this.updateUI();
            }

            updateUI() {
                document.getElementById('timeline-slider').value = this.currentIndex;
                document.getElementById('current-round-display').textContent = `Round ${this.currentIndex}`;

                // Update timeline gradient based on progress
                const progress = this.history.length > 0 ? (this.currentIndex / (this.history.length - 1)) * 100 : 0;
                const slider = document.getElementById('timeline-slider');
                slider.style.background = `linear-gradient(to right, #667eea ${progress}%, rgba(102, 126, 234, 0.3) ${progress}%)`;
            }

            captureSnapshot() {
                if (!this.initialized) {
                    alert('Please initialize replay first');
                    return;
                }

                const snapshot = {
                    round: this.currentIndex,
                    timestamp: new Date().toISOString(),
                    data: this.history[this.currentIndex]
                };
                this.snapshots.push(snapshot);

                document.getElementById('snapshots-count').textContent = `Snapshots: ${this.snapshots.length}`;
                addLog(`Snapshot captured at Round ${this.currentIndex}`);
            }

            compareSnapshots() {
                if (this.snapshots.length < 2) {
                    alert('Capture at least 2 snapshots to compare');
                    return;
                }

                const snap1 = this.snapshots[this.snapshots.length - 2];
                const snap2 = this.snapshots[this.snapshots.length - 1];

                const comparison = `
Snapshot Comparison:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Snapshot 1: Round ${snap1.round}
Timestamp: ${new Date(snap1.timestamp).toLocaleString()}
Matches: ${snap1.data.matches?.length || 0}

Snapshot 2: Round ${snap2.round}
Timestamp: ${new Date(snap2.timestamp).toLocaleString()}
Matches: ${snap2.data.matches?.length || 0}

Round Difference: ${snap2.round - snap1.round}
                `;

                alert(comparison);
                addLog('Compared last 2 snapshots');
            }

            exportReplay() {
                if (!this.initialized) {
                    alert('No replay data to export');
                    return;
                }

                const exportData = {
                    tournament_id: 'replay_export',
                    total_rounds: this.history.length,
                    history: this.history,
                    snapshots: this.snapshots,
                    exported_at: new Date().toISOString()
                };

                const blob = new Blob([JSON.stringify(exportData, null, 2)], {
                    type: 'application/json'
                });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `tournament_replay_${Date.now()}.json`;
                a.click();
                URL.revokeObjectURL(url);

                addLog('Replay data exported');
            }
        }

        // Global replay manager instance
        const replayManager = new ReplayManager();

        // Control functions (called from HTML)
        function replayJumpStart() {
            replayManager.jumpTo(0);
        }

        function replayJumpEnd() {
            replayManager.jumpTo(replayManager.history.length - 1);
        }

        function replayStepForward() {
            replayManager.stepForward();
        }

        function replayStepBack() {
            replayManager.stepBack();
        }

        function replayTogglePlay() {
            replayManager.togglePlay();
        }

        function replayScrub(value) {
            replayManager.jumpTo(parseInt(value));
        }

        function setPlaybackSpeed(speed) {
            replayManager.playbackSpeed = parseFloat(speed);
            if (replayManager.isPlaying) {
                replayManager.stopPlayback();
                replayManager.startPlayback();
            }
            addLog(`Playback speed set to ${speed}x`);
        }

        function captureSnapshot() {
            replayManager.captureSnapshot();
        }

        function compareSnapshots() {
            replayManager.compareSnapshots();
        }

        function exportReplay() {
            replayManager.exportReplay();
        }

        // Winner Celebration Functions
        function showWinnerCelebration(winner) {
            const modal = document.getElementById('winner-modal');

            // Populate winner data
            document.getElementById('winner-avatar').textContent = winner.player_id ? winner.player_id.substring(0, 2).toUpperCase() : '🥇';
            document.getElementById('winner-name').textContent = winner.display_name || winner.player_id || 'Champion';
            document.getElementById('winner-strategy').textContent = `Strategy: ${winner.strategy || 'Unknown'}`;
            document.getElementById('winner-wins').textContent = winner.wins || 0;
            document.getElementById('winner-points').textContent = winner.points || 0;
            document.getElementById('winner-winrate').textContent = `${(winner.win_rate || 0).toFixed(1)}%`;

            // Show modal
            modal.classList.remove('hidden');

            // Create confetti
            createConfetti();

            // Log event
            addLog(`🏆 Tournament Winner: ${winner.display_name || winner.player_id}`);
        }

        function createConfetti() {
            const container = document.getElementById('confetti-container');
            container.innerHTML = ''; // Clear existing confetti

            const colors = ['#ffd700', '#ff6b6b', '#4ecdc4', '#45b7d1', '#f7b731', '#5f27cd'];
            const confettiCount = 100;

            for (let i = 0; i < confettiCount; i++) {
                const confetti = document.createElement('div');
                confetti.className = 'confetti-piece';
                confetti.style.left = Math.random() * 100 + '%';
                confetti.style.animationDelay = Math.random() * 3 + 's';
                confetti.style.animationDuration = (Math.random() * 2 + 2) + 's';
                confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
                confetti.style.width = (Math.random() * 10 + 5) + 'px';
                confetti.style.height = (Math.random() * 10 + 5) + 'px';
                container.appendChild(confetti);
            }
        }

        function closeWinnerModal() {
            const modal = document.getElementById('winner-modal');
            modal.classList.add('hidden');
        }

        // Handle tournament completion with winner celebration
        function handleTournamentComplete(data) {
            // Support both direct data and event-wrapped data
            const winnerDetails = data.winner_details || data.metadata?.winner_details;
            const winnerId = data.winner || winnerDetails?.player_id;

            addLog(`🏆 Tournament Complete! Winner: ${winnerDetails?.display_name || winnerId || 'Unknown'}`);

            // Show winner celebration if we have winner details
            if (winnerId && winnerDetails) {
                setTimeout(() => {
                    showWinnerCelebration(winnerDetails);
                }, 500);
            } else if (winnerId) {
                // Fallback: construct basic winner data from standings
                const standings = document.getElementById('standings-tbody');
                if (standings && standings.firstElementChild) {
                    // Get top player from standings
                    const topPlayerRow = standings.firstElementChild;
                    const playerName = topPlayerRow.querySelector('.player-name')?.textContent || winnerId;
                    const wins = parseInt(topPlayerRow.querySelector('.wins-cell')?.textContent || '0');
                    const points = parseFloat(topPlayerRow.querySelector('.score-cell')?.textContent || '0');
                    const winRate = parseFloat(topPlayerRow.querySelector('.winrate-cell')?.textContent || '0');

                    setTimeout(() => {
                        showWinnerCelebration({
                            player_id: winnerId,
                            display_name: playerName,
                            wins: wins,
                            points: points,
                            win_rate: winRate,
                            strategy: topPlayerRow.querySelector('.strategy-badge')?.textContent || 'Unknown'
                        });
                    }, 500);
                }
            }
        }

        function startTournament() {
            // Show loading indicator
            const statusEl = document.getElementById('status');
            const originalText = statusEl.textContent;
            statusEl.textContent = 'Starting...';
            statusEl.className = 'connection-status';
            statusEl.style.background = '#27ae60';

            addLog('🚀 Starting tournament...', 'info');

            // Call dashboard's start API (which proxies to league manager)
            fetch('/api/league/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(r => r.json())
            .then(response => {
                console.log('Start response:', response);
                if (response.success) {
                    // Restore status
                    statusEl.textContent = 'Connected';
                    statusEl.className = 'connection-status connected';
                    statusEl.style.background = '';

                    const data = response.data || {};
                    const players = data.players || 0;
                    const rounds = data.rounds || 0;

                    addLog('✅ Tournament started successfully!', 'success');
                    addLog(`👥 Players: ${players} | 🎯 Rounds: ${rounds}`, 'info');
                    addLog('💡 Run rounds: uv run python -m src.main --run-round', 'info');

                    // Show success message
                    alert(`Tournament started successfully!\\n\\nPlayers: ${players}\\nRounds: ${rounds}\\n\\nYou can now run rounds with:\\nuv run python -m src.main --run-round`);
                } else {
                    statusEl.textContent = originalText;
                    statusEl.className = 'connection-status connected';
                    statusEl.style.background = '';
                    const errorMsg = response.error || 'Unknown error';
                    addLog('❌ Failed to start: ' + errorMsg, 'error');
                    alert('Failed to start tournament:\\n' + errorMsg);
                }
            })
            .catch(error => {
                console.error('Start error:', error);
                statusEl.textContent = originalText;
                statusEl.className = 'connection-status connected';
                statusEl.style.background = '';
                addLog('❌ Error starting tournament: ' + error.message, 'error');
                alert('Error starting tournament:\\n' + error.message);
            });
        }

        function runRound() {
            // Show loading indicator
            const statusEl = document.getElementById('status');
            const originalText = statusEl.textContent;
            statusEl.textContent = 'Running Round...';
            statusEl.className = 'connection-status';
            statusEl.style.background = '#3498db';

            addLog('▶️ Running next round...', 'info');

            // Call dashboard's run_round API (which proxies to league manager)
            fetch('/api/league/run_round', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(r => r.json())
            .then(response => {
                console.log('Run round response:', response);
                if (response.success) {
                    // Restore status
                    statusEl.textContent = 'Connected';
                    statusEl.className = 'connection-status connected';
                    statusEl.style.background = '';

                    const data = response.data || {};
                    const roundNum = data.round || '?';
                    const matches = data.matches || [];

                    addLog(`✅ Round ${roundNum} started with ${matches.length} matches!`, 'success');
                    addLog('🎮 Matches are now playing...', 'info');
                } else {
                    statusEl.textContent = originalText;
                    statusEl.className = 'connection-status connected';
                    statusEl.style.background = '';
                    const errorMsg = response.error || 'Unknown error';
                    addLog('❌ Failed to run round: ' + errorMsg, 'error');

                    // Check if it's "all rounds completed" message
                    if (errorMsg.includes('All rounds completed') || errorMsg.includes('already completed')) {
                        alert('All rounds have been completed!\\n\\nReset the tournament to start a new one.');
                    } else {
                        alert('Failed to run round:\\n' + errorMsg);
                    }
                }
            })
            .catch(error => {
                console.error('Run round error:', error);
                statusEl.textContent = originalText;
                statusEl.className = 'connection-status connected';
                statusEl.style.background = '';
                addLog('❌ Error running round: ' + error.message, 'error');
                alert('Error running round:\\n' + error.message);
            });
        }

        function clearData() {
            if (!confirm('Are you sure you want to reset the tournament? This will clear all match history and scores, but keep players registered.')) {
                return;
            }

            // Show loading indicator
            const statusEl = document.getElementById('status');
            const originalText = statusEl.textContent;
            statusEl.textContent = 'Resetting...';
            statusEl.className = 'connection-status';
            statusEl.style.background = '#f39c12';

            addLog('🔄 Resetting tournament...', 'info');

            // Call dashboard's reset API (which proxies to league manager)
            fetch('/api/league/reset', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(r => r.json())
            .then(response => {
                console.log('Reset response:', response);
                if (response.success) {
                    // Clear frontend data
                    performanceData = {};
                    opponentModelData = {};
                    regretData = {};
                    events = [];
                    currentMatches = {};
                    playerLastMoves = {};
                    window.matchupMatrixData = null;
                    window.tournamentState = null;

                    // Clear displays
                    document.getElementById('event-log').innerHTML = '';
                    document.getElementById('standings-tbody').innerHTML = '<tr><td colspan="9" style="text-align: center; color: #a0aec0; padding: 40px;">Tournament reset. Waiting for new league...</td></tr>';
                    document.getElementById('active-matches').innerHTML = '<p style="text-align: center; color: #a0aec0;">No active matches</p>';
                    document.getElementById('game-type').textContent = '-';
                    document.getElementById('current-round').textContent = '-';
                    document.getElementById('active-players').textContent = '-';

                    // Clear tournament flow sections
                    document.getElementById('matchup-matrix').innerHTML = '<p style="text-align: center; color: #a0aec0; padding: 40px;">No matches yet</p>';
                    document.getElementById('head-to-head-stats').innerHTML = '<p style="text-align: center; color: #a0aec0; padding: 40px;">No statistics yet</p>';
                    document.getElementById('standings-race-chart').innerHTML = '<p style="text-align: center; color: #a0aec0; padding: 40px;">No standings yet</p>';

                    // Purge all Plotly charts in Strategy Learning Evolution
                    try {
                        Plotly.purge('beliefs-chart');
                        Plotly.purge('confidence-chart');
                        Plotly.purge('regret-chart-evolution');
                        Plotly.purge('learning-chart');
                        Plotly.purge('performance-chart');
                        console.log('[Reset] All Plotly charts purged');
                    } catch (e) {
                        console.error('[Reset] Error purging charts:', e);
                    }

                    // Clear chart containers
                    document.getElementById('beliefs-chart').innerHTML = '<p style="text-align: center; color: #a0aec0; padding: 40px;">Waiting for data...</p>';
                    document.getElementById('confidence-chart').innerHTML = '<p style="text-align: center; color: #a0aec0; padding: 40px;">Waiting for data...</p>';
                    document.getElementById('regret-chart-evolution').innerHTML = '<p style="text-align: center; color: #a0aec0; padding: 40px;">Waiting for data...</p>';
                    document.getElementById('learning-chart').innerHTML = '<p style="text-align: center; color: #a0aec0; padding: 40px;">Waiting for data...</p>';

                    // Restore status
                    statusEl.textContent = 'Connected';
                    statusEl.className = 'connection-status connected';
                    statusEl.style.background = '';

                    addLog('✅ Tournament reset successfully!', 'success');
                    addLog('💡 Run: uv run python -m src.main --start-league', 'info');

                    // Show success message
                    alert('Tournament reset successfully!\\n\\nYou can now start a new league by running:\\nuv run python -m src.main --start-league');
                } else {
                    statusEl.textContent = originalText;
                    statusEl.className = 'connection-status connected';
                    statusEl.style.background = '';
                    addLog('Failed to reset: ' + (response.result?.error || response.error?.message || 'Unknown error'), 'error');
                    alert('Failed to reset tournament:\\n' + (response.result?.error || response.error?.message || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Reset error:', error);
                statusEl.textContent = originalText;
                statusEl.className = 'connection-status connected';
                statusEl.style.background = '';
                addLog('Error resetting tournament: ' + error.message, 'error');
                alert('Error resetting tournament:\\n' + error.message);
            });
        }

        function exportData() {
            // Fetch comprehensive analytics from API
            addLog('Exporting comprehensive analytics...');

            fetch('/api/analytics/export')
                .then(r => r.json())
                .then(analyticsData => {
                    // Combine analytics with current dashboard data
                    const data = {
                        ...analyticsData,
                        dashboard_state: {
                            performance: performanceData,
                            opponentModels: opponentModelData,
                            regrets: regretData,
                            events: events
                        },
                        exported_by: 'dashboard',
                        format_version: '2.0'
                    };

                    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `tournament-analytics-${Date.now()}.json`;
                    a.click();
                    URL.revokeObjectURL(url);

                    addLog('✓ Comprehensive analytics exported (research-ready)');
                })
                .catch(error => {
                    console.error('Export failed:', error);

                    // Fallback to dashboard data only
                    const data = {
                        performance: performanceData,
                        opponentModels: opponentModelData,
                        regrets: regretData,
                        events: events,
                        exported_at: new Date().toISOString(),
                        note: 'Limited export - analytics API unavailable'
                    };

                    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `dashboard-data-${Date.now()}.json`;
                    a.click();
                    URL.revokeObjectURL(url);

                    addLog('⚠ Partial data exported (analytics unavailable)');
                });
        }

        // Auto-connect on load
        window.onload = () => {
            connectWebSocket();
        };
    </script>
</body>
</html>
        """


# ============================================================================
# Global Dashboard Instance
# ============================================================================

_dashboard_instance = None


def get_dashboard() -> DashboardAPI:
    """Get global dashboard instance (singleton)."""
    global _dashboard_instance
    if _dashboard_instance is None:
        _dashboard_instance = DashboardAPI()
    return _dashboard_instance


def reset_dashboard():
    """Reset dashboard singleton to initial state."""
    global _dashboard_instance
    _dashboard_instance = None
    logger.info("Dashboard instance reset")


# ============================================================================
# Integration Helpers
# ============================================================================


async def stream_game_event(
    event_type: str,
    round: int,
    players: list[str],
    moves: dict[str, str],
    scores: dict[str, float],
    **metadata,
):
    """Convenience function to stream game event to dashboard."""
    dashboard = get_dashboard()
    event = GameEvent(
        timestamp=datetime.now().isoformat(),
        event_type=event_type,
        round=round,
        players=players,
        moves=moves,
        scores=scores,
        metadata=metadata,
    )
    await dashboard.stream_event(event)
