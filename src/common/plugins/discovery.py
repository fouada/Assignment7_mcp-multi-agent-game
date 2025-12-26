"""
Plugin Discovery
================

Automatic discovery of plugins from entry points and directories.

Supports two discovery mechanisms:
1. Entry points: Plugins defined in pyproject.toml [project.entry-points]
2. Directory scanning: Plugins in specified directories

Usage:
    # Discover all plugins from config
    config = {
        "entry_point_group": "mcp_game.plugins",
        "directory_scan": {
            "enabled": True,
            "paths": ["plugins", "~/.mcp_game/plugins"],
            "pattern": "*_plugin.py"
        }
    }

    plugins = await PluginDiscovery.discover_all(config)

    # Register discovered plugins
    registry = get_plugin_registry()
    for plugin in plugins:
        await registry.register_plugin(plugin)
"""

import importlib
import importlib.metadata
import importlib.util
import sys
from pathlib import Path
from typing import Any

from ..logger import get_logger
from .base import PluginInterface, PluginLoadError
from .registry import get_plugin_registry

logger = get_logger(__name__)


class PluginDiscovery:
    """
    Plugin discovery coordinator.

    Handles automatic discovery of plugins through various mechanisms.
    """

    @staticmethod
    async def discover_all(config: dict[str, Any]) -> list[PluginInterface]:
        """
        Discover all plugins based on configuration.

        Combines entry point and directory discovery based on config settings.

        Args:
            config: Discovery configuration with settings for entry points
                   and directory scanning

        Returns:
            List of discovered plugin instances

        Example config:
            {
                "entry_point_group": "mcp_game.plugins",
                "directory_scan": {
                    "enabled": True,
                    "paths": ["plugins", "~/.mcp_game/plugins"],
                    "pattern": "*_plugin.py"
                },
                "auto_discover": True
            }
        """
        plugins = []

        # Entry point discovery
        if "entry_point_group" in config:
            try:
                entry_plugins = await PluginDiscovery.discover_from_entry_points(
                    config["entry_point_group"]
                )
                plugins.extend(entry_plugins)
                logger.info(f"Discovered {len(entry_plugins)} plugins from entry points")
            except Exception as e:
                logger.error(f"Entry point discovery failed: {e}")

        # Directory scanning
        dir_config = config.get("directory_scan", {})
        if dir_config.get("enabled", False):
            for path_str in dir_config.get("paths", []):
                try:
                    path = Path(path_str).expanduser().resolve()
                    if path.exists():
                        pattern = dir_config.get("pattern", "*_plugin.py")
                        dir_plugins = await PluginDiscovery.discover_from_directory(path, pattern)
                        plugins.extend(dir_plugins)
                        logger.info(f"Discovered {len(dir_plugins)} plugins from {path}")
                    else:
                        logger.debug(f"Plugin directory not found: {path}")
                except Exception as e:
                    logger.error(f"Directory discovery failed for {path_str}: {e}")

        logger.info(f"Total plugins discovered: {len(plugins)}")
        return plugins

    @staticmethod
    async def discover_from_entry_points(
        group: str = "mcp_game.plugins",
    ) -> list[PluginInterface]:
        """
        Discover plugins from entry points.

        Looks for entry points defined in pyproject.toml:

        [project.entry-points."mcp_game.plugins"]
        my_plugin = "my_package.plugin:MyPlugin"

        Args:
            group: Entry point group name

        Returns:
            List of plugin instances loaded from entry points
        """
        plugins = []

        try:
            # Get entry points
            entry_points = importlib.metadata.entry_points()

            # Handle different Python versions
            if hasattr(entry_points, "select"):
                # Python 3.10+
                group_eps = entry_points.select(group=group)
            else:
                # Python 3.9
                # Type ignore for compatibility with older Python versions
                group_eps = entry_points.get(group, [])  # type: ignore[arg-type]

            # Load each entry point
            for ep in group_eps:
                try:
                    # Load the entry point
                    plugin_class = ep.load()

                    # Instantiate if it's a class
                    if isinstance(plugin_class, type):
                        plugin = plugin_class()
                    else:
                        # Already instantiated or a factory function
                        plugin = plugin_class

                    # Validate it implements PluginInterface
                    if isinstance(plugin, PluginInterface):
                        plugins.append(plugin)
                        logger.info(f"Loaded plugin from entry point: {ep.name}")
                    else:
                        logger.warning(f"Entry point {ep.name} does not implement PluginInterface")

                except Exception as e:
                    logger.error(f"Failed to load plugin from entry point {ep.name}: {e}")

        except Exception as e:
            logger.error(f"Failed to discover entry points: {e}")

        return plugins

    @staticmethod
    async def discover_from_directory(
        path: Path, pattern: str = "*_plugin.py"
    ) -> list[PluginInterface]:
        """
        Discover plugins from a directory.

        Scans directory for Python files matching pattern, imports them,
        and looks for PluginInterface implementations.

        Args:
            path: Directory path to scan
            pattern: Glob pattern for plugin files (default: "*_plugin.py")

        Returns:
            List of plugin instances found in directory
        """
        plugins: list[Plugin] = []

        if not path.is_dir():
            logger.warning(f"Plugin directory not found: {path}")
            return plugins

        logger.debug(f"Scanning {path} for plugins matching {pattern}")

        # Find matching files
        for file_path in path.glob(pattern):
            if not file_path.is_file():
                continue

            try:
                # Load the module
                module = PluginDiscovery._load_module_from_file(file_path)

                # Find PluginInterface implementations
                for attr_name in dir(module):
                    try:
                        attr = getattr(module, attr_name)

                        # Check if it's a PluginInterface subclass (but not PluginInterface itself)
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, PluginInterface)
                            and attr != PluginInterface
                        ):
                            # Instantiate the plugin
                            plugin = attr()
                            plugins.append(plugin)
                            logger.info(f"Loaded plugin from file: {file_path.name} ({attr_name})")

                    except Exception as e:
                        logger.error(
                            f"Failed to instantiate plugin {attr_name} from {file_path.name}: {e}"
                        )

            except Exception as e:
                logger.error(f"Failed to load plugin file {file_path}: {e}")

        return plugins

    @staticmethod
    def _load_module_from_file(file_path: Path):
        """
        Load a Python module from a file path.

        Args:
            file_path: Path to Python file

        Returns:
            Loaded module

        Raises:
            PluginLoadError: If module loading fails
        """
        try:
            # Generate module name from file path
            module_name = f"_plugin_{file_path.stem}_{id(file_path)}"

            # Create module spec
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                raise PluginLoadError(f"Failed to create module spec for {file_path}")

            # Load the module
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            return module

        except Exception as e:
            raise PluginLoadError(f"Failed to load module from {file_path}: {e}") from e

    @staticmethod
    async def load_and_register_plugins(config: dict[str, Any], auto_enable: bool = True) -> int:
        """
        Discover, load, and register all plugins.

        This is a convenience method that combines discovery and registration.

        Args:
            config: Discovery configuration
            auto_enable: Whether to automatically enable plugins after registration

        Returns:
            Count of successfully registered plugins
        """
        registry = get_plugin_registry()

        # Discover plugins
        plugins = await PluginDiscovery.discover_all(config)

        # Register each plugin
        count = 0
        for plugin in plugins:
            try:
                await registry.register_plugin(plugin, auto_enable=auto_enable)
                count += 1
            except Exception as e:
                metadata = plugin.get_metadata()
                logger.error(f"Failed to register plugin {metadata.name}: {e}")

        logger.info(f"Successfully registered {count}/{len(plugins)} plugins")
        return count

    @staticmethod
    def validate_plugin_file(file_path: Path) -> bool:
        """
        Validate that a file is a valid Python plugin file.

        Performs basic checks without fully loading the plugin.

        Args:
            file_path: Path to plugin file

        Returns:
            True if file appears to be a valid plugin
        """
        if not file_path.exists():
            return False

        if not file_path.is_file():
            return False

        if not file_path.suffix == ".py":
            return False

        # Check for basic Python syntax
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Try to compile the code (syntax check)
            compile(content, str(file_path), "exec")

            # Check for PluginInterface import (heuristic)
            if "PluginInterface" in content:
                return True

        except Exception as e:
            logger.debug(f"Plugin validation failed for {file_path}: {e}")

        return False


# Convenience functions


async def discover_plugins(config: dict[str, Any]) -> list[PluginInterface]:
    """
    Discover plugins from config.

    Convenience wrapper for PluginDiscovery.discover_all().

    Args:
        config: Discovery configuration

    Returns:
        List of discovered plugins
    """
    return await PluginDiscovery.discover_all(config)


async def auto_discover_and_register(config: dict[str, Any], auto_enable: bool = True) -> int:
    """
    Auto-discover and register plugins.

    Convenience wrapper for PluginDiscovery.load_and_register_plugins().

    Args:
        config: Discovery configuration
        auto_enable: Whether to auto-enable plugins

    Returns:
        Count of registered plugins
    """
    return await PluginDiscovery.load_and_register_plugins(config, auto_enable)
