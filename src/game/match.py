"""
Match Management
================

Higher-level match management for league games.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ..common.logger import get_logger
from .odd_even import GameResult, GameRole, OddEvenGame

logger = get_logger(__name__)


class MatchState(Enum):
    """Match state."""

    SCHEDULED = "scheduled"
    INVITATIONS_SENT = "invitations_sent"
    PLAYERS_READY = "players_ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class MatchPlayer:
    """Player in a match."""

    player_id: str
    endpoint: str
    display_name: str = ""
    ready: bool = False
    connected: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "display_name": self.display_name,
            "ready": self.ready,
            "connected": self.connected,
        }


@dataclass
class Match:
    """
    Represents a match between two players.

    A match contains a game and manages the match lifecycle:
    1. Schedule match
    2. Send invitations
    3. Wait for players to be ready
    4. Play the game
    5. Record results
    """

    match_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    round_id: int = 1
    league_id: str = ""

    # Assigned referee (Step 4: Round Announcement)
    referee_id: str | None = None

    # Players
    player1: MatchPlayer | None = None
    player2: MatchPlayer | None = None

    # Game
    game: OddEvenGame | None = None

    # State
    state: MatchState = MatchState.SCHEDULED

    # Results
    winner_id: str | None = None
    final_score: dict[str, int] = field(default_factory=dict)
    result: GameResult | None = None

    # Timestamps
    scheduled_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def __post_init__(self):
        logger.bind(match_id=self.match_id, round_id=self.round_id)

    def set_players(
        self,
        player1_id: str,
        player1_endpoint: str,
        player2_id: str,
        player2_endpoint: str,
        player1_name: str = "",
        player2_name: str = "",
    ) -> None:
        """Set the players for this match."""
        self.player1 = MatchPlayer(
            player_id=player1_id,
            endpoint=player1_endpoint,
            display_name=player1_name or player1_id,
        )
        self.player2 = MatchPlayer(
            player_id=player2_id,
            endpoint=player2_endpoint,
            display_name=player2_name or player2_id,
        )

        logger.info(f"Match players set: {player1_id} vs {player2_id}")

    def create_game(
        self,
        total_rounds: int = 5,
        player1_role: GameRole = GameRole.ODD,
    ) -> OddEvenGame:
        """Create the game for this match."""
        if not self.player1 or not self.player2:
            raise ValueError("Players must be set before creating game")

        self.game = OddEvenGame(
            game_id=f"{self.match_id}_game",
            player1_id=self.player1.player_id,
            player2_id=self.player2.player_id,
            player1_role=player1_role,
            total_rounds=total_rounds,
        )

        return self.game

    def mark_player_ready(self, player_id: str) -> bool:
        """
        Mark a player as ready.

        Returns True if both players are now ready.
        """
        if self.player1 and self.player1.player_id == player_id:
            self.player1.ready = True
        elif self.player2 and self.player2.player_id == player_id:
            self.player2.ready = True
        else:
            raise ValueError(f"Unknown player: {player_id}")

        # Check if both ready
        both_ready = (
            self.player1 and self.player1.ready and
            self.player2 and self.player2.ready
        )

        if both_ready:
            self.state = MatchState.PLAYERS_READY

        return both_ready

    def start(self) -> None:
        """Start the match."""
        if self.state != MatchState.PLAYERS_READY:
            raise ValueError(f"Cannot start match in state: {self.state.value}")

        if not self.game:
            self.create_game()

        self.game.start()
        self.state = MatchState.IN_PROGRESS
        self.started_at = datetime.utcnow()

        logger.info("Match started")

    def complete(self, result: GameResult) -> None:
        """Complete the match with result."""
        self.result = result
        self.winner_id = result.winner_id
        self.final_score = {
            self.player1.player_id: result.player1_score,
            self.player2.player_id: result.player2_score,
        }
        self.state = MatchState.COMPLETED
        self.completed_at = datetime.utcnow()

        logger.info(
            "Match completed",
            winner=self.winner_id,
            score=self.final_score,
        )

    def cancel(self, reason: str = "cancelled") -> None:
        """Cancel the match."""
        self.state = MatchState.CANCELLED
        self.completed_at = datetime.utcnow()

        logger.info(f"Match cancelled: {reason}")

    def get_player_endpoint(self, player_id: str) -> str:
        """Get player's endpoint."""
        if self.player1 and self.player1.player_id == player_id:
            return self.player1.endpoint
        elif self.player2 and self.player2.player_id == player_id:
            return self.player2.endpoint
        else:
            raise ValueError(f"Unknown player: {player_id}")

    def get_opponent(self, player_id: str) -> MatchPlayer:
        """Get opponent player."""
        if self.player1 and self.player1.player_id == player_id:
            return self.player2
        elif self.player2 and self.player2.player_id == player_id:
            return self.player1
        else:
            raise ValueError(f"Unknown player: {player_id}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "match_id": self.match_id,
            "round_id": self.round_id,
            "league_id": self.league_id,
            "state": self.state.value,
            "player1": self.player1.to_dict() if self.player1 else None,
            "player2": self.player2.to_dict() if self.player2 else None,
            "winner_id": self.winner_id,
            "final_score": self.final_score,
            "scheduled_at": self.scheduled_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @property
    def is_complete(self) -> bool:
        """Check if match is complete."""
        return self.state == MatchState.COMPLETED

    @property
    def is_cancelled(self) -> bool:
        """Check if match is cancelled."""
        return self.state == MatchState.CANCELLED

    @property
    def is_active(self) -> bool:
        """Check if match is currently active."""
        return self.state == MatchState.IN_PROGRESS


class MatchScheduler:
    """
    Schedules matches for a league round.

    Creates pairings for round-robin tournament.
    """

    @staticmethod
    def create_round_robin_schedule(
        player_ids: list[str],
    ) -> list[list[tuple]]:
        """
        Create round-robin schedule.

        Each player plays against every other player once.

        Args:
            player_ids: List of player IDs

        Returns:
            List of rounds, each containing tuples of (player1, player2)
        """
        n = len(player_ids)

        if n < 2:
            return []

        # If odd number, add a "bye" player
        players = list(player_ids)
        if n % 2 == 1:
            players.append(None)  # Bye
            n += 1

        rounds = []

        # Round-robin algorithm
        for _round_num in range(n - 1):
            round_matches = []

            for i in range(n // 2):
                p1 = players[i]
                p2 = players[n - 1 - i]

                # Skip bye matches
                if p1 is not None and p2 is not None:
                    round_matches.append((p1, p2))

            rounds.append(round_matches)

            # Rotate players (keep first player fixed)
            players = [players[0]] + [players[-1]] + players[1:-1]

        return rounds

    @staticmethod
    def create_matches_for_round(
        league_id: str,
        round_id: int,
        pairings: list[tuple],
        player_endpoints: dict[str, str],
        player_names: dict[str, str] = None,
    ) -> list[Match]:
        """
        Create Match objects for a round.

        Args:
            league_id: League identifier
            round_id: Round number
            pairings: List of (player1_id, player2_id) tuples
            player_endpoints: Dict of player_id -> endpoint
            player_names: Optional dict of player_id -> display_name

        Returns:
            List of Match objects
        """
        player_names = player_names or {}
        matches = []

        for i, (p1_id, p2_id) in enumerate(pairings):
            match = Match(
                match_id=f"R{round_id}M{i + 1}",
                round_id=round_id,
                league_id=league_id,
            )

            match.set_players(
                player1_id=p1_id,
                player1_endpoint=player_endpoints.get(p1_id, ""),
                player2_id=p2_id,
                player2_endpoint=player_endpoints.get(p2_id, ""),
                player1_name=player_names.get(p1_id, ""),
                player2_name=player_names.get(p2_id, ""),
            )

            matches.append(match)

        return matches

