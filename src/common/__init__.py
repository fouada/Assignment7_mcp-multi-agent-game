"""Common utilities and shared components."""

from .config import Config, ServerConfig, get_config
from .config_loader import (
    ConfigLoader,
    GamesRegistryConfig,
    LeagueConfigFile,
    PlayerDefaults,
    RefereeDefaults,
    SystemConfig,
    get_config_loader,
)
from .exceptions import (
    ConnectionError,
    GameError,
    MCPError,
    ProtocolError,
    RegistrationError,
    TimeoutError,
    ValidationError,
)
from .lifecycle import (
    AgentLifecycleManager,
    LifecycleEvent,
    LifecycleRegistry,
    StateTransition,
    get_lifecycle_registry,
)
from .logger import get_logger, setup_logging
from .protocol import (
    PROTOCOL_VERSION,
    GameStatus,
    MessageType,
    PlayerStatus,
    create_message,
    validate_message,
)
from .repositories import (
    DataManager,
    MatchData,
    MatchRepository,
    PlayerHistoryData,
    PlayerHistoryEntry,
    PlayerHistoryRepository,
    RoundEntry,
    RoundsData,
    RoundsRepository,
    StandingsData,
    StandingsEntry,
    StandingsRepository,
    get_data_manager,
)

__all__ = [
    # Config
    "Config",
    "ServerConfig",
    "get_config",
    # Logger
    "get_logger",
    "setup_logging",
    # Exceptions
    "MCPError",
    "ConnectionError",
    "ProtocolError",
    "ValidationError",
    "TimeoutError",
    "GameError",
    "RegistrationError",
    # Protocol
    "PROTOCOL_VERSION",
    "MessageType",
    "GameStatus",
    "PlayerStatus",
    "create_message",
    "validate_message",
    # Repositories
    "DataManager",
    "get_data_manager",
    "StandingsRepository",
    "RoundsRepository",
    "MatchRepository",
    "PlayerHistoryRepository",
    "StandingsData",
    "StandingsEntry",
    "RoundsData",
    "RoundEntry",
    "MatchData",
    "PlayerHistoryData",
    "PlayerHistoryEntry",
    # Lifecycle
    "AgentLifecycleManager",
    "LifecycleEvent",
    "LifecycleRegistry",
    "StateTransition",
    "get_lifecycle_registry",
    # Config Loader
    "ConfigLoader",
    "get_config_loader",
    "SystemConfig",
    "LeagueConfigFile",
    "GamesRegistryConfig",
    "RefereeDefaults",
    "PlayerDefaults",
]
