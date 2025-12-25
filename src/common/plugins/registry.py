"""
Plugin Registry
===============

Centralized registry for managing all plugins in the system.

The PluginRegistry is a singleton that manages the lifecycle of all plugins:
- Registration and unregistration
- Enable/disable control
- Dependency validation
- Plugin discovery and querying

Usage:
    # Get registry instance
    registry = get_plugin_registry()

    # Register a plugin
    await registry.register_plugin(my_plugin)

    # Enable a plugin
    await registry.enable_plugin("my_plugin")

    # List all plugins
    plugins = registry.list_plugins(filter_enabled=True)
"""

from typing import Any, Optional

from ..logger import get_logger
from .base import (
    PluginAlreadyRegisteredError,
    PluginContext,
    PluginDependencyError,
    PluginInterface,
    PluginMetadata,
    PluginNotFoundError,
)

logger = get_logger(__name__)


class PluginRegistry:
    """
    Singleton registry for managing all plugins.

    The registry maintains the state of all plugins and coordinates their
    lifecycle. It ensures that:
    - Plugins are registered only once
    - Dependencies are satisfied before enabling
    - Lifecycle methods are called in the correct order
    - Plugin state is tracked accurately

    Example:
        registry = get_plugin_registry()

        # Set plugin context
        context = PluginContext(
            registry=registry,
            config={},
            logger=logger,
        )
        registry.set_context(context)

        # Register and enable plugin
        await registry.register_plugin(my_plugin)
        await registry.enable_plugin("my_plugin")

        # Query plugins
        if registry.is_enabled("my_plugin"):
            plugin = registry.get_plugin("my_plugin")
    """

    _instance: Optional["PluginRegistry"] = None

    def __new__(cls) -> "PluginRegistry":
        """Ensure only one instance exists (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the registry."""
        if self._initialized:
            return

        self._plugins: dict[str, PluginInterface] = {}
        self._enabled: dict[str, bool] = {}
        self._metadata: dict[str, PluginMetadata] = {}
        self._context: PluginContext | None = None
        self._initialized = True

        logger.info("PluginRegistry initialized")

    def set_context(self, context: PluginContext) -> None:
        """
        Set the plugin context.

        The context provides plugins with access to system resources.
        This must be called before enabling plugins.

        Args:
            context: Plugin context with registry, config, logger, etc.
        """
        self._context = context
        logger.debug("Plugin context set")

    async def register_plugin(
        self,
        plugin: PluginInterface,
        auto_enable: bool = False,
    ) -> bool:
        """
        Register a plugin.

        Registers the plugin and calls its on_load() lifecycle method.
        Does not enable the plugin unless auto_enable is True.

        Args:
            plugin: Plugin instance to register
            auto_enable: Whether to automatically enable after registration

        Returns:
            True if registration successful

        Raises:
            PluginAlreadyRegisteredError: If plugin is already registered
            PluginDependencyError: If plugin dependencies are not met
        """
        metadata = plugin.get_metadata()
        name = metadata.name

        # Check if already registered
        if name in self._plugins:
            raise PluginAlreadyRegisteredError(name)

        # Validate dependencies
        is_valid, missing = self.validate_dependencies(metadata)
        if not is_valid:
            raise PluginDependencyError(name, missing)

        # Store plugin
        self._plugins[name] = plugin
        self._metadata[name] = metadata
        self._enabled[name] = False

        # Call on_load
        if self._context:
            try:
                await plugin.on_load(self._context)
            except Exception as e:
                # Rollback registration on error
                del self._plugins[name]
                del self._metadata[name]
                del self._enabled[name]
                logger.error(f"Failed to load plugin {name}: {e}")
                raise

        logger.info(f"Plugin registered: {name} v{metadata.version}")

        # Auto-enable if requested
        if auto_enable:
            await self.enable_plugin(name)

        return True

    async def unregister_plugin(self, name: str) -> bool:
        """
        Unregister a plugin.

        Disables the plugin if enabled, calls on_unload(), and removes
        it from the registry.

        Args:
            name: Name of plugin to unregister

        Returns:
            True if unregistration successful

        Raises:
            PluginNotFoundError: If plugin not found
        """
        if name not in self._plugins:
            raise PluginNotFoundError(name)

        plugin = self._plugins[name]

        # Disable if enabled
        if self._enabled.get(name):
            await self.disable_plugin(name)

        # Call on_unload
        if self._context:
            try:
                await plugin.on_unload(self._context)
            except Exception as e:
                logger.error(f"Error unloading plugin {name}: {e}")

        # Remove from registry
        del self._plugins[name]
        del self._metadata[name]
        del self._enabled[name]

        logger.info(f"Plugin unregistered: {name}")
        return True

    async def enable_plugin(self, name: str) -> bool:
        """
        Enable a plugin.

        Calls the plugin's on_enable() lifecycle method and marks
        it as enabled.

        Args:
            name: Name of plugin to enable

        Returns:
            True if enabling successful

        Raises:
            PluginNotFoundError: If plugin not found
        """
        if name not in self._plugins:
            raise PluginNotFoundError(name)

        if self._enabled.get(name):
            logger.warning(f"Plugin already enabled: {name}")
            return True

        plugin = self._plugins[name]

        if self._context:
            try:
                await plugin.on_enable(self._context)
            except Exception as e:
                logger.error(f"Failed to enable plugin {name}: {e}")
                raise

        self._enabled[name] = True
        logger.info(f"Plugin enabled: {name}")
        return True

    async def disable_plugin(self, name: str) -> bool:
        """
        Disable a plugin.

        Calls the plugin's on_disable() lifecycle method and marks
        it as disabled.

        Args:
            name: Name of plugin to disable

        Returns:
            True if disabling successful

        Raises:
            PluginNotFoundError: If plugin not found
        """
        if name not in self._plugins:
            raise PluginNotFoundError(name)

        if not self._enabled.get(name):
            logger.debug(f"Plugin already disabled: {name}")
            return True

        plugin = self._plugins[name]

        if self._context:
            try:
                await plugin.on_disable(self._context)
            except Exception as e:
                logger.error(f"Error disabling plugin {name}: {e}")

        self._enabled[name] = False
        logger.info(f"Plugin disabled: {name}")
        return True

    def get_plugin(self, name: str) -> PluginInterface | None:
        """
        Get a plugin by name.

        Args:
            name: Plugin name

        Returns:
            Plugin instance or None if not found
        """
        return self._plugins.get(name)

    def get_metadata(self, name: str) -> PluginMetadata | None:
        """
        Get plugin metadata by name.

        Args:
            name: Plugin name

        Returns:
            Plugin metadata or None if not found
        """
        return self._metadata.get(name)

    def list_plugins(self, filter_enabled: bool = False) -> list[PluginMetadata]:
        """
        List all plugins.

        Args:
            filter_enabled: If True, only return enabled plugins

        Returns:
            List of plugin metadata
        """
        if filter_enabled:
            return [
                self._metadata[name]
                for name in self._plugins
                if self._enabled.get(name, False)
            ]
        return list(self._metadata.values())

    def is_registered(self, name: str) -> bool:
        """
        Check if a plugin is registered.

        Args:
            name: Plugin name

        Returns:
            True if plugin is registered
        """
        return name in self._plugins

    def is_enabled(self, name: str) -> bool:
        """
        Check if a plugin is enabled.

        Args:
            name: Plugin name

        Returns:
            True if plugin is enabled
        """
        return self._enabled.get(name, False)

    def validate_dependencies(
        self, metadata: PluginMetadata
    ) -> tuple[bool, list[str]]:
        """
        Validate plugin dependencies.

        Checks that all dependencies listed in the plugin's metadata
        are registered in the registry.

        Args:
            metadata: Plugin metadata to validate

        Returns:
            Tuple of (is_valid, missing_dependencies)
        """
        missing = []
        for dep in metadata.dependencies:
            if dep not in self._plugins:
                missing.append(dep)

        return len(missing) == 0, missing

    def get_enabled_count(self) -> int:
        """Get count of enabled plugins."""
        return sum(1 for enabled in self._enabled.values() if enabled)

    def get_total_count(self) -> int:
        """Get total count of registered plugins."""
        return len(self._plugins)

    def get_summary(self) -> dict[str, Any]:
        """
        Get registry summary.

        Returns:
            Dictionary with registry statistics
        """
        return {
            "total_plugins": self.get_total_count(),
            "enabled_plugins": self.get_enabled_count(),
            "disabled_plugins": self.get_total_count() - self.get_enabled_count(),
            "plugins": [
                {
                    "name": metadata.name,
                    "version": metadata.version,
                    "enabled": self._enabled.get(metadata.name, False),
                }
                for metadata in self._metadata.values()
            ],
        }

    async def shutdown(self) -> None:
        """
        Shutdown all plugins.

        Disables and unregisters all plugins in reverse registration order.
        """
        logger.info("Shutting down plugin registry...")

        # Disable all plugins
        for name in list(self._plugins.keys()):
            if self._enabled.get(name):
                try:
                    await self.disable_plugin(name)
                except Exception as e:
                    logger.error(f"Error disabling plugin {name} during shutdown: {e}")

        # Unload all plugins
        for name in list(self._plugins.keys()):
            try:
                await self.unregister_plugin(name)
            except Exception as e:
                logger.error(f"Error unregistering plugin {name} during shutdown: {e}")

        logger.info("Plugin registry shutdown complete")

    def clear(self) -> None:
        """
        Clear all plugins (for testing).

        WARNING: This does not call lifecycle methods. Use shutdown() instead
        for proper cleanup.
        """
        self._plugins.clear()
        self._enabled.clear()
        self._metadata.clear()
        logger.warning("Plugin registry cleared (testing mode)")


# Global registry instance
_registry: PluginRegistry | None = None


def get_plugin_registry() -> PluginRegistry:
    """
    Get the global plugin registry instance.

    Returns:
        Singleton PluginRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry
