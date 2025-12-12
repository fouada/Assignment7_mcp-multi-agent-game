"""
Protocol Definitions
====================

MCP League Protocol v1 message schemas and validation.
All messages must conform to these schemas exactly.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from enum import Enum
import uuid
import json

# Protocol version - MUST be exactly this value
PROTOCOL_VERSION = "league.v1"


class MessageType(str, Enum):
    """All supported message types in the protocol."""
    
    # Registration
    LEAGUE_REGISTER_REQUEST = "LEAGUE_REGISTER_REQUEST"
    LEAGUE_REGISTER_RESPONSE = "LEAGUE_REGISTER_RESPONSE"
    
    # Game lifecycle
    GAME_INVITE = "GAME_INVITE"
    GAME_INVITE_RESPONSE = "GAME_INVITE_RESPONSE"
    GAME_START = "GAME_START"
    GAME_STATE = "GAME_STATE"
    GAME_END = "GAME_END"
    
    # Moves
    MOVE_REQUEST = "MOVE_REQUEST"
    MOVE_RESPONSE = "MOVE_RESPONSE"
    MOVE_RESULT = "MOVE_RESULT"
    
    # Round management
    ROUND_START = "ROUND_START"
    ROUND_END = "ROUND_END"
    ROUND_RESULT = "ROUND_RESULT"
    
    # League management
    STANDINGS_UPDATE = "STANDINGS_UPDATE"
    MATCH_SCHEDULE = "MATCH_SCHEDULE"
    
    # System
    HEARTBEAT = "HEARTBEAT"
    HEARTBEAT_RESPONSE = "HEARTBEAT_RESPONSE"
    ERROR = "ERROR"
    ACK = "ACK"


class GameStatus(str, Enum):
    """Game status values."""
    
    PENDING = "PENDING"
    WAITING_FOR_PLAYERS = "WAITING_FOR_PLAYERS"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"


class PlayerStatus(str, Enum):
    """Player status values."""
    
    REGISTERED = "REGISTERED"
    READY = "READY"
    IN_GAME = "IN_GAME"
    DISCONNECTED = "DISCONNECTED"
    DISQUALIFIED = "DISQUALIFIED"


class RegistrationStatus(str, Enum):
    """Registration response status."""
    
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class MoveValidity(str, Enum):
    """Move validation result."""
    
    VALID = "VALID"
    INVALID = "INVALID"
    TIMEOUT = "TIMEOUT"


class GameRole(str, Enum):
    """Player role in Odd/Even game."""
    
    ODD = "odd"
    EVEN = "even"


@dataclass
class BaseMessage:
    """Base class for all protocol messages."""
    
    protocol: str = PROTOCOL_VERSION
    message_type: MessageType = None
    league_id: str = ""
    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    
    # Optional fields
    round_id: Optional[int] = None
    match_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = {}
        for key, value in asdict(self).items():
            if value is not None:
                if isinstance(value, Enum):
                    data[key] = value.value
                else:
                    data[key] = value
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseMessage":
        """Create from dictionary."""
        # Convert string enums to enum types
        if "message_type" in data and isinstance(data["message_type"], str):
            data["message_type"] = MessageType(data["message_type"])
        return cls(**data)


# ============================================================================
# Registration Messages
# ============================================================================

@dataclass
class PlayerMeta:
    """Player metadata for registration."""
    
    display_name: str
    version: str = "1.0.0"
    game_types: List[str] = field(default_factory=lambda: ["even_odd"])
    contact_endpoint: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LeagueRegisterRequest(BaseMessage):
    """Player registration request."""
    
    message_type: MessageType = MessageType.LEAGUE_REGISTER_REQUEST
    player_meta: Optional[PlayerMeta] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        if self.player_meta:
            data["player_meta"] = self.player_meta.to_dict()
        return data


@dataclass
class LeagueRegisterResponse(BaseMessage):
    """League registration response."""
    
    message_type: MessageType = MessageType.LEAGUE_REGISTER_RESPONSE
    status: RegistrationStatus = RegistrationStatus.ACCEPTED
    player_id: Optional[str] = None
    reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["status"] = self.status.value
        return data


# ============================================================================
# Game Messages
# ============================================================================

@dataclass
class GameInvite(BaseMessage):
    """Game invitation from referee to player."""
    
    message_type: MessageType = MessageType.GAME_INVITE
    game_id: str = ""
    opponent_id: str = ""
    assigned_role: GameRole = GameRole.ODD  # odd or even
    rounds_to_play: int = 5


@dataclass
class GameInviteResponse(BaseMessage):
    """Player response to game invitation."""
    
    message_type: MessageType = MessageType.GAME_INVITE_RESPONSE
    game_id: str = ""
    accepted: bool = True
    reason: Optional[str] = None


@dataclass
class GameState:
    """Current state of a game."""
    
    game_id: str
    round_number: int
    total_rounds: int
    player1_id: str
    player2_id: str
    player1_score: int = 0
    player2_score: int = 0
    player1_role: GameRole = GameRole.ODD
    player2_role: GameRole = GameRole.EVEN
    status: GameStatus = GameStatus.IN_PROGRESS
    current_phase: str = "awaiting_moves"
    history: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["player1_role"] = self.player1_role.value
        data["player2_role"] = self.player2_role.value
        data["status"] = self.status.value
        return data


@dataclass
class GameStateMessage(BaseMessage):
    """Game state update message."""
    
    message_type: MessageType = MessageType.GAME_STATE
    game_state: Optional[GameState] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        if self.game_state:
            data["game_state"] = self.game_state.to_dict()
        return data


@dataclass
class GameStart(BaseMessage):
    """Game start notification."""
    
    message_type: MessageType = MessageType.GAME_START
    game_id: str = ""
    opponent_id: str = ""
    your_role: GameRole = GameRole.ODD
    rounds_to_play: int = 5


@dataclass
class GameEnd(BaseMessage):
    """Game end notification."""
    
    message_type: MessageType = MessageType.GAME_END
    game_id: str = ""
    winner_id: Optional[str] = None
    final_score: Dict[str, int] = field(default_factory=dict)
    reason: str = "completed"  # completed, forfeit, timeout, error


# ============================================================================
# Move Messages
# ============================================================================

@dataclass
class MoveRequest(BaseMessage):
    """Request for player to make a move."""
    
    message_type: MessageType = MessageType.MOVE_REQUEST
    game_id: str = ""
    round_number: int = 1
    your_role: GameRole = GameRole.ODD
    current_score: Dict[str, int] = field(default_factory=dict)
    time_limit_seconds: float = 30.0


@dataclass
class MoveResponse(BaseMessage):
    """Player's move response."""
    
    message_type: MessageType = MessageType.MOVE_RESPONSE
    game_id: str = ""
    round_number: int = 1
    move: int = 0  # 1-5 for odd/even game


@dataclass  
class MoveResult(BaseMessage):
    """Result of a round."""
    
    message_type: MessageType = MessageType.MOVE_RESULT
    game_id: str = ""
    round_number: int = 1
    your_move: int = 0
    opponent_move: int = 0
    sum_value: int = 0
    sum_is_odd: bool = True
    round_winner_id: Optional[str] = None
    your_new_score: int = 0
    opponent_new_score: int = 0


# ============================================================================
# Round Messages
# ============================================================================

@dataclass
class RoundStart(BaseMessage):
    """Round start notification."""
    
    message_type: MessageType = MessageType.ROUND_START
    round_number: int = 1
    matches: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class RoundResult(BaseMessage):
    """Round end results."""
    
    message_type: MessageType = MessageType.ROUND_RESULT
    round_number: int = 1
    results: List[Dict[str, Any]] = field(default_factory=list)


# ============================================================================
# System Messages
# ============================================================================

@dataclass
class Heartbeat(BaseMessage):
    """Heartbeat ping."""
    
    message_type: MessageType = MessageType.HEARTBEAT


@dataclass
class HeartbeatResponse(BaseMessage):
    """Heartbeat response."""
    
    message_type: MessageType = MessageType.HEARTBEAT_RESPONSE
    status: str = "alive"
    uptime_seconds: float = 0.0


@dataclass
class ErrorMessage(BaseMessage):
    """Error notification."""
    
    message_type: MessageType = MessageType.ERROR
    error_code: str = ""
    error_message: str = ""
    recoverable: bool = False


@dataclass
class Acknowledgement(BaseMessage):
    """Generic acknowledgement."""
    
    message_type: MessageType = MessageType.ACK
    original_message_id: str = ""
    success: bool = True


# ============================================================================
# Validation Functions
# ============================================================================

REQUIRED_FIELDS = {
    "protocol", "message_type", "league_id", "conversation_id", 
    "sender", "timestamp"
}


def validate_message(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate a message against the protocol.
    
    Returns:
        (is_valid, error_message)
    """
    # Check protocol version FIRST
    if data.get("protocol") != PROTOCOL_VERSION:
        return False, f"Invalid protocol version. Expected '{PROTOCOL_VERSION}', got '{data.get('protocol')}'"
    
    # Check required fields
    missing = REQUIRED_FIELDS - set(data.keys())
    if missing:
        return False, f"Missing required fields: {missing}"
    
    # Validate message type
    try:
        MessageType(data["message_type"])
    except ValueError:
        return False, f"Unknown message type: {data['message_type']}"
    
    # Validate timestamp format (should be ISO-8601)
    try:
        ts = data["timestamp"]
        if not ts.endswith("Z") and "+" not in ts:
            return False, "Timestamp should be in ISO-8601 format with timezone"
    except Exception:
        return False, "Invalid timestamp format"
    
    return True, None


def create_message(
    message_type: MessageType,
    sender: str,
    league_id: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a properly formatted protocol message.
    
    Args:
        message_type: Type of message
        sender: Sender identifier
        league_id: League identifier
        **kwargs: Additional message-specific fields
        
    Returns:
        Formatted message dictionary
    """
    message = {
        "protocol": PROTOCOL_VERSION,
        "message_type": message_type.value if isinstance(message_type, MessageType) else message_type,
        "league_id": league_id,
        "conversation_id": str(uuid.uuid4()),
        "sender": sender,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    
    # Add optional/additional fields
    message.update(kwargs)
    
    return message


# ============================================================================
# Message Factory
# ============================================================================

class MessageFactory:
    """Factory for creating protocol messages."""
    
    def __init__(self, sender: str, league_id: str):
        self.sender = sender
        self.league_id = league_id
    
    def _base_fields(self, message_type: MessageType, **extra) -> Dict[str, Any]:
        """Get base fields for any message."""
        return {
            "protocol": PROTOCOL_VERSION,
            "message_type": message_type.value,
            "league_id": self.league_id,
            "conversation_id": str(uuid.uuid4()),
            "sender": self.sender,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **extra
        }
    
    def register_request(
        self,
        display_name: str,
        version: str = "1.0.0",
        endpoint: str = "",
    ) -> Dict[str, Any]:
        """Create a registration request message."""
        return {
            **self._base_fields(MessageType.LEAGUE_REGISTER_REQUEST),
            "player_meta": {
                "display_name": display_name,
                "version": version,
                "game_types": ["even_odd"],
                "contact_endpoint": endpoint,
            }
        }
    
    def register_response(
        self,
        status: str,
        player_id: str,
        reason: Optional[str] = None,
        conversation_id: str = None,
    ) -> Dict[str, Any]:
        """Create a registration response message."""
        msg = {
            **self._base_fields(MessageType.LEAGUE_REGISTER_RESPONSE),
            "status": status,
            "player_id": player_id,
        }
        if reason:
            msg["reason"] = reason
        if conversation_id:
            msg["conversation_id"] = conversation_id
        return msg
    
    def game_invite(
        self,
        game_id: str,
        opponent_id: str,
        role: str,
        rounds: int = 5,
        match_id: str = None,
    ) -> Dict[str, Any]:
        """Create a game invitation message."""
        msg = {
            **self._base_fields(MessageType.GAME_INVITE),
            "game_id": game_id,
            "opponent_id": opponent_id,
            "assigned_role": role,
            "rounds_to_play": rounds,
        }
        if match_id:
            msg["match_id"] = match_id
        return msg
    
    def move_request(
        self,
        game_id: str,
        round_number: int,
        role: str,
        current_score: Dict[str, int],
        time_limit: float = 30.0,
    ) -> Dict[str, Any]:
        """Create a move request message."""
        return {
            **self._base_fields(MessageType.MOVE_REQUEST),
            "game_id": game_id,
            "round_number": round_number,
            "your_role": role,
            "current_score": current_score,
            "time_limit_seconds": time_limit,
        }
    
    def move_response(
        self,
        game_id: str,
        round_number: int,
        move: int,
    ) -> Dict[str, Any]:
        """Create a move response message."""
        return {
            **self._base_fields(MessageType.MOVE_RESPONSE),
            "game_id": game_id,
            "round_number": round_number,
            "move": move,
        }
    
    def move_result(
        self,
        game_id: str,
        round_number: int,
        your_move: int,
        opponent_move: int,
        winner_id: Optional[str],
        your_score: int,
        opponent_score: int,
    ) -> Dict[str, Any]:
        """Create a move result message."""
        sum_value = your_move + opponent_move
        return {
            **self._base_fields(MessageType.MOVE_RESULT),
            "game_id": game_id,
            "round_number": round_number,
            "your_move": your_move,
            "opponent_move": opponent_move,
            "sum_value": sum_value,
            "sum_is_odd": sum_value % 2 == 1,
            "round_winner_id": winner_id,
            "your_new_score": your_score,
            "opponent_new_score": opponent_score,
        }
    
    def game_end(
        self,
        game_id: str,
        winner_id: Optional[str],
        final_score: Dict[str, int],
        reason: str = "completed",
    ) -> Dict[str, Any]:
        """Create a game end message."""
        return {
            **self._base_fields(MessageType.GAME_END),
            "game_id": game_id,
            "winner_id": winner_id,
            "final_score": final_score,
            "reason": reason,
        }
    
    def heartbeat(self) -> Dict[str, Any]:
        """Create a heartbeat message."""
        return self._base_fields(MessageType.HEARTBEAT)
    
    def heartbeat_response(self, uptime: float = 0.0) -> Dict[str, Any]:
        """Create a heartbeat response."""
        return {
            **self._base_fields(MessageType.HEARTBEAT_RESPONSE),
            "status": "alive",
            "uptime_seconds": uptime,
        }
    
    def error(
        self,
        error_code: str,
        error_message: str,
        recoverable: bool = False,
    ) -> Dict[str, Any]:
        """Create an error message."""
        return {
            **self._base_fields(MessageType.ERROR),
            "error_code": error_code,
            "error_message": error_message,
            "recoverable": recoverable,
        }

