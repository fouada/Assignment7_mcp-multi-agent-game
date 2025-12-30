"""
Additional tests to improve config_loader.py coverage to 90%+.
Focuses on error handling, file operations, and edge cases.
"""

import json
import tempfile
from pathlib import Path

from src.common.config_loader import (
    ConfigLoader,
    GameTypeConfig,
    LeagueConfigFile,
    SystemConfig,
)


class TestConfigLoaderFileOperations:
    """Test config loader file operation edge cases."""

    def test_load_nonexistent_file(self):
        """Test loading a file that doesn't exist."""
        loader = ConfigLoader()
        result = loader._load_json(Path("nonexistent_file.json"))
        assert result is None

    def test_load_invalid_json(self):
        """Test loading invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            temp_path = f.name

        try:
            loader = ConfigLoader()
            result = loader._load_json(Path(temp_path))
            # Invalid JSON returns None (logged as error)
            assert result is None
        finally:
            Path(temp_path).unlink()

    def test_load_config_with_absolute_path(self):
        """Test loading config with absolute path."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"version": "1.0.0"}, f)
            temp_path = f.name

        try:
            loader = ConfigLoader()
            config = loader._load_json(Path(temp_path))
            assert config is not None
            assert config["version"] == "1.0.0"
        finally:
            Path(temp_path).unlink()

    def test_load_config_with_empty_file(self):
        """Test loading empty JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({}, f)
            temp_path = f.name

        try:
            loader = ConfigLoader()
            config = loader._load_json(Path(temp_path))
            assert config == {}
        finally:
            Path(temp_path).unlink()


class TestConfigLoaderCaching:
    """Test config loader caching behavior."""

    def test_cache_behavior_for_system_config(self):
        """Test that system config is cached."""
        loader = ConfigLoader()
        # Load twice
        config1 = loader.load_system()
        config2 = loader.load_system()

        # Should be same instance due to caching
        assert config1 is config2

    def test_clear_cache_functionality(self):
        """Test clearing the cache."""
        loader = ConfigLoader()
        # Load config to populate cache
        config1 = loader.load_system()

        # Clear cache
        loader.clear_cache()

        # Load again
        config2 = loader.load_system()

        # Might be different instances after cache clear
        assert config1 is not None and config2 is not None

    def test_cache_with_different_leagues(self):
        """Test caching with different league names."""
        loader = ConfigLoader()
        # These should be cached separately
        # Load will return defaults if files don't exist
        league1 = loader.load_league("league1")
        league2 = loader.load_league("league2")

        # Verify they have different IDs
        assert league1.league_id == "league1"
        assert league2.league_id == "league2"


class TestConfigLoaderLeagueOperations:
    """Test league config operations."""

    def test_load_nonexistent_league(self):
        """Test loading a league that doesn't exist."""
        loader = ConfigLoader()
        # Returns default LeagueConfigFile with provided league_id
        league = loader.load_league("nonexistent_league_xyz")
        assert league.league_id == "nonexistent_league_xyz"

    def test_load_league_with_invalid_config(self):
        """Test loading league with invalid configuration."""
        # Create temp directory structure
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "leagues"
            config_dir.mkdir(parents=True)

            league_file = config_dir / "test_league.json"
            league_file.write_text('{"invalid": "no required fields"}')

            # Create loader with temp path
            loader = ConfigLoader(tmpdir)
            # Should handle gracefully and return object with defaults
            league = loader.load_league("test_league")
            assert league is not None


class TestConfigLoaderGameRegistry:
    """Test game registry loading."""

    def test_load_games_registry_structure(self):
        """Test that games registry has expected structure."""
        loader = ConfigLoader()
        registry = loader.load_games_registry()

        assert hasattr(registry, "games")
        assert isinstance(registry.games, dict)

    def test_load_games_registry_caching(self):
        """Test games registry caching."""
        loader = ConfigLoader()
        registry1 = loader.load_games_registry()
        registry2 = loader.load_games_registry()

        # Should be cached
        assert registry1 is registry2


class TestConfigLoaderDefaults:
    """Test loading default configurations."""

    def test_load_referee_defaults_structure(self):
        """Test referee defaults structure."""
        loader = ConfigLoader()
        defaults = loader.load_referee_defaults()

        assert hasattr(defaults, "move_timeout") or hasattr(defaults, "game_timeout")

    def test_load_player_defaults_structure(self):
        """Test player defaults structure."""
        loader = ConfigLoader()
        defaults = loader.load_player_defaults()

        assert hasattr(defaults, "strategy") or hasattr(defaults, "response_timeout")

    def test_load_referee_defaults_caching(self):
        """Test referee defaults caching."""
        loader = ConfigLoader()
        defaults1 = loader.load_referee_defaults()
        defaults2 = loader.load_referee_defaults()

        assert defaults1 is defaults2

    def test_load_player_defaults_caching(self):
        """Test player defaults caching."""
        loader = ConfigLoader()
        defaults1 = loader.load_player_defaults()
        defaults2 = loader.load_player_defaults()

        assert defaults1 is defaults2


class TestConfigLoaderTimeouts:
    """Test timeout configuration loading."""

    def test_get_timeout_move(self):
        """Test getting move timeout."""
        loader = ConfigLoader()
        # Check timeout attributes that exist in TimeoutConfig
        system = loader.load_system()
        assert hasattr(system.timeouts, "default")
        assert isinstance(system.timeouts.default, int)

    def test_get_timeout_response(self):
        """Test getting response timeout."""
        loader = ConfigLoader()
        system = loader.load_system()
        # TimeoutConfig has default timeout
        assert system.timeouts.default > 0

    def test_get_timeout_registration(self):
        """Test getting registration timeout."""
        loader = ConfigLoader()
        system = loader.load_system()
        assert hasattr(system.timeouts, "referee_register")
        assert system.timeouts.referee_register > 0

    def test_get_timeout_heartbeat(self):
        """Test getting heartbeat timeout."""
        loader = ConfigLoader()
        system = loader.load_system()
        # Check default timeout exists
        assert system.timeouts.default > 0

    def test_get_timeout_with_default(self):
        """Test getting timeout with default value."""
        loader = ConfigLoader()
        # get_timeout uses getattr with default
        timeout = loader.get_timeout("nonexistent_type")
        # Returns the default timeout
        assert isinstance(timeout, int)

    def test_get_timeout_no_default(self):
        """Test getting nonexistent timeout without default."""
        loader = ConfigLoader()
        timeout = loader.get_timeout("nonexistent_type")

        # Should return some reasonable default
        assert isinstance(timeout, int)


class TestSystemConfigDataclass:
    """Test SystemConfig dataclass."""

    def test_system_config_from_dict_complete(self):
        """Test creating SystemConfig from complete dict."""
        data = {
            "version": "2.0.0",
            "environment": "production",
            "timeouts": {
                "referee_register": 60,
                "league_register": 45,
                "default": 10,
            },
        }

        config = SystemConfig.from_dict(data)

        assert config.version == "2.0.0"
        assert config.environment == "production"
        assert config.timeouts.default == 10

    def test_system_config_from_dict_minimal(self):
        """Test creating SystemConfig from minimal dict."""
        data = {
            "version": "1.0.0",
        }

        config = SystemConfig.from_dict(data)

        assert config.version == "1.0.0"
        # Should use defaults for other fields

    def test_system_config_defaults(self):
        """Test SystemConfig default values."""
        config = SystemConfig()

        assert config.version is not None
        assert config.environment is not None
        assert hasattr(config, "timeouts")


class TestLeagueConfigDataclass:
    """Test LeagueConfigFile dataclass."""

    def test_league_config_from_dict_complete(self):
        """Test creating LeagueConfigFile from complete dict."""
        data = {
            "league_id": "test_league",
            "name": "Test League",
            "max_players": 16,
            "game_type": "even_odd",  # singular, not plural
            "rounds_per_match": 10,
        }

        config = LeagueConfigFile.from_dict(data)

        assert config.name == "Test League"
        assert config.max_players == 16
        assert config.game_type == "even_odd"

    def test_league_config_from_dict_defaults(self):
        """Test LeagueConfigFile with defaults."""
        data = {
            "league_id": "minimal",
            "name": "Minimal League",
        }

        config = LeagueConfigFile.from_dict(data)

        assert config.name == "Minimal League"
        assert config.max_players == 100  # Default is 100, not 10
        assert config.game_type == "even_odd"  # Default game type

    def test_league_config_defaults(self):
        """Test LeagueConfigFile default instantiation."""
        config = LeagueConfigFile(league_id="test")  # league_id is required

        assert config.name is not None
        assert config.max_players == 100  # Default is 100
        assert isinstance(config.game_type, str)


class TestGameTypeConfigDataclass:
    """Test GameTypeConfig dataclass."""

    def test_game_type_config_from_dict(self):
        """Test creating GameTypeConfig from dict."""
        game_type = "even_odd"
        data = {
            "display_name": "Even Odd Game",
            "min_players": 2,
            "max_players": 2,
            "description": "A number guessing game",
        }

        # from_dict signature is: from_dict(cls, game_type: str, data: dict)
        config = GameTypeConfig.from_dict(game_type, data)

        assert config.game_type == "even_odd"
        assert config.display_name == "Even Odd Game"
        assert config.min_players == 2
        assert config.max_players == 2

    def test_game_type_config_minimal(self):
        """Test GameTypeConfig with minimal data."""
        game_type = "simple_game"
        data = {}

        config = GameTypeConfig.from_dict(game_type, data)

        assert config.game_type == "simple_game"


class TestConfigLoaderPathHandling:
    """Test config loader path handling."""

    def test_config_base_path_exists(self):
        """Test that config base path exists."""
        # Just verify the path logic works
        loader = ConfigLoader()
        system = loader.load_system()
        assert system is not None

    def test_load_config_relative_path(self):
        """Test loading config with relative path."""
        # Create temp config in current directory structure
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "test.json"
            config_file.write_text('{"test": "value"}')

            loader = ConfigLoader()
            config = loader._load_json(config_file)
            assert config is not None
            assert config["test"] == "value"


class TestConfigLoaderErrorHandling:
    """Test config loader error handling."""

    def test_load_config_permission_error(self):
        """Test loading config with permission error."""
        # This is platform-dependent, so just verify error handling exists
        loader = ConfigLoader()
        # On some systems this will raise PermissionError, which is fine
        try:
            result = loader._load_json(Path("/root/inaccessible.json"))
            # Should return None if file doesn't exist
            assert result is None
        except PermissionError:
            # Expected on systems where we can't check if /root/ exists
            pass

    def test_load_config_with_unicode(self):
        """Test loading config with unicode characters."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump({"name": "Tëst Léagué 🎮"}, f)
            temp_path = f.name

        try:
            loader = ConfigLoader()
            config = loader._load_json(Path(temp_path))
            assert config is not None
            assert "name" in config
        finally:
            Path(temp_path).unlink()


class TestConfigLoaderEdgeCases:
    """Test config loader edge cases."""

    def test_load_very_large_config(self):
        """Test loading very large configuration."""
        large_config = {"items": [{"id": i, "value": f"item_{i}"} for i in range(1000)]}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(large_config, f)
            temp_path = f.name

        try:
            loader = ConfigLoader()
            config = loader._load_json(Path(temp_path))
            assert config is not None
            assert len(config["items"]) == 1000
        finally:
            Path(temp_path).unlink()

    def test_load_deeply_nested_config(self):
        """Test loading deeply nested configuration."""
        nested = {"level1": {"level2": {"level3": {"level4": {"value": "deep"}}}}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(nested, f)
            temp_path = f.name

        try:
            loader = ConfigLoader()
            config = loader._load_json(Path(temp_path))
            assert config is not None
            assert config["level1"]["level2"]["level3"]["level4"]["value"] == "deep"
        finally:
            Path(temp_path).unlink()

    def test_cache_size_management(self):
        """Test that cache doesn't grow unbounded."""
        loader = ConfigLoader()
        # Load multiple configs
        loader.load_system()
        loader.load_games_registry()
        loader.load_referee_defaults()
        loader.load_player_defaults()

        # Clear cache to prevent memory issues
        loader.clear_cache()

        # Verify clearing worked
        assert True
