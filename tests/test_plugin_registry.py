"""
Tests for Plugin Registry
==========================

Tests the core plugin registry functionality including:
- Plugin registration and unregistration
- Plugin lifecycle (load, enable, disable, unload)
- Dependency validation
- Plugin queries and listing
"""

import pytest

from src.common.logger import get_logger
from src.common.plugins import (
    PluginAlreadyRegisteredError,
    PluginContext,
    PluginDependencyError,
    PluginInterface,
    PluginMetadata,
    PluginNotFoundError,
    PluginRegistry,
    get_plugin_registry,
)

logger = get_logger(__name__)


# Test plugin implementations


class SimplePlugin(PluginInterface):
    """Simple test plugin."""

    def __init__(self):
        super().__init__()
        self.loaded = False
        self.enabled = False

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="simple_plugin",
            version="1.0.0",
            author="Test",
            description="Simple test plugin",
        )

    async def on_load(self, context: PluginContext):
        await super().on_load(context)
        self.loaded = True

    async def on_enable(self, context: PluginContext):
        await super().on_enable(context)
        self.enabled = True

    async def on_disable(self, context: PluginContext):
        await super().on_disable(context)
        self.enabled = False

    async def on_unload(self, context: PluginContext):
        await super().on_unload(context)
        self.loaded = False


class DependentPlugin(PluginInterface):
    """Plugin with dependencies."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="dependent_plugin",
            version="1.0.0",
            dependencies=["simple_plugin"],
        )


class FailingPlugin(PluginInterface):
    """Plugin that fails during lifecycle."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(name="failing_plugin", version="1.0.0")

    async def on_load(self, context: PluginContext):
        raise RuntimeError("Failed to load")


# Fixtures


@pytest.fixture
def plugin_context():
    """Create plugin context for tests."""
    registry = PluginRegistry()
    return PluginContext(
        registry=registry,
        config={},
        logger=logger,
    )


@pytest.fixture
def clean_registry():
    """Get a clean plugin registry."""
    registry = get_plugin_registry()
    registry.clear()
    yield registry
    registry.clear()


# Tests


class TestPluginMetadata:
    """Test PluginMetadata dataclass."""

    def test_metadata_creation(self):
        """Test creating plugin metadata."""
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            author="Test Author",
            description="Test description",
            dependencies=["dep1", "dep2"],
        )

        assert metadata.name == "test_plugin"
        assert metadata.version == "1.0.0"
        assert metadata.author == "Test Author"
        assert metadata.description == "Test description"
        assert metadata.dependencies == ["dep1", "dep2"]

    def test_metadata_to_dict(self):
        """Test converting metadata to dictionary."""
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
        )

        data = metadata.to_dict()
        assert data["name"] == "test_plugin"
        assert data["version"] == "1.0.0"
        assert "author" in data
        assert "description" in data

    def test_metadata_from_dict(self):
        """Test creating metadata from dictionary."""
        data = {
            "name": "test_plugin",
            "version": "1.0.0",
            "author": "Test",
            "description": "Test plugin",
        }

        metadata = PluginMetadata.from_dict(data)
        assert metadata.name == "test_plugin"
        assert metadata.version == "1.0.0"


class TestPluginContext:
    """Test PluginContext."""

    def test_context_creation(self, plugin_context):
        """Test creating plugin context."""
        assert plugin_context.registry is not None
        assert plugin_context.logger is not None

    def test_get_config(self, plugin_context):
        """Test getting config values."""
        plugin_context.config = {"key1": "value1", "key2": "value2"}

        assert plugin_context.get_config("key1") == "value1"
        assert plugin_context.get_config("missing", "default") == "default"

    def test_has_config(self, plugin_context):
        """Test checking config keys."""
        plugin_context.config = {"key1": "value1"}

        assert plugin_context.has_config("key1") is True
        assert plugin_context.has_config("missing") is False


class TestPluginInterface:
    """Test PluginInterface base class."""

    @pytest.mark.asyncio
    async def test_plugin_properties(self, plugin_context):
        """Test plugin properties."""
        plugin = SimplePlugin()

        assert plugin.is_loaded is False
        assert plugin.is_enabled is False
        assert plugin.context is None

        await plugin.on_load(plugin_context)
        assert plugin.is_loaded is True
        assert plugin.context is not None

        await plugin.on_enable(plugin_context)
        assert plugin.is_enabled is True

    @pytest.mark.asyncio
    async def test_plugin_lifecycle(self, plugin_context):
        """Test complete plugin lifecycle."""
        plugin = SimplePlugin()

        # Load
        await plugin.on_load(plugin_context)
        assert plugin.loaded is True
        assert plugin.is_loaded is True

        # Enable
        await plugin.on_enable(plugin_context)
        assert plugin.enabled is True
        assert plugin.is_enabled is True

        # Disable
        await plugin.on_disable(plugin_context)
        assert plugin.enabled is False
        assert plugin.is_enabled is False

        # Unload
        await plugin.on_unload(plugin_context)
        assert plugin.loaded is False
        assert plugin.is_loaded is False


class TestPluginRegistry:
    """Test PluginRegistry."""

    def test_singleton(self):
        """Test registry is singleton."""
        registry1 = get_plugin_registry()
        registry2 = get_plugin_registry()
        assert registry1 is registry2

    @pytest.mark.asyncio
    async def test_register_plugin(self, clean_registry, plugin_context):
        """Test registering a plugin."""
        clean_registry.set_context(plugin_context)

        plugin = SimplePlugin()
        result = await clean_registry.register_plugin(plugin)

        assert result is True
        assert clean_registry.is_registered("simple_plugin")
        assert plugin.is_loaded is True

    @pytest.mark.asyncio
    async def test_register_duplicate_plugin(self, clean_registry, plugin_context):
        """Test registering duplicate plugin raises error."""
        clean_registry.set_context(plugin_context)

        plugin1 = SimplePlugin()
        await clean_registry.register_plugin(plugin1)

        plugin2 = SimplePlugin()
        with pytest.raises(PluginAlreadyRegisteredError):
            await clean_registry.register_plugin(plugin2)

    @pytest.mark.asyncio
    async def test_register_with_missing_dependencies(self, clean_registry, plugin_context):
        """Test registering plugin with missing dependencies fails."""
        clean_registry.set_context(plugin_context)

        plugin = DependentPlugin()
        with pytest.raises(PluginDependencyError) as exc_info:
            await clean_registry.register_plugin(plugin)

        assert "simple_plugin" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_register_with_satisfied_dependencies(self, clean_registry, plugin_context):
        """Test registering plugin with satisfied dependencies."""
        clean_registry.set_context(plugin_context)

        # Register dependency first
        simple = SimplePlugin()
        await clean_registry.register_plugin(simple)

        # Now register dependent plugin
        dependent = DependentPlugin()
        result = await clean_registry.register_plugin(dependent)
        assert result is True

    @pytest.mark.asyncio
    async def test_register_plugin_load_failure(self, clean_registry, plugin_context):
        """Test plugin registration rolls back on load failure."""
        clean_registry.set_context(plugin_context)

        plugin = FailingPlugin()
        with pytest.raises(RuntimeError):
            await clean_registry.register_plugin(plugin)

        # Plugin should not be registered
        assert not clean_registry.is_registered("failing_plugin")

    @pytest.mark.asyncio
    async def test_unregister_plugin(self, clean_registry, plugin_context):
        """Test unregistering a plugin."""
        clean_registry.set_context(plugin_context)

        plugin = SimplePlugin()
        await clean_registry.register_plugin(plugin)

        result = await clean_registry.unregister_plugin("simple_plugin")
        assert result is True
        assert not clean_registry.is_registered("simple_plugin")

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_plugin(self, clean_registry):
        """Test unregistering nonexistent plugin raises error."""
        with pytest.raises(PluginNotFoundError):
            await clean_registry.unregister_plugin("nonexistent")

    @pytest.mark.asyncio
    async def test_enable_plugin(self, clean_registry, plugin_context):
        """Test enabling a plugin."""
        clean_registry.set_context(plugin_context)

        plugin = SimplePlugin()
        await clean_registry.register_plugin(plugin)

        result = await clean_registry.enable_plugin("simple_plugin")
        assert result is True
        assert clean_registry.is_enabled("simple_plugin")
        assert plugin.is_enabled is True

    @pytest.mark.asyncio
    async def test_enable_nonexistent_plugin(self, clean_registry, plugin_context):
        """Test enabling nonexistent plugin raises error."""
        clean_registry.set_context(plugin_context)

        with pytest.raises(PluginNotFoundError):
            await clean_registry.enable_plugin("nonexistent")

    @pytest.mark.asyncio
    async def test_disable_plugin(self, clean_registry, plugin_context):
        """Test disabling a plugin."""
        clean_registry.set_context(plugin_context)

        plugin = SimplePlugin()
        await clean_registry.register_plugin(plugin)
        await clean_registry.enable_plugin("simple_plugin")

        result = await clean_registry.disable_plugin("simple_plugin")
        assert result is True
        assert not clean_registry.is_enabled("simple_plugin")
        assert plugin.is_enabled is False

    @pytest.mark.asyncio
    async def test_get_plugin(self, clean_registry, plugin_context):
        """Test getting plugin by name."""
        clean_registry.set_context(plugin_context)

        plugin = SimplePlugin()
        await clean_registry.register_plugin(plugin)

        retrieved = clean_registry.get_plugin("simple_plugin")
        assert retrieved is plugin

        missing = clean_registry.get_plugin("nonexistent")
        assert missing is None

    @pytest.mark.asyncio
    async def test_get_metadata(self, clean_registry, plugin_context):
        """Test getting plugin metadata."""
        clean_registry.set_context(plugin_context)

        plugin = SimplePlugin()
        await clean_registry.register_plugin(plugin)

        metadata = clean_registry.get_metadata("simple_plugin")
        assert metadata is not None
        assert metadata.name == "simple_plugin"

    @pytest.mark.asyncio
    async def test_list_plugins(self, clean_registry, plugin_context):
        """Test listing plugins."""
        clean_registry.set_context(plugin_context)

        # Register multiple plugins
        plugin1 = SimplePlugin()
        await clean_registry.register_plugin(plugin1)

        # List all
        all_plugins = clean_registry.list_plugins()
        assert len(all_plugins) == 1

        # Enable one
        await clean_registry.enable_plugin("simple_plugin")

        # List enabled only
        enabled = clean_registry.list_plugins(filter_enabled=True)
        assert len(enabled) == 1

    @pytest.mark.asyncio
    async def test_get_summary(self, clean_registry, plugin_context):
        """Test getting registry summary."""
        clean_registry.set_context(plugin_context)

        plugin = SimplePlugin()
        await clean_registry.register_plugin(plugin)
        await clean_registry.enable_plugin("simple_plugin")

        summary = clean_registry.get_summary()
        assert summary["total_plugins"] == 1
        assert summary["enabled_plugins"] == 1
        assert summary["disabled_plugins"] == 0

    @pytest.mark.asyncio
    async def test_auto_enable(self, clean_registry, plugin_context):
        """Test auto-enabling plugin during registration."""
        clean_registry.set_context(plugin_context)

        plugin = SimplePlugin()
        await clean_registry.register_plugin(plugin, auto_enable=True)

        assert clean_registry.is_enabled("simple_plugin")
        assert plugin.is_enabled is True

    @pytest.mark.asyncio
    async def test_shutdown(self, clean_registry, plugin_context):
        """Test shutting down registry."""
        clean_registry.set_context(plugin_context)

        plugin = SimplePlugin()
        await clean_registry.register_plugin(plugin, auto_enable=True)

        await clean_registry.shutdown()

        assert clean_registry.get_total_count() == 0
        assert plugin.is_loaded is False

    def test_clear(self, clean_registry):
        """Test clearing registry."""
        # This is for testing only - doesn't call lifecycle methods
        clean_registry.clear()
        assert clean_registry.get_total_count() == 0
