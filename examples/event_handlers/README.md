# Event Handlers Examples

This directory contains examples demonstrating how to create custom event handlers for the MCP Multi-Agent Game League.

## Overview

The event system allows you to:
- **Listen** to game events (moves, rounds, matches, etc.)
- **React** with custom logic (logging, analytics, notifications)
- **Integrate** with external systems (databases, dashboards, alerts)

## Quick Start

```python
from src.common.events import get_event_bus, on_event, GameStartedEvent

# Create a simple handler
@on_event("game.started", priority=10)
async def on_game_start(event: GameStartedEvent):
    print(f"Game {event.game_id} started!")

# Or register programmatically
bus = get_event_bus()
bus.on("player.move.after", my_handler_function)
```

## Examples

### 1. Event Logger (`custom_logger.py`)

**What it does**: Logs all events to a file for debugging and audit purposes.

**Key features**:
- Wildcard pattern matching (`*` matches all events)
- Event metadata access
- JSON lines format output

**Usage**:
```python
logger = EventLogger(log_file="events.jsonl")
# Now all events will be logged automatically
```

### 2. Game Analytics

**What it does**: Collects statistics about games, players, and strategies.

**Tracks**:
- Total games/rounds/moves
- Player win rates
- Strategy usage frequency
- Average decision times

**Usage**:
```python
analytics = GameAnalytics()

# After some games...
report = analytics.get_report()
print(f"Total games: {report['total_games']}")
print(f"Top player: {report['player_wins']}")
```

### 3. Game Monitor

**What it does**: Real-time monitoring of active games with notifications.

**Features**:
- Priority-based handlers (high priority for critical updates)
- State tracking for active games
- Notifications on match completion
- Automatic cleanup

**Usage**:
```python
monitor = GameMonitor()
# Monitor will automatically track all games and send notifications
```

### 4. Audit Trail

**What it does**: Security and compliance audit logging.

**Tracks**:
- Agent registrations
- All error events
- Player actions
- Suspicious activity

**Usage**:
```python
audit = AuditTrail()

# Later...
log = audit.get_audit_log()
for entry in log:
    print(f"{entry['timestamp']}: {entry['event_type']}")
```

## Running the Examples

```bash
# Run the full example
python examples/event_handlers/custom_logger.py

# Output:
# ============================================================
# Custom Event Handlers Example
# ============================================================
#
# Registered 12 event handlers
#
# --- Emitting test events ---
# ✓ Emitted game.started
# ✓ Emitted round.completed
# ...
```

## Event Patterns

The event system supports powerful pattern matching:

| Pattern | Matches | Example Events |
|---------|---------|----------------|
| `*` | All events | Any event |
| `game.*` | All game events | `game.started`, `game.ended` |
| `player.*.move` | Player move events | `player.odd.move`, `player.even.move` |
| `*.error` | All error events | `player.error`, `strategy.error` |
| `match.completed` | Specific event | Only `match.completed` |

## Available Event Types

### Game Events
- `game.started` - Game begins
- `game.ended` - Game completes
- `round.started` - Round begins
- `round.completed` - Round finishes

### Player Events
- `player.game.invited` - Player receives invitation
- `player.game.joined` - Player accepts invitation
- `player.move.before` - Before player decides move
- `player.move.after` - After player decides move

### Match Events
- `match.started` - Match begins
- `match.completed` - Match ends

### Tournament Events
- `tournament.round.started` - Tournament round begins
- `standings.updated` - Standings change

### Agent Events
- `agent.registered` - Agent registers with league

### Strategy Events
- `strategy.selected` - Strategy chosen
- `strategy.move.decided` - Strategy makes decision

## Event Handler API

### Using Decorators

```python
from src.common.events import on_event

@on_event("game.started", priority=10, tags=["analytics"])
async def my_handler(event):
    # Handler code here
    pass
```

### Programmatic Registration

```python
from src.common.events import get_event_bus

bus = get_event_bus()

# Register handler
handler_id = bus.on(
    pattern="game.*",
    handler=my_handler_function,
    priority=10,
    description="Handle game events"
)

# Later, unregister
bus.off(handler_id)
```

### Handler Priorities

Handlers execute in priority order (higher = earlier):

- **10+**: Critical handlers (state updates, validation)
- **5-9**: Important handlers (analytics, monitoring)
- **0-4**: Normal handlers (logging, notifications)
- **Negative**: Cleanup handlers

## Creating Custom Handlers

### Basic Handler

```python
async def my_handler(event: BaseEvent):
    """Handle any event."""
    print(f"Event: {event.event_type}")
```

### Typed Handler

```python
from src.common.events import GameStartedEvent

async def on_game_start(event: GameStartedEvent):
    """Handle game started event with type checking."""
    print(f"Game {event.game_id} started!")
    print(f"Players: {event.players}")
```

### Stateful Handler Class

```python
class MyHandler:
    def __init__(self):
        self.event_count = 0
        bus = get_event_bus()
        bus.on("*", self.handle_event)

    async def handle_event(self, event: BaseEvent):
        self.event_count += 1
        print(f"Handled {self.event_count} events")
```

## Best Practices

### 1. Error Handling

Always wrap handlers in try-except to prevent failures:

```python
async def safe_handler(event: BaseEvent):
    try:
        # Your logic here
        process_event(event)
    except Exception as e:
        logger.error(f"Handler error: {e}")
```

### 2. Performance

- Keep handlers fast (avoid blocking operations)
- Use async/await properly
- Don't do heavy processing in high-priority handlers

### 3. Logging

- Log handler actions for debugging
- Include event context (game_id, player_id, etc.)
- Use appropriate log levels

### 4. Testing

- Test handlers independently
- Use event bus's `reset()` for test isolation
- Mock external dependencies

## Integration Examples

### Database Integration

```python
@on_event("match.completed")
async def save_to_database(event: MatchCompletedEvent):
    async with database.transaction():
        await database.matches.insert({
            "match_id": event.match_id,
            "winner": event.winner,
            "scores": event.final_scores,
            "timestamp": event.timestamp,
        })
```

### Webhook Integration

```python
@on_event("tournament.round.started")
async def notify_webhook(event: TournamentRoundStartedEvent):
    async with aiohttp.ClientSession() as session:
        await session.post(
            "https://api.example.com/webhook",
            json=event.model_dump()
        )
```

### Dashboard Updates

```python
@on_event("standings.updated")
async def update_dashboard(event: StandingsUpdatedEvent):
    # Publish to WebSocket clients
    await websocket_manager.broadcast({
        "type": "standings_update",
        "data": event.standings
    })
```

## Debugging

### View Registered Handlers

```python
bus = get_event_bus()

# All handlers
handlers = bus.get_handlers()
print(f"Total handlers: {len(handlers)}")

# Handlers for specific pattern
game_handlers = bus.get_handlers("game.*")
for handler in game_handlers:
    print(f"- {handler.pattern} (priority {handler.priority})")
```

### Event History

```python
# Get recent events
history = bus.get_event_history(limit=10)
for event in history:
    print(f"{event.timestamp}: {event.event_type}")
```

### Statistics

```python
stats = bus.get_stats()
print(f"Total events: {stats['total_events']}")
print(f"Total handlers: {stats['total_handlers']}")
print(f"Total errors: {stats['total_errors']}")
```

## Further Reading

- [Event System Documentation](../../docs/HOOKS_AND_EVENTS.md)
- [Event Types Reference](../../src/common/events/types.py)
- [Event Bus API](../../src/common/events/bus.py)

## Support

For questions or issues:
- File an issue on GitHub
- Check the documentation
- Review the example code
