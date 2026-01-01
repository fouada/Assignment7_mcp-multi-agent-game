"""
Plugin Base Abstractions
=========================

Core abstractions for the plugin system.

This module defines the foundational interfaces and data structures for plugins:
- PluginInterface: Abstract base class that all plugins must implement
- PluginMetadata: Information about a plugin (name, version, author, etc.)
- PluginContext: Runtime context provided to plugins (registry, config, logger)
- PluginConfig: Configuration for enabling/disabling and prioritizing plugins
- PluginCapability: Plugin capability flags for feature detection
- PluginState: Plugin lifecycle state tracking

MIT-Level Features:
- Version compatibility checking with semver
- Plugin sandboxing support
- Security validation hooks
- Performance profiling integration
- Hot-reload support
- Plugin marketplace metadata
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from ..logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# Enums and Constants
# ============================================================================


class PluginState(Enum):
    """Plugin lifecycle states."""

    UNLOADED = "unloaded"  # Plugin not loaded
    LOADED = "loaded"  # Plugin loaded but not enabled
    ENABLED = "enabled"  # Plugin enabled and active
    DISABLED = "disabled"  # Plugin disabled but still loaded
    ERROR = "error"  # Plugin in error state
    RELOADING = "reloading"  # Plugin being hot-reloaded


class PluginCapability(Enum):
    """Plugin capability flags."""

    HOT_RELOAD = "hot_reload"  # Supports hot reloading
    SANDBOXED = "sandboxed"  # Runs in sandbox
    ASYNC_ONLY = "async_only"  # Requires async environment
    REQUIRES_GPU = "requires_gpu"  # Needs GPU access
    REQUIRES_NETWORK = "requires_network"  # Needs network access
    TELEMETRY = "telemetry"  # Collects telemetry
    MODIFIES_GAME_STATE = "modifies_game_state"  # Can modify game state
    PROVIDES_HOOKS = "provides_hooks"  # Provides hook points
    PROVIDES_EXTENSIONS = "provides_extensions"  # Provides extension points


# ============================================================================
# Data Classes
# ============================================================================


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
        min_system_version: Minimum system version required
        max_system_version: Maximum system version supported
        capabilities: Plugin capabilities
        tags: Categorization tags
        homepage: Plugin homepage URL
        repository: Source code repository URL
        license: License identifier (e.g., "MIT", "Apache-2.0")
        platform: Target platform ("any", "linux", "darwin", "win32")
        python_requires: Python version requirement (e.g., ">=3.10")
        api_version: Plugin API version
        checksum: Plugin file checksum for security validation
        signature: Digital signature for marketplace
        created_at: Plugin creation timestamp
        updated_at: Plugin last update timestamp
    """

    name: str
    version: str
    author: str = ""
    description: str = ""
    dependencies: list[str] = field(default_factory=list)
    entry_point: str = ""

    # Version compatibility
    min_system_version: str = "0.1.0"
    max_system_version: str | None = None

    # Capabilities and features
    capabilities: list[PluginCapability] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    # Links and metadata
    homepage: str = ""
    repository: str = ""
    license: str = "MIT"

    # Platform and requirements
    platform: str = "any"
    python_requires: str = ">=3.10"
    api_version: str = "1.0.0"

    # Security and validation
    checksum: str = ""
    signature: str = ""

    # Timestamps
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary for serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "dependencies": self.dependencies,
            "entry_point": self.entry_point,
            "min_system_version": self.min_system_version,
            "max_system_version": self.max_system_version,
            "capabilities": [c.value for c in self.capabilities],
            "tags": self.tags,
            "homepage": self.homepage,
            "repository": self.repository,
            "license": self.license,
            "platform": self.platform,
            "python_requires": self.python_requires,
            "api_version": self.api_version,
            "checksum": self.checksum,
            "signature": self.signature,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PluginMetadata":
        """Create metadata from dictionary."""
        # Parse capabilities
        capabilities = []
        for cap_str in data.get("capabilities", []):
            try:
                capabilities.append(PluginCapability(cap_str))
            except ValueError:
                logger.warning(f"Unknown capability: {cap_str}")

        # Parse timestamps
        created_at = None
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(str(data["created_at"]).replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        updated_at = None
        if data.get("updated_at"):
            try:
                updated_at = datetime.fromisoformat(str(data["updated_at"]).replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        return cls(
            name=data["name"],
            version=data["version"],
            author=data.get("author", ""),
            description=data.get("description", ""),
            dependencies=data.get("dependencies", []),
            entry_point=data.get("entry_point", ""),
            min_system_version=data.get("min_system_version", "0.1.0"),
            max_system_version=data.get("max_system_version"),
            capabilities=capabilities,
            tags=data.get("tags", []),
            homepage=data.get("homepage", ""),
            repository=data.get("repository", ""),
            license=data.get("license", "MIT"),
            platform=data.get("platform", "any"),
            python_requires=data.get("python_requires", ">=3.10"),
            api_version=data.get("api_version", "1.0.0"),
            checksum=data.get("checksum", ""),
            signature=data.get("signature", ""),
            created_at=created_at,
            updated_at=updated_at,
        )

    def is_compatible(self, system_version: str) -> bool:
        """
        Check if plugin is compatible with system version.

        Args:
            system_version: System version string (semver)

        Returns:
            True if compatible, False otherwise
        """
        try:
            from packaging import version

            sys_ver = version.parse(system_version)
            min_ver = version.parse(self.min_system_version)

            if sys_ver < min_ver:
                return False

            if self.max_system_version:
                max_ver = version.parse(self.max_system_version)
                if sys_ver > max_ver:
                    return False

            return True
        except Exception as e:
            logger.error(f"Version compatibility check failed: {e}")
            return False

    def has_capability(self, capability: PluginCapability) -> bool:
        """Check if plugin has specific capability."""
        return capability in self.capabilities


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
    settings: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
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
    - hook_manager: Hook manager for registering hooks
    - extension_registry: Extension point registry
    - system_version: System version string
    - environment: Runtime environment info (dev, test, prod)
    """

    registry: Any  # PluginRegistry
    config: dict[str, Any]
    logger: Any
    event_bus: Any | None = None
    strategy_registry: Any | None = None
    hook_manager: Any | None = None  # HookManager
    extension_registry: Any | None = None  # ExtensionRegistry
    system_version: str = "0.1.0"
    environment: str = "production"

    # Additional context for advanced plugins
    _data: dict[str, Any] = field(default_factory=dict)
    _performance_metrics: dict[str, float] = field(default_factory=dict)

    def get_config(self, key: str, default: Any | None = None) -> Any:
        """Get configuration value by key."""
        return self.config.get(key, default)

    def has_config(self, key: str) -> bool:
        """Check if configuration key exists."""
        return key in self.config

    def set_data(self, key: str, value: Any) -> None:
        """Store plugin-specific data in context."""
        self._data[key] = value

    def get_data(self, key: str, default: Any | None = None) -> Any:
        """Retrieve plugin-specific data from context."""
        return self._data.get(key, default)

    def record_metric(self, name: str, value: float) -> None:
        """Record a performance metric."""
        self._performance_metrics[name] = value

    def get_metrics(self) -> dict[str, float]:
        """Get all performance metrics."""
        return self._performance_metrics.copy()

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment in ("dev", "development", "test")

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment in ("prod", "production")


class PluginInterface(ABC):
    """
    Abstract base interface for all plugins.

    Plugins must implement this interface to be loaded by the plugin system.
    The lifecycle methods are called in this order:
    1. on_validate() - Validate plugin before loading (security, compatibility)
    2. on_load() - Plugin is loaded and validated
    3. on_configure() - Plugin receives configuration
    4. on_enable() - Plugin is enabled and can start operations
    5. on_disable() - Plugin is disabled and should stop operations
    6. on_reload() - Plugin is hot-reloaded (if supported)
    7. on_unload() - Plugin is unloaded and should clean up resources

    Example:
        class MyPlugin(PluginInterface):
            def get_metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="my_plugin",
                    version="1.0.0",
                    author="Me",
                    description="My awesome plugin",
                    capabilities=[PluginCapability.HOT_RELOAD]
                )

            async def on_enable(self, context: PluginContext):
                context.logger.info("My plugin enabled!")

            async def on_validate(self, context: PluginContext) -> bool:
                # Custom validation logic
                return True
    """

    def __init__(self):
        """Initialize plugin."""
        self._enabled: bool = False
        self._loaded: bool = False
        self._state: PluginState = PluginState.UNLOADED
        self._context: PluginContext | None = None
        self._error: Optional[Exception] = None
        self._load_time: Optional[datetime] = None
        self._enable_time: Optional[datetime] = None

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

    async def on_validate(self, context: PluginContext) -> bool:
        """
        Validate plugin before loading (security, compatibility checks).

        Override this method to implement custom validation logic.
        This is called before on_load() and can prevent loading if validation fails.

        Args:
            context: Plugin context with access to system resources

        Returns:
            True if validation passed, False otherwise

        Example:
            async def on_validate(self, context: PluginContext) -> bool:
                # Check system compatibility
                metadata = self.get_metadata()
                if not metadata.is_compatible(context.system_version):
                    return False
                # Check required capabilities
                if context.is_production() and not self.is_production_ready():
                    return False
                return True
        """
        # Default: validate version compatibility
        metadata = self.get_metadata()
        return metadata.is_compatible(context.system_version)

    async def on_configure(self, context: PluginContext, config: dict[str, Any]) -> None:
        """
        Configure plugin after loading.

        Override this method to handle plugin-specific configuration.
        Called after on_load() but before on_enable().

        Args:
            context: Plugin context with access to system resources
            config: Plugin-specific configuration dictionary

        Example:
            async def on_configure(self, context: PluginContext, config: dict[str, Any]) -> None:
                self.log_level = config.get("log_level", "INFO")
                self.output_dir = config.get("output_dir", "./logs")
        """
        logger.debug(f"Plugin configured: {self.get_metadata().name}")

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
        self._state = PluginState.LOADED
        self._load_time = datetime.utcnow()
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
        self._state = PluginState.ENABLED
        self._enable_time = datetime.utcnow()
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
        self._state = PluginState.DISABLED
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
        self._state = PluginState.UNLOADED
        self._context = None
        logger.debug(f"Plugin unloaded: {self.get_metadata().name}")

    async def on_reload(self, context: PluginContext) -> None:
        """
        Called when plugin is hot-reloaded.

        Override this method to handle hot-reloading. Only called if plugin
        has HOT_RELOAD capability.

        Args:
            context: Plugin context with access to system resources

        Example:
            async def on_reload(self, context: PluginContext) -> None:
                # Save current state
                state = self.get_state()
                # Reload resources
                await self.reload_resources()
                # Restore state
                self.restore_state(state)
        """
        metadata = self.get_metadata()
        if PluginCapability.HOT_RELOAD in metadata.capabilities:
            self._state = PluginState.RELOADING
            logger.info(f"Plugin reloading: {metadata.name}")
        else:
            logger.warning(f"Plugin {metadata.name} does not support hot reload")

    async def on_error(self, context: PluginContext, error: Exception) -> None:
        """
        Called when plugin encounters an error.

        Override this method to handle errors gracefully.

        Args:
            context: Plugin context with access to system resources
            error: Exception that occurred
        """
        self._error = error
        self._state = PluginState.ERROR
        logger.error(f"Plugin error: {self.get_metadata().name}: {error}")

    def get_hooks(self) -> list[tuple[str, Callable]]:
        """
        Get list of hooks provided by this plugin.

        Override to provide custom hooks.

        Returns:
            List of (hook_name, hook_function) tuples

        Example:
            def get_hooks(self) -> list[tuple[str, Callable]]:
                return [
                    ("before_match", self.before_match_hook),
                    ("after_match", self.after_match_hook),
                ]
        """
        return []

    def get_extensions(self) -> dict[str, Any]:
        """
        Get extension points provided by this plugin.

        Override to provide custom extension points.

        Returns:
            Dictionary of extension_point_name -> provider

        Example:
            def get_extensions(self) -> dict[str, Any]:
                return {
                    "custom_strategy": MyStrategyProvider,
                    "custom_validator": MyValidator,
                }
        """
        return {}

    @property
    def is_enabled(self) -> bool:
        """Check if plugin is enabled."""
        return self._enabled

    @property
    def is_loaded(self) -> bool:
        """Check if plugin is loaded."""
        return self._loaded

    @property
    def context(self) -> PluginContext | None:
        """Get plugin context."""
        return self._context

    @property
    def state(self) -> PluginState:
        """Get current plugin state."""
        return self._state

    @property
    def error(self) -> Optional[Exception]:
        """Get last error if any."""
        return self._error

    @property
    def load_time(self) -> Optional[datetime]:
        """Get plugin load timestamp."""
        return self._load_time

    @property
    def enable_time(self) -> Optional[datetime]:
        """Get plugin enable timestamp."""
        return self._enable_time

    @property
    def uptime(self) -> float:
        """Get plugin uptime in seconds since enabled."""
        if self._enable_time and self._enabled:
            return (datetime.utcnow() - self._enable_time).total_seconds()
        return 0.0


# ============================================================================
# Exceptions
# ============================================================================


class PluginError(Exception):
    """Base exception for plugin errors."""

    pass


class PluginLoadError(PluginError):
    """Exception raised when plugin loading fails."""

    pass


class PluginDependencyError(PluginError):
    """Exception raised when plugin dependencies are not met."""

    def __init__(self, plugin_name: str, missing_dependencies: list[str]):
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


class PluginValidationError(PluginError):
    """Exception raised when plugin validation fails."""

    def __init__(self, plugin_name: str, reason: str):
        self.plugin_name = plugin_name
        self.reason = reason
        super().__init__(f"Plugin '{plugin_name}' validation failed: {reason}")


class PluginSecurityError(PluginError):
    """Exception raised when plugin security check fails."""

    def __init__(self, plugin_name: str, reason: str):
        self.plugin_name = plugin_name
        self.reason = reason
        super().__init__(f"Plugin '{plugin_name}' security check failed: {reason}")


class PluginCompatibilityError(PluginError):
    """Exception raised when plugin is incompatible with system."""

    def __init__(self, plugin_name: str, required_version: str, system_version: str):
        self.plugin_name = plugin_name
        self.required_version = required_version
        self.system_version = system_version
        super().__init__(
            f"Plugin '{plugin_name}' requires system version {required_version}, "
            f"but current version is {system_version}"
        )


class PluginConfigurationError(PluginError):
    """Exception raised when plugin configuration is invalid."""

    def __init__(self, plugin_name: str, reason: str):
        self.plugin_name = plugin_name
        self.reason = reason
        super().__init__(f"Plugin '{plugin_name}' configuration error: {reason}")
