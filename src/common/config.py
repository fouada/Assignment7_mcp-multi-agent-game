"""
Configuration Management
========================

Centralized configuration for the MCP Game System.
Supports environment variables, config files, and defaults.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from pathlib import Path
import json

# Default ports following the specification
DEFAULT_PORTS = {
    "league_manager": 8000,
    "referee": 8001,
    "player_base": 8100,  # Players use 81XX range
}


@dataclass
class ServerConfig:
    """Configuration for an MCP server."""
    
    name: str
    host: str = "localhost"
    port: int = 8000
    endpoint: str = "/mcp"
    timeout: float = 30.0
    max_retries: int = 3
    heartbeat_interval: float = 10.0
    
    @property
    def url(self) -> str:
        """Get the full server URL."""
        return f"http://{self.host}:{self.port}{self.endpoint}"
    
    @property
    def base_url(self) -> str:
        """Get base URL without endpoint."""
        return f"http://{self.host}:{self.port}"


# Default LLM models for each provider
DEFAULT_LLM_MODELS = {
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4",
}


@dataclass
class LLMConfig:
    """
    Configuration for LLM integration.
    
    Supported providers:
    - anthropic: Claude models (claude-sonnet-4-20250514, claude-3-opus, etc.)
    - openai: GPT models (gpt-4, gpt-4-turbo, gpt-3.5-turbo, etc.)
    
    API keys are loaded from environment variables:
    - ANTHROPIC_API_KEY for Anthropic
    - OPENAI_API_KEY for OpenAI
    """
    
    provider: str = "anthropic"  # "anthropic" or "openai"
    model: Optional[str] = None  # Auto-selected based on provider if None
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1000
    timeout: float = 60.0
    
    def __post_init__(self):
        # Auto-select model based on provider if not specified
        if self.model is None:
            self.model = DEFAULT_LLM_MODELS.get(self.provider, "gpt-4")
        
        # Try to get API key from environment if not provided
        if self.api_key is None:
            if self.provider == "anthropic":
                self.api_key = os.getenv("ANTHROPIC_API_KEY")
            elif self.provider == "openai":
                self.api_key = os.getenv("OPENAI_API_KEY")


@dataclass
class GameConfig:
    """Configuration for game rules."""
    
    game_type: str = "even_odd"
    rounds_per_match: int = 5  # Best of N rounds
    move_timeout: float = 30.0  # Seconds to make a move
    min_value: int = 1  # Minimum finger value
    max_value: int = 5  # Maximum finger value


@dataclass 
class LeagueConfig:
    """Configuration for league management."""
    
    league_id: str = "league_2024_01"
    min_players: int = 2
    max_players: int = 100
    matches_per_round: int = 2  # Parallel matches
    round_robin: bool = True


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter_factor: float = 0.1


@dataclass
class Config:
    """Main configuration container."""
    
    # Server configs
    league_manager: ServerConfig = field(
        default_factory=lambda: ServerConfig(
            name="league_manager",
            port=DEFAULT_PORTS["league_manager"]
        )
    )
    referee: ServerConfig = field(
        default_factory=lambda: ServerConfig(
            name="referee", 
            port=DEFAULT_PORTS["referee"]
        )
    )
    
    # Player configs (will be populated dynamically)
    players: Dict[str, ServerConfig] = field(default_factory=dict)
    
    # Other configs
    llm: LLMConfig = field(default_factory=LLMConfig)
    game: GameConfig = field(default_factory=GameConfig)
    league: LeagueConfig = field(default_factory=LeagueConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # Debug mode
    debug: bool = False
    
    def add_player(self, player_id: str, port: Optional[int] = None) -> ServerConfig:
        """Add a player configuration."""
        if port is None:
            # Auto-assign port: 8101, 8102, etc.
            port = DEFAULT_PORTS["player_base"] + len(self.players) + 1
        
        player_config = ServerConfig(
            name=f"player_{player_id}",
            port=port
        )
        self.players[player_id] = player_config
        return player_config
    
    def get_player_config(self, player_id: str) -> Optional[ServerConfig]:
        """Get player configuration by ID."""
        return self.players.get(player_id)
    
    @classmethod
    def from_file(cls, path: str) -> "Config":
        """Load configuration from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """Create config from dictionary."""
        config = cls()
        
        if "league_manager" in data:
            config.league_manager = ServerConfig(**data["league_manager"])
        if "referee" in data:
            config.referee = ServerConfig(**data["referee"])
        if "players" in data:
            for pid, pdata in data["players"].items():
                config.players[pid] = ServerConfig(**pdata)
        if "llm" in data:
            config.llm = LLMConfig(**data["llm"])
        if "game" in data:
            config.game = GameConfig(**data["game"])
        if "league" in data:
            config.league = LeagueConfig(**data["league"])
        if "retry" in data:
            config.retry = RetryConfig(**data["retry"])
        if "log_level" in data:
            config.log_level = data["log_level"]
        if "debug" in data:
            config.debug = data["debug"]
            
        return config
    
    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return {
            "league_manager": {
                "name": self.league_manager.name,
                "host": self.league_manager.host,
                "port": self.league_manager.port,
                "endpoint": self.league_manager.endpoint,
            },
            "referee": {
                "name": self.referee.name,
                "host": self.referee.host,
                "port": self.referee.port,
                "endpoint": self.referee.endpoint,
            },
            "players": {
                pid: {
                    "name": pc.name,
                    "host": pc.host,
                    "port": pc.port,
                    "endpoint": pc.endpoint,
                }
                for pid, pc in self.players.items()
            },
            "game": {
                "game_type": self.game.game_type,
                "rounds_per_match": self.game.rounds_per_match,
            },
            "league": {
                "league_id": self.league.league_id,
            },
            "log_level": self.log_level,
            "debug": self.debug,
        }


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
        
        # Check for config file
        config_paths = [
            Path("config/servers.json"),
            Path("servers.json"),
            Path.home() / ".mcp_game" / "config.json",
        ]
        
        for path in config_paths:
            if path.exists():
                _config = Config.from_file(str(path))
                break
    
    return _config


def set_config(config: Config) -> None:
    """Set global configuration instance."""
    global _config
    _config = config

