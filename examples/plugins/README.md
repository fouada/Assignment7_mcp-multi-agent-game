# Plugin Examples

This directory contains example plugins demonstrating the MCP Game League plugin system.

## Available Examples

### 1. Quantum Strategy Plugin (`quantum_strategy_plugin.py`)

A quantum-inspired strategy that uses wave function collapse and interference patterns to make decisions.

**Features:**
- Wave function superposition of possible moves
- Interference patterns based on game history
- Quantum decoherence (noise) simulation
- Born rule for probability calculation

**Usage:**
```python
from src.agents.strategies import create_strategy

# Create quantum strategy
strategy = create_strategy("quantum")
```

## Creating Your Own Plugin

### Method 1: Using the `@strategy_plugin` Decorator (Recommended)

The simplest way to create a strategy plugin:

```python
from src.agents.strategies import Strategy, StrategyConfig, strategy_plugin
from src.agents.player import GameRole

@strategy_plugin(
    name="my_strategy",
    version="1.0.0",
    description="My custom strategy",
    category="experimental"
)
class MyStrategy(Strategy):
    async def decide_move(
        self,
        game_id: str,
        round_number: int,
        my_role: GameRole,
        my_score: int,
        opponent_score: int,
        history: list,
    ) -> int:
        # Your strategy logic here
        return 5  # Example: always return 5
```

### Method 2: Manual Registration

Register your strategy programmatically:

```python
from src.agents.strategies import register_strategy_plugin, Strategy

class MyStrategy(Strategy):
    async def decide_move(self, ...):
        pass

# Register manually
register_strategy_plugin(
    name="my_strategy",
    strategy_class=MyStrategy,
    version="1.0.0",
    description="My custom strategy"
)
```

### Method 3: Entry Points (Package Distribution)

For distributing your plugin as a package, use entry points in `pyproject.toml`:

```toml
[project.entry-points."mcp_game.plugins"]
my_strategy = "my_package.strategies:MyStrategyPlugin"
```

### Method 4: Directory Scanning

Place your plugin in the plugins directory (configured in `config/plugins/plugins_config.json`):

1. Create a file ending with `_plugin.py` (e.g., `my_strategy_plugin.py`)
2. Implement `PluginInterface` or use `@strategy_plugin`
3. The plugin will be auto-discovered on startup

## Plugin Interface

For full lifecycle control, implement `PluginInterface`:

```python
from src.common.plugins import PluginInterface, PluginMetadata, PluginContext

class MyPlugin(PluginInterface):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my-plugin",
            version="1.0.0",
            author="Your Name",
            description="My awesome plugin",
            dependencies=[],
        )

    async def on_load(self, context: PluginContext):
        # Called when plugin is loaded
        context.logger.info("Plugin loaded")

    async def on_enable(self, context: PluginContext):
        # Called when plugin is enabled
        context.logger.info("Plugin enabled")

    async def on_disable(self, context: PluginContext):
        # Called when plugin is disabled
        context.logger.info("Plugin disabled")

    async def on_unload(self, context: PluginContext):
        # Called before plugin is unloaded
        context.logger.info("Plugin unloaded")
```

## Testing Your Plugin

### Unit Testing

```python
import pytest
from src.agents.strategies import StrategyConfig
from src.agents.player import GameRole
from my_strategy_plugin import MyStrategy

@pytest.mark.asyncio
async def test_my_strategy():
    config = StrategyConfig(min_value=1, max_value=10)
    strategy = MyStrategy(config=config)

    move = await strategy.decide_move(
        game_id="test",
        round_number=1,
        my_role=GameRole.ODD,
        my_score=0,
        opponent_score=0,
        history=[],
    )

    assert 1 <= move <= 10
```

### Integration Testing

Test your strategy in a real game:

```python
from src.agents import create_player

# Create player with your strategy
player = create_player(
    name="TestPlayer",
    port=8101,
    strategy_type="my_strategy"
)
```

## Configuration

Plugin discovery is configured in `config/plugins/plugins_config.json`:

```json
{
  "plugin_discovery": {
    "enabled": true,
    "entry_point_group": "mcp_game.plugins",
    "directory_scan": {
      "enabled": true,
      "paths": ["plugins", "~/.mcp_game/plugins", "examples/plugins"],
      "pattern": "*_plugin.py"
    },
    "auto_enable": true
  }
}
```

## Best Practices

1. **Use Decorators**: The `@strategy_plugin` decorator is the simplest approach for most cases

2. **Validate Inputs**: Always validate move ranges and handle edge cases

3. **Handle History**: Check if history is empty before accessing it

4. **Log Appropriately**: Use the logger to help with debugging:
   ```python
   from src.common.logger import get_logger
   logger = get_logger(__name__)
   logger.info("My strategy made a decision", move=move)
   ```

5. **Document Your Strategy**: Add docstrings explaining your strategy's algorithm

6. **Test Thoroughly**: Write unit tests and integration tests

7. **Handle Errors Gracefully**: Catch exceptions and provide fallback behavior

## Common Pitfalls

1. **Not Handling Empty History**: Check `if history:` before accessing history[0]

2. **Move Out of Range**: Always respect `config.min_value` and `config.max_value`

3. **Blocking Operations**: Use `async`/`await` for I/O operations

4. **Import Errors**: Make sure your plugin can be imported before registration

5. **Missing Dependencies**: List all dependencies in plugin metadata

## Resources

- **Main Documentation**: `/docs/PLUGIN_DEVELOPMENT.md`
- **Strategy Base Class**: `/src/agents/strategies/base.py`
- **Plugin System**: `/src/common/plugins/`
- **Existing Strategies**: `/src/agents/strategies/game_theory.py`

## Getting Help

- Check the main documentation in `/docs/`
- Look at existing strategy implementations in `/src/agents/strategies/`
- Review the quantum strategy example in this directory
- Run the tests: `uv run pytest tests/test_plugin_*.py`
