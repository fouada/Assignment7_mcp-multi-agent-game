"""
Configuration Loader
================================

Loads configuration from JSON files in the config/ directory.

File structure:
- config/system.json - System-wide settings
- config/agents/agents_config.json - Agent configurations
- config/leagues/<league_id>.json - League configurations
- config/games/games_registry.json - Game type registry
- config/defaults/{referee,player}.json - Default configs
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field

from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class TimeoutConfig:
    """Timeout configuration from system.json."""
    
    referee_register: int = 10
    league_register: int = 10
    game_join_ack: int = 5
    choose_parity: int = 30
    game_over: int = 5
    match_result_report: int = 10
    league_query: int = 10
    default: int = 10
    
    @classmethod
    def from_dict(cls, data: Dict) -> "TimeoutConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SystemConfig:
    """System configuration from system.json."""
    
    version: str = "2.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    data_path: str = "data"
    logs_path: str = "logs"
    timeouts: TimeoutConfig = field(default_factory=TimeoutConfig)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "SystemConfig":
        timeouts = TimeoutConfig.from_dict(data.get("timeouts", {}))
        return cls(
            version=data.get("version", "2.0"),
            environment=data.get("environment", "development"),
            debug=data.get("debug", False),
            log_level=data.get("log_level", "INFO"),
            data_path=data.get("data_path", "data"),
            logs_path=data.get("logs_path", "logs"),
            timeouts=timeouts,
        )


@dataclass
class LeagueConfigFile:
    """League configuration from leagues/<league_id>.json."""
    
    league_id: str
    name: str = ""
    description: str = ""
    game_type: str = "even_odd"
    format: str = "round_robin"
    min_players: int = 2
    max_players: int = 100
    rounds_per_match: int = 5
    scoring: Dict[str, int] = field(default_factory=lambda: {"win": 3, "draw": 1, "loss": 0})
    
    @classmethod
    def from_dict(cls, data: Dict) -> "LeagueConfigFile":
        return cls(
            league_id=data.get("league_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            game_type=data.get("game_type", "even_odd"),
            format=data.get("format", "round_robin"),
            min_players=data.get("min_players", 2),
            max_players=data.get("max_players", 100),
            rounds_per_match=data.get("rounds_per_match", 5),
            scoring=data.get("scoring", {"win": 3, "draw": 1, "loss": 0}),
        )


@dataclass
class GameTypeConfig:
    """Game type configuration from games_registry.json."""
    
    game_type: str
    display_name: str = ""
    description: str = ""
    min_players: int = 2
    max_players: int = 2
    version: str = "1.0.0"
    rules: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, game_type: str, data: Dict) -> "GameTypeConfig":
        return cls(
            game_type=game_type,
            display_name=data.get("display_name", ""),
            description=data.get("description", ""),
            min_players=data.get("min_players", 2),
            max_players=data.get("max_players", 2),
            version=data.get("version", "1.0.0"),
            rules=data.get("rules", {}),
        )


@dataclass
class GamesRegistryConfig:
    """Games registry configuration."""
    
    games: Dict[str, GameTypeConfig] = field(default_factory=dict)
    default_game: str = "even_odd"
    
    @classmethod
    def from_dict(cls, data: Dict) -> "GamesRegistryConfig":
        games = {}
        for game_type, game_data in data.get("games", {}).items():
            games[game_type] = GameTypeConfig.from_dict(game_type, game_data)
        return cls(
            games=games,
            default_game=data.get("default_game", "even_odd"),
        )


@dataclass
class RefereeDefaults:
    """Default referee configuration."""
    
    move_timeout: int = 30
    game_timeout: int = 300
    max_retries: int = 3
    heartbeat_interval: int = 10
    log_level: str = "INFO"
    
    @classmethod
    def from_dict(cls, data: Dict) -> "RefereeDefaults":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class PlayerDefaults:
    """Default player configuration."""
    
    strategy: str = "random"
    response_timeout: int = 30
    max_retries: int = 3
    heartbeat_interval: int = 10
    log_level: str = "INFO"
    llm: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "PlayerDefaults":
        return cls(
            strategy=data.get("strategy", "random"),
            response_timeout=data.get("response_timeout", 30),
            max_retries=data.get("max_retries", 3),
            heartbeat_interval=data.get("heartbeat_interval", 10),
            log_level=data.get("log_level", "INFO"),
            llm=data.get("llm", {}),
        )


class ConfigLoader:
    """
    Configuration loader for the SDK.
    
    Loads all configuration files from the config/ directory.
    
    Usage:
        loader = ConfigLoader("config")
        system = loader.load_system()
        league = loader.load_league("league_2025_even_odd")
        games = loader.load_games_registry()
    """
    
    def __init__(self, config_path: str = "config"):
        self.config_path = Path(config_path)
        self._cache: Dict[str, Any] = {}
    
    def _load_json(self, path: Path) -> Optional[Dict]:
        """Load JSON file, return None if not found."""
        if not path.exists():
            logger.warning(f"Config file not found: {path}")
            return None
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {path}: {e}")
            return None
    
    def load_system(self) -> SystemConfig:
        """Load system configuration."""
        if "system" in self._cache:
            return self._cache["system"]
        
        path = self.config_path / "system.json"
        data = self._load_json(path)
        
        config = SystemConfig.from_dict(data) if data else SystemConfig()
        self._cache["system"] = config
        return config
    
    def load_agents(self) -> Dict[str, Any]:
        """Load agents configuration."""
        if "agents" in self._cache:
            return self._cache["agents"]
        
        path = self.config_path / "agents" / "agents_config.json"
        data = self._load_json(path)
        
        self._cache["agents"] = data or {}
        return self._cache["agents"]
    
    def load_league(self, league_id: str) -> LeagueConfigFile:
        """Load league configuration."""
        cache_key = f"league_{league_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        path = self.config_path / "leagues" / f"{league_id}.json"
        data = self._load_json(path)
        
        if data:
            config = LeagueConfigFile.from_dict(data)
        else:
            config = LeagueConfigFile(league_id=league_id)
        
        self._cache[cache_key] = config
        return config
    
    def load_games_registry(self) -> GamesRegistryConfig:
        """Load games registry configuration."""
        if "games" in self._cache:
            return self._cache["games"]
        
        path = self.config_path / "games" / "games_registry.json"
        data = self._load_json(path)
        
        config = GamesRegistryConfig.from_dict(data) if data else GamesRegistryConfig()
        self._cache["games"] = config
        return config
    
    def load_referee_defaults(self) -> RefereeDefaults:
        """Load default referee configuration."""
        if "referee_defaults" in self._cache:
            return self._cache["referee_defaults"]
        
        path = self.config_path / "defaults" / "referee.json"
        data = self._load_json(path)
        
        config = RefereeDefaults.from_dict(data) if data else RefereeDefaults()
        self._cache["referee_defaults"] = config
        return config
    
    def load_player_defaults(self) -> PlayerDefaults:
        """Load default player configuration."""
        if "player_defaults" in self._cache:
            return self._cache["player_defaults"]
        
        path = self.config_path / "defaults" / "player.json"
        data = self._load_json(path)
        
        config = PlayerDefaults.from_dict(data) if data else PlayerDefaults()
        self._cache["player_defaults"] = config
        return config
    
    def clear_cache(self) -> None:
        """Clear configuration cache."""
        self._cache.clear()
    
    def get_timeout(self, operation: str) -> int:
        """Get timeout for a specific operation."""
        system = self.load_system()
        return getattr(system.timeouts, operation, system.timeouts.default)


# Global config loader instance
_loader: Optional[ConfigLoader] = None


def get_config_loader(config_path: str = "config") -> ConfigLoader:
    """Get global config loader instance."""
    global _loader
    if _loader is None:
        _loader = ConfigLoader(config_path)
    return _loader

