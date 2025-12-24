"""
Custom Event Handlers Example
==============================

Demonstrates how to create custom event handlers for the MCP Multi-Agent Game League.

This example shows:
1. Using the @on_event decorator to register handlers
2. Handling specific and wildcard event patterns
3. Accessing event data
4. Logging and auditing with events
5. Analytics and metrics collection

Usage:
    python examples/event_handlers/custom_logger.py
"""

import asyncio
from datetime import datetime
from typing import Dict, List
from collections import defaultdict

from src.common.events import (
    get_event_bus,
    on_event,
    BaseEvent,
    GameStartedEvent,
    RoundCompletedEvent,
    MatchCompletedEvent,
    PlayerMoveAfterEvent,
    StrategySelectedEvent,
)
from src.common.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# Example 1: Simple Event Logger
# ============================================================================


class EventLogger:
    """
    Simple event logger that logs all events to a file.

    Demonstrates:
    - Using @on_event decorator
    - Handling wildcard patterns
    - Accessing event metadata
    """

    def __init__(self, log_file: str = "event_log.jsonl"):
        """
        Initialize event logger.

        Args:
            log_file: Path to JSON lines log file
        """
        self.log_file = log_file
        self.event_count = 0

        # Register handlers using decorator
        self.register_handlers()

    def register_handlers(self):
        """Register event handlers."""
        # Log all events to file
        get_event_bus().on(
            pattern="*",
            handler=self.log_all_events,
            priority=0,
            description="Log all events to file",
        )

    async def log_all_events(self, event: BaseEvent):
        """
        Log all events to file.

        Args:
            event: Any event type
        """
        self.event_count += 1

        # Convert event to dict
        event_dict = event.model_dump()

        # Add to log file (in production, use proper file handling)
        logger.info(f"Event logged: {event.event_type}", event_id=event.event_id)

        # In production, write to actual file:
        # with open(self.log_file, 'a') as f:
        #     f.write(json.dumps(event_dict) + '\n')


# ============================================================================
# Example 2: Game Analytics Collector
# ============================================================================


class GameAnalytics:
    """
    Collects game analytics from events.

    Demonstrates:
    - Collecting data from multiple event types
    - Using event patterns to filter
    - Aggregating statistics
    """

    def __init__(self):
        """Initialize analytics collector."""
        self.stats = {
            "total_games": 0,
            "total_rounds": 0,
            "total_moves": 0,
            "player_wins": defaultdict(int),
            "strategy_usage": defaultdict(int),
            "average_decision_time": [],
        }

        self.register_handlers()

    def register_handlers(self):
        """Register event handlers."""
        bus = get_event_bus()

        # Track game starts
        bus.on("game.started", self.on_game_started, priority=5)

        # Track round completions
        bus.on("round.completed", self.on_round_completed, priority=5)

        # Track player moves
        bus.on("player.move.after", self.on_player_move, priority=5)

        # Track match completions
        bus.on("match.completed", self.on_match_completed, priority=5)

        # Track strategy selections
        bus.on("strategy.selected", self.on_strategy_selected, priority=5)

    async def on_game_started(self, event: GameStartedEvent):
        """Handle game started event."""
        self.stats["total_games"] += 1
        logger.info(
            f"Analytics: Game started - Total games: {self.stats['total_games']}"
        )

    async def on_round_completed(self, event: RoundCompletedEvent):
        """Handle round completed event."""
        self.stats["total_rounds"] += 1

    async def on_player_move(self, event: PlayerMoveAfterEvent):
        """Handle player move event."""
        self.stats["total_moves"] += 1

        # Track decision time
        if event.decision_time_ms > 0:
            self.stats["average_decision_time"].append(event.decision_time_ms)

    async def on_match_completed(self, event: MatchCompletedEvent):
        """Handle match completed event."""
        # Track winner
        if event.winner:
            self.stats["player_wins"][event.winner] += 1

    async def on_strategy_selected(self, event: StrategySelectedEvent):
        """Handle strategy selected event."""
        self.stats["strategy_usage"][event.strategy_name] += 1

    def get_report(self) -> Dict:
        """
        Get analytics report.

        Returns:
            Dictionary with analytics
        """
        avg_decision_time = (
            sum(self.stats["average_decision_time"])
            / len(self.stats["average_decision_time"])
            if self.stats["average_decision_time"]
            else 0
        )

        return {
            "total_games": self.stats["total_games"],
            "total_rounds": self.stats["total_rounds"],
            "total_moves": self.stats["total_moves"],
            "player_wins": dict(self.stats["player_wins"]),
            "strategy_usage": dict(self.stats["strategy_usage"]),
            "average_decision_time_ms": round(avg_decision_time, 2),
        }


# ============================================================================
# Example 3: Real-time Game Monitor
# ============================================================================


class GameMonitor:
    """
    Real-time game monitoring with event handlers.

    Demonstrates:
    - Priority-based handlers
    - Multiple handlers for same event
    - Event pattern matching
    """

    def __init__(self):
        """Initialize game monitor."""
        self.active_games = {}
        self.register_handlers()

    def register_handlers(self):
        """Register event handlers with priorities."""
        bus = get_event_bus()

        # High priority - track game state first
        bus.on("game.*", self.update_game_state, priority=10)

        # Medium priority - notifications
        bus.on("match.completed", self.notify_match_complete, priority=5)

        # Low priority - cleanup
        bus.on("match.completed", self.cleanup_game, priority=1)

    async def update_game_state(self, event: BaseEvent):
        """Update game state tracking."""
        if hasattr(event, "game_id"):
            game_id = event.game_id
            if game_id not in self.active_games:
                self.active_games[game_id] = {
                    "started_at": datetime.utcnow(),
                    "events": [],
                }

            self.active_games[game_id]["events"].append(event.event_type)

    async def notify_match_complete(self, event: MatchCompletedEvent):
        """Send notifications when match completes."""
        logger.info(
            f"Match completed: {event.match_id}",
            winner=event.winner,
            duration=f"{event.duration_seconds:.1f}s",
        )

        # In production, send actual notifications:
        # - Email/SMS alerts
        # - Webhook to external systems
        # - Dashboard updates

    async def cleanup_game(self, event: MatchCompletedEvent):
        """Cleanup game data after completion."""
        # Remove from active games
        if hasattr(event, "match_id"):
            for game_id in list(self.active_games.keys()):
                # In production, match game_id to match_id properly
                pass


# ============================================================================
# Example 4: Audit Trail
# ============================================================================


class AuditTrail:
    """
    Security audit trail using events.

    Demonstrates:
    - Security event tracking
    - Compliance logging
    - Suspicious activity detection
    """

    def __init__(self):
        """Initialize audit trail."""
        self.audit_log: List[Dict] = []
        self.register_handlers()

    def register_handlers(self):
        """Register audit handlers."""
        bus = get_event_bus()

        # Track all agent registrations
        bus.on("agent.registered", self.audit_registration, priority=10)

        # Track all errors
        bus.on("*.error", self.audit_error, priority=10)

        # Track player actions
        bus.on("player.*", self.audit_player_action, priority=5)

    async def audit_registration(self, event: BaseEvent):
        """Audit agent registration."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "registration",
            "agent_id": getattr(event, "agent_id", None),
            "agent_type": getattr(event, "agent_type", None),
            "source": event.source,
        }

        self.audit_log.append(entry)
        logger.info(f"Audit: Agent registered - {entry}")

    async def audit_error(self, event: BaseEvent):
        """Audit error events."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "error",
            "error_type": getattr(event, "error_type", "unknown"),
            "error_message": getattr(event, "error_message", ""),
            "source": event.source,
            "severity": "high",
        }

        self.audit_log.append(entry)
        logger.warning(f"Audit: Error detected - {entry}")

    async def audit_player_action(self, event: BaseEvent):
        """Audit player actions."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event.event_type,
            "player_id": getattr(event, "player_id", None),
            "action": event.event_type.split(".")[-1],
        }

        self.audit_log.append(entry)

    def get_audit_log(self) -> List[Dict]:
        """Get audit log."""
        return self.audit_log


# ============================================================================
# Example Usage
# ============================================================================


async def main():
    """
    Example usage of custom event handlers.

    Shows how to:
    1. Create handler instances
    2. Register them with the event bus
    3. Emit test events
    4. Retrieve analytics
    """
    print("=" * 60)
    print("Custom Event Handlers Example")
    print("=" * 60)

    # Create handler instances
    event_logger = EventLogger()
    analytics = GameAnalytics()
    monitor = GameMonitor()
    audit = AuditTrail()

    print(f"\nRegistered {get_event_bus().get_handler_count()} event handlers")

    # Emit some test events
    bus = get_event_bus()

    print("\n--- Emitting test events ---")

    # Test event 1: Game started
    await bus.emit(
        "game.started",
        GameStartedEvent(
            game_id="game_001",
            game_type="even_odd",
            players=["P01", "P02"],
            referee_id="REF01",
            source="test",
        ),
    )
    print("✓ Emitted game.started")

    # Test event 2: Round completed
    await bus.emit(
        "round.completed",
        RoundCompletedEvent(
            game_id="game_001",
            round_number=1,
            moves={"P01": 5, "P02": 3},
            scores={"P01": 1, "P02": 0},
            cumulative_scores={"P01": 1, "P02": 0},
            source="test",
        ),
    )
    print("✓ Emitted round.completed")

    # Test event 3: Player move
    await bus.emit(
        "player.move.after",
        PlayerMoveAfterEvent(
            player_id="P01",
            game_id="game_001",
            round_number=1,
            move=5,
            decision_time_ms=123.45,
            source="test",
        ),
    )
    print("✓ Emitted player.move.after")

    # Test event 4: Match completed
    await bus.emit(
        "match.completed",
        MatchCompletedEvent(
            match_id="match_001",
            winner="P01",
            final_scores={"P01": 3, "P02": 2},
            total_rounds=5,
            duration_seconds=45.6,
            source="test",
        ),
    )
    print("✓ Emitted match.completed")

    # Get analytics report
    print("\n--- Analytics Report ---")
    report = analytics.get_report()
    for key, value in report.items():
        print(f"{key}: {value}")

    # Get event bus stats
    print("\n--- Event Bus Stats ---")
    stats = bus.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")

    # Get audit log
    print(f"\n--- Audit Log ---")
    print(f"Total audit entries: {len(audit.get_audit_log())}")

    print("\n✓ Example completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
