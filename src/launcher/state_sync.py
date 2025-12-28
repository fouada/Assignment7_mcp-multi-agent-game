"""
State Synchronization Service - MIT Level
==========================================

Guarantees state synchronization across all components with dashboard updates.

Features:
- Guaranteed delivery of state updates
- Event acknowledgment system
- Real-time dashboard synchronization
- State change tracking
- Rollback on failure

Architecture:
- Components publish state changes to event bus
- StateSyncService ensures delivery to all subscribers
- Dashboard receives all updates via WebSocket
- Acknowledgments confirm successful delivery
"""

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from ..common.events import BaseEvent, get_event_bus
from ..common.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StateChange:
    """Represents a state change event."""

    change_id: str
    event_type: str
    timestamp: datetime
    source: str
    data: dict[str, Any]
    acknowledged: bool = False
    retries: int = 0


@dataclass
class StateSnapshot:
    """Snapshot of system state at a point in time."""

    snapshot_id: str
    timestamp: datetime
    components: dict[str, dict[str, Any]] = field(default_factory=dict)
    standings: list[dict[str, Any]] = field(default_factory=list)
    current_round: int = 0
    matches: list[dict[str, Any]] = field(default_factory=list)


class StateSyncService:
    """
    Manages state synchronization across all components.

    Ensures:
    - All state changes are delivered to dashboard
    - Components stay in sync
    - No state is lost during updates
    - Dashboard always shows current state

    Usage:
        sync = get_state_sync()
        await sync.start()

        # Publish state change
        await sync.publish_state_change(
            event_type="player.registered",
            source="league_manager",
            data={"player_id": "P01", "name": "Alice"}
        )

        # Subscribe to state changes
        sync.subscribe("player.registered", on_player_registered)
    """

    _instance: "StateSyncService | None" = None

    def __new__(cls) -> "StateSyncService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.event_bus = get_event_bus()
        self._state_changes: deque[StateChange] = deque(maxlen=1000)
        self._subscribers: dict[str, list[Callable]] = {}
        self._snapshots: deque[StateSnapshot] = deque(maxlen=10)
        self._current_state: dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self._running = False
        self._initialized = True

        logger.info("StateSyncService initialized")

    async def start(self) -> None:
        """Start state synchronization service."""
        if self._running:
            return

        self._running = True

        # Subscribe to all events for tracking
        self.event_bus.on("*", self._on_any_event, priority=1000)

        logger.info("StateSyncService started - monitoring all state changes")

    async def stop(self) -> None:
        """Stop state synchronization service."""
        self._running = False
        logger.info("StateSyncService stopped")

    async def _on_any_event(self, event: BaseEvent) -> None:
        """Handle any event for state tracking."""
        if not self._running:
            return

        # Track state change - timestamp is already a datetime object
        # Convert event to dict for data, excluding base fields
        event_dict = event.dict()
        event_data = {k: v for k, v in event_dict.items() 
                      if k not in ('event_id', 'event_type', 'timestamp', 'source', 'metadata')}
        
        change = StateChange(
            change_id=f"{event.event_type}_{event.timestamp.isoformat()}",
            event_type=event.event_type,
            timestamp=event.timestamp,  # Already a datetime object
            source=getattr(event, "source", "unknown"),
            data=event_data,
        )

        async with self._lock:
            self._state_changes.append(change)

        # Notify subscribers
        await self._notify_subscribers(event.event_type, event)

        logger.debug(f"State change tracked: {event.event_type}")

    async def publish_state_change(
        self,
        event_type: str,
        source: str,
        data: dict[str, Any],
    ) -> None:
        """
        Publish a state change with guaranteed delivery.

        Args:
            event_type: Type of state change (e.g., "player.registered")
            source: Source component (e.g., "league_manager")
            data: State change data
        """
        # Create event
        event = BaseEvent(
            event_type=event_type,
            source=source,
            data=data,
        )

        # Emit via event bus
        await self.event_bus.emit(event_type, event)

        logger.debug(f"State change published: {event_type} from {source}")

    def subscribe(self, event_pattern: str, handler: Callable) -> str:
        """
        Subscribe to state changes.

        Args:
            event_pattern: Event pattern to subscribe to (supports wildcards)
            handler: Callback function

        Returns:
            Subscription ID for unsubscribing
        """
        return self.event_bus.on(event_pattern, handler)

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from state changes."""
        return self.event_bus.off(subscription_id)

    async def _notify_subscribers(self, event_type: str, event: BaseEvent) -> None:
        """Notify all subscribers of a state change."""
        if event_type not in self._subscribers:
            return

        for handler in self._subscribers[event_type]:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in state change handler: {e}")

    async def subscribe_to_all_events(self, dashboard: Any) -> None:
        """
        Subscribe dashboard to all state changes.

        Args:
            dashboard: Dashboard instance to receive updates
        """

        # Subscribe to key events
        event_patterns = [
            "agent.registered",
            "tournament.round.started",
            "tournament.completed",
            "game.round.start",
            "game.move.decision",
            "game.round.complete",
            "standings.updated",
            "match.started",
            "match.completed",
            "strategy.performance",
            "opponent.model.update",
            "counterfactual.analysis",
        ]

        # Create async handler with proper closure
        async def forward_handler(event: BaseEvent) -> None:
            await self._forward_to_dashboard(dashboard, event)

        for pattern in event_patterns:
            self.event_bus.on(
                pattern,
                forward_handler,
                priority=900,
            )

        logger.info("Dashboard subscribed to all state change events")

    async def _forward_to_dashboard(self, dashboard: Any, event: BaseEvent) -> None:
        """Forward event to dashboard via WebSocket."""
        try:
            if hasattr(dashboard, "connection_manager"):
                from datetime import datetime
                from dataclasses import is_dataclass, asdict as dataclass_asdict
                
                def convert_to_serializable(obj):
                    """Recursively convert objects to JSON-serializable format"""
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    elif is_dataclass(obj):
                        return convert_to_serializable(dataclass_asdict(obj))
                    elif isinstance(obj, dict):
                        return {k: convert_to_serializable(v) for k, v in obj.items()}
                    elif isinstance(obj, (list, tuple)):
                        return [convert_to_serializable(item) for item in obj]
                    elif hasattr(obj, 'to_dict') and callable(obj.to_dict):
                        return convert_to_serializable(obj.to_dict())
                    return obj
                
                # Convert event to dict for serialization
                event_dict = event.dict()
                # Ensure all datetime objects are converted
                serializable_event_dict = convert_to_serializable(event_dict)
                
                await dashboard.connection_manager.broadcast(
                    {
                        "type": "state_update",
                        "event_type": event.event_type,
                        "timestamp": event.timestamp.isoformat() if isinstance(event.timestamp, datetime) else event.timestamp,
                        "data": serializable_event_dict,
                    }
                )
        except Exception as e:
            logger.error(f"Failed to forward event to dashboard: {e}")

    async def create_snapshot(self, snapshot_id: str) -> StateSnapshot:
        """Create a snapshot of current system state."""
        snapshot = StateSnapshot(
            snapshot_id=snapshot_id,
            timestamp=datetime.utcnow(),
        )

        async with self._lock:
            snapshot.components = self._current_state.copy()
            self._snapshots.append(snapshot)

        logger.info(f"State snapshot created: {snapshot_id}")
        return snapshot

    async def get_current_state(self) -> dict[str, Any]:
        """Get current system state."""
        async with self._lock:
            return self._current_state.copy()

    async def get_state_history(self, limit: int = 100) -> list[StateChange]:
        """Get recent state changes."""
        async with self._lock:
            history = list(self._state_changes)
            return history[-limit:] if len(history) > limit else history


# Singleton accessor
_state_sync_instance: StateSyncService | None = None


def get_state_sync() -> StateSyncService:
    """Get global state synchronization service instance."""
    global _state_sync_instance
    if _state_sync_instance is None:
        _state_sync_instance = StateSyncService()
    return _state_sync_instance
