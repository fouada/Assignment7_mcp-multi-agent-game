# Plugin System Quick Start Guide

## 5-Minute Quick Start

### 1. Create a Simple Plugin

```python
# my_plugin.py
from src.common.plugins import PluginInterface, PluginMetadata
from src.common.hooks import before_hook, after_hook

class MyPlugin(PluginInterface):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my_plugin",
            version="1.0.0",
            description="My first plugin"
        )

    async def on_enable(self, context):
        context.logger.info("Plugin enabled!")

    @before_hook("match.started")
    async def log_match_start(self, context):
        print(f"Match starting: {context.data['match_id']}")
```

### 2. Register and Use

```python
from src.common.plugins import get_plugin_registry
from my_plugin import MyPlugin

# Get registry
registry = get_plugin_registry()

# Register
plugin = MyPlugin()
await registry.register_plugin(plugin, auto_enable=True)
```

### 3. Execute Hooks

```python
from src.common.hooks import get_hook_manager

# Get manager
manager = get_hook_manager()

# Execute hooks
result = await manager.execute(
    "match.started",
    context_data={"match_id": "M001"}
)

if result.success:
    print(f"Executed {result.hooks_executed} hooks")
```

---

## Available Hook Points

### League Manager Hooks
```python
"league.player.register.before"
"league.player.register.after"
"league.match.result.before"
"league.match.result.after"
"league.standings.update.before"
"league.standings.update.after"
"league.tournament.complete.before"
"league.tournament.complete.after"
```

### Referee Hooks
```python
"referee.match.start.before"
"referee.match.start.after"
"referee.round.start.before"
"referee.round.start.after"
"referee.move.validate.before"
"referee.move.validate.after"
"referee.match.complete.before"
"referee.match.complete.after"
```

### Player Hooks
```python
"player.decision.before"
"player.decision.after"
"player.move.submit.before"
"player.move.submit.after"
"player.game.end.before"
"player.game.end.after"
```

---

## Hook Decorators

### Before Hook
```python
@before_hook("match.started", priority=100)
async def validate_match(context):
    if len(context.data['players']) != 2:
        context.cancel("Invalid players")
```

### After Hook
```python
@after_hook("match.completed")
async def save_result(context):
    await save_to_database(context.data)
```

### Around Hook
```python
@around_hook("strategy.decide")
async def profile_decision(context, next_hook):
    start = time.time()
    result = await next_hook(context) if next_hook else None
    context.set("time", time.time() - start)
    return result
```

---

## Plugin Capabilities

```python
from src.common.plugins import PluginCapability

# Declare capabilities
capabilities=[
    PluginCapability.HOT_RELOAD,      # Supports hot reload
    PluginCapability.TELEMETRY,       # Collects metrics
    PluginCapability.REQUIRES_NETWORK # Needs network
]
```

---

## Error Handling

```python
# In hook handler
async def my_hook(context):
    try:
        # Your logic
        pass
    except Exception as e:
        context.set_error(e)
        return None

# Check for errors
result = await manager.execute("my.hook")
if result.errors:
    print(f"Errors occurred: {result.errors}")
```

---

## Configuration

```yaml
# config/plugins/my_plugin.yaml
enabled: true
priority: 100
settings:
  log_level: INFO
  output_dir: ./logs
  feature_x: true
```

---

## Testing Your Plugin

```python
# tests/test_my_plugin.py
import pytest
from my_plugin import MyPlugin

@pytest.mark.asyncio
async def test_plugin_loads():
    plugin = MyPlugin()
    metadata = plugin.get_metadata()
    assert metadata.name == "my_plugin"

@pytest.mark.asyncio
async def test_plugin_hook():
    # Test hook execution
    pass
```

---

## Common Patterns

### Logging Plugin
```python
class LoggingPlugin(PluginInterface):
    async def on_enable(self, context):
        @after_hook("*")  # All events
        async def log_event(hook_context):
            context.logger.info(f"Event: {hook_context.event_name}")
```

### Metrics Plugin
```python
class MetricsPlugin(PluginInterface):
    async def on_enable(self, context):
        self.metrics = {}

        @after_hook("match.completed")
        async def record_match(hook_context):
            self.metrics["matches"] = self.metrics.get("matches", 0) + 1
```

### Validation Plugin
```python
class ValidationPlugin(PluginInterface):
    async def on_enable(self, context):
        @before_hook("player.move.validate")
        async def validate_move(hook_context):
            move = hook_context.data['move']
            if not (1 <= move <= 10):
                hook_context.cancel("Invalid move range")
```

---

## Debugging

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Get hook statistics
manager = get_hook_manager()
stats = manager.get_stats()
print(f"Total hooks: {stats['total_hooks']}")
print(f"Total executions: {stats['total_executions']}")

# List registered hooks
hooks = manager.get_hooks("match.*")
for hook in hooks:
    print(f"{hook.hook_name}: {hook.plugin_name} (priority={hook.priority})")
```

---

## Performance Tips

1. **Use async handlers**: ~10x faster than sync
2. **Set timeouts**: Prevent hanging hooks
3. **Use priorities wisely**: Critical hooks = HIGH priority
4. **Batch operations**: Don't make DB calls in every hook
5. **Cache results**: Use `context.set_data()` for caching

---

## Security Best Practices

1. **Validate inputs**: Always validate hook context data
2. **Check capabilities**: Don't assume capabilities exist
3. **Handle errors**: Never let exceptions crash the system
4. **Limit resource usage**: Set reasonable timeouts
5. **Verify checksums**: Validate plugin integrity

---

## Need Help?

- **Architecture Docs**: See `PLUGIN_ARCHITECTURE.md`
- **Full Implementation**: See `PLUGIN_SYSTEM_IMPLEMENTATION_SUMMARY.md`
- **Examples**: Check `plugins/` directory
- **Tests**: See `tests/test_plugins/`

---

## Advanced: Manual Hook Registration

```python
from src.common.hooks import get_hook_manager, HookType, HookPriority

manager = get_hook_manager()

# Register manually
async def my_handler(context):
    print(f"Event: {context.event_name}")

hook_id = manager.register(
    hook_name="my.event",
    handler=my_handler,
    hook_type=HookType.BEFORE,
    priority=HookPriority.HIGH.value,
    plugin_name="my_plugin"
)

# Unregister later
manager.unregister(hook_id)
```

---

## Advanced: Custom Execution Mode

```python
from src.common.hooks import HookExecutionMode

# Execute in parallel
result = await manager.execute(
    "my.event",
    context_data={"data": "value"},
    execution_mode=HookExecutionMode.PARALLEL,
    timeout=5.0
)
```

---

## That's It!

You now have everything you need to create powerful plugins for the MCP Multi-Agent Game System.

Start with simple logging, then progress to metrics, validation, and custom strategies.

Happy coding!
