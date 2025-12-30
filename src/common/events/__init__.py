"""
Event System
============

Production-grade event bus and hook system for the MCP Multi-Agent Game League.

Provides:
- EventBus: Central event bus with wildcard matching and priority queues
- Event Types: Standard event types for games, agents, strategies, plugins, system
- Decorators: Convenient decorators for event handling (@on_event, @before, @after)

Usage:
    from src.common.events import (
        get_event_bus,
        on_event,
        GameStartedEvent,
        PlayerMoveAfterEvent,
    )

    # Register handler with decorator
    @on_event("game.started", priority=10)
    async def on_game_start(event: GameStartedEvent):
        print(f"Game {event.game_id} started!")

    # Or register programmatically
    bus = get_event_bus()
    handler_id = bus.on("game.*", my_handler)

    # Emit event
    await bus.emit("game.started", GameStartedEvent(game_id="123", ...))

    # Unregister
    bus.off(handler_id)
"""

# Event Bus
from .bus import EventBus, HandlerMetadata, get_event_bus

# Decorators
from .decorators import (
    after,
    before,
    emit_on_exception,
    on_error,
    on_event,
)

# Event Types
from .types import (
    AgentConnectedEvent,
    AgentDisconnectedEvent,
    AgentErrorEvent,
    # Agent Events
    AgentRegisteredEvent,
    # Base
    BaseEvent,
    # Analytics Events
    CounterfactualAnalysisEvent,
    GameEndedEvent,
    # Game Events
    GameStartedEvent,
    MatchCompletedEvent,
    # Match Events
    MatchStartedEvent,
    MoveDecidedEvent,
    OpponentModelUpdateEvent,
    # Player Events
    PlayerGameInvitedEvent,
    PlayerGameJoinedEvent,
    PlayerMoveAfterEvent,
    PlayerMoveBeforeEvent,
    PluginDisabledEvent,
    PluginEnabledEvent,
    PluginErrorEvent,
    # Plugin Events
    PluginLoadedEvent,
    RoundCompletedEvent,
    RoundStartedEvent,
    StandingsUpdatedEvent,
    StrategyErrorEvent,
    StrategyPerformanceEvent,
    # Strategy Events
    StrategySelectedEvent,
    SystemErrorEvent,
    SystemShutdownEvent,
    # System Events
    SystemStartupEvent,
    TournamentCompletedEvent,
    # Tournament Events
    TournamentRoundStartedEvent,
)

__all__ = [
    # Event Bus
    "EventBus",
    "HandlerMetadata",
    "get_event_bus",
    # Base
    "BaseEvent",
    # Game Events
    "GameStartedEvent",
    "GameEndedEvent",
    "RoundStartedEvent",
    "RoundCompletedEvent",
    # Agent Events
    "AgentRegisteredEvent",
    "AgentConnectedEvent",
    "AgentDisconnectedEvent",
    "AgentErrorEvent",
    # Strategy Events
    "StrategySelectedEvent",
    "MoveDecidedEvent",
    "StrategyErrorEvent",
    # Player Events
    "PlayerGameInvitedEvent",
    "PlayerGameJoinedEvent",
    "PlayerMoveBeforeEvent",
    "PlayerMoveAfterEvent",
    # Plugin Events
    "PluginLoadedEvent",
    "PluginEnabledEvent",
    "PluginDisabledEvent",
    "PluginErrorEvent",
    # System Events
    "SystemStartupEvent",
    "SystemShutdownEvent",
    "SystemErrorEvent",
    # Match Events
    "MatchStartedEvent",
    "MatchCompletedEvent",
    # Tournament Events
    "TournamentRoundStartedEvent",
    "StandingsUpdatedEvent",
    "TournamentCompletedEvent",
    # Analytics Events
    "StrategyPerformanceEvent",
    "OpponentModelUpdateEvent",
    "CounterfactualAnalysisEvent",
    # Decorators
    "on_event",
    "before",
    "after",
    "on_error",
    "emit_on_exception",
]
