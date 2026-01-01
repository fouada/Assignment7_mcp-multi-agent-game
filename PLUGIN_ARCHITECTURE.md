# Plugin Architecture - MCP Multi-Agent Game System

## Overview

This document describes the comprehensive, production-level plugin architecture for the MCP Multi-Agent Game System. The architecture is inspired by industry-leading plugin systems like WordPress, VS Code, and pytest, providing a flexible and powerful extensibility framework.

## Architecture Components

### 1. Core Plugin System (`src/common/plugins/`)

#### Enhanced Plugin Base (`base.py`)

**New Features:**
- **Lifecycle States**: UNLOADED → LOADED → ENABLED → DISABLED → ERROR → RELOADING
- **Version Compatibility**: Semver-based version checking with `min_system_version` and `max_system_version`
- **Plugin Capabilities**: Feature flags (HOT_RELOAD, SANDBOXED, ASYNC_ONLY, etc.)
- **Security Validation**: Checksum and signature support for plugin validation
- **Performance Metrics**: Load time, enable time, uptime tracking
- **Error Handling**: Last error tracking and error state management

**New Lifecycle Hooks:**
```python
async def on_validate(context) -> bool      # Validate before loading
async def on_configure(context, config)     # Configure after loading
async def on_load(context)                  # Load plugin resources
async def on_enable(context)                # Enable plugin operations
async def on_disable(context)               # Disable plugin operations
async def on_reload(context)                # Hot-reload plugin (if supported)
async def on_unload(context)                # Cleanup plugin resources
async def on_error(context, error)          # Handle errors
```

**Enhanced Metadata:**
```python
@dataclass
class PluginMetadata:
    # Basic info
    name: str
    version: str
    author: str
    description: str

    # Dependencies and compatibility
    dependencies: list[str]
    min_system_version: str
    max_system_version: str | None

    # Capabilities and features
    capabilities: list[PluginCapability]
    tags: list[str]

    # Marketplace metadata
    homepage: str
    repository: str
    license: str

    # Platform requirements
    platform: str
    python_requires: str
    api_version: str

    # Security
    checksum: str
    signature: str

    # Timestamps
    created_at: datetime | None
    updated_at: datetime | None
```

**New Exceptions:**
- `PluginValidationError` - Validation failed
- `PluginSecurityError` - Security check failed
- `PluginCompatibilityError` - Incompatible with system
- `PluginConfigurationError` - Invalid configuration

#### Plugin Discovery (`discovery.py`)

**Features:**
- Entry point discovery from `pyproject.toml`
- Directory scanning with pattern matching
- Plugin validation before loading
- Auto-discovery and registration

**Usage:**
```python
# Discover from entry points
plugins = await PluginDiscovery.discover_from_entry_points("mcp_game.plugins")

# Discover from directory
plugins = await PluginDiscovery.discover_from_directory(
    Path("plugins"),
    pattern="*_plugin.py"
)

# Auto-discover and register
count = await PluginDiscovery.load_and_register_plugins(config)
```

#### Plugin Registry (`registry.py`)

**Features:**
- Singleton pattern for centralized management
- Dependency validation
- Lifecycle management
- Enable/disable control
- Query and introspection

**Usage:**
```python
registry = get_plugin_registry()

# Register plugin
await registry.register_plugin(my_plugin, auto_enable=True)

# Enable/disable
await registry.enable_plugin("my_plugin")
await registry.disable_plugin("my_plugin")

# Query
plugins = registry.list_plugins(filter_enabled=True)
metadata = registry.get_metadata("my_plugin")
```

### 2. Comprehensive Hooks System (`src/common/hooks/`)

#### Hook Types (`types.py`)

**Hook Types:**
- `BEFORE` - Execute before main action
- `AFTER` - Execute after main action
- `AROUND` - Wrap main action (modify input/output)
- `FILTER` - Modify data in pipeline
- `ACTION` - Side effects only

**Priority Levels:**
- `HIGHEST` (100) - Critical hooks
- `HIGH` (75) - High priority
- `NORMAL` (50) - Default
- `LOW` (25) - Low priority
- `LOWEST` (10) - Last to execute

**Execution Modes:**
- `SEQUENTIAL` - One by one (default)
- `PARALLEL` - All at once (async only)
- `FIRST_SUCCESS` - Stop after first success
- `FIRST_FAILURE` - Stop after first failure

**Hook Context:**
```python
@dataclass
class HookContext:
    event_name: str
    data: dict[str, Any]
    original_data: dict[str, Any]
    metadata: dict[str, Any]
    cancelled: bool
    error: Optional[Exception]

    def get(key, default=None) -> Any
    def set(key, value) -> None
    def cancel(reason="") -> None
    def set_error(error) -> None
```

#### Hook Manager (`hook_manager.py`)

**Features:**
- Singleton pattern
- Priority-based execution
- Wildcard pattern matching
- Timeout support
- Error isolation
- Performance profiling
- Execution statistics

**Usage:**
```python
manager = get_hook_manager()

# Register hook
hook_id = manager.register(
    hook_name="match.started",
    handler=my_handler,
    priority=HookPriority.HIGH.value,
    plugin_name="my_plugin"
)

# Execute hooks
result = await manager.execute(
    "match.started",
    context_data={"match_id": "M001", "players": ["P1", "P2"]}
)

# Unregister
manager.unregister(hook_id)
```

**Configuration:**
```python
manager.configure(
    enabled=True,
    default_execution_mode=HookExecutionMode.SEQUENTIAL,
    error_handling="isolate",  # "isolate", "propagate", "stop"
    max_execution_time=30.0,
    profiling_enabled=True
)
```

#### Hook Decorators (`decorators.py`)

**Decorators:**

```python
# Before hook
@before_hook("match.started", priority=100)
async def validate_match(context):
    if len(context.data['players']) != 2:
        context.cancel("Invalid players")

# After hook
@after_hook("match.completed", priority=50)
async def save_result(context):
    await save_to_database(context.data)

# Around hook
@around_hook("strategy.decide", priority=100)
async def profile_decision(context, next_hook):
    start = time.time()
    result = await next_hook(context) if next_hook else None
    context.set("decision_time", time.time() - start)
    return result

# Filter hook
@filter_hook("player.move.validate")
async def normalize_move(context):
    move = max(1, min(10, context.data['move']))
    context.set('move', move)
    return context
```

### 3. Extensibility Framework (`src/common/extensibility/`)

**Planned Components:**

#### Extension Points (`extension_points.py`)
Define system extension points:
- Strategy providers
- Validator providers
- Logger providers
- Metrics collectors
- Event handlers

#### Extension Registry (`registry.py`)
Manage extension registrations:
- Register providers
- Query extensions
- Resolve dependencies
- Validate implementations

#### Providers (`providers.py`)
Base provider classes:
- `StrategyProvider`
- `ValidatorProvider`
- `MetricsProvider`
- `LoggerProvider`

### 4. Agent-Level Hooks

**Hook Points by Agent:**

#### League Manager Hooks
```python
# Registration
"league.player.register.before"
"league.player.register.after"
"league.referee.register.before"
"league.referee.register.after"

# Match scheduling
"league.schedule.create.before"
"league.schedule.create.after"
"league.round.start.before"
"league.round.start.after"

# Results
"league.match.result.before"
"league.match.result.after"
"league.standings.update.before"
"league.standings.update.after"
"league.tournament.complete.before"
"league.tournament.complete.after"
```

#### Referee Hooks
```python
# Match lifecycle
"referee.match.create.before"
"referee.match.create.after"
"referee.match.start.before"
"referee.match.start.after"

# Round management
"referee.round.start.before"
"referee.round.start.after"
"referee.round.complete.before"
"referee.round.complete.after"

# Move validation
"referee.move.receive.before"
"referee.move.receive.after"
"referee.move.validate.before"
"referee.move.validate.after"

# Results
"referee.match.complete.before"
"referee.match.complete.after"
"referee.result.report.before"
"referee.result.report.after"
```

#### Player Hooks
```python
# Registration
"player.register.before"
"player.register.after"

# Game lifecycle
"player.game.invite.before"
"player.game.invite.after"
"player.game.join.before"
"player.game.join.after"

# Decision making
"player.decision.before"
"player.decision.after"
"player.move.submit.before"
"player.move.submit.after"

# Results
"player.result.receive.before"
"player.result.receive.after"
"player.game.end.before"
"player.game.end.after"
```

### 5. Example Plugins

#### Logging Plugin (`plugins/logging_plugin/`)
```python
class LoggingPlugin(PluginInterface):
    """Advanced logging plugin with multiple outputs."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="logging_plugin",
            version="1.0.0",
            author="MCP Team",
            description="Advanced logging with file, console, and remote outputs",
            capabilities=[PluginCapability.HOT_RELOAD],
            tags=["logging", "monitoring"]
        )

    async def on_enable(self, context: PluginContext):
        # Register hooks for all important events
        hook_manager = context.hook_manager

        hook_manager.register(
            "match.started",
            self.log_match_start,
            priority=HookPriority.HIGH.value
        )
```

#### Metrics Plugin (`plugins/metrics_plugin/`)
```python
class MetricsPlugin(PluginInterface):
    """Collect and export metrics to Prometheus/Grafana."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="metrics_plugin",
            version="1.0.0",
            description="Metrics collection and export",
            capabilities=[PluginCapability.TELEMETRY],
            tags=["metrics", "monitoring", "prometheus"]
        )
```

#### Replay Plugin (`plugins/replay_plugin/`)
```python
class ReplayPlugin(PluginInterface):
    """Record and replay game matches."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="replay_plugin",
            version="1.0.0",
            description="Game replay recording and playback",
            capabilities=[PluginCapability.MODIFIES_GAME_STATE],
            tags=["replay", "recording"]
        )
```

#### Custom Strategy Plugin (`plugins/custom_strategy_plugin/`)
```python
class CustomStrategyPlugin(PluginInterface):
    """Add custom player strategies via plugin."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="custom_strategy_plugin",
            version="1.0.0",
            description="Custom strategy implementations",
            capabilities=[PluginCapability.PROVIDES_EXTENSIONS],
            tags=["strategy", "ai"]
        )

    def get_extensions(self) -> dict[str, Any]:
        return {
            "strategy": MyCustomStrategy,
        }
```

#### Notification Plugin (`plugins/notification_plugin/`)
```python
class NotificationPlugin(PluginInterface):
    """Send real-time notifications via Slack, Discord, Email."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="notification_plugin",
            version="1.0.0",
            description="Real-time notifications",
            capabilities=[PluginCapability.REQUIRES_NETWORK],
            tags=["notifications", "alerts"]
        )
```

### 6. Plugin Configuration

#### Global Config (`config/plugins/plugins.yaml`)
```yaml
# Plugin system configuration
system:
  enabled: true
  auto_discover: true
  environment: production
  system_version: "0.1.0"

# Discovery configuration
discovery:
  entry_point_group: "mcp_game.plugins"
  directory_scan:
    enabled: true
    paths:
      - "plugins"
      - "~/.mcp_game/plugins"
    pattern: "*_plugin.py"

# Plugin-specific configs
plugins:
  logging_plugin:
    enabled: true
    priority: 100
    settings:
      log_level: "INFO"
      output_dir: "./logs"
      console: true
      file: true
      remote: false

  metrics_plugin:
    enabled: true
    priority: 90
    settings:
      port: 9090
      export_interval: 60
      prometheus_enabled: true

  replay_plugin:
    enabled: false
    settings:
      output_dir: "./replays"
      compression: true
      max_replays: 1000
```

#### Schema (`config/plugins/plugin-schema.json`)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "system": {
      "type": "object",
      "properties": {
        "enabled": {"type": "boolean"},
        "auto_discover": {"type": "boolean"},
        "environment": {"enum": ["dev", "test", "production"]},
        "system_version": {"type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$"}
      }
    },
    "plugins": {
      "type": "object",
      "patternProperties": {
        ".*": {
          "type": "object",
          "properties": {
            "enabled": {"type": "boolean"},
            "priority": {"type": "integer", "minimum": 0, "maximum": 100"},
            "settings": {"type": "object"}
          }
        }
      }
    }
  }
}
```

## Usage Examples

### Creating a Simple Plugin

```python
from src.common.plugins import PluginInterface, PluginMetadata, PluginCapability
from src.common.hooks import before_hook, after_hook

class MyPlugin(PluginInterface):
    """My custom plugin."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my_plugin",
            version="1.0.0",
            author="Me",
            description="My awesome plugin",
            capabilities=[PluginCapability.HOT_RELOAD],
            tags=["custom"]
        )

    async def on_validate(self, context: PluginContext) -> bool:
        # Custom validation
        return context.system_version >= "0.1.0"

    async def on_enable(self, context: PluginContext):
        # Register hooks
        @before_hook("match.started", priority=100, plugin_name="my_plugin")
        async def before_match(hook_context):
            context.logger.info(f"Match starting: {hook_context.data['match_id']}")

        @after_hook("match.completed", priority=50, plugin_name="my_plugin")
        async def after_match(hook_context):
            context.logger.info(f"Match completed: {hook_context.data['winner']}")

    async def on_disable(self, context: PluginContext):
        # Cleanup
        context.logger.info("Plugin disabled")
```

### Registering a Plugin

```python
# Method 1: Auto-discovery
from src.common.plugins import auto_discover_and_register

config = {
    "entry_point_group": "mcp_game.plugins",
    "directory_scan": {
        "enabled": True,
        "paths": ["plugins"],
        "pattern": "*_plugin.py"
    }
}

count = await auto_discover_and_register(config)
print(f"Registered {count} plugins")

# Method 2: Manual registration
from src.common.plugins import get_plugin_registry

registry = get_plugin_registry()
plugin = MyPlugin()

await registry.register_plugin(plugin, auto_enable=True)
```

### Using Hooks in Agents

```python
from src.common.hooks import get_hook_manager

class LeagueManager:
    async def start_match(self, match_id: str, players: list[str]):
        hook_manager = get_hook_manager()

        # Execute before hooks
        context_data = {"match_id": match_id, "players": players}
        result = await hook_manager.execute(
            "match.started",
            context_data=context_data
        )

        if result.cancelled:
            logger.warning(f"Match start cancelled: {result.context.metadata}")
            return False

        # Start match...

        # Execute after hooks
        await hook_manager.execute(
            "match.completed",
            context_data={"match_id": match_id, "winner": winner}
        )

        return True
```

## MIT-Level Features

### 1. Plugin Sandboxing
- Isolate plugins in separate processes or containers
- Restrict file system and network access
- Resource limits (CPU, memory, time)

### 2. Hot-Reloading
- Reload plugins without restarting system
- State preservation across reloads
- Graceful degradation on reload failure

### 3. Security Validation
- Checksum verification
- Digital signature validation
- Permission system
- Security audit logs

### 4. Performance Profiling
- Hook execution time tracking
- Resource usage monitoring
- Performance regression detection
- Optimization recommendations

### 5. Plugin Marketplace
- Plugin discovery and installation
- Version management
- Dependency resolution
- Rating and reviews
- Security audits

### 6. Telemetry and Monitoring
- Prometheus metrics export
- Grafana dashboards
- Alert configuration
- Performance analytics

## Testing Strategy

### Unit Tests (`tests/test_plugins/`)

```python
# test_plugin_base.py
def test_plugin_metadata_creation()
def test_plugin_lifecycle()
def test_plugin_validation()
def test_version_compatibility()

# test_hook_manager.py
def test_hook_registration()
def test_hook_execution()
def test_hook_priorities()
def test_hook_error_handling()

# test_decorators.py
def test_before_hook_decorator()
def test_after_hook_decorator()
def test_around_hook_decorator()
```

### Integration Tests
```python
# test_plugin_integration.py
def test_plugin_discovery_and_registration()
def test_plugin_with_hooks()
def test_multiple_plugins_interaction()
```

## Performance Considerations

1. **Hook Execution Overhead**: ~0.1-1ms per hook
2. **Plugin Loading**: ~10-50ms per plugin
3. **Memory Overhead**: ~1-5MB per plugin
4. **Recommended Limits**:
   - Max 50 plugins
   - Max 500 hooks
   - Max 30s hook execution time

## Security Considerations

1. **Plugin Validation**: Always validate before loading
2. **Signature Verification**: Required for production
3. **Sandboxing**: Isolate untrusted plugins
4. **Permission System**: Restrict plugin capabilities
5. **Audit Logging**: Log all plugin operations

## Future Enhancements

1. **Plugin Dependencies**: NPM-style dependency resolution
2. **Plugin Versioning**: Semantic versioning support
3. **Plugin Marketplace**: Web-based marketplace
4. **Plugin CLI**: `mcp plugin install/uninstall/list`
5. **Plugin IDE**: VS Code extension for plugin development
6. **Plugin Testing Framework**: Automated plugin testing
7. **Plugin Documentation Generator**: Auto-generate docs
8. **Plugin Performance Analyzer**: Profiling and optimization

## References

- [WordPress Plugin API](https://codex.wordpress.org/Plugin_API)
- [VS Code Extension API](https://code.visualstudio.com/api)
- [Pytest Plugin System](https://docs.pytest.org/en/latest/how-to/plugins.html)
- [FastAPI Middleware](https://fastapi.tiangolo.com/tutorial/middleware/)
- [Django Signals](https://docs.djangoproject.com/en/stable/topics/signals/)

## Conclusion

This plugin architecture provides a production-ready, extensible foundation for the MCP Multi-Agent Game System. It enables developers to extend and customize the system without modifying core code, following industry best practices and patterns.

The system is designed to scale from simple logging plugins to complex AI strategy implementations, while maintaining performance, security, and reliability standards expected in production environments.
