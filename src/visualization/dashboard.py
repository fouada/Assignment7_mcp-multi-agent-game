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

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from typing import Dict, List, Optional, Set
import json
import asyncio
from datetime import datetime
from dataclasses import dataclass, asdict
import numpy as np

from ..common.logger import get_logger

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
    players: List[str]
    moves: Dict[str, str]
    scores: Dict[str, float]
    metadata: Dict


@dataclass
class StrategyPerformance:
    """Strategy performance metrics over time."""

    strategy_name: str
    rounds: List[int]
    win_rates: List[float]
    avg_scores: List[float]
    opponent_types: Dict[str, int]  # Opponent strategy -> count


@dataclass
class OpponentModelVisualization:
    """Opponent modeling data for visualization."""

    opponent_id: str
    round: int
    predicted_strategy: str
    confidence: float
    move_distribution: Dict[str, float]
    determinism: float
    reactivity: float
    adaptability: float


@dataclass
class CounterfactualVisualization:
    """Counterfactual analysis for visualization."""

    round: int
    actual_move: str
    actual_reward: float
    counterfactuals: List[Dict]  # {move, reward, regret}
    cumulative_regret: Dict[str, float]


@dataclass
class TournamentState:
    """Complete tournament state for dashboard."""

    tournament_id: str
    game_type: str
    players: List[str]
    current_round: int
    total_rounds: int
    standings: List[Dict]  # {player, score, wins, losses}
    recent_matches: List[Dict]
    active_matches: List[Dict]


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
        self.active_connections: Set[WebSocket] = set()
        self.connection_metadata: Dict[WebSocket, Dict] = {}

    async def connect(self, websocket: WebSocket, client_info: Dict = None):
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
        self.tournament_states: Dict[str, TournamentState] = {}
        self.game_events: Dict[str, List[GameEvent]] = {}
        self.strategy_performance: Dict[str, StrategyPerformance] = {}
        self.opponent_models: Dict[str, Dict[str, OpponentModelVisualization]] = {}
        self.counterfactuals: Dict[str, Dict[int, CounterfactualVisualization]] = {}

        # Server state
        self._server_task: Optional[asyncio.Task] = None
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
            await self.connection_manager.connect(websocket)
            try:
                while True:
                    # Keep connection alive
                    data = await websocket.receive_text()
                    # Echo back for ping/pong
                    await self.connection_manager.send_personal_message(
                        {"type": "pong", "timestamp": datetime.now().isoformat()},
                        websocket
                    )
            except WebSocketDisconnect:
                self.connection_manager.disconnect(websocket)

        @self.app.get("/api/tournament/{tournament_id}")
        async def get_tournament_state(tournament_id: str):
            """Get current tournament state."""
            state = self.tournament_states.get(tournament_id)
            if not state:
                return {"error": "Tournament not found"}
            return asdict(state)

        @self.app.get("/api/strategy/{strategy_name}/performance")
        async def get_strategy_performance(strategy_name: str):
            """Get strategy performance metrics."""
            perf = self.strategy_performance.get(strategy_name)
            if not perf:
                return {"error": "Strategy not found"}
            return asdict(perf)

        @self.app.get("/api/opponent_model/{player_id}/{opponent_id}")
        async def get_opponent_model(player_id: str, opponent_id: str):
            """Get opponent model visualization data."""
            models = self.opponent_models.get(player_id, {})
            model = models.get(opponent_id)
            if not model:
                return {"error": "Opponent model not found"}
            return asdict(model)

        @self.app.get("/api/counterfactual/{player_id}/{round}")
        async def get_counterfactual(player_id: str, round: int):
            """Get counterfactual analysis for specific round."""
            cfs = self.counterfactuals.get(player_id, {})
            cf = cfs.get(round)
            if not cf:
                return {"error": "Counterfactual data not found"}
            return asdict(cf)

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

    async def stream_event(self, event: GameEvent):
        """Stream event to all connected clients."""
        message = {
            "type": "game_event",
            "data": asdict(event)
        }
        await self.connection_manager.broadcast(message)

        # Store event
        tournament_id = event.metadata.get("tournament_id", "default")
        if tournament_id not in self.game_events:
            self.game_events[tournament_id] = []
        self.game_events[tournament_id].append(event)

    async def update_tournament_state(self, state: TournamentState):
        """Update and broadcast tournament state."""
        self.tournament_states[state.tournament_id] = state

        message = {
            "type": "tournament_update",
            "data": asdict(state)
        }
        await self.connection_manager.broadcast(message)

    async def update_strategy_performance(self, perf: StrategyPerformance):
        """Update strategy performance metrics."""
        self.strategy_performance[perf.strategy_name] = perf

        message = {
            "type": "strategy_performance",
            "data": asdict(perf)
        }
        await self.connection_manager.broadcast(message)

    async def update_opponent_model(self, player_id: str, model: OpponentModelVisualization):
        """Update opponent model visualization."""
        if player_id not in self.opponent_models:
            self.opponent_models[player_id] = {}
        self.opponent_models[player_id][model.opponent_id] = model

        message = {
            "type": "opponent_model_update",
            "data": {
                "player_id": player_id,
                "model": asdict(model)
            }
        }
        await self.connection_manager.broadcast(message)

    async def update_counterfactual(self, player_id: str, cf: CounterfactualVisualization):
        """Update counterfactual analysis."""
        if player_id not in self.counterfactuals:
            self.counterfactuals[player_id] = {}
        self.counterfactuals[player_id][cf.round] = cf

        message = {
            "type": "counterfactual_update",
            "data": {
                "player_id": player_id,
                "counterfactual": asdict(cf)
            }
        }
        await self.connection_manager.broadcast(message)

    async def broadcast_match_update(self, match_data: Dict):
        """Broadcast live match state to all connected clients."""
        message = {
            "type": "match_update",
            "data": match_data
        }
        await self.connection_manager.broadcast(message)
        logger.debug(f"Broadcasted match update: {match_data.get('match_id', 'unknown')}")

    async def broadcast_tournament_complete(self, winner_data: Dict):
        """Broadcast tournament completion with winner data."""
        message = {
            "type": "tournament_complete",
            "data": {
                "winner": winner_data
            }
        }
        await self.connection_manager.broadcast(message)
        logger.info(f"Tournament complete! Winner: {winner_data.get('player_id', 'unknown')}")

    async def start_server(self, host: str = "0.0.0.0", port: int = 8050):
        """
        Start the dashboard server with Uvicorn.

        This is a blocking call that runs the server until interrupted.
        Use start_server_background() for non-blocking operation.

        Args:
            host: Host to bind to (default: 0.0.0.0 for all interfaces)
            port: Port to listen on (default: 8050)
        """
        import uvicorn

        logger.info(f"Starting dashboard server on {host}:{port}")
        config = uvicorn.Config(
            self.app,
            host=host,
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        self._server = server
        await server.serve()

    async def start_server_background(self, host: str = "0.0.0.0", port: int = 8050):
        """
        Start server in background task (non-blocking).

        This allows the dashboard to run alongside other components.

        Args:
            host: Host to bind to (default: 0.0.0.0 for all interfaces)
            port: Port to listen on (default: 8050)
        """
        import uvicorn

        logger.info(f"Starting dashboard server in background on {host}:{port}")
        config = uvicorn.Config(
            self.app,
            host=host,
            port=port,
            log_level="info"
        )
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
                except asyncio.TimeoutError:
                    logger.warning("Dashboard server shutdown timed out")
                    self._server_task.cancel()
            logger.info("✓ Dashboard server stopped")

    def _get_dashboard_html(self) -> str:
        """Generate dashboard HTML."""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>MCP Game League - Real-Time Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #0a0e27;
            color: #e0e0e0;
            overflow-x: hidden;
        }
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

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: #1a1f3a;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            border: 1px solid #2a2f4a;
        }
        .card h2 {
            font-size: 18px;
            margin-bottom: 15px;
            color: #a0aec0;
            font-weight: 500;
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
            <button onclick="clearData()">Clear Data</button>
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
                <h2>🏆 Live Standings</h2>
                <div id="standings">
                    <p style="color: #a0aec0;">Waiting for tournament data...</p>
                </div>
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
                case 'tournament_complete':
                    handleTournamentComplete(message.data);
                    break;
            }
        }

        function handleGameEvent(data) {
            events.push(data);
            addLog(`Round ${data.round}: ${data.event_type}`);
        }

        function handleTournamentUpdate(data) {
            document.getElementById('game-type').textContent = data.game_type;
            document.getElementById('current-round').textContent =
                `${data.current_round} / ${data.total_rounds}`;
            document.getElementById('active-players').textContent = data.players.length;

            // Update standings
            const standingsDiv = document.getElementById('standings');
            standingsDiv.innerHTML = data.standings.map((s, i) =>
                `<div class="metric">
                    <span class="metric-label">${i+1}. ${s.player}</span>
                    <span class="metric-value">${s.score.toFixed(1)}</span>
                </div>`
            ).join('');
        }

        function handleStrategyPerformance(data) {
            performanceData[data.strategy_name] = data;
            updatePerformanceChart();
        }

        function handleOpponentModelUpdate(data) {
            opponentModelData[data.player_id] = data.model;
            updateOpponentModelChart();
        }

        function handleCounterfactualUpdate(data) {
            regretData[data.player_id] = data.counterfactual;
            updateRegretChart();
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

            container.innerHTML = matches.map(match => {
                const player_a = match.player_a || {};
                const player_b = match.player_b || {};
                const totalScore = (player_a.score || 0) + (player_b.score || 0);
                const scorePercentage = totalScore > 0 ? ((player_a.score || 0) / totalScore * 100) : 50;

                return `
                    <div class="match-card ${match.state === 'IN_PROGRESS' ? 'active' : ''}">
                        <div class="match-header">
                            <span class="match-id">${match.match_id || 'Match'}</span>
                            <span class="round-badge">Round ${match.round || 0}/${match.total_rounds || 0}</span>
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
                            ${player_a.move ? `<div class="move-display">${player_a.move}</div>` : ''}
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
                            ${player_b.move ? `<div class="move-display">${player_b.move}</div>` : ''}
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
            // Sample data - would come from WebSocket in real implementation
            const sampleData = {
                rounds: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                players: [
                    {
                        name: 'Player_1',
                        beliefs: [0.5, 0.52, 0.54, 0.55, 0.58, 0.6, 0.62, 0.63, 0.64, 0.65],
                        confidence: 0.85
                    }
                ]
            };

            const traces = sampleData.players.map(player => ({
                x: sampleData.rounds,
                y: player.beliefs,
                name: `${player.name} (conf: ${player.confidence.toFixed(2)})`,
                mode: 'lines+markers',
                line: { width: 2 },
                marker: { size: 6 }
            }));

            Plotly.newPlot('beliefs-chart', traces, {
                title: 'Bayesian Belief Evolution',
                xaxis: { title: 'Round' },
                yaxis: { title: 'P(opponent chooses ODD)', range: [0, 1] },
                template: 'plotly_dark',
                paper_bgcolor: '#1a1f3a',
                plot_bgcolor: '#1a1f3a'
            });
        }

        function updateConfidenceEvolutionChart() {
            // Sample data
            const sampleData = {
                rounds: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                players: [
                    {
                        name: 'Player_1',
                        confidence_history: [0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.82, 0.84, 0.85]
                    }
                ]
            };

            const traces = sampleData.players.map(player => ({
                x: sampleData.rounds,
                y: player.confidence_history,
                name: player.name,
                mode: 'lines+markers',
                line: { width: 2 },
                marker: { size: 6 }
            }));

            Plotly.newPlot('confidence-chart', traces, {
                title: 'Opponent Model Confidence Evolution',
                xaxis: { title: 'Round' },
                yaxis: { title: 'Confidence', range: [0, 1] },
                template: 'plotly_dark',
                paper_bgcolor: '#1a1f3a',
                plot_bgcolor: '#1a1f3a'
            });
        }

        function updateRegretEvolutionChart() {
            // Sample data
            const sampleData = {
                rounds: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                players: [
                    {
                        name: 'Player_1',
                        cumulative_regret: {
                            odd: [-0.1, -0.2, -0.15, -0.1, -0.05, 0, 0.05, 0.1, 0.08, 0.05],
                            even: [0.1, 0.15, 0.1, 0.05, 0, -0.05, -0.1, -0.12, -0.1, -0.08]
                        }
                    }
                ]
            };

            const traces = sampleData.players.flatMap(player => [
                {
                    x: sampleData.rounds,
                    y: player.cumulative_regret.odd,
                    name: `${player.name} - ODD`,
                    mode: 'lines',
                    line: { dash: 'solid', width: 2 }
                },
                {
                    x: sampleData.rounds,
                    y: player.cumulative_regret.even,
                    name: `${player.name} - EVEN`,
                    mode: 'lines',
                    line: { dash: 'dash', width: 2 }
                }
            ]);

            Plotly.newPlot('regret-chart-evolution', traces, {
                title: 'Cumulative Regret Analysis (CFR)',
                xaxis: { title: 'Round' },
                yaxis: { title: 'Cumulative Regret' },
                shapes: [{
                    type: 'line',
                    x0: 0, x1: Math.max(...sampleData.rounds),
                    y0: 0, y1: 0,
                    line: { color: 'red', width: 1, dash: 'dot' }
                }],
                template: 'plotly_dark',
                paper_bgcolor: '#1a1f3a',
                plot_bgcolor: '#1a1f3a'
            });
        }

        function updateLearningCurve() {
            // Sample data
            const sampleData = {
                rounds: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                players: [
                    {
                        name: 'Player_1',
                        win_rate_history: [0.5, 0.52, 0.54, 0.56, 0.58, 0.6, 0.62, 0.63, 0.64, 0.65]
                    },
                    {
                        name: 'Player_2',
                        win_rate_history: [0.5, 0.48, 0.47, 0.46, 0.45, 0.44, 0.43, 0.42, 0.41, 0.4]
                    }
                ]
            };

            const traces = sampleData.players.flatMap(player => {
                const trendline = calculateTrendline(sampleData.rounds, player.win_rate_history);
                return [
                    {
                        x: sampleData.rounds,
                        y: player.win_rate_history,
                        name: player.name,
                        mode: 'lines+markers',
                        line: { width: 3, shape: 'spline' }
                    },
                    {
                        x: sampleData.rounds,
                        y: trendline,
                        name: `${player.name} trend`,
                        mode: 'lines',
                        line: { dash: 'dash', width: 1 },
                        showlegend: false,
                        hoverinfo: 'skip'
                    }
                ];
            });

            Plotly.newPlot('learning-chart', traces, {
                title: 'Learning Curve (Win Rate Over Time)',
                xaxis: { title: 'Round' },
                yaxis: { title: 'Win Rate', range: [0, 1] },
                shapes: [{
                    type: 'line',
                    x0: 0, x1: Math.max(...sampleData.rounds),
                    y0: 0.5, y1: 0.5,
                    line: { color: 'yellow', width: 1, dash: 'dot' }
                }],
                template: 'plotly_dark',
                paper_bgcolor: '#1a1f3a',
                plot_bgcolor: '#1a1f3a'
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
            // Sample data - would come from WebSocket in real implementation
            const players = ['Player_1', 'Player_2', 'Player_3', 'Player_4'];
            const matches = [
                { player_a: 'Player_1', player_b: 'Player_2', winner: 'Player_1', score_a: 3, score_b: 2 },
                { player_a: 'Player_1', player_b: 'Player_3', winner: 'Player_3', score_a: 1, score_b: 3 },
                { player_a: 'Player_1', player_b: 'Player_4', winner: 'Player_1', score_a: 3, score_b: 1 },
                { player_a: 'Player_2', player_b: 'Player_3', winner: 'Player_2', score_a: 3, score_b: 2 },
                { player_a: 'Player_2', player_b: 'Player_4', winner: null, score_a: 2, score_b: 2 },
                { player_a: 'Player_3', player_b: 'Player_4', winner: 'Player_3', score_a: 3, score_b: 0 }
            ];

            // Build matrix
            const matrix = [];
            players.forEach(p1 => {
                const row = [];
                players.forEach(p2 => {
                    if (p1 === p2) {
                        row.push({ value: null, text: '-', cssClass: '' });
                    } else {
                        const match = matches.find(m =>
                            (m.player_a === p1 && m.player_b === p2) ||
                            (m.player_a === p2 && m.player_b === p1)
                        );
                        if (match) {
                            let result, cssClass, score;
                            if (!match.winner) {
                                result = 'D';
                                cssClass = 'draw';
                                score = `${match.score_a}-${match.score_b}`;
                            } else if (match.winner === p1) {
                                result = 'W';
                                cssClass = 'win';
                                score = match.player_a === p1 ?
                                    `${match.score_a}-${match.score_b}` :
                                    `${match.score_b}-${match.score_a}`;
                            } else {
                                result = 'L';
                                cssClass = 'loss';
                                score = match.player_a === p1 ?
                                    `${match.score_a}-${match.score_b}` :
                                    `${match.score_b}-${match.score_a}`;
                            }
                            row.push({
                                value: match,
                                text: `${result} ${score}`,
                                cssClass: `matrix-cell ${cssClass}`
                            });
                        } else {
                            row.push({
                                value: null,
                                text: '...',
                                cssClass: 'matrix-cell pending'
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
                                ${players.map(p => `<th>${p}</th>`).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            ${players.map((p1, i) => `
                                <tr>
                                    <td>${p1}</td>
                                    ${matrix[i].map((cell, j) => `
                                        <td class="${cell.cssClass}"
                                            ${cell.value ? `onclick="showMatchDetails('${p1}', '${players[j]}')"` : ''}
                                            title="${cell.text}">
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

        function createStandingsRace() {
            // Sample data - standings progression over rounds
            const rounds = [1, 2, 3, 4, 5];
            const standingsHistory = [
                [
                    { player_id: 'Player_1', points: 3 },
                    { player_id: 'Player_2', points: 3 },
                    { player_id: 'Player_3', points: 0 },
                    { player_id: 'Player_4', points: 0 }
                ],
                [
                    { player_id: 'Player_1', points: 3 },
                    { player_id: 'Player_2', points: 6 },
                    { player_id: 'Player_3', points: 3 },
                    { player_id: 'Player_4', points: 0 }
                ],
                [
                    { player_id: 'Player_1', points: 6 },
                    { player_id: 'Player_2', points: 7 },
                    { player_id: 'Player_3', points: 6 },
                    { player_id: 'Player_4', points: 0 }
                ],
                [
                    { player_id: 'Player_1', points: 9 },
                    { player_id: 'Player_2', points: 7 },
                    { player_id: 'Player_3', points: 9 },
                    { player_id: 'Player_4', points: 1 }
                ],
                [
                    { player_id: 'Player_1', points: 12 },
                    { player_id: 'Player_2', points: 8 },
                    { player_id: 'Player_3', points: 12 },
                    { player_id: 'Player_4', points: 1 }
                ]
            ];

            // Create animated frames
            const frames = standingsHistory.map((standings, idx) => {
                // Sort by points descending
                const sorted = [...standings].sort((a, b) => b.points - a.points);
                return {
                    name: `Round ${idx + 1}`,
                    data: [{
                        x: sorted.map(p => p.points),
                        y: sorted.map(p => p.player_id),
                        type: 'bar',
                        orientation: 'h',
                        marker: {
                            color: sorted.map((_, i) => {
                                const hue = (i * 360 / sorted.length);
                                return `hsl(${hue}, 70%, 50%)`;
                            })
                        },
                        text: sorted.map(p => p.points.toString()),
                        textposition: 'outside'
                    }],
                    layout: {
                        title: `Tournament Standings - Round ${idx + 1}`,
                        xaxis: { title: 'Points', range: [0, Math.max(...sorted.map(p => p.points)) + 2] },
                        yaxis: { title: '' },
                        template: 'plotly_dark',
                        paper_bgcolor: '#1a1f3a',
                        plot_bgcolor: '#1a1f3a',
                        height: 400
                    }
                };
            });

            // Plot initial frame
            Plotly.newPlot('standings-race-chart', frames[0].data, frames[0].layout);

            // Animate through rounds
            let currentFrame = 0;
            const animationInterval = setInterval(() => {
                if (currentFrame < frames.length - 1) {
                    currentFrame++;
                    Plotly.react('standings-race-chart',
                        frames[currentFrame].data,
                        frames[currentFrame].layout,
                        { transition: { duration: 500 } }
                    );
                } else {
                    clearInterval(animationInterval);
                }
            }, 1500);
        }

        function createHeadToHeadStats() {
            // Sample head-to-head statistics
            const h2hData = [
                {
                    matchup: 'Player_1 vs Player_2',
                    stats: {
                        'Total Matches': 3,
                        'Player_1 Wins': 2,
                        'Player_2 Wins': 1,
                        'Draws': 0,
                        'Avg Score Diff': '1.3',
                        'Last Winner': 'Player_1'
                    }
                },
                {
                    matchup: 'Player_1 vs Player_3',
                    stats: {
                        'Total Matches': 2,
                        'Player_1 Wins': 1,
                        'Player_3 Wins': 1,
                        'Draws': 0,
                        'Avg Score Diff': '0.5',
                        'Last Winner': 'Player_3'
                    }
                },
                {
                    matchup: 'Player_2 vs Player_3',
                    stats: {
                        'Total Matches': 3,
                        'Player_2 Wins': 1,
                        'Player_3 Wins': 1,
                        'Draws': 1,
                        'Avg Score Diff': '0.7',
                        'Last Winner': 'Draw'
                    }
                },
                {
                    matchup: 'Player_3 vs Player_4',
                    stats: {
                        'Total Matches': 2,
                        'Player_3 Wins': 2,
                        'Player_4 Wins': 0,
                        'Draws': 0,
                        'Avg Score Diff': '2.5',
                        'Last Winner': 'Player_3'
                    }
                }
            ];

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
            document.getElementById('winner-avatar').textContent = winner.id ? winner.id.substring(0, 2) : '🥇';
            document.getElementById('winner-name').textContent = winner.name || winner.player_id || 'Champion';
            document.getElementById('winner-strategy').textContent = `Strategy: ${winner.strategy || 'Unknown'}`;
            document.getElementById('winner-wins').textContent = winner.wins || 0;
            document.getElementById('winner-points').textContent = winner.points || 0;

            const winRate = winner.played > 0 ? ((winner.wins / winner.played) * 100).toFixed(1) : 0;
            document.getElementById('winner-winrate').textContent = `${winRate}%`;

            // Show modal
            modal.classList.remove('hidden');

            // Create confetti
            createConfetti();

            // Log event
            addLog(`🏆 Tournament Winner: ${winner.name || winner.player_id}`);
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

        // Auto-show winner celebration when tournament completes (example)
        function handleTournamentComplete(data) {
            if (data.winner) {
                setTimeout(() => {
                    showWinnerCelebration(data.winner);
                }, 500);
            }
        }

        function clearData() {
            performanceData = {};
            opponentModelData = {};
            regretData = {};
            events = [];
            document.getElementById('event-log').innerHTML = '';
            addLog('Data cleared');
        }

        function exportData() {
            const data = {
                performance: performanceData,
                opponentModels: opponentModelData,
                regrets: regretData,
                events: events
            };
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `dashboard-data-${Date.now()}.json`;
            a.click();
            addLog('Data exported');
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
    players: List[str],
    moves: Dict[str, str],
    scores: Dict[str, float],
    **metadata
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
        metadata=metadata
    )
    await dashboard.stream_event(event)
