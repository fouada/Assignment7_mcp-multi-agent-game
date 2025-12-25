"""
Event Types
===========

Standard event types for the MCP Multi-Agent Game League.

Provides:
- BaseEvent: Base class for all events with common fields
- GameEvents: Events related to game lifecycle (started, ended, rounds)
- AgentEvents: Events related to agent lifecycle (registered, connected, disconnected)
- StrategyEvents: Events related to strategy decisions
- PluginEvents: Events related to plugin lifecycle
- SystemEvents: Events related to system lifecycle (startup, shutdown, errors)

Usage:
    from src.common.events import GameStartedEvent

    event = GameStartedEvent(
        game_id="game_123",
        players=["player1", "player2"],
        game_type="odd_even"
    )
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    """Base class for all events."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic config."""

        json_encoders = {datetime: lambda v: v.isoformat()}
        extra = "allow"  # Allow extra fields for flexible event data


# ============================================================================
# Game Events
# ============================================================================


class GameStartedEvent(BaseEvent):
    """Event emitted when a game starts."""

    event_type: str = "game.started"
    game_id: str
    game_type: str
    players: list[str]
    referee_id: str = ""


class GameEndedEvent(BaseEvent):
    """Event emitted when a game ends."""

    event_type: str = "game.ended"
    game_id: str
    game_type: str
    winner: str | None = None
    final_scores: dict[str, int] = Field(default_factory=dict)
    total_rounds: int = 0


class RoundStartedEvent(BaseEvent):
    """Event emitted when a round starts."""

    event_type: str = "round.started"
    game_id: str
    round_number: int
    players: list[str]


class RoundCompletedEvent(BaseEvent):
    """Event emitted when a round completes."""

    event_type: str = "round.completed"
    game_id: str
    round_number: int
    moves: dict[str, int] = Field(default_factory=dict)
    scores: dict[str, int] = Field(default_factory=dict)
    cumulative_scores: dict[str, int] = Field(default_factory=dict)


# ============================================================================
# Agent Events
# ============================================================================


class AgentRegisteredEvent(BaseEvent):
    """Event emitted when an agent registers."""

    event_type: str = "agent.registered"
    agent_id: str
    agent_type: str  # "player", "referee", "league_manager"
    agent_name: str = ""


class AgentConnectedEvent(BaseEvent):
    """Event emitted when an agent connects."""

    event_type: str = "agent.connected"
    agent_id: str
    agent_type: str
    endpoint: str = ""


class AgentDisconnectedEvent(BaseEvent):
    """Event emitted when an agent disconnects."""

    event_type: str = "agent.disconnected"
    agent_id: str
    agent_type: str
    reason: str = ""


class AgentErrorEvent(BaseEvent):
    """Event emitted when an agent encounters an error."""

    event_type: str = "agent.error"
    agent_id: str
    agent_type: str
    error_type: str
    error_message: str
    traceback: str = ""


# ============================================================================
# Strategy Events
# ============================================================================


class StrategySelectedEvent(BaseEvent):
    """Event emitted when a strategy is selected."""

    event_type: str = "strategy.selected"
    agent_id: str
    strategy_name: str
    strategy_type: str = ""
    is_plugin: bool = False


class MoveDecidedEvent(BaseEvent):
    """Event emitted when a strategy decides a move."""

    event_type: str = "strategy.move.decided"
    agent_id: str
    game_id: str
    round_number: int
    strategy_name: str
    move: int
    decision_time_ms: float = 0.0


class StrategyErrorEvent(BaseEvent):
    """Event emitted when a strategy encounters an error."""

    event_type: str = "strategy.error"
    agent_id: str
    game_id: str
    strategy_name: str
    error_type: str
    error_message: str


# ============================================================================
# Player Events
# ============================================================================


class PlayerGameInvitedEvent(BaseEvent):
    """Event emitted when a player is invited to a game."""

    event_type: str = "player.game.invited"
    player_id: str
    game_id: str
    game_type: str
    referee_id: str


class PlayerGameJoinedEvent(BaseEvent):
    """Event emitted when a player joins a game."""

    event_type: str = "player.game.joined"
    player_id: str
    game_id: str
    role: str = ""


class PlayerMoveBeforeEvent(BaseEvent):
    """Event emitted before a player makes a move."""

    event_type: str = "player.move.before"
    player_id: str
    game_id: str
    round_number: int
    my_role: str
    my_score: int
    opponent_score: int


class PlayerMoveAfterEvent(BaseEvent):
    """Event emitted after a player makes a move."""

    event_type: str = "player.move.after"
    player_id: str
    game_id: str
    round_number: int
    move: int
    decision_time_ms: float = 0.0


# ============================================================================
# Plugin Events
# ============================================================================


class PluginLoadedEvent(BaseEvent):
    """Event emitted when a plugin is loaded."""

    event_type: str = "plugin.loaded"
    plugin_name: str
    plugin_version: str
    plugin_type: str = ""


class PluginEnabledEvent(BaseEvent):
    """Event emitted when a plugin is enabled."""

    event_type: str = "plugin.enabled"
    plugin_name: str


class PluginDisabledEvent(BaseEvent):
    """Event emitted when a plugin is disabled."""

    event_type: str = "plugin.disabled"
    plugin_name: str
    reason: str = ""


class PluginErrorEvent(BaseEvent):
    """Event emitted when a plugin encounters an error."""

    event_type: str = "plugin.error"
    plugin_name: str
    error_type: str
    error_message: str
    phase: str = ""  # "load", "enable", "disable", "unload"


# ============================================================================
# System Events
# ============================================================================


class SystemStartupEvent(BaseEvent):
    """Event emitted when the system starts."""

    event_type: str = "system.startup"
    component: str
    version: str = ""


class SystemShutdownEvent(BaseEvent):
    """Event emitted when the system shuts down."""

    event_type: str = "system.shutdown"
    component: str
    reason: str = ""


class SystemErrorEvent(BaseEvent):
    """Event emitted when a system error occurs."""

    event_type: str = "system.error"
    component: str
    error_type: str
    error_message: str
    traceback: str = ""
    severity: str = "error"  # "warning", "error", "critical"


# ============================================================================
# Match Events
# ============================================================================


class MatchStartedEvent(BaseEvent):
    """Event emitted when a match starts."""

    event_type: str = "match.started"
    match_id: str
    game_type: str
    players: list[str]
    referee_id: str


class MatchCompletedEvent(BaseEvent):
    """Event emitted when a match completes."""

    event_type: str = "match.completed"
    match_id: str
    winner: str | None = None
    final_scores: dict[str, int] = Field(default_factory=dict)
    total_rounds: int = 0
    duration_seconds: float = 0.0


# ============================================================================
# Tournament Events
# ============================================================================


class TournamentRoundStartedEvent(BaseEvent):
    """Event emitted when a tournament round starts."""

    event_type: str = "tournament.round.started"
    round_number: int
    total_rounds: int
    matches: list[str] = Field(default_factory=list)


class StandingsUpdatedEvent(BaseEvent):
    """Event emitted when standings are updated."""

    event_type: str = "standings.updated"
    standings: list[dict[str, Any]] = Field(default_factory=list)
    round_number: int = 0


class TournamentCompletedEvent(BaseEvent):
    """Event emitted when a tournament completes."""

    event_type: str = "tournament.completed"
    winner: str | None = None
    final_standings: list[dict[str, Any]] = Field(default_factory=list)
    total_rounds: int = 0
    total_matches: int = 0
