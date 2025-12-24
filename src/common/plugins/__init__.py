"""
Plugin System
=============

Extensible plugin architecture for the MCP Multi-Agent Game League.

Provides:
- PluginInterface: Base class for all plugins
- PluginRegistry: Central registry for managing plugins
- PluginDiscovery: Automatic plugin discovery from entry points and directories
- Plugin lifecycle management (load, enable, disable, unload)

Usage:
    # Define a plugin
    class MyPlugin(PluginInterface):
        def get_metadata(self) -> PluginMetadata:
            return PluginMetadata(name="my_plugin", version="1.0.0")

        async def on_enable(self, context: PluginContext):
            # Plugin initialization
            pass

    # Register and enable
    registry = get_plugin_registry()
    await registry.register_plugin(MyPlugin())
    await registry.enable_plugin("my_plugin")
"""

from .base import (
    PluginInterface,
    PluginMetadata,
    PluginContext,
    PluginConfig,
    PluginError,
    PluginLoadError,
    PluginDependencyError,
    PluginAlreadyRegisteredError,
    PluginNotFoundError,
)
from .registry import (
    PluginRegistry,
    get_plugin_registry,
)
from .discovery import (
    PluginDiscovery,
    discover_plugins,
    auto_discover_and_register,
)

__all__ = [
    # Base abstractions
    "PluginInterface",
    "PluginMetadata",
    "PluginContext",
    "PluginConfig",
    # Exceptions
    "PluginError",
    "PluginLoadError",
    "PluginDependencyError",
    "PluginAlreadyRegisteredError",
    "PluginNotFoundError",
    # Registry
    "PluginRegistry",
    "get_plugin_registry",
    # Discovery
    "PluginDiscovery",
    "discover_plugins",
    "auto_discover_and_register",
]
