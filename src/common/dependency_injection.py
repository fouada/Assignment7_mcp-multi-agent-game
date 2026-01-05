"""
Dependency Injection Container
================================

Production-grade dependency injection system for managing object lifecycles
and dependencies.

Features:
- Singleton, transient, and scoped lifetimes
- Constructor injection
- Interface-based registration
- Lazy initialization
- Circular dependency detection
- Child containers (scopes)
- Decorator-based registration

Example:
    # Register services
    container = DependencyContainer()
    container.register(ILogger, ConsoleLogger, lifetime=Lifetime.SINGLETON)
    container.register(IDatabase, PostgresDatabase, lifetime=Lifetime.SCOPED)

    # Resolve dependencies (auto-inject constructor params)
    service = container.resolve(MyService)  # ILogger auto-injected

    # Use decorator
    @injectable(IMyService, lifetime=Lifetime.TRANSIENT)
    class MyService:
        def __init__(self, logger: ILogger, db: IDatabase):
            self.logger = logger
            self.db = db
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from threading import Lock
from typing import Any, TypeVar, get_type_hints

from .logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


# ============================================================================
# Lifetime Strategies
# ============================================================================


class Lifetime(Enum):
    """Service lifetime strategies."""

    SINGLETON = "singleton"  # One instance for entire container
    TRANSIENT = "transient"  # New instance every time
    SCOPED = "scoped"  # One instance per scope (child container)


# ============================================================================
# Service Descriptors
# ============================================================================


@dataclass
class ServiceDescriptor:
    """
    Describes how to construct a service.

    Attributes:
        service_type: Interface or abstract class
        implementation_type: Concrete implementation class
        factory: Optional factory function
        instance: Pre-created instance (for singletons)
        lifetime: Service lifetime strategy
        dependencies: Constructor dependencies (resolved from type hints)
    """

    service_type: type
    implementation_type: type | None = None
    factory: Callable[..., Any] | None = None
    instance: Any | None = None
    lifetime: Lifetime = Lifetime.TRANSIENT
    dependencies: list[type] = None  # type: ignore[assignment]

    def __post_init__(self):
        """Initialize dependencies from implementation constructor."""
        if self.dependencies is None:
            self.dependencies = []

        # Extract dependencies from constructor type hints
        if self.implementation_type:
            try:
                hints = get_type_hints(self.implementation_type.__init__)
                # Skip 'self' and 'return'
                self.dependencies = [
                    hint for name, hint in hints.items() if name not in ("self", "return")
                ]
            except Exception as e:
                logger.debug(f"Could not extract dependencies for {self.service_type}: {e}")


# ============================================================================
# Dependency Container
# ============================================================================


class DependencyContainer:
    """
    Dependency injection container.

    Manages registration and resolution of services with dependency injection.
    Supports multiple lifetime strategies and automatic constructor injection.

    Example:
        # Create container
        container = DependencyContainer()

        # Register services
        container.register(ILogger, ConsoleLogger, Lifetime.SINGLETON)
        container.register(ICache, RedisCache, Lifetime.SCOPED)
        container.register_instance(IConfig, config_instance)

        # Register with factory
        container.register_factory(
            IDatabase,
            lambda c: PostgresDatabase(c.resolve(IConfig)),
            Lifetime.SINGLETON
        )

        # Resolve services (dependencies auto-injected)
        logger = container.resolve(ILogger)
        service = container.resolve(MyService)  # Gets ILogger, ICache auto-injected

        # Create scope
        with container.create_scope() as scope:
            scoped_service = scope.resolve(IScopedService)
    """

    def __init__(self, parent: "DependencyContainer | None" = None):
        """
        Initialize container.

        Args:
            parent: Parent container for scoped resolution
        """
        self._services: dict[type, ServiceDescriptor] = {}
        self._singletons: dict[type, Any] = {}
        self._parent = parent
        self._lock = Lock()
        self._resolving: set[type] = set()  # Circular dependency detection

    def register(
        self,
        service_type: type[T],
        implementation_type: type[T],
        lifetime: Lifetime = Lifetime.TRANSIENT,
    ) -> None:
        """
        Register a service with its implementation.

        Args:
            service_type: Interface or abstract class
            implementation_type: Concrete implementation
            lifetime: Service lifetime strategy

        Example:
            container.register(ILogger, ConsoleLogger, Lifetime.SINGLETON)
            container.register(IDatabase, PostgresDB, Lifetime.SCOPED)
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation_type,
            lifetime=lifetime,
        )

        with self._lock:
            self._services[service_type] = descriptor

        logger.debug(
            f"Registered {service_type.__name__} -> {implementation_type.__name__} "
            f"({lifetime.value})"
        )

    def register_instance(self, service_type: type[T], instance: T) -> None:
        """
        Register a pre-created instance (always singleton).

        Args:
            service_type: Service type
            instance: Pre-created instance

        Example:
            config = load_config()
            container.register_instance(IConfig, config)
        """
        descriptor = ServiceDescriptor(
            service_type=service_type, instance=instance, lifetime=Lifetime.SINGLETON
        )

        with self._lock:
            self._services[service_type] = descriptor
            self._singletons[service_type] = instance

        logger.debug(f"Registered instance of {service_type.__name__}")

    def register_factory(
        self,
        service_type: type[T],
        factory: Callable[["DependencyContainer"], T],
        lifetime: Lifetime = Lifetime.TRANSIENT,
    ) -> None:
        """
        Register a factory function for creating instances.

        Args:
            service_type: Service type
            factory: Factory function that receives container and returns instance
            lifetime: Service lifetime strategy

        Example:
            container.register_factory(
                IDatabase,
                lambda c: PostgresDB(c.resolve(IConfig).db_url),
                Lifetime.SINGLETON
            )
        """
        descriptor = ServiceDescriptor(
            service_type=service_type, factory=factory, lifetime=lifetime
        )

        with self._lock:
            self._services[service_type] = descriptor

        logger.debug(f"Registered factory for {service_type.__name__} ({lifetime.value})")

    def resolve(self, service_type: type[T]) -> T:
        """
        Resolve a service instance.

        Automatically injects constructor dependencies based on type hints.

        Args:
            service_type: Type to resolve

        Returns:
            Service instance with dependencies injected

        Raises:
            ServiceNotFoundError: If service not registered
            CircularDependencyError: If circular dependency detected

        Example:
            logger = container.resolve(ILogger)
            service = container.resolve(MyService)  # Dependencies auto-injected
        """
        # Check circular dependencies
        if service_type in self._resolving:
            raise CircularDependencyError(service_type)

        # Try this container first
        descriptor = self._services.get(service_type)

        # Try parent if not found
        if descriptor is None and self._parent:
            return self._parent.resolve(service_type)

        if descriptor is None:
            raise ServiceNotFoundError(service_type)

        # Handle different lifetimes
        if descriptor.lifetime == Lifetime.SINGLETON:
            return self._resolve_singleton(service_type, descriptor)
        elif descriptor.lifetime == Lifetime.SCOPED:
            return self._resolve_scoped(service_type, descriptor)
        else:  # TRANSIENT
            return self._resolve_transient(service_type, descriptor)

    def _resolve_singleton(self, service_type: type[T], descriptor: ServiceDescriptor) -> T:
        """Resolve singleton instance."""
        # Check if already created
        if service_type in self._singletons:
            return self._singletons[service_type]

        with self._lock:
            # Double-check after acquiring lock
            if service_type in self._singletons:
                return self._singletons[service_type]

            # Create instance
            instance = self._create_instance(service_type, descriptor)
            self._singletons[service_type] = instance

            return instance

    def _resolve_scoped(self, service_type: type[T], descriptor: ServiceDescriptor) -> T:
        """Resolve scoped instance (singleton per scope)."""
        # In root container, scoped = singleton
        return self._resolve_singleton(service_type, descriptor)

    def _resolve_transient(self, service_type: type[T], descriptor: ServiceDescriptor) -> T:
        """Resolve transient instance (new every time)."""
        return self._create_instance(service_type, descriptor)

    def _create_instance(self, service_type: type[T], descriptor: ServiceDescriptor) -> T:
        """Create service instance with dependency injection."""
        # Mark as resolving for circular dependency detection
        self._resolving.add(service_type)

        try:
            # Use existing instance if available
            if descriptor.instance is not None:
                return descriptor.instance

            # Use factory if available
            if descriptor.factory:
                return descriptor.factory(self)

            # Use implementation type
            if descriptor.implementation_type:
                return self._construct_with_injection(descriptor.implementation_type)

            raise ServiceResolutionError(service_type, "No implementation or factory provided")

        finally:
            self._resolving.discard(service_type)

    def _construct_with_injection(self, implementation_type: type[T]) -> T:
        """
        Construct instance with constructor dependency injection.

        Inspects constructor type hints and resolves dependencies automatically.
        """
        try:
            # Get constructor type hints
            hints = get_type_hints(implementation_type.__init__)

            # Skip 'self' and 'return'
            param_types = {
                name: hint for name, hint in hints.items() if name not in ("self", "return")
            }

            # Resolve dependencies
            kwargs = {}
            for param_name, param_type in param_types.items():
                try:
                    kwargs[param_name] = self.resolve(param_type)
                except ServiceNotFoundError:
                    # Dependency not registered - try to continue without it
                    logger.warning(
                        f"Dependency {param_type.__name__} not registered "
                        f"for {implementation_type.__name__}.{param_name}"
                    )

            # Construct instance
            return implementation_type(**kwargs)

        except Exception as e:
            raise ServiceResolutionError(implementation_type, str(e)) from e

    def try_resolve(self, service_type: type[T]) -> T | None:
        """
        Try to resolve a service, returning None if not found.

        Args:
            service_type: Type to resolve

        Returns:
            Service instance or None if not registered
        """
        try:
            return self.resolve(service_type)
        except ServiceNotFoundError:
            return None

    def is_registered(self, service_type: type) -> bool:
        """Check if a service is registered."""
        return service_type in self._services or (
            self._parent and self._parent.is_registered(service_type)
        )

    def create_scope(self) -> "DependencyContainer":
        """
        Create a child container (scope).

        Scoped services will be singletons within this scope.

        Returns:
            Child container

        Example:
            with container.create_scope() as scope:
                service = scope.resolve(IScopedService)
                # service is singleton within this scope
        """
        return DependencyContainer(parent=self)

    def __enter__(self) -> "DependencyContainer":
        """Context manager support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        self._singletons.clear()

    def get_registered_services(self) -> list[type]:
        """Get list of registered service types."""
        services = list(self._services.keys())
        if self._parent:
            services.extend(self._parent.get_registered_services())
        return services

    def clear(self) -> None:
        """Clear all registrations (for testing)."""
        with self._lock:
            self._services.clear()
            self._singletons.clear()
            self._resolving.clear()


# ============================================================================
# Decorators
# ============================================================================


def injectable(
    service_type: type | None = None, lifetime: Lifetime = Lifetime.TRANSIENT
) -> Callable[[type[T]], type[T]]:
    """
    Decorator to mark a class as injectable.

    Registers the class in the global container when the module is imported.

    Args:
        service_type: Interface type (defaults to the class itself)
        lifetime: Service lifetime

    Example:
        @injectable(ILogger, Lifetime.SINGLETON)
        class ConsoleLogger:
            def log(self, message: str):
                print(message)

        # Now ILogger is automatically registered
        logger = get_container().resolve(ILogger)
    """

    def decorator(cls: type[T]) -> type[T]:
        # Register in global container when module loads
        interface = service_type or cls
        get_container().register(interface, cls, lifetime)
        return cls

    return decorator


# ============================================================================
# Global Container
# ============================================================================

_global_container: DependencyContainer | None = None


def get_container() -> DependencyContainer:
    """
    Get the global dependency container.

    Returns:
        Global DependencyContainer instance
    """
    global _global_container
    if _global_container is None:
        _global_container = DependencyContainer()
    return _global_container


def set_container(container: DependencyContainer) -> None:
    """
    Set the global dependency container.

    Args:
        container: Container to use as global
    """
    global _global_container
    _global_container = container


# ============================================================================
# Exceptions
# ============================================================================


class DIError(Exception):
    """Base exception for dependency injection errors."""

    pass


class ServiceNotFoundError(DIError):
    """Service not registered in container."""

    def __init__(self, service_type: type):
        self.service_type = service_type
        super().__init__(f"Service not registered: {service_type.__name__}")


class ServiceResolutionError(DIError):
    """Failed to resolve service."""

    def __init__(self, service_type: type, reason: str):
        self.service_type = service_type
        self.reason = reason
        super().__init__(f"Failed to resolve {service_type.__name__}: {reason}")


class CircularDependencyError(DIError):
    """Circular dependency detected."""

    def __init__(self, service_type: type):
        self.service_type = service_type
        super().__init__(f"Circular dependency detected when resolving {service_type.__name__}")

