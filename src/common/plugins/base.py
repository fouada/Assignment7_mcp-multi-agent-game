"""
Plugin Base Abstractions
=========================

Core abstractions for the plugin system.

This module defines the foundational interfaces and data structures for plugins:
- PluginInterface: Abstract base class that all plugins must implement
- PluginMetadata: Information about a plugin (name, version, author, etc.)
- PluginContext: Runtime context provided to plugins (registry, config, logger)
- PluginConfig: Configuration for enabling/disabling and prioritizing plugins
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..logger import get_logger

logger = get_logger(__name__)


@dataclass
class PluginMetadata:
    """
    Metadata describing a plugin.

    Attributes:
        name: Unique identifier for the plugin
        version: Semantic version (e.g., "1.0.0")
        author: Plugin author/maintainer
        description: Human-readable description
        dependencies: List of plugin names this plugin depends on
        entry_point: Entry point string for discovery
    """

    name: str
    version: str
    author: str = ""
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    entry_point: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "dependencies": self.dependencies,
            "entry_point": self.entry_point,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginMetadata":
        """Create metadata from dictionary."""
        return cls(
            name=data["name"],
            version=data["version"],
            author=data.get("author", ""),
            description=data.get("description", ""),
            dependencies=data.get("dependencies", []),
            entry_point=data.get("entry_point", ""),
        )


@dataclass
class PluginConfig:
    """
    Configuration for a plugin.

    Attributes:
        enabled: Whether the plugin is enabled
        priority: Priority for plugin execution (higher = earlier)
        settings: Plugin-specific configuration settings
    """

    enabled: bool = True
    priority: int = 0
    settings: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "enabled": self.enabled,
            "priority": self.priority,
            "settings": self.settings,
        }


@dataclass
class PluginContext:
    """
    Runtime context provided to plugins.

    Provides access to system resources:
    - registry: Plugin registry for plugin interaction
    - config: Configuration dictionary
    - logger: Logger instance
    - event_bus: Event bus (if available)
    - strategy_registry: Strategy registry (if available)
    """

    registry: Any  # PluginRegistry
    config: Dict[str, Any]
    logger: Any
    event_bus: Optional[Any] = None
    strategy_registry: Optional[Any] = None

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        return self.config.get(key, default)

    def has_config(self, key: str) -> bool:
        """Check if configuration key exists."""
        return key in self.config


class PluginInterface(ABC):
    """
    Abstract base interface for all plugins.

    Plugins must implement this interface to be loaded by the plugin system.
    The lifecycle methods are called in this order:
    1. on_load() - Plugin is loaded and validated
    2. on_enable() - Plugin is enabled and can start operations
    3. on_disable() - Plugin is disabled and should stop operations
    4. on_unload() - Plugin is unloaded and should clean up resources

    Example:
        class MyPlugin(PluginInterface):
            def get_metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="my_plugin",
                    version="1.0.0",
                    author="Me",
                    description="My awesome plugin"
                )

            async def on_enable(self, context: PluginContext):
                context.logger.info("My plugin enabled!")
    """

    def __init__(self):
        """Initialize plugin."""
        self._enabled = False
        self._loaded = False
        self._context: Optional[PluginContext] = None

    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """
        Return plugin metadata.

        This method must be implemented by all plugins to provide
        information about the plugin.

        Returns:
            PluginMetadata containing plugin information
        """
        pass

    async def on_load(self, context: PluginContext) -> None:
        """
        Called when the plugin is loaded.

        Override this method to perform initialization that doesn't
        require the plugin to be enabled (e.g., validation, setup).

        Args:
            context: Plugin context with access to system resources
        """
        self._context = context
        self._loaded = True
        logger.debug(f"Plugin loaded: {self.get_metadata().name}")

    async def on_enable(self, context: PluginContext) -> None:
        """
        Called when the plugin is enabled.

        Override this method to start plugin operations.
        This is where you should register event handlers, start
        background tasks, etc.

        Args:
            context: Plugin context with access to system resources
        """
        self._context = context
        self._enabled = True
        logger.debug(f"Plugin enabled: {self.get_metadata().name}")

    async def on_disable(self, context: PluginContext) -> None:
        """
        Called when the plugin is disabled.

        Override this method to stop plugin operations.
        This is where you should unregister event handlers, stop
        background tasks, etc.

        Args:
            context: Plugin context with access to system resources
        """
        self._enabled = False
        logger.debug(f"Plugin disabled: {self.get_metadata().name}")

    async def on_unload(self, context: PluginContext) -> None:
        """
        Called before the plugin is unloaded.

        Override this method to perform cleanup operations.
        After this method returns, the plugin should be ready for
        garbage collection.

        Args:
            context: Plugin context with access to system resources
        """
        self._loaded = False
        self._context = None
        logger.debug(f"Plugin unloaded: {self.get_metadata().name}")

    @property
    def is_enabled(self) -> bool:
        """Check if plugin is enabled."""
        return self._enabled

    @property
    def is_loaded(self) -> bool:
        """Check if plugin is loaded."""
        return self._loaded

    @property
    def context(self) -> Optional[PluginContext]:
        """Get plugin context."""
        return self._context


class PluginError(Exception):
    """Base exception for plugin errors."""

    pass


class PluginLoadError(PluginError):
    """Exception raised when plugin loading fails."""

    pass


class PluginDependencyError(PluginError):
    """Exception raised when plugin dependencies are not met."""

    def __init__(self, plugin_name: str, missing_dependencies: List[str]):
        self.plugin_name = plugin_name
        self.missing_dependencies = missing_dependencies
        super().__init__(
            f"Plugin '{plugin_name}' has missing dependencies: {', '.join(missing_dependencies)}"
        )


class PluginAlreadyRegisteredError(PluginError):
    """Exception raised when attempting to register an already registered plugin."""

    def __init__(self, plugin_name: str):
        self.plugin_name = plugin_name
        super().__init__(f"Plugin '{plugin_name}' is already registered")


class PluginNotFoundError(PluginError):
    """Exception raised when a plugin is not found."""

    def __init__(self, plugin_name: str):
        self.plugin_name = plugin_name
        super().__init__(f"Plugin '{plugin_name}' not found")
