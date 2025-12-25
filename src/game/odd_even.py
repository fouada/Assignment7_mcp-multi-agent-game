"""
Odd/Even Game Implementation
============================

Implementation of the Odd/Even game.

Rules:
- Two players each choose a number (1-5 fingers)
- Players reveal simultaneously
- Sum is calculated
- Player with "odd" role wins if sum is ODD
- Player with "even" role wins if sum is EVEN
- Can be played in rounds for best-of-N format
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ..common.exceptions import (
    GameError,
    InvalidGameStateError,
    InvalidMoveError,
)
from ..common.logger import get_logger

logger = get_logger(__name__)


class GameRole(Enum):
    """Player role in Odd/Even game."""

    ODD = "odd"
    EVEN = "even"


class GamePhase(Enum):
    """
    Current phase of the game.

    States:
    - WAITING_FOR_PLAYERS: Waiting for players to join/accept
    - COLLECTING_CHOICES: Collecting move choices from players
    - DRAWING_NUMBER: Processing moves and calculating sum
    - FINISHED: Game/round complete
    """

    WAITING_FOR_PLAYERS = "waiting_for_players"
    COLLECTING_CHOICES = "collecting_choices"
    DRAWING_NUMBER = "drawing_number"
    FINISHED = "finished"


@dataclass
class Move:
    """A player's move."""

    player_id: str
    value: int  # 1-5
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def validate(self, min_value: int = 1, max_value: int = 10) -> None:
        """
        Validate the move.

        Raises:
            InvalidMoveError: If move is invalid
        """
        if not isinstance(self.value, int):
            raise InvalidMoveError(
                self.value, "Move must be an integer", valid_range=(min_value, max_value)
            )

        if not min_value <= self.value <= max_value:
            raise InvalidMoveError(
                self.value,
                f"Move must be between {min_value} and {max_value}",
                valid_range=(min_value, max_value),
            )


@dataclass
class RoundResult:
    """Result of a single round."""

    round_number: int
    player1_move: int
    player2_move: int
    sum_value: int
    sum_is_odd: bool
    winner_id: str | None  # None for tie (shouldn't happen in odd/even)

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_number": self.round_number,
            "player1_move": self.player1_move,
            "player2_move": self.player2_move,
            "sum_value": self.sum_value,
            "sum_is_odd": self.sum_is_odd,
            "winner_id": self.winner_id,
        }


@dataclass
class GameResult:
    """Final result of a game."""

    game_id: str
    winner_id: str | None
    player1_score: int
    player2_score: int
    total_rounds: int
    reason: str = "completed"  # completed, forfeit, timeout, error
    rounds: list[RoundResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "game_id": self.game_id,
            "winner_id": self.winner_id,
            "player1_score": self.player1_score,
            "player2_score": self.player2_score,
            "total_rounds": self.total_rounds,
            "reason": self.reason,
            "rounds": [r.to_dict() for r in self.rounds],
        }


class OddEvenRules:
    """
    Rules engine for Odd/Even game.

    Stateless - can be shared across games.
    Numbers are drawn between 1-10 per specification.
    """

    def __init__(
        self,
        min_value: int = 1,
        max_value: int = 10,  # numbers 1-10
    ):
        self.min_value = min_value
        self.max_value = max_value

    def validate_move(self, move: Move) -> bool:
        """Validate a move according to rules."""
        try:
            move.validate(self.min_value, self.max_value)
            return True
        except InvalidMoveError:
            return False

    def calculate_result(
        self,
        move1: Move,
        move2: Move,
        player1_role: GameRole,
    ) -> tuple[int, bool, str | None]:
        """
        Calculate result of two moves.

        Args:
            move1: Player 1's move
            move2: Player 2's move
            player1_role: Player 1's assigned role (ODD or EVEN)

        Returns:
            (sum_value, is_odd, winner_player_id)
        """
        sum_value = move1.value + move2.value
        is_odd = sum_value % 2 == 1

        # Determine winner based on roles
        if player1_role == GameRole.ODD:
            # Player 1 wins if sum is odd, Player 2 wins if sum is even
            winner_id = move1.player_id if is_odd else move2.player_id
        else:
            # Player 1 wins if sum is even, Player 2 wins if sum is odd
            winner_id = move1.player_id if not is_odd else move2.player_id

        return sum_value, is_odd, winner_id

    def determine_game_winner(
        self,
        player1_score: int,
        player2_score: int,
        player1_id: str,
        player2_id: str,
    ) -> str | None:
        """Determine overall game winner."""
        if player1_score > player2_score:
            return player1_id
        elif player2_score > player1_score:
            return player2_id
        else:
            return None  # Tie


class OddEvenGame:
    """
    Complete Odd/Even game manager.

    Manages a full game between two players with multiple rounds.
    """

    def __init__(
        self,
        game_id: str | None = None,
        player1_id: str = "",
        player2_id: str = "",
        player1_role: GameRole = GameRole.ODD,
        total_rounds: int = 5,
        rules: OddEvenRules | None = None,
    ):
        self.game_id = game_id or str(uuid.uuid4())
        self.player1_id = player1_id
        self.player2_id = player2_id
        self.player1_role = player1_role
        self.player2_role = GameRole.EVEN if player1_role == GameRole.ODD else GameRole.ODD
        self.total_rounds = total_rounds
        self.rules = rules or OddEvenRules()

        # Game state
        self.current_round = 0
        self.phase = GamePhase.WAITING_FOR_PLAYERS
        self.player1_score = 0
        self.player2_score = 0

        # Current round moves
        self._current_moves: dict[str, Move] = {}

        # History
        self.round_history: list[RoundResult] = []

        # Timestamps
        self.created_at = datetime.utcnow()
        self.started_at: datetime | None = None
        self.ended_at: datetime | None = None

        logger.bind(game_id=self.game_id)

    def start(self) -> None:
        """Start the game - transitions from WAITING_FOR_PLAYERS to COLLECTING_CHOICES."""
        if self.phase != GamePhase.WAITING_FOR_PLAYERS:
            raise InvalidGameStateError("Game already started")

        self.started_at = datetime.utcnow()
        self.current_round = 1
        self.phase = GamePhase.COLLECTING_CHOICES

        logger.info(
            "Game started",
            player1=self.player1_id,
            player2=self.player2_id,
            rounds=self.total_rounds,
        )

    def submit_move(self, player_id: str, value: int) -> bool:
        """
        Submit a move for a player (Step 3: Collect Choices).

        Args:
            player_id: ID of the player making the move
            value: Move value (1-5)

        Returns:
            True if both players have submitted moves

        Raises:
            InvalidMoveError: If move is invalid
            InvalidGameStateError: If game is not in correct state
        """
        if self.phase != GamePhase.COLLECTING_CHOICES:
            raise InvalidGameStateError(f"Cannot submit move in phase: {self.phase.value}")

        if player_id not in (self.player1_id, self.player2_id):
            raise InvalidMoveError(value, f"Unknown player: {player_id}")

        if player_id in self._current_moves:
            raise InvalidMoveError(value, "Player has already submitted a move this round")

        # Create and validate move
        move = Move(player_id=player_id, value=value)
        move.validate(self.rules.min_value, self.rules.max_value)

        # Store move
        self._current_moves[player_id] = move

        logger.debug(f"Move submitted by {player_id}", value=value)

        # Check if both moves received - transition to DRAWING_NUMBER
        if len(self._current_moves) == 2:
            self.phase = GamePhase.DRAWING_NUMBER
            return True

        return False

    def resolve_round(self) -> RoundResult:
        """
        Resolve the current round (Steps 4 & 5: Draw Number and Determine Winner).

        Returns:
            RoundResult with round outcome

        Raises:
            InvalidGameStateError: If not all moves submitted
        """
        if self.phase != GamePhase.DRAWING_NUMBER:
            raise InvalidGameStateError(f"Cannot resolve round in phase: {self.phase.value}")

        move1 = self._current_moves[self.player1_id]
        move2 = self._current_moves[self.player2_id]

        # Step 4: Calculate sum (Draw Number)
        sum_value, is_odd, winner_id = self.rules.calculate_result(move1, move2, self.player1_role)

        # Step 5: Update scores (Determine Winner)
        if winner_id == self.player1_id:
            self.player1_score += 1
        elif winner_id == self.player2_id:
            self.player2_score += 1

        # Create result
        result = RoundResult(
            round_number=self.current_round,
            player1_move=move1.value,
            player2_move=move2.value,
            sum_value=sum_value,
            sum_is_odd=is_odd,
            winner_id=winner_id,
        )

        # Store in history
        self.round_history.append(result)

        logger.info(
            f"Round {self.current_round} resolved",
            sum=sum_value,
            is_odd=is_odd,
            winner=winner_id,
        )

        # Clear current moves
        self._current_moves.clear()

        # Check if game is complete
        if self.current_round >= self.total_rounds:
            self.phase = GamePhase.FINISHED
            self.ended_at = datetime.utcnow()
        else:
            # Move to next round - back to COLLECTING_CHOICES
            self.current_round += 1
            self.phase = GamePhase.COLLECTING_CHOICES

        return result

    def get_player_score(self, player_id: str) -> int:
        """Get the current score for a player."""
        if player_id == self.player1_id:
            return self.player1_score
        elif player_id == self.player2_id:
            return self.player2_score
        return 0

    def get_opponent_score(self, player_id: str) -> int:
        """Get the current score for a player's opponent."""
        if player_id == self.player1_id:
            return self.player2_score
        elif player_id == self.player2_id:
            return self.player1_score
        return 0

    def get_result(self) -> GameResult:
        """
        Get final game result (Step 6: Report Result).

        Returns:
            GameResult with final scores and winner

        Raises:
            InvalidGameStateError: If game not complete
        """
        if self.phase != GamePhase.FINISHED:
            raise InvalidGameStateError("Game is not complete")

        winner_id = self.rules.determine_game_winner(
            self.player1_score,
            self.player2_score,
            self.player1_id,
            self.player2_id,
        )

        return GameResult(
            game_id=self.game_id,
            winner_id=winner_id,
            player1_score=self.player1_score,
            player2_score=self.player2_score,
            total_rounds=self.total_rounds,
            rounds=self.round_history,
        )

    def forfeit(self, player_id: str) -> GameResult:
        """
        Handle player forfeit.

        Args:
            player_id: ID of forfeiting player

        Returns:
            GameResult with forfeit outcome
        """
        if player_id == self.player1_id:
            winner_id = self.player2_id
        elif player_id == self.player2_id:
            winner_id = self.player1_id
        else:
            raise InvalidMoveError(0, f"Unknown player: {player_id}")

        self.phase = GamePhase.FINISHED
        self.ended_at = datetime.utcnow()

        logger.info(f"Game forfeited by {player_id}")

        return GameResult(
            game_id=self.game_id,
            winner_id=winner_id,
            player1_score=self.player1_score,
            player2_score=self.player2_score,
            total_rounds=self.current_round,
            reason="forfeit",
            rounds=self.round_history,
        )

    def timeout(self, player_id: str) -> GameResult:
        """Handle player timeout."""
        self.phase = GamePhase.FINISHED
        self.ended_at = datetime.utcnow()

        if player_id == self.player1_id:
            winner_id = self.player2_id
        else:
            winner_id = self.player1_id

        logger.info(f"Game timeout for {player_id}")

        return GameResult(
            game_id=self.game_id,
            winner_id=winner_id,
            player1_score=self.player1_score,
            player2_score=self.player2_score,
            total_rounds=self.current_round,
            reason="timeout",
            rounds=self.round_history,
        )

    def get_state(self) -> dict[str, Any]:
        """Get current game state."""
        return {
            "game_id": self.game_id,
            "phase": self.phase.value,
            "current_round": self.current_round,
            "total_rounds": self.total_rounds,
            "player1_id": self.player1_id,
            "player2_id": self.player2_id,
            "player1_role": self.player1_role.value,
            "player2_role": self.player2_role.value,
            "player1_score": self.player1_score,
            "player2_score": self.player2_score,
            "moves_submitted": list(self._current_moves.keys()),
            "history": [r.to_dict() for r in self.round_history],
        }

    def get_player_role(self, player_id: str) -> GameRole:
        """Get player's assigned role."""
        if player_id == self.player1_id:
            return self.player1_role
        elif player_id == self.player2_id:
            return self.player2_role
        else:
            raise GameError(f"Unknown player: {player_id}")

    def get_opponent_id(self, player_id: str) -> str:
        """Get opponent's ID."""
        if player_id == self.player1_id:
            return self.player2_id
        elif player_id == self.player2_id:
            return self.player1_id
        else:
            raise GameError(f"Unknown player: {player_id}")

    @property
    def is_complete(self) -> bool:
        """Check if game is complete (FINISHED state)."""
        return self.phase == GamePhase.FINISHED

    @property
    def is_started(self) -> bool:
        """Check if game has started (not in WAITING_FOR_PLAYERS)."""
        return self.phase != GamePhase.WAITING_FOR_PLAYERS

    @property
    def awaiting_moves(self) -> bool:
        """Check if collecting choices from players."""
        return self.phase == GamePhase.COLLECTING_CHOICES
