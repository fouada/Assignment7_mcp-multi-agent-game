"""
Strategy Plugin Registry
=========================

Registry for strategy plugins with decorator-based registration.

Provides a strategy-specific plugin system that integrates with
the general plugin infrastructure while adding strategy-specific
functionality.

Usage:
    # Define a strategy plugin using decorator
    @strategy_plugin(
        name="my_strategy",
        version="1.0.0",
        description="My custom strategy"
    )
    class MyStrategy(Strategy):
        async def decide_move(self, ...):
            pass

    # Or register manually
    registry = get_strategy_plugin_registry()
    registry.register_strategy("my_strategy", MyStrategy)

    # Create strategy instance
    strategy = registry.create_strategy("my_strategy", config=...)
"""

from collections.abc import Callable
from typing import Any, Optional

from ...common.logger import get_logger
from .base import Strategy, StrategyConfig

logger = get_logger(__name__)


class StrategyPluginRegistry:
    """
    Registry for strategy plugins.

    Provides strategy-specific registration and creation functionality
    that integrates with the StrategyFactory.

    This registry is separate from the main PluginRegistry to allow
    strategy-specific operations like:
    - Strategy-specific metadata (difficulty, category, etc.)
    - Strategy creation with configuration
    - Strategy listing and discovery
    """

    _instance: Optional["StrategyPluginRegistry"] = None

    def __new__(cls) -> "StrategyPluginRegistry":
        """Ensure only one instance exists (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the strategy plugin registry."""
        if self._initialized:
            return

        self._strategies: dict[str, type[Strategy]] = {}
        self._metadata: dict[str, dict[str, Any]] = {}
        self._factories: dict[str, Callable] = {}
        self._initialized = True

        logger.info("StrategyPluginRegistry initialized")

    def register_strategy(
        self,
        name: str,
        strategy_class: type[Strategy],
        metadata: dict[str, Any] | None = None,
        factory: Callable | None = None,
    ) -> None:
        """
        Register a strategy plugin.

        Args:
            name: Unique name for the strategy
            strategy_class: Strategy class (must subclass Strategy)
            metadata: Optional metadata (version, description, etc.)
            factory: Optional factory function for custom instantiation

        Raises:
            ValueError: If name is already registered or strategy_class is invalid
        """
        # Validate
        if not issubclass(strategy_class, Strategy):
            raise ValueError(
                f"Strategy class {strategy_class.__name__} must subclass Strategy"
            )

        # Warn if overwriting
        if name in self._strategies:
            logger.warning(f"Overwriting existing strategy plugin: {name}")

        # Register
        self._strategies[name] = strategy_class
        self._metadata[name] = metadata or {}
        if factory:
            self._factories[name] = factory

        logger.info(f"Registered strategy plugin: {name}")

    def unregister_strategy(self, name: str) -> bool:
        """
        Unregister a strategy plugin.

        Args:
            name: Strategy name to unregister

        Returns:
            True if strategy was registered and removed
        """
        if name in self._strategies:
            del self._strategies[name]
            del self._metadata[name]
            if name in self._factories:
                del self._factories[name]
            logger.info(f"Unregistered strategy plugin: {name}")
            return True
        return False

    def get_strategy_class(self, name: str) -> type[Strategy] | None:
        """
        Get strategy class by name.

        Args:
            name: Strategy name

        Returns:
            Strategy class or None if not found
        """
        return self._strategies.get(name)

    def create_strategy(
        self,
        name: str,
        config: StrategyConfig | None = None,
        **kwargs,
    ) -> Strategy:
        """
        Create a strategy instance.

        Uses custom factory if registered, otherwise instantiates directly.

        Args:
            name: Strategy name
            config: Strategy configuration
            **kwargs: Additional arguments for strategy constructor

        Returns:
            Strategy instance

        Raises:
            ValueError: If strategy not found
        """
        if name not in self._strategies:
            raise ValueError(f"Strategy plugin not found: {name}")

        # Use custom factory if available
        if name in self._factories:
            factory = self._factories[name]
            return factory(config=config, **kwargs)

        # Default instantiation
        strategy_class = self._strategies[name]

        # Build config if not provided
        if config is None:
            config_dict = {k: v for k, v in kwargs.items() if k in StrategyConfig.__dataclass_fields__}
            if config_dict:
                config = StrategyConfig(**config_dict)

        # Instantiate
        if config is not None:
            return strategy_class(config=config)
        else:
            return strategy_class()

    def list_strategies(self) -> dict[str, dict[str, Any]]:
        """
        List all registered strategy plugins.

        Returns:
            Dictionary mapping strategy names to their metadata
        """
        return {
            name: {
                "class": cls.__name__,
                "module": cls.__module__,
                **self._metadata.get(name, {}),
            }
            for name, cls in self._strategies.items()
        }

    def is_registered(self, name: str) -> bool:
        """
        Check if a strategy is registered.

        Args:
            name: Strategy name

        Returns:
            True if strategy is registered
        """
        return name in self._strategies

    def get_metadata(self, name: str) -> dict[str, Any] | None:
        """
        Get metadata for a strategy.

        Args:
            name: Strategy name

        Returns:
            Metadata dictionary or None if not found
        """
        return self._metadata.get(name)

    def get_count(self) -> int:
        """Get count of registered strategies."""
        return len(self._strategies)

    def clear(self) -> None:
        """Clear all registered strategies (for testing)."""
        self._strategies.clear()
        self._metadata.clear()
        self._factories.clear()
        logger.warning("Strategy plugin registry cleared (testing mode)")


# Global instance
_strategy_registry: StrategyPluginRegistry | None = None


def get_strategy_plugin_registry() -> StrategyPluginRegistry:
    """
    Get the global strategy plugin registry instance.

    Returns:
        Singleton StrategyPluginRegistry instance
    """
    global _strategy_registry
    if _strategy_registry is None:
        _strategy_registry = StrategyPluginRegistry()
    return _strategy_registry


# Decorator for easy registration


def strategy_plugin(
    name: str,
    version: str = "1.0.0",
    description: str = "",
    category: str = "custom",
    config_schema: dict | None = None,
    factory: Callable | None = None,
):
    """
    Decorator to register a strategy as a plugin.

    Usage:
        @strategy_plugin(
            name="my_strategy",
            version="1.0.0",
            description="My custom strategy",
            category="adaptive"
        )
        class MyStrategy(Strategy):
            async def decide_move(self, ...):
                pass

    Args:
        name: Unique strategy name
        version: Semantic version
        description: Human-readable description
        category: Strategy category (e.g., "classic", "game_theory", "custom")
        config_schema: JSON schema for configuration validation
        factory: Optional factory function for custom instantiation

    Returns:
        Decorator function
    """

    def decorator(cls: type[Strategy]) -> type[Strategy]:
        # Validate
        if not issubclass(cls, Strategy):
            raise ValueError("@strategy_plugin can only decorate Strategy subclasses")

        # Build metadata
        metadata = {
            "version": version,
            "description": description,
            "category": category,
            "config_schema": config_schema,
        }

        # Register
        registry = get_strategy_plugin_registry()
        registry.register_strategy(
            name=name, strategy_class=cls, metadata=metadata, factory=factory
        )

        # Add metadata to class for introspection
        cls._plugin_metadata = metadata
        cls._plugin_name = name

        logger.debug(f"Strategy plugin decorated: {name} ({cls.__name__})")

        return cls

    return decorator


# Utility functions


def register_strategy_plugin(
    name: str,
    strategy_class: type[Strategy],
    version: str = "1.0.0",
    description: str = "",
    **metadata,
) -> None:
    """
    Register a strategy plugin programmatically.

    Alternative to the @strategy_plugin decorator for cases where
    you can't use decorators.

    Args:
        name: Strategy name
        strategy_class: Strategy class
        version: Version string
        description: Description
        **metadata: Additional metadata
    """
    registry = get_strategy_plugin_registry()
    full_metadata = {"version": version, "description": description, **metadata}
    registry.register_strategy(name, strategy_class, metadata=full_metadata)


def list_strategy_plugins() -> dict[str, dict[str, Any]]:
    """
    List all registered strategy plugins.

    Returns:
        Dictionary of strategy plugins with metadata
    """
    registry = get_strategy_plugin_registry()
    return registry.list_strategies()


def get_strategy_plugin(name: str) -> type[Strategy] | None:
    """
    Get a strategy plugin class by name.

    Args:
        name: Strategy name

    Returns:
        Strategy class or None if not found
    """
    registry = get_strategy_plugin_registry()
    return registry.get_strategy_class(name)


def create_strategy_plugin(
    name: str, config: StrategyConfig | None = None, **kwargs
) -> Strategy:
    """
    Create a strategy plugin instance.

    Args:
        name: Strategy name
        config: Strategy configuration
        **kwargs: Additional arguments

    Returns:
        Strategy instance

    Raises:
        ValueError: If strategy not found
    """
    registry = get_strategy_plugin_registry()
    return registry.create_strategy(name, config=config, **kwargs)
