"""
Tests for Plugin Discovery
===========================

Tests the plugin discovery mechanisms:
- Entry point discovery
- Directory scanning
- Plugin validation
- Auto-discovery and registration
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from src.common.logger import get_logger
from src.common.plugins import (
    PluginContext,
    PluginDiscovery,
    PluginInterface,
    auto_discover_and_register,
    discover_plugins,
    get_plugin_registry,
)

logger = get_logger(__name__)


# Test plugin for directory discovery


SIMPLE_PLUGIN_CODE = '''
"""Simple test plugin."""
from src.common.plugins import PluginInterface, PluginMetadata, PluginContext

class TestDiscoveryPlugin(PluginInterface):
    """Test plugin for discovery."""

    def get_metadata(self):
        return PluginMetadata(
            name="test_discovery_plugin",
            version="1.0.0",
            description="Test plugin for discovery"
        )
'''

INVALID_PLUGIN_CODE = '''
"""Invalid plugin - missing PluginInterface."""
class NotAPlugin:
    pass
'''


# Fixtures


@pytest.fixture
def temp_plugin_dir():
    """Create temporary plugin directory."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def clean_registry():
    """Get clean plugin registry."""
    registry = get_plugin_registry()
    registry.clear()
    yield registry
    registry.clear()


# Tests


class TestPluginDiscovery:
    """Test PluginDiscovery class."""

    @pytest.mark.asyncio
    async def test_discover_from_directory_no_plugins(self, temp_plugin_dir):
        """Test discovering from empty directory."""
        plugins = await PluginDiscovery.discover_from_directory(temp_plugin_dir)
        assert len(plugins) == 0

    @pytest.mark.asyncio
    async def test_discover_from_directory_with_plugin(self, temp_plugin_dir):
        """Test discovering plugin from directory."""
        # Create plugin file
        plugin_file = temp_plugin_dir / "test_plugin.py"
        plugin_file.write_text(SIMPLE_PLUGIN_CODE)

        # Discover plugins
        plugins = await PluginDiscovery.discover_from_directory(temp_plugin_dir)

        assert len(plugins) == 1
        assert isinstance(plugins[0], PluginInterface)
        assert plugins[0].get_metadata().name == "test_discovery_plugin"

    @pytest.mark.asyncio
    async def test_discover_from_directory_with_pattern(self, temp_plugin_dir):
        """Test discovering with custom pattern."""
        # Create files with different names
        (temp_plugin_dir / "my_strategy_plugin.py").write_text(SIMPLE_PLUGIN_CODE)
        (temp_plugin_dir / "other_file.py").write_text(SIMPLE_PLUGIN_CODE)

        # Discover with specific pattern
        plugins = await PluginDiscovery.discover_from_directory(
            temp_plugin_dir, pattern="*_strategy_plugin.py"
        )

        assert len(plugins) == 1

    @pytest.mark.asyncio
    async def test_discover_from_directory_invalid_plugin(self, temp_plugin_dir):
        """Test discovering directory with invalid plugin."""
        # Create invalid plugin file
        plugin_file = temp_plugin_dir / "invalid_plugin.py"
        plugin_file.write_text(INVALID_PLUGIN_CODE)

        # Should not find any plugins
        plugins = await PluginDiscovery.discover_from_directory(temp_plugin_dir)
        assert len(plugins) == 0

    @pytest.mark.asyncio
    async def test_discover_from_nonexistent_directory(self):
        """Test discovering from nonexistent directory."""
        fake_dir = Path("/nonexistent/directory")
        plugins = await PluginDiscovery.discover_from_directory(fake_dir)
        assert len(plugins) == 0

    @pytest.mark.asyncio
    async def test_discover_all_with_config(self, temp_plugin_dir):
        """Test discover_all with configuration."""
        # Create plugin file
        (temp_plugin_dir / "test_plugin.py").write_text(SIMPLE_PLUGIN_CODE)

        # Configure discovery
        config = {
            "directory_scan": {
                "enabled": True,
                "paths": [str(temp_plugin_dir)],
                "pattern": "*.py",
            }
        }

        # Discover
        plugins = await PluginDiscovery.discover_all(config)
        assert len(plugins) >= 1

    @pytest.mark.asyncio
    async def test_discover_all_disabled(self):
        """Test discover_all with discovery disabled."""
        config = {"directory_scan": {"enabled": False, "paths": ["/some/path"]}}

        plugins = await PluginDiscovery.discover_all(config)
        # Should not discover anything when disabled
        assert isinstance(plugins, list)

    @pytest.mark.asyncio
    async def test_load_and_register_plugins(self, temp_plugin_dir, clean_registry):
        """Test loading and registering discovered plugins."""
        # Create plugin file
        (temp_plugin_dir / "test_plugin.py").write_text(SIMPLE_PLUGIN_CODE)

        # Set context
        context = PluginContext(
            registry=clean_registry,
            config={},
            logger=logger,
        )
        clean_registry.set_context(context)

        # Configure discovery
        config = {
            "directory_scan": {
                "enabled": True,
                "paths": [str(temp_plugin_dir)],
                "pattern": "*.py",
            }
        }

        # Load and register
        count = await PluginDiscovery.load_and_register_plugins(config, auto_enable=True)

        assert count >= 1
        assert clean_registry.is_registered("test_discovery_plugin")
        assert clean_registry.is_enabled("test_discovery_plugin")


class TestPluginValidation:
    """Test plugin file validation."""

    def test_validate_plugin_file_valid(self, temp_plugin_dir):
        """Test validating valid plugin file."""
        plugin_file = temp_plugin_dir / "valid_plugin.py"
        plugin_file.write_text(SIMPLE_PLUGIN_CODE)

        is_valid = PluginDiscovery.validate_plugin_file(plugin_file)
        assert is_valid is True

    def test_validate_plugin_file_nonexistent(self):
        """Test validating nonexistent file."""
        fake_file = Path("/nonexistent/file.py")
        is_valid = PluginDiscovery.validate_plugin_file(fake_file)
        assert is_valid is False

    def test_validate_plugin_file_not_python(self, temp_plugin_dir):
        """Test validating non-Python file."""
        text_file = temp_plugin_dir / "readme.txt"
        text_file.write_text("Not a plugin")

        is_valid = PluginDiscovery.validate_plugin_file(text_file)
        assert is_valid is False

    def test_validate_plugin_file_syntax_error(self, temp_plugin_dir):
        """Test validating file with syntax error."""
        plugin_file = temp_plugin_dir / "broken_plugin.py"
        plugin_file.write_text("def broken(:\n    pass")

        is_valid = PluginDiscovery.validate_plugin_file(plugin_file)
        assert is_valid is False

    def test_validate_plugin_file_no_plugin_interface(self, temp_plugin_dir):
        """Test validating file without PluginInterface."""
        plugin_file = temp_plugin_dir / "no_plugin.py"
        plugin_file.write_text("x = 1")

        is_valid = PluginDiscovery.validate_plugin_file(plugin_file)
        assert is_valid is False


class TestConvenienceFunctions:
    """Test convenience functions."""

    @pytest.mark.asyncio
    async def test_discover_plugins_function(self, temp_plugin_dir):
        """Test discover_plugins convenience function."""
        (temp_plugin_dir / "test_plugin.py").write_text(SIMPLE_PLUGIN_CODE)

        config = {
            "directory_scan": {
                "enabled": True,
                "paths": [str(temp_plugin_dir)],
            }
        }

        plugins = await discover_plugins(config)
        assert isinstance(plugins, list)

    @pytest.mark.asyncio
    async def test_auto_discover_and_register_function(self, temp_plugin_dir, clean_registry):
        """Test auto_discover_and_register convenience function."""
        (temp_plugin_dir / "test_plugin.py").write_text(SIMPLE_PLUGIN_CODE)

        context = PluginContext(
            registry=clean_registry,
            config={},
            logger=logger,
        )
        clean_registry.set_context(context)

        config = {
            "directory_scan": {
                "enabled": True,
                "paths": [str(temp_plugin_dir)],
            }
        }

        count = await auto_discover_and_register(config, auto_enable=False)
        assert count >= 1


class TestEntryPointDiscovery:
    """Test entry point discovery.

    Note: Entry point discovery requires actual installed packages,
    so these tests verify the mechanism without actual entry points.
    """

    @pytest.mark.asyncio
    async def test_discover_from_entry_points_no_group(self):
        """Test discovering with nonexistent entry point group."""
        plugins = await PluginDiscovery.discover_from_entry_points(group="nonexistent.group")
        # Should return empty list, not error
        assert isinstance(plugins, list)
        assert len(plugins) == 0

    @pytest.mark.asyncio
    async def test_discover_from_entry_points_default_group(self):
        """Test discovering from default group."""
        # This will find no plugins in test environment, but tests the mechanism
        plugins = await PluginDiscovery.discover_from_entry_points()
        assert isinstance(plugins, list)


class TestMultiplePlugins:
    """Test discovering multiple plugins."""

    @pytest.mark.asyncio
    async def test_discover_multiple_plugins(self, temp_plugin_dir):
        """Test discovering multiple plugins from directory."""
        # Create multiple plugin files with _plugin.py suffix
        for i in range(3):
            plugin_code = f"""
from src.common.plugins import PluginInterface, PluginMetadata

class TestPlugin{i}(PluginInterface):
    def get_metadata(self):
        return PluginMetadata(name="plugin_{i}", version="1.0.0")
"""
            (temp_plugin_dir / f"test{i}_plugin.py").write_text(plugin_code)

        # Discover all (using default pattern)
        plugins = await PluginDiscovery.discover_from_directory(temp_plugin_dir)
        assert len(plugins) == 3

    @pytest.mark.asyncio
    async def test_discover_mixed_files(self, temp_plugin_dir):
        """Test discovering from directory with mixed files."""
        # Valid plugin
        (temp_plugin_dir / "valid_plugin.py").write_text(SIMPLE_PLUGIN_CODE)

        # Invalid plugin
        (temp_plugin_dir / "invalid_plugin.py").write_text(INVALID_PLUGIN_CODE)

        # Non-plugin Python file
        (temp_plugin_dir / "helper.py").write_text("def helper(): pass")

        # Non-Python file
        (temp_plugin_dir / "readme.txt").write_text("Documentation")

        # Should only find valid plugin
        plugins = await PluginDiscovery.discover_from_directory(temp_plugin_dir)
        assert len(plugins) == 1


class TestPluginLoadingErrors:
    """Test error handling during plugin loading."""

    @pytest.mark.asyncio
    async def test_discover_plugin_with_import_error(self, temp_plugin_dir):
        """Test discovering plugin with import error."""
        broken_plugin = """
from src.common.plugins import PluginInterface, PluginMetadata
from nonexistent_module import something

class BrokenPlugin(PluginInterface):
    def get_metadata(self):
        return PluginMetadata(name="broken", version="1.0.0")
"""
        (temp_plugin_dir / "broken_plugin.py").write_text(broken_plugin)

        # Should handle error gracefully
        plugins = await PluginDiscovery.discover_from_directory(temp_plugin_dir)
        # Broken plugin should not be discovered
        assert len(plugins) == 0

    @pytest.mark.asyncio
    async def test_discover_plugin_with_runtime_error(self, temp_plugin_dir):
        """Test discovering plugin that raises error on instantiation."""
        error_plugin = """
from src.common.plugins import PluginInterface, PluginMetadata

class ErrorPlugin(PluginInterface):
    def __init__(self):
        raise RuntimeError("Cannot instantiate")

    def get_metadata(self):
        return PluginMetadata(name="error", version="1.0.0")
"""
        (temp_plugin_dir / "error_plugin.py").write_text(error_plugin)

        # Should handle error gracefully
        plugins = await PluginDiscovery.discover_from_directory(temp_plugin_dir)
        assert len(plugins) == 0
