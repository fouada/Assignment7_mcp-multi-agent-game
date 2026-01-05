"""
Extension Points Registry
==========================

Production-grade extension point system for pluggable functionality.

Extension points allow plugins to extend specific parts of the system
in a type-safe, discoverable manner.

Features:
- Type-safe extension registration
- Priority-based extension ordering
- Extension point discovery
- Validation and constraints
- Multiple extensions per point
- Lazy loading support

Concepts:
    - Extension Point: A named location where plugins can extend functionality
    - Extension: A plugin-provided implementation for an extension point
    - Provider: Interface that extensions must implement

Example:
    # Define extension point
    registry = get_extension_registry()

    # Register extension point
    registry.register_point(
        "strategy.custom",
        provider_type=IStrategy,
        description="Custom game strategies"
    )

    # Plugin provides extension
    @extension_provider("strategy.custom", priority=100)
    class MyCustomStrategy(IStrategy):
        def decide_move(self, context):
            return 3

    # Use extensions
    strategies = registry.get_extensions("strategy.custom")
    for strategy in strategies:
        move = strategy.decide_move(context)
"""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from .logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


# ============================================================================
# Extension Point Definitions
# ============================================================================


@dataclass
class ExtensionPoint:
    """
    Definition of an extension point.

    Attributes:
        name: Unique identifier for this extension point
        provider_type: Interface/abstract class that extensions must implement
        description: Human-readable description
        tags: Categorization tags
        multiple: Whether multiple extensions are allowed
        required: Whether at least one extension is required
        validation_fn: Optional validation function for extensions
    """

    name: str
    provider_type: type
    description: str = ""
    tags: list[str] = field(default_factory=list)
    multiple: bool = True  # Allow multiple extensions
    required: bool = False  # At least one required
    validation_fn: Callable[[Any], bool] | None = None

    def validate_extension(self, extension: Any) -> bool:
        """
        Validate an extension for this point.

        Args:
            extension: Extension instance to validate

        Returns:
            True if valid, False otherwise
        """
        # Check type
        if not isinstance(extension, self.provider_type):
            logger.error(
                f"Extension for '{self.name}' must implement {self.provider_type.__name__}"
            )
            return False

        # Custom validation
        if self.validation_fn:
            try:
                if not self.validation_fn(extension):
                    logger.error(f"Extension validation failed for '{self.name}'")
                    return False
            except Exception as e:
                logger.error(f"Extension validation error for '{self.name}': {e}")
                return False

        return True


@dataclass
class Extension:
    """
    Registered extension instance.

    Attributes:
        point_name: Extension point this extends
        provider: Extension provider instance
        priority: Extension priority (higher = earlier)
        plugin_name: Name of plugin providing this extension
        metadata: Additional metadata
        lazy_factory: Optional lazy initialization factory
    """

    point_name: str
    provider: Any
    priority: int = 0
    plugin_name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    lazy_factory: Callable[[], Any] | None = None

    _initialized: bool = False

    def get_provider(self) -> Any:
        """Get provider instance (lazy initialize if needed)."""
        if not self._initialized and self.lazy_factory:
            self.provider = self.lazy_factory()
            self._initialized = True
        return self.provider


# ============================================================================
# Extension Registry
# ============================================================================


class ExtensionRegistry:
    """
    Central registry for extension points and extensions.

    Manages registration and discovery of extension points and their implementations.

    Example:
        # Get registry
        registry = get_extension_registry()

        # Register extension point
        registry.register_point(
            "validators.move",
            IValidator,
            description="Move validation logic"
        )

        # Register extension
        registry.register_extension(
            "validators.move",
            RangeValidator(),
            priority=100
        )

        # Get extensions
        validators = registry.get_extensions("validators.move")
        for validator in validators:
            validator.validate(move)
    """

    _instance: "ExtensionRegistry | None" = None

    def __new__(cls) -> "ExtensionRegistry":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize registry."""
        if self._initialized:
            return

        # Extension points: name -> ExtensionPoint
        self._points: dict[str, ExtensionPoint] = {}

        # Extensions: point_name -> list[Extension]
        self._extensions: dict[str, list[Extension]] = defaultdict(list)

        self._initialized = True
        logger.debug("ExtensionRegistry initialized")

    def register_point(
        self,
        name: str,
        provider_type: type[T],
        description: str = "",
        tags: list[str] | None = None,
        multiple: bool = True,
        required: bool = False,
        validation_fn: Callable[[T], bool] | None = None,
    ) -> ExtensionPoint:
        """
        Register an extension point.

        Args:
            name: Unique extension point identifier
            provider_type: Interface that extensions must implement
            description: Human-readable description
            tags: Categorization tags
            multiple: Whether multiple extensions are allowed
            required: Whether at least one extension is required
            validation_fn: Optional validation function

        Returns:
            Created ExtensionPoint

        Example:
            registry.register_point(
                "validators.move",
                IValidator,
                description="Validates player moves",
                tags=["validation", "rules"],
                multiple=True
            )
        """
        point = ExtensionPoint(
            name=name,
            provider_type=provider_type,
            description=description,
            tags=tags or [],
            multiple=multiple,
            required=required,
            validation_fn=validation_fn,
        )

        self._points[name] = point
        logger.info(f"Extension point registered: {name} ({provider_type.__name__})")

        return point

    def register_extension(
        self,
        point_name: str,
        provider: T,
        priority: int = 0,
        plugin_name: str = "",
        metadata: dict[str, Any] | None = None,
        lazy_factory: Callable[[], T] | None = None,
    ) -> bool:
        """
        Register an extension for a point.

        Args:
            point_name: Extension point to extend
            provider: Extension provider instance
            priority: Extension priority (higher executes first)
            plugin_name: Name of plugin providing this extension
            metadata: Additional metadata
            lazy_factory: Optional lazy initialization factory

        Returns:
            True if registered successfully

        Example:
            registry.register_extension(
                "validators.move",
                RangeValidator(min=1, max=5),
                priority=100,
                plugin_name="core"
            )
        """
        # Check if point exists
        if point_name not in self._points:
            logger.error(f"Extension point not found: {point_name}")
            return False

        point = self._points[point_name]

        # Validate extension
        if not lazy_factory and not point.validate_extension(provider):
            return False

        # Check multiple constraint
        if not point.multiple and self._extensions[point_name]:
            logger.error(f"Extension point '{point_name}' does not allow multiple extensions")
            return False

        # Create extension
        extension = Extension(
            point_name=point_name,
            provider=provider,
            priority=priority,
            plugin_name=plugin_name,
            metadata=metadata or {},
            lazy_factory=lazy_factory,
        )

        # Add to registry
        self._extensions[point_name].append(extension)

        # Sort by priority (descending)
        self._extensions[point_name].sort(key=lambda e: e.priority, reverse=True)

        logger.info(
            f"Extension registered: {point_name} (priority={priority}, "
            f"plugin={plugin_name or 'unknown'})"
        )

        return True

    def get_extensions(self, point_name: str) -> list[Any]:
        """
        Get all extensions for a point.

        Returns extensions in priority order (highest first).

        Args:
            point_name: Extension point name

        Returns:
            List of extension provider instances

        Example:
            validators = registry.get_extensions("validators.move")
            for validator in validators:
                result = validator.validate(data)
        """
        if point_name not in self._extensions:
            return []

        # Lazy initialize and return providers
        return [ext.get_provider() for ext in self._extensions[point_name]]

    def get_extension(self, point_name: str, index: int = 0) -> Any | None:
        """
        Get a single extension for a point.

        Args:
            point_name: Extension point name
            index: Extension index (0 = highest priority)

        Returns:
            Extension provider or None if not found
        """
        extensions = self.get_extensions(point_name)
        if index < len(extensions):
            return extensions[index]
        return None

    def get_point(self, name: str) -> ExtensionPoint | None:
        """
        Get extension point definition.

        Args:
            name: Extension point name

        Returns:
            ExtensionPoint or None if not found
        """
        return self._points.get(name)

    def list_points(
        self,
        tags: list[str] | None = None,
        provider_type: type | None = None,
    ) -> list[ExtensionPoint]:
        """
        List extension points matching criteria.

        Args:
            tags: Filter by tags (any match)
            provider_type: Filter by provider type

        Returns:
            List of matching extension points
        """
        points = list(self._points.values())

        # Filter by tags
        if tags:
            points = [p for p in points if any(tag in p.tags for tag in tags)]

        # Filter by provider type
        if provider_type:
            points = [p for p in points if p.provider_type == provider_type]

        return points

    def has_extensions(self, point_name: str) -> bool:
        """Check if extension point has any extensions."""
        return bool(self._extensions.get(point_name))

    def get_extension_count(self, point_name: str) -> int:
        """Get number of extensions for a point."""
        return len(self._extensions.get(point_name, []))

    def validate_required_points(self) -> tuple[bool, list[str]]:
        """
        Validate that all required extension points have extensions.

        Returns:
            Tuple of (is_valid, missing_extensions)
        """
        missing = []

        for point in self._points.values():
            if point.required and not self.has_extensions(point.name):
                missing.append(point.name)

        return len(missing) == 0, missing

    def clear(self) -> None:
        """Clear all extension points and extensions (for testing)."""
        self._points.clear()
        self._extensions.clear()
        logger.debug("Extension registry cleared")


# ============================================================================
# Decorators
# ============================================================================


def extension_provider(
    point_name: str,
    priority: int = 0,
    plugin_name: str = "",
    metadata: dict[str, Any] | None = None,
) -> Callable[[type[T]], type[T]]:
    """
    Decorator to mark a class as an extension provider.

    Automatically registers the class when the module is imported.

    Args:
        point_name: Extension point to extend
        priority: Extension priority
        plugin_name: Plugin name
        metadata: Additional metadata

    Example:
        @extension_provider("strategy.custom", priority=100)
        class MyStrategy(IStrategy):
            def decide_move(self, context):
                return 3

        # Automatically registered when module loads
    """

    def decorator(cls: type[T]) -> type[T]:
        # Register lazily (class will be instantiated when first accessed)
        get_extension_registry().register_extension(
            point_name=point_name,
            provider=None,  # Will be lazy-loaded
            priority=priority,
            plugin_name=plugin_name,
            metadata=metadata or {},
            lazy_factory=lambda: cls(),  # Lazy instantiation
        )
        return cls

    return decorator


# ============================================================================
# Typed Extension Points (Generic)
# ============================================================================


class TypedExtensionPoint(Generic[T]):
    """
    Type-safe extension point wrapper.

    Provides type hints for extension access.

    Example:
        # Define typed extension point
        ValidatorPoint = TypedExtensionPoint[IValidator]("validators.move")

        # Register (type-checked by IDE)
        ValidatorPoint.register(RangeValidator())

        # Get extensions (type is known)
        validators: list[IValidator] = ValidatorPoint.get_all()
    """

    def __init__(self, name: str):
        """
        Initialize typed extension point.

        Args:
            name: Extension point name
        """
        self.name = name
        self.registry = get_extension_registry()

    def register(
        self,
        provider: T,
        priority: int = 0,
        plugin_name: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Register extension with type safety."""
        return self.registry.register_extension(
            self.name, provider, priority, plugin_name, metadata
        )

    def get_all(self) -> list[T]:
        """Get all extensions with correct type."""
        return self.registry.get_extensions(self.name)  # type: ignore[return-value]

    def get_first(self) -> T | None:
        """Get highest priority extension."""
        return self.registry.get_extension(self.name)  # type: ignore[return-value]

    def has_extensions(self) -> bool:
        """Check if extensions are registered."""
        return self.registry.has_extensions(self.name)


# ============================================================================
# Global Registry
# ============================================================================

_global_registry: ExtensionRegistry | None = None


def get_extension_registry() -> ExtensionRegistry:
    """
    Get the global extension registry.

    Returns:
        Singleton ExtensionRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ExtensionRegistry()
    return _global_registry


def register_core_extension_points() -> None:
    """
    Register core extension points for the system.

    Should be called during system initialization.
    """
    registry = get_extension_registry()

    # Strategy extension point
    from ..agents.strategies.base import Strategy

    registry.register_point(
        "strategy.custom",
        Strategy,
        description="Custom game strategies",
        tags=["strategy", "game"],
        multiple=True,
    )

    # Middleware extension point
    from ..middleware.base import Middleware

    registry.register_point(
        "middleware.request",
        Middleware,
        description="Request processing middleware",
        tags=["middleware", "request"],
        multiple=True,
    )

    # Event handler extension point
    registry.register_point(
        "event.handler",
        Callable,  # type: ignore[arg-type]
        description="Event handlers",
        tags=["event", "handler"],
        multiple=True,
    )

    logger.info("Core extension points registered")

