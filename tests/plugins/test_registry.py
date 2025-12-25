from unittest.mock import MagicMock

import pytest

from src.common.events.bus import EventBus
from src.common.plugins.base import PluginInterface, PluginMetadata
from src.common.plugins.registry import PluginContext


class MockPlugin(PluginInterface):
    def __init__(self, name="mock_plugin"):
        super().__init__()
        self.name = name
        self.enabled_called = False
        self.disabled_called = False
        self.loaded_called = False

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(name=self.name, version="1.0.0")

    async def on_load(self, context):
        await super().on_load(context)
        self.loaded_called = True

    async def on_enable(self, context):
        await super().on_enable(context)
        self.enabled_called = True

    async def on_disable(self, context):
        await super().on_disable(context)
        self.disabled_called = True

@pytest.fixture
def registry():
    # Reset singleton if possible, or create new instance for testing if implementation allows
    # In this case, we'll just instantiate a new one for testing logic
    # Note: src.common.plugins.registry.PluginRegistry is a Singleton, so we need to be careful.
    # The implementation has a _instance check.
    # Ideally, we'd add a method to reset it or mock it.
    # For now, let's use the provided 'clear' method.
    from src.common.plugins.registry import get_plugin_registry
    reg = get_plugin_registry()
    reg.clear()
    return reg

@pytest.fixture
def context(registry):
    return PluginContext(
        registry=registry,
        config={},
        logger=MagicMock(),
        event_bus=EventBus()
    )

@pytest.mark.asyncio
async def test_plugin_lifecycle(registry, context):
    registry.set_context(context)
    plugin = MockPlugin()

    # Register
    await registry.register_plugin(plugin, auto_enable=False)
    assert plugin.is_loaded
    assert plugin.loaded_called
    assert not plugin.is_enabled

    # Enable
    await registry.enable_plugin("mock_plugin")
    assert plugin.is_enabled
    assert plugin.enabled_called

    # Disable
    await registry.disable_plugin("mock_plugin")
    assert not plugin.is_enabled
    assert plugin.disabled_called

@pytest.mark.asyncio
async def test_plugin_dependencies(registry, context):
    registry.set_context(context)

    # Plugin A depends on Plugin B
    class DependentPlugin(MockPlugin):
        def get_metadata(self):
            return PluginMetadata(
                name="dep_plugin",
                version="1.0.0",
                dependencies=["base_plugin"]
            )

    base = MockPlugin("base_plugin")
    dep = DependentPlugin("dep_plugin")

    # Register base first
    await registry.register_plugin(base)

    # Register dependent should succeed
    await registry.register_plugin(dep)

    assert registry.is_registered("base_plugin")
    assert registry.is_registered("dep_plugin")


