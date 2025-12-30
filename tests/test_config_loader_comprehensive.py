"""
Comprehensive tests for config loader to increase coverage.

Tests error conditions, edge cases, and less-common paths.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.common.config_loader import (
    ConfigLoader,
    SystemConfig,
    LeagueConfigFile,
    GameTypeConfig,
)


class TestConfigLoaderErrorHandling:
    """Test ConfigLoader error handling."""

    def test_load_nonexistent_league_config(self):
        """Test loading a league config that doesn't exist."""
        loader = ConfigLoader()
        config = loader.load_league("nonexistent_league")
        assert config is None

    def test_load_invalid_json_system_config(self):
        """Test loading invalid JSON in system config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "system.json"
            config_path.write_text("invalid json {")
            
            loader = ConfigLoader(str(tmpdir))
            with pytest.raises(json.JSONDecodeError):
                loader.load_system()

    def test_load_invalid_json_league_config(self):
        """Test loading invalid JSON in league config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            leagues_dir = Path(tmpdir) / "leagues"
            leagues_dir.mkdir()
            league_path = leagues_dir / "test_league.json"
            league_path.write_text("invalid json {")
            
            loader = ConfigLoader(str(tmpdir))
            with pytest.raises(json.JSONDecodeError):
                loader.load_league("test_league")

    def test_load_missing_system_config_file(self):
        """Test loading when system.json doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ConfigLoader(str(tmpdir))
            with pytest.raises(FileNotFoundError):
                loader.load_system()

    def test_load_games_registry_missing_file(self):
        """Test loading games registry when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ConfigLoader(str(tmpdir))
            with pytest.raises(FileNotFoundError):
                loader.load_games_registry()

    def test_load_referee_defaults_missing_file(self):
        """Test loading referee defaults when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ConfigLoader(str(tmpdir))
            with pytest.raises(FileNotFoundError):
                loader.load_referee_defaults()

    def test_load_player_defaults_missing_file(self):
        """Test loading player defaults when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ConfigLoader(str(tmpdir))
            with pytest.raises(FileNotFoundError):
                loader.load_player_defaults()


class TestSystemConfigEdgeCases:
    """Test SystemConfig edge cases."""

    def test_system_config_from_dict_minimal(self):
        """Test SystemConfig with minimal required fields."""
        data = {
            "version": "1.0.0",
            "logging": {"level": "INFO"},
            "timeouts": {}
        }
        config = SystemConfig.from_dict(data)
        assert config.version == "1.0.0"
        assert config.logging["level"] == "INFO"

    def test_system_config_from_dict_with_all_fields(self):
        """Test SystemConfig with all possible fields."""
        data = {
            "version": "1.0.0",
            "logging": {
                "level": "DEBUG",
                "format": "json",
                "output": "file"
            },
            "timeouts": {
                "connection": 10,
                "response": 30,
                "move": 5
            },
            "retry": {
                "max_attempts": 3,
                "backoff": "exponential"
            },
            "observability": {
                "metrics": True,
                "tracing": True
            }
        }
        config = SystemConfig.from_dict(data)
        assert config.version == "1.0.0"
        assert config.logging["level"] == "DEBUG"
        assert config.timeouts["connection"] == 10
        assert config.retry["max_attempts"] == 3
        assert config.observability["metrics"] is True

    def test_system_config_defaults(self):
        """Test SystemConfig default values."""
        config = SystemConfig()
        assert config.version == "1.0.0"
        assert isinstance(config.logging, dict)
        assert isinstance(config.timeouts, dict)


class TestLeagueConfigFileEdgeCases:
    """Test LeagueConfigFile edge cases."""

    def test_league_config_from_dict_minimal(self):
        """Test LeagueConfigFile with minimal fields."""
        data = {
            "name": "Test League",
            "game_type": "odd_even",
            "max_players": 10
        }
        config = LeagueConfigFile.from_dict(data)
        assert config.name == "Test League"
        assert config.game_type == "odd_even"
        assert config.max_players == 10

    def test_league_config_from_dict_with_optional_fields(self):
        """Test LeagueConfigFile with all fields."""
        data = {
            "name": "Test League",
            "game_type": "odd_even",
            "max_players": 10,
            "rounds": 5,
            "rules": {
                "min_players": 2,
                "allow_draws": True
            },
            "scoring": {
                "win": 3,
                "draw": 1,
                "loss": 0
            },
            "registration": {
                "deadline": "2024-12-31",
                "auto_close": True
            }
        }
        config = LeagueConfigFile.from_dict(data)
        assert config.name == "Test League"
        assert config.rounds == 5
        assert config.rules["min_players"] == 2
        assert config.scoring["win"] == 3


class TestGameTypeConfigEdgeCases:
    """Test GameTypeConfig edge cases."""

    def test_game_type_config_from_dict_minimal(self):
        """Test GameTypeConfig with minimal fields."""
        data = {
            "name": "Odd Even",
            "id": "odd_even",
            "players": 2
        }
        config = GameTypeConfig.from_dict(data)
        assert config.name == "Odd Even"
        assert config.id == "odd_even"
        assert config.players == 2

    def test_game_type_config_from_dict_with_all_fields(self):
        """Test GameTypeConfig with all fields."""
        data = {
            "name": "Odd Even",
            "id": "odd_even",
            "players": 2,
            "description": "A number guessing game",
            "rules": {
                "min_value": 1,
                "max_value": 50
            },
            "timeouts": {
                "move": 10,
                "response": 5
            },
            "config": {
                "rounds": 3,
                "scoring": "points"
            }
        }
        config = GameTypeConfig.from_dict(data)
        assert config.name == "Odd Even"
        assert config.description == "A number guessing game"
        assert config.rules["min_value"] == 1
        assert config.timeouts["move"] == 10
        assert config.config["rounds"] == 3


class TestConfigLoaderCaching:
    """Test ConfigLoader caching behavior."""

    def test_system_config_cached(self):
        """Test that system config is cached."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "system.json"
            config_data = {
                "version": "1.0.0",
                "logging": {"level": "INFO"},
                "timeouts": {}
            }
            config_path.write_text(json.dumps(config_data))
            
            loader = ConfigLoader(str(tmpdir))
            config1 = loader.load_system()
            config2 = loader.load_system()
            
            # Should be the same object (cached)
            assert config1 is config2

    def test_clear_cache(self):
        """Test clearing the cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "system.json"
            config_data = {
                "version": "1.0.0",
                "logging": {"level": "INFO"},
                "timeouts": {}
            }
            config_path.write_text(json.dumps(config_data))
            
            loader = ConfigLoader(str(tmpdir))
            config1 = loader.load_system()
            loader.clear_cache()
            config2 = loader.load_system()
            
            # Should be different objects after cache clear
            assert config1 is not config2
            # But should have same values
            assert config1.version == config2.version


class TestConfigLoaderTimeouts:
    """Test timeout configuration."""

    def test_get_timeout_from_system_config(self):
        """Test getting timeout from system config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "system.json"
            config_data = {
                "version": "1.0.0",
                "logging": {"level": "INFO"},
                "timeouts": {
                    "connection": 15,
                    "response": 25,
                    "move": 10
                }
            }
            config_path.write_text(json.dumps(config_data))
            
            loader = ConfigLoader(str(tmpdir))
            
            connection_timeout = loader.get_timeout("connection")
            assert connection_timeout == 15
            
            response_timeout = loader.get_timeout("response")
            assert response_timeout == 25

    def test_get_timeout_with_default(self):
        """Test getting timeout with default value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "system.json"
            config_data = {
                "version": "1.0.0",
                "logging": {"level": "INFO"},
                "timeouts": {}
            }
            config_path.write_text(json.dumps(config_data))
            
            loader = ConfigLoader(str(tmpdir))
            
            # Should return default when timeout not configured
            timeout = loader.get_timeout("nonexistent", default=42)
            assert timeout == 42


class TestConfigLoaderIntegration:
    """Test ConfigLoader integration scenarios."""

    def test_load_all_configs(self):
        """Test loading all configuration types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create system config
            system_path = Path(tmpdir) / "system.json"
            system_path.write_text(json.dumps({
                "version": "1.0.0",
                "logging": {"level": "INFO"},
                "timeouts": {}
            }))
            
            # Create games registry
            games_path = Path(tmpdir) / "games" / "registry.json"
            games_path.parent.mkdir()
            games_path.write_text(json.dumps({
                "games": [
                    {
                        "name": "Odd Even",
                        "id": "odd_even",
                        "players": 2
                    }
                ]
            }))
            
            # Create referee defaults
            defaults_path = Path(tmpdir) / "defaults" / "referee.json"
            defaults_path.parent.mkdir()
            defaults_path.write_text(json.dumps({
                "timeout": 30,
                "max_concurrent_games": 5
            }))
            
            # Create player defaults
            player_defaults_path = Path(tmpdir) / "defaults" / "player.json"
            player_defaults_path.write_text(json.dumps({
                "strategy": "random",
                "timeout": 10
            }))
            
            # Create league config
            leagues_path = Path(tmpdir) / "leagues" / "test_league.json"
            leagues_path.parent.mkdir()
            leagues_path.write_text(json.dumps({
                "name": "Test League",
                "game_type": "odd_even",
                "max_players": 10
            }))
            
            loader = ConfigLoader(str(tmpdir))
            
            # Load all configs
            system = loader.load_system()
            games = loader.load_games_registry()
            referee = loader.load_referee_defaults()
            player = loader.load_player_defaults()
            league = loader.load_league("test_league")
            
            assert system is not None
            assert games is not None
            assert referee is not None
            assert player is not None
            assert league is not None
            assert league.name == "Test League"

