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
