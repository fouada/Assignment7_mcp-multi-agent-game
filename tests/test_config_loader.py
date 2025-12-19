"""
Tests for configuration loader (Section 7).
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path

from src.common.config_loader import (
    ConfigLoader,
    SystemConfig,
    TimeoutConfig,
    LeagueConfigFile,
    GamesRegistryConfig,
    GameTypeConfig,
    RefereeDefaults,
    PlayerDefaults,
)


class TestConfigLoader:
    """Test configuration loader."""
    
    def setup_method(self):
        """Setup temp config directory."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self._create_config_structure()
        self.loader = ConfigLoader(str(self.temp_dir))
    
    def teardown_method(self):
        """Cleanup."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_config_structure(self):
        """Create config directory structure."""
        # Create directories
        (self.temp_dir / "agents").mkdir()
        (self.temp_dir / "leagues").mkdir()
        (self.temp_dir / "games").mkdir()
        (self.temp_dir / "defaults").mkdir()
        
        # system.json
        with open(self.temp_dir / "system.json", 'w') as f:
            json.dump({
                "version": "2.0",
                "environment": "test",
                "debug": True,
                "timeouts": {
                    "referee_register": 15,
                    "default": 10,
                },
            }, f)
        
        # leagues/test_league.json
        with open(self.temp_dir / "leagues" / "test_league.json", 'w') as f:
            json.dump({
                "league_id": "test_league",
                "name": "Test League",
                "min_players": 4,
                "max_players": 8,
            }, f)
        
        # games/games_registry.json
        with open(self.temp_dir / "games" / "games_registry.json", 'w') as f:
            json.dump({
                "games": {
                    "even_odd": {
                        "display_name": "Even/Odd",
                        "min_players": 2,
                        "max_players": 2,
                    },
                },
                "default_game": "even_odd",
            }, f)
        
        # defaults/referee.json
        with open(self.temp_dir / "defaults" / "referee.json", 'w') as f:
            json.dump({
                "move_timeout": 45,
                "max_retries": 5,
            }, f)
        
        # defaults/player.json
        with open(self.temp_dir / "defaults" / "player.json", 'w') as f:
            json.dump({
                "strategy": "pattern",
                "response_timeout": 20,
            }, f)
    
    def test_load_system(self):
        """Test loading system configuration."""
        config = self.loader.load_system()
        
        assert config.version == "2.0"
        assert config.environment == "test"
        assert config.debug is True
        assert config.timeouts.referee_register == 15
        assert config.timeouts.default == 10
    
    def test_load_system_cached(self):
        """Test that system config is cached."""
        config1 = self.loader.load_system()
        config2 = self.loader.load_system()
        
        assert config1 is config2
    
    def test_load_league(self):
        """Test loading league configuration."""
        config = self.loader.load_league("test_league")
        
        assert config.league_id == "test_league"
        assert config.name == "Test League"
        assert config.min_players == 4
        assert config.max_players == 8
    
    def test_load_nonexistent_league(self):
        """Test loading nonexistent league returns defaults."""
        config = self.loader.load_league("nonexistent")
        
        assert config.league_id == "nonexistent"
        assert config.min_players == 2  # default
    
    def test_load_games_registry(self):
        """Test loading games registry."""
        config = self.loader.load_games_registry()
        
        assert "even_odd" in config.games
        assert config.games["even_odd"].display_name == "Even/Odd"
        assert config.default_game == "even_odd"
    
    def test_load_referee_defaults(self):
        """Test loading referee defaults."""
        config = self.loader.load_referee_defaults()
        
        assert config.move_timeout == 45
        assert config.max_retries == 5
    
    def test_load_player_defaults(self):
        """Test loading player defaults."""
        config = self.loader.load_player_defaults()
        
        assert config.strategy == "pattern"
        assert config.response_timeout == 20
    
    def test_get_timeout(self):
        """Test getting operation timeout."""
        timeout = self.loader.get_timeout("referee_register")
        assert timeout == 15
        
        default_timeout = self.loader.get_timeout("unknown_operation")
        assert default_timeout == 10  # default
    
    def test_clear_cache(self):
        """Test cache clearing."""
        config1 = self.loader.load_system()
        self.loader.clear_cache()
        config2 = self.loader.load_system()
        
        assert config1 is not config2


class TestSystemConfig:
    """Test SystemConfig dataclass."""
    
    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "version": "3.0",
            "environment": "production",
            "debug": False,
            "timeouts": {"default": 20},
        }
        
        config = SystemConfig.from_dict(data)
        
        assert config.version == "3.0"
        assert config.environment == "production"
        assert config.timeouts.default == 20
    
    def test_defaults(self):
        """Test default values."""
        config = SystemConfig()
        
        assert config.version == "2.0"
        assert config.debug is False


class TestLeagueConfigFile:
    """Test LeagueConfigFile dataclass."""
    
    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "league_id": "my_league",
            "name": "My League",
            "scoring": {"win": 5, "draw": 2, "loss": 0},
        }
        
        config = LeagueConfigFile.from_dict(data)
        
        assert config.league_id == "my_league"
        assert config.scoring["win"] == 5


class TestGameTypeConfig:
    """Test GameTypeConfig dataclass."""
    
    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "display_name": "Test Game",
            "min_players": 3,
            "rules": {"max_rounds": 10},
        }
        
        config = GameTypeConfig.from_dict("test_game", data)
        
        assert config.game_type == "test_game"
        assert config.display_name == "Test Game"
        assert config.rules["max_rounds"] == 10


class TestLoadFromActualConfig:
    """Test loading from actual config directory."""
    
    def test_load_from_project_config(self):
        """Test loading from project's config directory."""
        loader = ConfigLoader("config")
        
        # Load system config
        system = loader.load_system()
        assert system.version is not None
        
        # Load games registry
        games = loader.load_games_registry()
        assert "even_odd" in games.games
        
        # Load defaults
        referee = loader.load_referee_defaults()
        assert referee.move_timeout > 0
        
        player = loader.load_player_defaults()
        assert player.strategy in ["random", "pattern", "llm"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

