"""
Agent Lifecycle Management
========================================

Manages agent state transitions and lifecycle events.

State Diagram:

    ┌──────────────────────────────────────────┐
    │                                          │
    │  ┌──────┐   register   ┌────────────┐   │
    │  │ INIT │ ───────────► │ REGISTERED │   │
    │  └──┬───┘              └─────┬──────┘   │
    │     │                        │          │
    │     │ error            league_start     │
    │     │                        │          │
    │     │                        ▼          │
    │     │                   ┌────────┐      │
    │     │                   │ ACTIVE │◄─────┤
    │     │                   └────┬───┘      │ recover
    │     │                        │          │
    │     │                   timeout         │
    │     │                        │          │
    │     │                        ▼          │
    │     │                  ┌───────────┐    │
    │     │                  │ SUSPENDED │────┘
    │     │                  └─────┬─────┘
    │     │                        │
    │     │                   max_fails
    │     │                        │
    │     ▼                        ▼
    │  ┌──────────────────────────────────┐
    │  │            SHUTDOWN              │
    │  └──────────────────────────────────┘
    │
    └──────────────────────────────────────────┘
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .logger import get_logger
from .protocol import AgentState

logger = get_logger(__name__)


class LifecycleEvent(str, Enum):
    """Events that trigger state transitions."""

    # Registration events
    REGISTER_SUCCESS = "register_success"
    REGISTER_FAILED = "register_failed"

    # League events
    LEAGUE_START = "league_start"
    LEAGUE_END = "league_end"

    # Activity events
    TIMEOUT = "timeout"
    RECOVER = "recover"
    MAX_FAILS = "max_fails"

    # System events
    SHUTDOWN_REQUEST = "shutdown_request"
    ERROR = "error"


@dataclass
class StateTransition:
    """Record of a state transition."""

    from_state: AgentState
    to_state: AgentState
    event: LifecycleEvent
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "event": self.event.value,
            "timestamp": self.timestamp.isoformat() + "Z",
            "metadata": self.metadata,
        }


class AgentLifecycleManager:
    """
    Manages agent lifecycle and state transitions.

    Usage:
        lifecycle = AgentLifecycleManager(agent_id="P01", agent_type="player")

        # Register callbacks
        lifecycle.on_state_change(lambda old, new: print(f"{old} -> {new}"))

        # Transition states
        await lifecycle.transition(LifecycleEvent.REGISTER_SUCCESS)

        # Check current state
        if lifecycle.state == AgentState.ACTIVE:
            # Agent is active
            pass
    """

    # Valid transitions map
    TRANSITIONS: dict[AgentState, dict[LifecycleEvent, AgentState]] = {
        AgentState.INIT: {
            LifecycleEvent.REGISTER_SUCCESS: AgentState.REGISTERED,
            LifecycleEvent.REGISTER_FAILED: AgentState.SHUTDOWN,
            LifecycleEvent.ERROR: AgentState.SHUTDOWN,
            LifecycleEvent.SHUTDOWN_REQUEST: AgentState.SHUTDOWN,
        },
        AgentState.REGISTERED: {
            LifecycleEvent.LEAGUE_START: AgentState.ACTIVE,
            LifecycleEvent.LEAGUE_END: AgentState.SHUTDOWN,
            LifecycleEvent.ERROR: AgentState.SHUTDOWN,
            LifecycleEvent.SHUTDOWN_REQUEST: AgentState.SHUTDOWN,
        },
        AgentState.ACTIVE: {
            LifecycleEvent.TIMEOUT: AgentState.SUSPENDED,
            LifecycleEvent.LEAGUE_END: AgentState.SHUTDOWN,
            LifecycleEvent.ERROR: AgentState.SUSPENDED,
            LifecycleEvent.SHUTDOWN_REQUEST: AgentState.SHUTDOWN,
        },
        AgentState.SUSPENDED: {
            LifecycleEvent.RECOVER: AgentState.ACTIVE,
            LifecycleEvent.MAX_FAILS: AgentState.SHUTDOWN,
            LifecycleEvent.SHUTDOWN_REQUEST: AgentState.SHUTDOWN,
        },
        AgentState.SHUTDOWN: {},  # Terminal state
    }

    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        initial_state: AgentState = AgentState.INIT,
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self._state = initial_state
        self._history: list[StateTransition] = []
        self._callbacks: list[Callable[[AgentState, AgentState], None]] = []
        self._async_callbacks: list[Callable[[AgentState, AgentState], Any]] = []

        # Failure tracking
        self._failure_count = 0
        self._max_failures = 3

        # Timestamps
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()

        logger.debug(f"AgentLifecycleManager created for {agent_type}:{agent_id}")

    @property
    def state(self) -> AgentState:
        """Get current state."""
        return self._state

    @property
    def is_active(self) -> bool:
        """Check if agent is in an active state (not shutdown)."""
        return self._state not in (AgentState.SHUTDOWN,)

    @property
    def can_participate(self) -> bool:
        """Check if agent can participate in games."""
        return self._state in (AgentState.REGISTERED, AgentState.ACTIVE)

    @property
    def history(self) -> list[StateTransition]:
        """Get state transition history."""
        return self._history.copy()

    def on_state_change(
        self,
        callback: Callable[[AgentState, AgentState], None],
    ) -> None:
        """Register a callback for state changes."""
        self._callbacks.append(callback)

    def on_state_change_async(
        self,
        callback: Callable[[AgentState, AgentState], Any],
    ) -> None:
        """Register an async callback for state changes."""
        self._async_callbacks.append(callback)

    def can_transition(self, event: LifecycleEvent) -> bool:
        """Check if a transition is valid for the current state."""
        valid_events = self.TRANSITIONS.get(self._state, {})
        return event in valid_events

    def get_next_state(self, event: LifecycleEvent) -> AgentState | None:
        """Get the next state for an event, or None if invalid."""
        valid_events = self.TRANSITIONS.get(self._state, {})
        return valid_events.get(event)

    async def transition(
        self,
        event: LifecycleEvent,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Attempt a state transition.

        Returns True if transition was successful.
        """
        if not self.can_transition(event):
            logger.warning(
                f"Invalid transition: {self._state.value} + {event.value}",
                agent_id=self.agent_id,
            )
            return False

        old_state = self._state
        new_state = self.get_next_state(event)

        # Record transition
        transition = StateTransition(
            from_state=old_state,
            to_state=new_state,
            event=event,
            metadata=metadata or {},
        )
        self._history.append(transition)

        # Update state
        self._state = new_state
        self.last_activity = datetime.utcnow()

        logger.info(
            f"State transition: {old_state.value} → {new_state.value}",
            agent_id=self.agent_id,
            event=event.value,
        )

        # Call sync callbacks
        for callback in self._callbacks:
            try:
                callback(old_state, new_state)
            except Exception as e:
                logger.error(f"Callback error: {e}")

        # Call async callbacks
        for callback in self._async_callbacks:
            try:
                await callback(old_state, new_state)
            except Exception as e:
                logger.error(f"Async callback error: {e}")

        return True

    def record_failure(self) -> bool:
        """
        Record a failure and check if max failures reached.

        Returns True if max failures reached (should transition to SHUTDOWN).
        """
        self._failure_count += 1
        logger.warning(
            f"Failure recorded: {self._failure_count}/{self._max_failures}",
            agent_id=self.agent_id,
        )
        return self._failure_count >= self._max_failures

    def reset_failures(self) -> None:
        """Reset failure count (e.g., after successful recovery)."""
        self._failure_count = 0

    def get_uptime(self) -> float:
        """Get agent uptime in seconds."""
        return (datetime.utcnow() - self.created_at).total_seconds()

    def get_state_info(self) -> dict[str, Any]:
        """Get current state information."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "state": self._state.value,
            "is_active": self.is_active,
            "can_participate": self.can_participate,
            "failure_count": self._failure_count,
            "max_failures": self._max_failures,
            "uptime_seconds": self.get_uptime(),
            "created_at": self.created_at.isoformat() + "Z",
            "last_activity": self.last_activity.isoformat() + "Z",
            "transition_count": len(self._history),
        }


class LifecycleRegistry:
    """
    Registry for tracking all agent lifecycles.

    Used by the league manager to monitor agent states.
    """

    def __init__(self):
        self._agents: dict[str, AgentLifecycleManager] = {}

    def register(self, lifecycle: AgentLifecycleManager) -> None:
        """Register an agent lifecycle."""
        key = f"{lifecycle.agent_type}:{lifecycle.agent_id}"
        self._agents[key] = lifecycle
        logger.debug(f"Registered lifecycle: {key}")

    def unregister(self, agent_id: str, agent_type: str) -> None:
        """Unregister an agent lifecycle."""
        key = f"{agent_type}:{agent_id}"
        if key in self._agents:
            del self._agents[key]
            logger.debug(f"Unregistered lifecycle: {key}")

    def get(self, agent_id: str, agent_type: str) -> AgentLifecycleManager | None:
        """Get an agent's lifecycle manager."""
        key = f"{agent_type}:{agent_id}"
        return self._agents.get(key)

    def get_by_state(self, state: AgentState) -> list[AgentLifecycleManager]:
        """Get all agents in a specific state."""
        return [lc for lc in self._agents.values() if lc.state == state]

    def get_active_agents(self) -> list[AgentLifecycleManager]:
        """Get all active agents."""
        return [lc for lc in self._agents.values() if lc.is_active]

    def get_all(self) -> list[AgentLifecycleManager]:
        """Get all registered lifecycles."""
        return list(self._agents.values())

    def get_summary(self) -> dict[str, Any]:
        """Get summary of all agent states."""
        state_counts = {}
        for state in AgentState:
            state_counts[state.value] = len(self.get_by_state(state))

        return {
            "total_agents": len(self._agents),
            "active_agents": len(self.get_active_agents()),
            "state_counts": state_counts,
        }


# Global lifecycle registry
_registry: LifecycleRegistry | None = None


def get_lifecycle_registry() -> LifecycleRegistry:
    """Get global lifecycle registry."""
    global _registry
    if _registry is None:
        _registry = LifecycleRegistry()
    return _registry
