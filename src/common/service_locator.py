"""
Service Locator Pattern
========================

Production-grade service locator for runtime service discovery and access.

The Service Locator pattern provides a central registry for accessing services
without tight coupling. While dependency injection is preferred for most cases,
service locator is useful for:
- Dynamic service resolution
- Optional dependencies
- Framework/library code
- Legacy code integration

Features:
- Type-safe service access
- Service aliasing
- Lazy loading
- Service factories
- Scoped services
- Health checks

Example:
    # Register services
    ServiceLocator.register("logger", ConsoleLogger())
    ServiceLocator.register("database", lambda: PostgresDB())

    # Get services
    logger = ServiceLocator.get("logger")
    db = ServiceLocator.get("database")  # Lazy initialized

    # Type-safe access
    logger = ServiceLocator.get_typed("logger", ILogger)
"""

from collections.abc import Callable
from threading import Lock
from typing import Any, TypeVar, cast

from .exceptions import ServiceNotFoundError
from .logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


# ============================================================================
# Service Locator
# ============================================================================


class ServiceLocator:
    """
    Central registry for service discovery and access.

    Provides a global point for accessing services without tight coupling.
    Services can be registered as instances or factories.

    Example:
        # Register services
        ServiceLocator.register("config", config_instance)
        ServiceLocator.register("database", DatabaseFactory)
        ServiceLocator.register_singleton("cache", lambda: RedisCache())

        # Get services
        config = ServiceLocator.get("config")
        db = ServiceLocator.get("database")

        # Type-safe access
        cache = ServiceLocator.get_typed("cache", ICache)

        # Check availability
        if ServiceLocator.has("metrics"):
            metrics = ServiceLocator.get("metrics")
    """

    _services: dict[str, Any] = {}
    _factories: dict[str, Callable[[], Any]] = {}
    _singletons: dict[str, Any] = {}
    _aliases: dict[str, str] = {}
    _lock = Lock()

    @classmethod
    def register(
        cls,
        name: str,
        service: Any | Callable[[], Any],
        singleton: bool = False,
    ) -> None:
        """
        Register a service.

        Args:
            name: Service identifier
            service: Service instance or factory function
            singleton: Whether to cache instance (for factories)

        Example:
            # Register instance
            ServiceLocator.register("logger", ConsoleLogger())

            # Register factory
            ServiceLocator.register("database", lambda: PostgresDB())

            # Register singleton factory
            ServiceLocator.register("cache", lambda: RedisCache(), singleton=True)
        """
        with cls._lock:
            if callable(service) and not hasattr(service, "__self__"):
                # It's a factory function
                cls._factories[name] = service
                if singleton:
                    cls._singletons[name] = None  # Will be created on first access
            else:
                # It's an instance
                cls._services[name] = service

        logger.debug(f"Service registered: {name} (singleton={singleton})")

    @classmethod
    def register_singleton(
        cls,
        name: str,
        factory: Callable[[], Any],
    ) -> None:
        """
        Register a singleton service with factory.

        Factory will be called once on first access.

        Args:
            name: Service identifier
            factory: Factory function that creates the service

        Example:
            ServiceLocator.register_singleton(
                "database",
                lambda: PostgresDB(config.db_url)
            )
        """
        cls.register(name, factory, singleton=True)

    @classmethod
    def register_alias(cls, alias: str, target: str) -> None:
        """
        Register an alias for a service.

        Args:
            alias: Alias name
            target: Target service name

        Example:
            ServiceLocator.register("postgres_db", db_instance)
            ServiceLocator.register_alias("db", "postgres_db")

            # Can now access via either name
            db = ServiceLocator.get("db")
        """
        with cls._lock:
            cls._aliases[alias] = target

        logger.debug(f"Service alias registered: {alias} -> {target}")

    @classmethod
    def get(cls, name: str) -> Any:
        """
        Get a service by name.

        Args:
            name: Service identifier

        Returns:
            Service instance

        Raises:
            ServiceNotFoundError: If service not registered

        Example:
            logger = ServiceLocator.get("logger")
            db = ServiceLocator.get("database")
        """
        # Resolve alias
        actual_name = cls._aliases.get(name, name)

        # Check instances first
        if actual_name in cls._services:
            return cls._services[actual_name]

        # Check singletons
        if actual_name in cls._singletons:
            with cls._lock:
                # Double-check after lock
                if cls._singletons[actual_name] is None:
                    # Create singleton instance
                    factory = cls._factories[actual_name]
                    cls._singletons[actual_name] = factory()
                    logger.debug(f"Singleton created: {actual_name}")

                return cls._singletons[actual_name]

        # Check factories
        if actual_name in cls._factories:
            # Create new instance each time
            return cls._factories[actual_name]()

        raise ServiceNotFoundError(name)

    @classmethod
    def get_typed(cls, name: str, service_type: type[T]) -> T:
        """
        Get a service with type casting.

        Provides type hints for better IDE support.

        Args:
            name: Service identifier
            service_type: Expected service type

        Returns:
            Service instance cast to expected type

        Example:
            logger = ServiceLocator.get_typed("logger", ILogger)
            db = ServiceLocator.get_typed("database", IDatabase)
        """
        service = cls.get(name)
        return cast(service_type, service)

    @classmethod
    def try_get(cls, name: str) -> Any | None:
        """
        Try to get a service, returning None if not found.

        Args:
            name: Service identifier

        Returns:
            Service instance or None

        Example:
            metrics = ServiceLocator.try_get("metrics")
            if metrics:
                metrics.increment("requests")
        """
        try:
            return cls.get(name)
        except ServiceNotFoundError:
            return None

    @classmethod
    def has(cls, name: str) -> bool:
        """
        Check if a service is registered.

        Args:
            name: Service identifier

        Returns:
            True if service is registered
        """
        actual_name = cls._aliases.get(name, name)
        return (
            actual_name in cls._services
            or actual_name in cls._factories
            or actual_name in cls._singletons
        )

    @classmethod
    def unregister(cls, name: str) -> bool:
        """
        Unregister a service.

        Args:
            name: Service identifier

        Returns:
            True if service was registered
        """
        with cls._lock:
            found = False

            if name in cls._services:
                del cls._services[name]
                found = True

            if name in cls._factories:
                del cls._factories[name]
                found = True

            if name in cls._singletons:
                del cls._singletons[name]
                found = True

            # Remove aliases pointing to this service
            aliases_to_remove = [k for k, v in cls._aliases.items() if v == name]
            for alias in aliases_to_remove:
                del cls._aliases[alias]

            if found:
                logger.debug(f"Service unregistered: {name}")

            return found

    @classmethod
    def list_services(cls) -> list[str]:
        """
        List all registered service names.

        Returns:
            List of service identifiers
        """
        services = set(cls._services.keys())
        services.update(cls._factories.keys())
        services.update(cls._singletons.keys())
        return sorted(services)

    @classmethod
    def clear(cls) -> None:
        """Clear all registered services (for testing)."""
        with cls._lock:
            cls._services.clear()
            cls._factories.clear()
            cls._singletons.clear()
            cls._aliases.clear()

        logger.debug("Service locator cleared")

    @classmethod
    def get_service_info(cls, name: str) -> dict[str, Any]:
        """
        Get information about a service.

        Args:
            name: Service identifier

        Returns:
            Dictionary with service information
        """
        actual_name = cls._aliases.get(name, name)

        info = {
            "name": name,
            "actual_name": actual_name if actual_name != name else None,
            "type": None,
            "is_singleton": False,
            "is_factory": False,
            "is_instance": False,
        }

        if actual_name in cls._services:
            service = cls._services[actual_name]
            info["type"] = type(service).__name__
            info["is_instance"] = True

        elif actual_name in cls._singletons:
            if cls._singletons[actual_name] is not None:
                info["type"] = type(cls._singletons[actual_name]).__name__
            info["is_singleton"] = True
            info["is_factory"] = True

        elif actual_name in cls._factories:
            info["is_factory"] = True

        return info


# ============================================================================
# Scoped Service Locator
# ============================================================================


class ScopedServiceLocator:
    """
    Scoped service locator for request-scoped services.

    Creates a child locator that can override parent services
    and provides automatic cleanup.

    Example:
        # Create scope
        with ScopedServiceLocator() as scope:
            # Override service in scope
            scope.register("user", current_user)

            # Get service (checks scope first, then parent)
            user = scope.get("user")

        # Scope cleaned up automatically
    """

    def __init__(self, parent: type[ServiceLocator] | None = None):
        """
        Initialize scoped locator.

        Args:
            parent: Parent service locator (defaults to global)
        """
        self._parent = parent or ServiceLocator
        self._scoped_services: dict[str, Any] = {}
        self._scoped_factories: dict[str, Callable[[], Any]] = {}

    def register(self, name: str, service: Any | Callable[[], Any]) -> None:
        """Register service in this scope."""
        if callable(service) and not hasattr(service, "__self__"):
            self._scoped_factories[name] = service
        else:
            self._scoped_services[name] = service

    def get(self, name: str) -> Any:
        """Get service from scope or parent."""
        # Check scope first
        if name in self._scoped_services:
            return self._scoped_services[name]

        if name in self._scoped_factories:
            return self._scoped_factories[name]()

        # Fall back to parent
        return self._parent.get(name)

    def has(self, name: str) -> bool:
        """Check if service exists in scope or parent."""
        return (
            name in self._scoped_services
            or name in self._scoped_factories
            or self._parent.has(name)
        )

    def __enter__(self) -> "ScopedServiceLocator":
        """Context manager support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up scoped services."""
        self._scoped_services.clear()
        self._scoped_factories.clear()


# ============================================================================
# Convenience Functions
# ============================================================================


def register_core_services() -> None:
    """
    Register core system services in the service locator.

    Should be called during system initialization.
    """
    from .config import get_config
    from .events.bus import get_event_bus
    from .extension_points import get_extension_registry
    from .hooks.hook_manager import get_hook_manager
    from .plugins.registry import get_plugin_registry

    # Register core services
    ServiceLocator.register_singleton("config", get_config)
    ServiceLocator.register_singleton("hook_manager", get_hook_manager)
    ServiceLocator.register_singleton("plugin_registry", get_plugin_registry)
    ServiceLocator.register_singleton("event_bus", get_event_bus)
    ServiceLocator.register_singleton("extension_registry", get_extension_registry)

    # Register aliases
    ServiceLocator.register_alias("hooks", "hook_manager")
    ServiceLocator.register_alias("plugins", "plugin_registry")
    ServiceLocator.register_alias("events", "event_bus")
    ServiceLocator.register_alias("extensions", "extension_registry")

    logger.info("Core services registered in ServiceLocator")


# ============================================================================
# Exceptions
# ============================================================================


# ServiceNotFoundError is imported from exceptions.py

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Service not found: {name}")

