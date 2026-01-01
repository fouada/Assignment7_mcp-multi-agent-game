"""
Ultimate Dashboard Integration Module
=====================================

This module provides comprehensive integration between the game league
and the Ultimate MIT-Level Dashboard, ensuring all tabs receive real-time
data and all visualizations are properly populated.

Data Flow:
---------
GameOrchestrator → Event Bus → DashboardIntegration → Ultimate Dashboard → WebSocket → Browser

Components:
----------
1. DashboardIntegration: Event handler that processes game events
2. DataAggregator: Collects and transforms data for dashboard
3. MetricsCalculator: Computes real-time statistics
4. InnovationMonitor: Tracks innovation performance

Usage:
-----
```python
from src.visualization.ultimate_dashboard import UltimateDashboard
from src.visualization.ultimate_integration import UltimateDashboardIntegration

# Create dashboard
dashboard = UltimateDashboard(port=8050)
await dashboard.start()

# Create integration
integration = UltimateDashboardIntegration(dashboard, event_bus)
await integration.initialize()

# Dashboard will automatically receive all game events
```
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..common.events import EventBus
from ..common.logger import get_logger
from .ultimate_dashboard import UltimateDashboard

logger = get_logger(__name__)


class DataAggregator:
    """Aggregates and transforms game data for dashboard visualization."""

    def __init__(self):
        self.players: Dict[str, Dict[str, Any]] = {}
        self.match_history: List[Dict[str, Any]] = []
        self.round_stats: List[Dict[str, Any]] = []

    def register_player(self, player_id: str, strategy: str, **kwargs):
        """Register a player with their strategy."""
        self.players[player_id] = {
            "player_id": player_id,
            "strategy": strategy,
            "score": 0.0,
            "wins": 0,
            "losses": 0,
            "total_matches": 0,
            "rounds_won": 0,
            "rounds_lost": 0,
            **kwargs
        }
        logger.debug(f"Registered player {player_id} with strategy {strategy}")

    def update_player_stats(self, player_id: str, **updates):
        """Update player statistics."""
        if player_id in self.players:
            self.players[player_id].update(updates)
            logger.debug(f"Updated stats for {player_id}: {updates}")

    def record_match(self, match_data: Dict[str, Any]):
        """Record a completed match."""
        self.match_history.append({
            **match_data,
            "timestamp": datetime.now().isoformat()
        })
        logger.debug(f"Recorded match: {match_data.get('match_id')}")

    def record_round_stats(self, round_num: int, stats: Dict[str, Any]):
        """Record statistics for a round."""
        self.round_stats.append({
            "round": round_num,
            **stats,
            "timestamp": datetime.now().isoformat()
        })

    def get_standings(self) -> List[Dict[str, Any]]:
        """Get current player standings sorted by score."""
        standings = sorted(
            self.players.values(),
            key=lambda p: (p.get("score", 0), p.get("wins", 0)),
            reverse=True
        )
        return standings

    def get_player_metrics(self, player_id: str) -> Dict[str, Any]:
        """Get comprehensive metrics for a player."""
        if player_id not in self.players:
            return {}

        player = self.players[player_id]
        total_matches = player.get("total_matches", 0)

        return {
            **player,
            "win_rate": (player.get("wins", 0) / total_matches * 100) if total_matches > 0 else 0,
            "avg_score": player.get("score", 0) / total_matches if total_matches > 0 else 0,
            "round_win_rate": (
                player.get("rounds_won", 0) /
                (player.get("rounds_won", 0) + player.get("rounds_lost", 0)) * 100
            ) if (player.get("rounds_won", 0) + player.get("rounds_lost", 0)) > 0 else 0
        }


class MetricsCalculator:
    """Calculates real-time metrics for dashboard visualization."""

    @staticmethod
    def calculate_tournament_metrics(aggregator: DataAggregator) -> Dict[str, Any]:
        """Calculate overall tournament metrics."""
        standings = aggregator.get_standings()

        if not standings:
            return {
                "total_players": 0,
                "total_matches": 0,
                "avg_score": 0,
                "avg_win_rate": 0
            }

        total_matches = sum(p.get("total_matches", 0) for p in standings) // 2
        avg_score = sum(p.get("score", 0) for p in standings) / len(standings)

        win_rates = [
            (p.get("wins", 0) / p.get("total_matches", 1)) * 100
            for p in standings if p.get("total_matches", 0) > 0
        ]
        avg_win_rate = sum(win_rates) / len(win_rates) if win_rates else 0

        return {
            "total_players": len(standings),
            "total_matches": total_matches,
            "avg_score": avg_score,
            "avg_win_rate": avg_win_rate,
            "matches_per_player": total_matches / len(standings) if standings else 0
        }

    @staticmethod
    def calculate_strategy_performance(aggregator: DataAggregator) -> Dict[str, Dict[str, Any]]:
        """Calculate performance metrics by strategy."""
        strategy_stats: Dict[str, List[Dict[str, Any]]] = {}

        for player in aggregator.players.values():
            strategy = player.get("strategy", "Unknown")
            if strategy not in strategy_stats:
                strategy_stats[strategy] = []
            strategy_stats[strategy].append(player)

        performance = {}
        for strategy, players in strategy_stats.items():
            total_matches = sum(p.get("total_matches", 0) for p in players)
            total_wins = sum(p.get("wins", 0) for p in players)
            total_score = sum(p.get("score", 0) for p in players)

            performance[strategy] = {
                "player_count": len(players),
                "total_matches": total_matches,
                "total_wins": total_wins,
                "win_rate": (total_wins / total_matches * 100) if total_matches > 0 else 0,
                "avg_score": total_score / len(players),
                "avg_matches": total_matches / len(players)
            }

        return performance


class InnovationMonitor:
    """Monitors and tracks innovation-specific metrics."""

    def __init__(self):
        self.innovation_stats = {
            "brqc": {"enabled": True, "consensus_time": [], "speedup": []},
            "byzantine": {"enabled": True, "detections": 0, "false_positives": 0},
            "quantum": {"enabled": True, "convergence_times": [], "win_rate_boost": []},
            "few_shot": {"enabled": True, "adaptation_times": []},
            "causal": {"enabled": False, "inferences": 0}
        }

    def record_brqc_consensus(self, consensus_time: float, speedup: float):
        """Record BRQC consensus metrics."""
        self.innovation_stats["brqc"]["consensus_time"].append(consensus_time)
        self.innovation_stats["brqc"]["speedup"].append(speedup)

    def record_byzantine_detection(self, detected: bool, false_positive: bool = False):
        """Record Byzantine fault detection."""
        if detected:
            self.innovation_stats["byzantine"]["detections"] += 1
        if false_positive:
            self.innovation_stats["byzantine"]["false_positives"] += 1

    def get_innovation_summary(self) -> Dict[str, Any]:
        """Get summary of all innovation metrics."""
        summary = {}

        for innovation, stats in self.innovation_stats.items():
            if innovation == "brqc" and stats["consensus_time"]:
                summary[innovation] = {
                    "enabled": stats["enabled"],
                    "avg_consensus_time": sum(stats["consensus_time"]) / len(stats["consensus_time"]),
                    "avg_speedup": sum(stats["speedup"]) / len(stats["speedup"]) if stats["speedup"] else 0,
                    "samples": len(stats["consensus_time"])
                }
            elif innovation == "byzantine":
                total = stats["detections"] + stats["false_positives"]
                summary[innovation] = {
                    "enabled": stats["enabled"],
                    "detection_rate": (stats["detections"] / total * 100) if total > 0 else 100,
                    "total_detections": stats["detections"],
                    "false_positives": stats["false_positives"]
                }
            elif innovation == "quantum" and stats["convergence_times"]:
                summary[innovation] = {
                    "enabled": stats["enabled"],
                    "avg_convergence_time": sum(stats["convergence_times"]) / len(stats["convergence_times"]),
                    "win_rate_boost": sum(stats["win_rate_boost"]) / len(stats["win_rate_boost"]) if stats["win_rate_boost"] else 0
                }
            else:
                summary[innovation] = {"enabled": stats["enabled"]}

        return summary


class UltimateDashboardIntegration:
    """
    Complete integration between game league and Ultimate Dashboard.

    Handles:
    - Event processing from game league
    - Data aggregation and transformation
    - Real-time metrics calculation
    - WebSocket message broadcasting
    - All dashboard tab data population
    """

    def __init__(self, dashboard: UltimateDashboard, event_bus: EventBus):
        """
        Initialize dashboard integration.

        Args:
            dashboard: Ultimate dashboard instance
            event_bus: Event bus for game events
        """
        self.dashboard = dashboard
        self.event_bus = event_bus

        # Data components
        self.aggregator = DataAggregator()
        self.metrics_calc = MetricsCalculator()
        self.innovation_monitor = InnovationMonitor()

        # Tournament state
        self.tournament_id: Optional[str] = None
        self.current_round: int = 0
        self.total_rounds: int = 0
        self.tournament_started: bool = False
        self.tournament_complete: bool = False

    async def initialize(self, tournament_id: str = "default", total_rounds: int = 10):
        """
        Initialize the integration.

        Args:
            tournament_id: Tournament identifier
            total_rounds: Total number of rounds
        """
        self.tournament_id = tournament_id
        self.total_rounds = total_rounds

        # Subscribe to all relevant events
        self._subscribe_to_events()

        logger.info(f"Ultimate Dashboard Integration initialized for tournament {tournament_id}")

    def _subscribe_to_events(self):
        """Subscribe to all game events."""
        # Tournament events
        self.event_bus.on("tournament.start", self._on_tournament_start)
        self.event_bus.on("tournament.complete", self._on_tournament_complete)

        # Round events
        self.event_bus.on("round.start", self._on_round_start)
        self.event_bus.on("round.complete", self._on_round_complete)

        # Match events
        self.event_bus.on("match.start", self._on_match_start)
        self.event_bus.on("match.complete", self._on_match_complete)

        # Game events
        self.event_bus.on("game.move", self._on_game_move)
        self.event_bus.on("game.round.complete", self._on_game_round_complete)

        # Player events
        self.event_bus.on("player.registered", self._on_player_registered)
        self.event_bus.on("player.stats.update", self._on_player_stats_update)

        # Innovation events
        self.event_bus.on("innovation.brqc.consensus", self._on_brqc_consensus)
        self.event_bus.on("innovation.byzantine.detection", self._on_byzantine_detection)

        logger.debug("Subscribed to all game events")

    def register_player(self, player_id: str, strategy: str, **kwargs):
        """Register a player with the dashboard."""
        self.aggregator.register_player(player_id, strategy, **kwargs)

    # Event Handlers

    async def _on_tournament_start(self, event: Dict[str, Any]):
        """Handle tournament start event."""
        self.tournament_started = True
        self.current_round = 0

        logger.info("Tournament started - broadcasting to dashboard")

        await self._broadcast_tournament_update()

    async def _on_tournament_complete(self, event: Dict[str, Any]):
        """Handle tournament complete event."""
        self.tournament_complete = True

        standings = self.aggregator.get_standings()
        if standings:
            winner = standings[0]
            logger.info(f"Tournament complete - Winner: {winner['player_id']}")

            await self.dashboard.send_tournament_complete(winner)

    async def _on_round_start(self, event: Dict[str, Any]):
        """Handle round start event."""
        self.current_round = event.get("round", self.current_round + 1)

        logger.debug(f"Round {self.current_round} started")

        await self._broadcast_tournament_update()

    async def _on_round_complete(self, event: Dict[str, Any]):
        """Handle round complete event."""
        round_num = event.get("round", self.current_round)

        # Record round statistics
        self.aggregator.record_round_stats(round_num, event.get("stats", {}))

        await self._broadcast_tournament_update()

    async def _on_match_start(self, event: Dict[str, Any]):
        """Handle match start event."""
        logger.debug(f"Match started: {event.get('match_id')}")

    async def _on_match_complete(self, event: Dict[str, Any]):
        """Handle match complete event."""
        match_data = event.get("match", {})

        # Record match
        self.aggregator.record_match(match_data)

        # Update player stats
        for player_id in [match_data.get("player_a"), match_data.get("player_b")]:
            if player_id:
                self.aggregator.update_player_stats(player_id, **event.get(f"{player_id}_stats", {}))

        await self._broadcast_tournament_update()

    async def _on_game_move(self, event: Dict[str, Any]):
        """Handle game move event."""
        # Can be used for real-time move visualization
        pass

    async def _on_game_round_complete(self, event: Dict[str, Any]):
        """Handle game round complete event."""
        # Update round statistics
        pass

    async def _on_player_registered(self, event: Dict[str, Any]):
        """Handle player registered event."""
        player_id = event.get("player_id")
        strategy = event.get("strategy", "Unknown")

        if player_id:
            self.register_player(player_id, strategy)
            await self._broadcast_tournament_update()

    async def _on_player_stats_update(self, event: Dict[str, Any]):
        """Handle player stats update event."""
        player_id = event.get("player_id")
        if player_id:
            self.aggregator.update_player_stats(player_id, **event.get("stats", {}))
            await self._broadcast_tournament_update()

    async def _on_brqc_consensus(self, event: Dict[str, Any]):
        """Handle BRQC consensus event."""
        consensus_time = event.get("consensus_time", 0)
        speedup = event.get("speedup", 0)

        self.innovation_monitor.record_brqc_consensus(consensus_time, speedup)

    async def _on_byzantine_detection(self, event: Dict[str, Any]):
        """Handle Byzantine detection event."""
        detected = event.get("detected", False)
        false_positive = event.get("false_positive", False)

        self.innovation_monitor.record_byzantine_detection(detected, false_positive)

    # Broadcasting Methods

    async def _broadcast_tournament_update(self):
        """Broadcast tournament update to dashboard."""
        standings = self.aggregator.get_standings()

        await self.dashboard.send_tournament_update(
            current_round=self.current_round,
            total_rounds=self.total_rounds,
            standings=standings
        )

    async def cleanup(self):
        """Cleanup integration resources."""
        # Unsubscribe from events if needed
        logger.info("Ultimate Dashboard Integration cleaned up")


# Singleton instances
_integration_instance: Optional[UltimateDashboardIntegration] = None


def get_ultimate_dashboard_integration() -> Optional[UltimateDashboardIntegration]:
    """Get the singleton dashboard integration instance."""
    return _integration_instance


def set_ultimate_dashboard_integration(integration: UltimateDashboardIntegration):
    """Set the singleton dashboard integration instance."""
    global _integration_instance
    _integration_instance = integration
