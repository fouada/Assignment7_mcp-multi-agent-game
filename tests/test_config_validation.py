"""
Tests for configuration loading and validation.
Covers config file loading, defaults, and error handling.
"""

import json
import pytest
from pathlib import Path
import tempfile

from src.common.config_loader import ConfigLoader, SystemConfig, LeagueConfigFile


class TestConfigLoaderBehavior:
    """Test ConfigLoader behavior with various scenarios."""

    def test_config_loader_load_games_registry(self):
        """Test loading games registry configuration."""
        loader = ConfigLoader()
        games = loader.load_games_registry()

        assert games is not None
        assert hasattr(games, 'games') or hasattr(games, 'default_game')

    def test_config_loader_load_referee_defaults(self):
        """Test loading referee default configuration."""
        loader = ConfigLoader()
        config = loader.load_referee_defaults()

        assert config is not None
        assert hasattr(config, 'move_timeout') or hasattr(config, 'game_timeout')

    def test_config_loader_load_player_defaults(self):
        """Test loading player default configuration."""
        loader = ConfigLoader()
        config = loader.load_player_defaults()

        assert config is not None
        assert hasattr(config, 'strategy') or hasattr(config, 'response_timeout')

    def test_config_loader_get_timeout_values(self):
        """Test getting various timeout values."""
        loader = ConfigLoader()

        # Test various timeout types
        timeout_types = ["connection", "move", "response", "registration"]

        for timeout_type in timeout_types:
            timeout = loader.get_timeout(timeout_type)
            assert isinstance(timeout, (int, float))
            assert timeout > 0


class TestSystemConfigStructure:
    """Test SystemConfig structure and defaults."""

    def test_system_config_has_version(self):
        """Test that SystemConfig has version attribute."""
        loader = ConfigLoader()
        config = loader.load_system()

        assert hasattr(config, 'version')
        assert config.version is not None

    def test_system_config_has_timeouts(self):
        """Test that SystemConfig has timeout configurations."""
        loader = ConfigLoader()
        config = loader.load_system()

        assert hasattr(config, 'timeouts')


class TestLeagueConfigStructure:
    """Test LeagueConfig structure."""

    def test_league_config_from_dict(self):
        """Test creating LeagueConfig from dictionary."""
        data = {
            "league_id": "test_league",
            "name": "Test League",
            "description": "A test league",
            "game_type": "even_odd",
            "format": "round_robin",
            "min_players": 2,
            "max_players": 10,
            "rounds_per_match": 5,
            "scoring": {"win": 3, "draw": 1, "loss": 0}
        }

        config = LeagueConfigFile.from_dict(data)

        assert config.league_id == "test_league"
        assert config.name == "Test League"
        assert config.game_type == "even_odd"
        assert config.min_players == 2
        assert config.max_players == 10

    def test_league_config_defaults(self):
        """Test LeagueConfig default values."""
        data = {
            "league_id": "minimal_league"
        }

        config = LeagueConfigFile.from_dict(data)

        # Should have defaults
        assert config.league_id == "minimal_league"
        assert isinstance(config.scoring, dict)

