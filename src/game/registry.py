"""
Game Registry
=============

Registry for game types to support extensibility.

The registry allows adding new game types without modifying existing code.
Each game type must implement the GameInterface protocol.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, Callable
from datetime import datetime

from ..common.logger import get_logger

logger = get_logger(__name__)


@dataclass
class GameMove:
    """
    Generic game move structure.
    
    Base class for all game-specific moves.
    Allows uniform handling of moves across different game types.
    """
    
    player_id: str
    game_id: str
    round_number: int
    move_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "player_id": self.player_id,
            "game_id": self.game_id,
            "round_number": self.round_number,
            "move_data": self.move_data,
            "timestamp": self.timestamp.isoformat() + "Z",
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GameMove":
        """Create from dictionary."""
        return cls(
            player_id=data["player_id"],
            game_id=data["game_id"],
            round_number=data["round_number"],
            move_data=data.get("move_data", {}),
        )


@dataclass
class GameRoundResult:
    """
    Generic round result structure.
    
    Used to communicate results back to players regardless of game type.
    """
    
    game_id: str
    round_number: int
    winner_id: Optional[str]
    result_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "round_number": self.round_number,
            "winner_id": self.winner_id,
            **self.result_data,
        }


class GameInterface(ABC):
    """
    Abstract interface for game implementations.
    
    All game types must implement this interface to be registered
    in the game registry.
    """
    
    @property
    @abstractmethod
    def game_type(self) -> str:
        """Return the game type identifier (e.g., 'even_odd')."""
        pass
    
    @property
    @abstractmethod
    def min_players(self) -> int:
        """Minimum number of players required."""
        pass
    
    @property
    @abstractmethod
    def max_players(self) -> int:
        """Maximum number of players allowed."""
        pass
    
    @abstractmethod
    def start(self) -> None:
        """Start the game."""
        pass
    
    @abstractmethod
    def submit_move(self, player_id: str, move_data: Any) -> bool:
        """
        Submit a move for a player.
        
        Returns True if all expected moves have been received.
        """
        pass
    
    @abstractmethod
    def resolve_round(self) -> GameRoundResult:
        """Resolve the current round and return the result."""
        pass
    
    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """Get the current game state."""
        pass
    
    @property
    @abstractmethod
    def is_complete(self) -> bool:
        """Check if the game is complete."""
        pass
    
    @abstractmethod
    def get_result(self) -> Dict[str, Any]:
        """Get the final game result."""
        pass


@dataclass
class GameTypeInfo:
    """Information about a registered game type."""
    
    game_type: str
    display_name: str
    description: str
    min_players: int
    max_players: int
    factory: Callable[..., GameInterface]
    version: str = "1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "game_type": self.game_type,
            "display_name": self.display_name,
            "description": self.description,
            "min_players": self.min_players,
            "max_players": self.max_players,
            "version": self.version,
        }


class GameRegistry:
    """
    Registry for game types.
    
    Singleton pattern to ensure single registry instance.
    
    Usage:
        # Register a game type
        GameRegistry.register(
            game_type="even_odd",
            display_name="Even/Odd",
            description="Players choose numbers, sum determines winner",
            min_players=2,
            max_players=2,
            factory=OddEvenGame,
        )
        
        # Create a game instance
        game = GameRegistry.create_game("even_odd", player1_id="P01", player2_id="P02")
        
        # List available game types
        types = GameRegistry.list_game_types()
    """
    
    _instance: Optional["GameRegistry"] = None
    _games: Dict[str, GameTypeInfo] = {}
    
    def __new__(cls) -> "GameRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._games = {}
        return cls._instance
    
    @classmethod
    def register(
        cls,
        game_type: str,
        display_name: str,
        description: str,
        min_players: int,
        max_players: int,
        factory: Callable[..., GameInterface],
        version: str = "1.0.0",
    ) -> None:
        """
        Register a new game type.
        
        Args:
            game_type: Unique identifier for the game type
            display_name: Human-readable name
            description: Game description
            min_players: Minimum players required
            max_players: Maximum players allowed
            factory: Callable that creates game instances
            version: Game type version
        """
        if game_type in cls._games:
            logger.warning(f"Overwriting existing game type: {game_type}")
        
        cls._games[game_type] = GameTypeInfo(
            game_type=game_type,
            display_name=display_name,
            description=description,
            min_players=min_players,
            max_players=max_players,
            factory=factory,
            version=version,
        )
        
        logger.info(f"Registered game type: {game_type} ({display_name})")
    
    @classmethod
    def unregister(cls, game_type: str) -> bool:
        """
        Unregister a game type.
        
        Returns True if the game type was registered and removed.
        """
        if game_type in cls._games:
            del cls._games[game_type]
            logger.info(f"Unregistered game type: {game_type}")
            return True
        return False
    
    @classmethod
    def get_game_info(cls, game_type: str) -> Optional[GameTypeInfo]:
        """Get information about a game type."""
        return cls._games.get(game_type)
    
    @classmethod
    def is_registered(cls, game_type: str) -> bool:
        """Check if a game type is registered."""
        return game_type in cls._games
    
    @classmethod
    def list_game_types(cls) -> List[Dict[str, Any]]:
        """List all registered game types."""
        return [info.to_dict() for info in cls._games.values()]
    
    @classmethod
    def create_game(cls, game_type: str, **kwargs) -> GameInterface:
        """
        Create a game instance.
        
        Args:
            game_type: Type of game to create
            **kwargs: Arguments passed to the game factory
            
        Returns:
            New game instance
            
        Raises:
            ValueError: If game type is not registered
        """
        if game_type not in cls._games:
            raise ValueError(f"Unknown game type: {game_type}. "
                           f"Available types: {list(cls._games.keys())}")
        
        info = cls._games[game_type]
        game = info.factory(**kwargs)
        
        logger.debug(f"Created game instance: {game_type}")
        return game
    
    @classmethod
    def validate_players(cls, game_type: str, num_players: int) -> tuple[bool, Optional[str]]:
        """
        Validate player count for a game type.
        
        Returns (is_valid, error_message).
        """
        if game_type not in cls._games:
            return False, f"Unknown game type: {game_type}"
        
        info = cls._games[game_type]
        if num_players < info.min_players:
            return False, f"Not enough players. Minimum: {info.min_players}"
        if num_players > info.max_players:
            return False, f"Too many players. Maximum: {info.max_players}"
        
        return True, None
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered game types (for testing)."""
        cls._games.clear()


def register_default_games() -> None:
    """
    Register the default game types.
    
    Called at module import to ensure even_odd is always available.
    """
    from .odd_even import OddEvenGame
    
    if not GameRegistry.is_registered("even_odd"):
        GameRegistry.register(
            game_type="even_odd",
            display_name="Even/Odd",
            description="Two players choose numbers 1-5. Sum determines winner based on odd/even role.",
            min_players=2,
            max_players=2,
            factory=OddEvenGame,
            version="1.0.0",
        )


# Register default games on module import
try:
    register_default_games()
except ImportError:
    # OddEvenGame might not be importable during initial setup
    pass

