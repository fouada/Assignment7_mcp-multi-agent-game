# Plugin System and Extensibility Guide

The MCP Multi-Agent Game League features a production-grade plugin system and event bus that allows you to extend functionality without modifying the core codebase.

## Architecture

The system is built on two pillars:
1.  **Plugin Registry:** Manages the lifecycle of extensions (Load -> Enable -> Disable -> Unload).
2.  **Event Bus:** A decoupled communication channel for hooks and observability.

## Creating a Plugin

Plugins are Python classes that implement the `PluginInterface`.

### 1. Basic Plugin Structure

Create a file named `my_plugin.py` in the `plugins/` directory:

```python
from src.common.plugins import PluginInterface, PluginMetadata, PluginContext
from src.common.logger import get_logger

logger = get_logger(__name__)

class MyPlugin(PluginInterface):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my_plugin",
            version="1.0.0",
            author="Your Name",
            description="A sample plugin",
            dependencies=[]  # List other plugins you depend on
        )

    async def on_load(self, context: PluginContext) -> None:
        """Called when plugin is loaded (before enabling)."""
        logger.info("MyPlugin loaded")

    async def on_enable(self, context: PluginContext) -> None:
        """Called when plugin is enabled. Register hooks here."""
        logger.info("MyPlugin enabled")
        
        # Access system components
        registry = context.registry
        config = context.config
        
        # Register event listeners
        if context.event_bus:
            context.event_bus.on("game.started", self.on_game_start)

    async def on_disable(self, context: PluginContext) -> None:
        """Cleanup resources."""
        logger.info("MyPlugin disabled")

    async def on_unload(self, context: PluginContext) -> None:
        """Final cleanup."""
        logger.info("MyPlugin unloaded")
        
    async def on_game_start(self, event):
        logger.info(f"Game started! ID: {event.game_id}")
```

### 2. Custom Strategies

You can add new player strategies using the `@strategy_plugin` decorator. These are automatically registered with the `StrategyFactory`.

```python
from src.agents.strategies import Strategy, strategy_plugin, GameRole

@strategy_plugin(
    name="aggressive_random",
    version="1.0.0",
    description="Random strategy that prefers higher numbers"
)
class AggressiveRandomStrategy(Strategy):
    async def decide_move(self, game_id, round_number, my_role, **kwargs):
        # Implementation here
        return 5
```

## Event Hooks

The system emits rich events that you can subscribe to.

### Key Events

| Event Type | Description | Data |
|------------|-------------|------|
| `agent.registered` | New player/referee registered | `agent_id`, `agent_type` |
| `match.started` | A match has begun | `match_id`, `players` |
| `round.completed` | Round finished | `game_id`, `round_number`, `moves`, `scores` |
| `match.completed` | Match finished | `match_id`, `winner`, `final_scores` |
| `standings.updated` | League standings changed | `round_number`, `standings` |

### Using the Event Bus

```python
from src.common.events import get_event_bus, on_event

# 1. Using decorator
@on_event("match.completed", priority=10)
async def log_match_result(event):
    print(f"Winner: {event.winner}")

# 2. Using bus directly
bus = get_event_bus()
bus.on("player.*.move", track_moves)
```

## Directory Structure

```
project/
  ├── plugins/           # Place your *_plugin.py files here
  ├── src/
  │   ├── common/
  │   │   ├── plugins/   # Core plugin logic
  │   │   └── events/    # Core event logic
```

## Running with Plugins

Just run the league as normal. The system automatically discovers plugins in the `plugins/` directory and any installed packages exposing the `mcp_game.plugins` entry point.

```bash
python -m src.main --run
```

