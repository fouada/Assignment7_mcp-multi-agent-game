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


# ============================================================================
# Timeouts (Section 2.7) - Response time limits per message type
# ============================================================================

class Timeouts:
    """
    Response timeout values in seconds (Table 5).
    
    If an agent doesn't respond within the timeout, the action fails.
    """
    
    REFEREE_REGISTER = 10.0      # Referee registration to league
    LEAGUE_REGISTER = 10.0       # Player registration to league
    GAME_JOIN_ACK = 5.0          # Confirm joining a game
    CHOOSE_PARITY = 30.0         # Choose odd/even (make a move)
    GAME_OVER = 5.0              # Receive game result
    MATCH_RESULT_REPORT = 10.0   # Report result to league
    LEAGUE_QUERY = 10.0          # Query league information
    DEFAULT = 10.0               # Default timeout for all other messages
    
    @classmethod
    def get_timeout(cls, message_type: str) -> float:
        """Get timeout for a specific message type."""
        timeout_map = {
            "REFEREE_REGISTER_REQUEST": cls.REFEREE_REGISTER,
            "REFEREE_REGISTER_RESPONSE": cls.REFEREE_REGISTER,
            "LEAGUE_REGISTER_REQUEST": cls.LEAGUE_REGISTER,
            "LEAGUE_REGISTER_RESPONSE": cls.LEAGUE_REGISTER,
            "GAME_JOIN_ACK": cls.GAME_JOIN_ACK,
            "GAME_INVITE_RESPONSE": cls.GAME_JOIN_ACK,
            "CHOOSE_PARITY": cls.CHOOSE_PARITY,
            "MOVE_REQUEST": cls.CHOOSE_PARITY,
            "MOVE_RESPONSE": cls.CHOOSE_PARITY,
            "GAME_OVER": cls.GAME_OVER,
            "GAME_END": cls.GAME_OVER,
            "MATCH_RESULT_REPORT": cls.MATCH_RESULT_REPORT,
            "LEAGUE_QUERY": cls.LEAGUE_QUERY,
        }
        return timeout_map.get(message_type, cls.DEFAULT)


def generate_auth_token(player_id: str, league_id: str) -> str:
    """
    Generate an authentication token for a registered player.
    
    Token format: tok_{player_id}_{hash}
    Example: tok_p01_abc123def456ghi789...
    
    Args:
        player_id: The player's ID (e.g., "P01")
        league_id: The league ID
        
    Returns:
        A unique authentication token
    """
    import hashlib
    import time
    
    # Create token from player_id, league_id, timestamp, and random UUID
    token_data = f"{player_id}:{league_id}:{time.time()}:{uuid.uuid4()}"
    token_hash = hashlib.sha256(token_data.encode()).hexdigest()[:24]
    # Format: tok_{player_id_lowercase}_{hash}
    return f"tok_{player_id.lower()}_{token_hash}"


class MessageType(str, Enum):
    """All supported message types in the protocol."""
    
    # Player Registration
    LEAGUE_REGISTER_REQUEST = "LEAGUE_REGISTER_REQUEST"
    LEAGUE_REGISTER_RESPONSE = "LEAGUE_REGISTER_RESPONSE"
    
    # Referee Registration (Step 1 of league flow)
    REFEREE_REGISTER_REQUEST = "REFEREE_REGISTER_REQUEST"
    REFEREE_REGISTER_RESPONSE = "REFEREE_REGISTER_RESPONSE"
    
    # Game lifecycle
    GAME_INVITE = "GAME_INVITE"
    GAME_INVITE_RESPONSE = "GAME_INVITE_RESPONSE"
    GAME_JOIN_ACK = "GAME_JOIN_ACK"  # Confirm joining game (5 sec timeout)
    GAME_START = "GAME_START"
    GAME_STATE = "GAME_STATE"
    GAME_END = "GAME_END"
    GAME_OVER = "GAME_OVER"  # Receive game result (5 sec timeout)
    
    # Moves
    MOVE_REQUEST = "MOVE_REQUEST"
    MOVE_RESPONSE = "MOVE_RESPONSE"
    MOVE_RESULT = "MOVE_RESULT"
    CHOOSE_PARITY = "CHOOSE_PARITY"  # Choose odd/even (30 sec timeout)
    
    # Round management
    ROUND_ANNOUNCEMENT = "ROUND_ANNOUNCEMENT"  # Step 4: Announce round with matches & referees
    ROUND_START = "ROUND_START"
    ROUND_END = "ROUND_END"
    ROUND_RESULT = "ROUND_RESULT"
    
    # League management
    STANDINGS_UPDATE = "STANDINGS_UPDATE"
    MATCH_SCHEDULE = "MATCH_SCHEDULE"
    MATCH_RESULT_REPORT = "MATCH_RESULT_REPORT"  # Report result to league (10 sec timeout)
    LEAGUE_QUERY = "LEAGUE_QUERY"  # Query league info (10 sec timeout)
    
    # System
    HEARTBEAT = "HEARTBEAT"
    HEARTBEAT_RESPONSE = "HEARTBEAT_RESPONSE"
    ERROR = "ERROR"
    ACK = "ACK"
    
    # Error types (Section 2.9)
    LEAGUE_ERROR = "LEAGUE_ERROR"  # League-level errors from league_manager
    GAME_ERROR = "GAME_ERROR"      # Game-level errors from referee


class GameStatus(str, Enum):
    """Game status values."""
    
    PENDING = "PENDING"
    WAITING_FOR_PLAYERS = "WAITING_FOR_PLAYERS"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"


class AgentState(str, Enum):
    """
    Agent lifecycle states (Section 2.8).
    
    State transitions:
    - INIT → REGISTERED (register)
    - INIT → SHUTDOWN (error)
    - REGISTERED → ACTIVE (league_start)
    - REGISTERED → SHUTDOWN (league_end)
    - ACTIVE → SUSPENDED (timeout)
    - SUSPENDED → ACTIVE (recover)
    - SUSPENDED → SHUTDOWN (max_fails)
    """
    
    INIT = "INIT"              # Agent started but not yet registered
    REGISTERED = "REGISTERED"  # Registered successfully, has auth_token
    ACTIVE = "ACTIVE"          # Active and participating in games
    SUSPENDED = "SUSPENDED"    # Temporarily suspended (not responding)
    SHUTDOWN = "SHUTDOWN"      # Agent has finished activity
    
    @classmethod
    def can_transition(cls, from_state: "AgentState", to_state: "AgentState") -> bool:
        """Check if a state transition is valid."""
        valid_transitions = {
            cls.INIT: {cls.REGISTERED, cls.SHUTDOWN},
            cls.REGISTERED: {cls.ACTIVE, cls.SHUTDOWN},
            cls.ACTIVE: {cls.SUSPENDED, cls.SHUTDOWN},
            cls.SUSPENDED: {cls.ACTIVE, cls.SHUTDOWN},
            cls.SHUTDOWN: set(),  # Terminal state
        }
        return to_state in valid_transitions.get(from_state, set())


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


class ErrorCode(str, Enum):
    """
    Standard error codes (Section 2.9).
    
    E0xx - Timeout errors
    E1xx - Registration errors
    E2xx - Game errors
    E3xx - Protocol errors
    """
    
    # Timeout errors
    E001 = "E001"  # TIMEOUT_ERROR - Response not received in time
    
    # Registration errors  
    E005 = "E005"  # PLAYER_NOT_REGISTERED
    E006 = "E006"  # REFEREE_NOT_REGISTERED
    E007 = "E007"  # ALREADY_REGISTERED
    E008 = "E008"  # REGISTRATION_CLOSED
    
    # Game errors
    E010 = "E010"  # INVALID_MOVE
    E011 = "E011"  # GAME_NOT_FOUND
    E012 = "E012"  # NOT_YOUR_TURN
    E013 = "E013"  # GAME_ALREADY_ENDED
    
    # Protocol errors
    E020 = "E020"  # INVALID_MESSAGE
    E021 = "E021"  # INVALID_TIMESTAMP
    E022 = "E022"  # INVALID_AUTH_TOKEN
    E023 = "E023"  # PROTOCOL_VERSION_MISMATCH


ERROR_NAMES = {
    ErrorCode.E001: "TIMEOUT_ERROR",
    ErrorCode.E005: "PLAYER_NOT_REGISTERED",
    ErrorCode.E006: "REFEREE_NOT_REGISTERED",
    ErrorCode.E007: "ALREADY_REGISTERED",
    ErrorCode.E008: "REGISTRATION_CLOSED",
    ErrorCode.E010: "INVALID_MOVE",
    ErrorCode.E011: "GAME_NOT_FOUND",
    ErrorCode.E012: "NOT_YOUR_TURN",
    ErrorCode.E013: "GAME_ALREADY_ENDED",
    ErrorCode.E020: "INVALID_MESSAGE",
    ErrorCode.E021: "INVALID_TIMESTAMP",
    ErrorCode.E022: "INVALID_AUTH_TOKEN",
    ErrorCode.E023: "PROTOCOL_VERSION_MISMATCH",
}


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
    auth_token: Optional[str] = None  # Required after registration
    
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
    
    def __init__(self, sender: str, league_id: str, auth_token: Optional[str] = None):
        self.sender = sender
        self.league_id = league_id
        self.auth_token = auth_token
    
    def set_auth_token(self, token: str) -> None:
        """Set the auth token for all subsequent messages."""
        self.auth_token = token
    
    def _base_fields(self, message_type: MessageType, **extra) -> Dict[str, Any]:
        """Get base fields for any message."""
        fields = {
            "protocol": PROTOCOL_VERSION,
            "message_type": message_type.value,
            "league_id": self.league_id,
            "conversation_id": str(uuid.uuid4()),
            "sender": self.sender,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **extra
        }
        # Include auth_token if set (required after registration)
        if self.auth_token:
            fields["auth_token"] = self.auth_token
        return fields
    
    def register_request(
        self,
        display_name: str,
        version: str = "1.0.0",
        endpoint: str = "",
    ) -> Dict[str, Any]:
        """Create a player registration request message."""
        return {
            **self._base_fields(MessageType.LEAGUE_REGISTER_REQUEST),
            "player_meta": {
                "display_name": display_name,
                "version": version,
                "game_types": ["even_odd"],
                "contact_endpoint": endpoint,
            }
        }
    
    def referee_register_request(
        self,
        referee_id: str,
        endpoint: str,
        version: str = "1.0.0",
    ) -> Dict[str, Any]:
        """Create a referee registration request message (Step 1 of league flow)."""
        return {
            **self._base_fields(MessageType.REFEREE_REGISTER_REQUEST),
            "referee_meta": {
                "referee_id": referee_id,
                "version": version,
                "contact_endpoint": endpoint,
            }
        }
    
    def referee_register_response(
        self,
        status: str,
        referee_id: str,
        reason: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a referee registration response message."""
        msg = {
            **self._base_fields(MessageType.REFEREE_REGISTER_RESPONSE),
            "status": status,
            "referee_id": referee_id,
        }
        if reason:
            msg["reason"] = reason
        if auth_token:
            msg["auth_token"] = auth_token
        return msg
    
    def register_response(
        self,
        status: str,
        player_id: str,
        reason: Optional[str] = None,
        conversation_id: str = None,
        auth_token: Optional[str] = None,
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
        if auth_token:
            msg["auth_token"] = auth_token
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
    
    def round_announcement(
        self,
        round_number: int,
        matches: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Create a round announcement message (Step 4 of league flow).
        
        Each match in the list should include:
        - match_id: str
        - player1_id: str
        - player2_id: str
        - referee_id: str (assigned referee)
        """
        return {
            **self._base_fields(MessageType.ROUND_ANNOUNCEMENT),
            "round_number": round_number,
            "matches": matches,
            "total_matches": len(matches),
        }
    
    def standings_update(
        self,
        round_number: int,
        total_rounds: int,
        standings: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Create a standings update message (Step 6 of league flow).
        
        Published to all players after each round completes.
        
        Each standing entry should include:
        - rank: int
        - player_id: str
        - display_name: str
        - wins: int
        - losses: int
        - draws: int
        - points: int
        """
        return {
            **self._base_fields(MessageType.STANDINGS_UPDATE),
            "round_number": round_number,
            "total_rounds": total_rounds,
            "standings": standings,
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
        """Create a generic error message."""
        return {
            **self._base_fields(MessageType.ERROR),
            "error_code": error_code,
            "error_message": error_message,
            "recoverable": recoverable,
        }
    
    def league_error(
        self,
        error_code: str,
        error_name: str,
        error_description: str,
        context: Optional[Dict[str, Any]] = None,
        retryable: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a LEAGUE_ERROR message (Section 2.9.1).
        
        Sent by league_manager for league-level errors.
        """
        msg = {
            **self._base_fields(MessageType.LEAGUE_ERROR),
            "error_code": error_code,
            "error_name": error_name,
            "error_description": error_description,
            "retryable": retryable,
        }
        if context:
            msg["context"] = context
        return msg
    
    def game_error(
        self,
        error_code: str,
        error_name: str,
        error_description: str,
        match_id: str,
        player_id: str,
        game_state: str,
        retryable: bool = True,
        retry_count: int = 0,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Create a GAME_ERROR message (Section 2.9.2).
        
        Sent by referee for game-level errors.
        """
        return {
            **self._base_fields(MessageType.GAME_ERROR),
            "match_id": match_id,
            "player_id": player_id,
            "error_code": error_code,
            "error_name": error_name,
            "error_description": error_description,
            "game_state": game_state,
            "retryable": retryable,
            "retry_count": retry_count,
            "max_retries": max_retries,
        }

