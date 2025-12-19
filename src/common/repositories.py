"""
Data Repositories
==================

Persistence layer for league data (Section 6).

File access permissions:
- config/*: Read-only for agents, write by system admin
- standings.json: Read by all, write by League Manager
- rounds.json: Read by all, write by League Manager
- matches/<match_id>.json: Read by all, write by Referee
- history.json: Read/write by owning Player only
- logs/*: Write by each agent (own log only)
"""

import json
import os
import fcntl
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar, Generic
import asyncio

from .logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class Repository(ABC, Generic[T]):
    """
    Abstract base repository.
    
    Provides common file-based persistence operations.
    """
    
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    @abstractmethod
    def save(self, data: T) -> None:
        """Save data to storage."""
        pass
    
    @abstractmethod
    def load(self) -> Optional[T]:
        """Load data from storage."""
        pass
    
    def _read_json(self, path: Path) -> Optional[Dict]:
        """Read JSON file with file locking."""
        if not path.exists():
            return None
        
        with open(path, 'r', encoding='utf-8') as f:
            # Acquire shared lock for reading
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                return json.load(f)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    
    def _write_json(self, path: Path, data: Dict) -> None:
        """Write JSON file with file locking."""
        # Write to temp file first, then rename (atomic)
        temp_path = path.with_suffix('.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            # Acquire exclusive lock for writing
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        temp_path.rename(path)


@dataclass
class StandingsEntry:
    """A single entry in the standings table."""
    
    rank: int
    player_id: str
    display_name: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    points: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StandingsData:
    """Full standings data structure."""
    
    league_id: str
    round_id: int
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    standings: List[StandingsEntry] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "league_id": self.league_id,
            "round_id": self.round_id,
            "timestamp": self.timestamp,
            "standings": [s.to_dict() for s in self.standings],
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "StandingsData":
        standings = [
            StandingsEntry(**s) for s in data.get("standings", [])
        ]
        return cls(
            league_id=data["league_id"],
            round_id=data["round_id"],
            timestamp=data.get("timestamp", ""),
            standings=standings,
        )


class StandingsRepository(Repository[StandingsData]):
    """
    Repository for league standings.
    
    File: data/leagues/<league_id>/standings.json
    Write access: League Manager only
    """
    
    def __init__(self, base_path: Path, league_id: str):
        super().__init__(base_path / "leagues" / league_id)
        self.league_id = league_id
        self.file_path = self.base_path / "standings.json"
    
    def save(self, data: StandingsData) -> None:
        """Save standings to file."""
        self._write_json(self.file_path, data.to_dict())
        logger.debug(f"Saved standings for round {data.round_id}")
    
    def load(self) -> Optional[StandingsData]:
        """Load standings from file."""
        data = self._read_json(self.file_path)
        if data:
            return StandingsData.from_dict(data)
        return None
    
    def get_player_rank(self, player_id: str) -> Optional[int]:
        """Get a player's current rank."""
        standings = self.load()
        if standings:
            for entry in standings.standings:
                if entry.player_id == player_id:
                    return entry.rank
        return None


@dataclass
class RoundEntry:
    """A single round's data."""
    
    round_id: int
    started_at: str
    completed_at: Optional[str] = None
    matches: List[Dict[str, Any]] = field(default_factory=list)
    results: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RoundsData:
    """Full rounds history data."""
    
    league_id: str
    total_rounds: int
    current_round: int
    rounds: List[RoundEntry] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "league_id": self.league_id,
            "total_rounds": self.total_rounds,
            "current_round": self.current_round,
            "rounds": [r.to_dict() for r in self.rounds],
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "RoundsData":
        rounds = [RoundEntry(**r) for r in data.get("rounds", [])]
        return cls(
            league_id=data["league_id"],
            total_rounds=data["total_rounds"],
            current_round=data["current_round"],
            rounds=rounds,
        )


class RoundsRepository(Repository[RoundsData]):
    """
    Repository for round history.
    
    File: data/leagues/<league_id>/rounds.json
    Write access: League Manager only
    """
    
    def __init__(self, base_path: Path, league_id: str):
        super().__init__(base_path / "leagues" / league_id)
        self.league_id = league_id
        self.file_path = self.base_path / "rounds.json"
    
    def save(self, data: RoundsData) -> None:
        """Save rounds history."""
        self._write_json(self.file_path, data.to_dict())
        logger.debug(f"Saved rounds history (current: {data.current_round})")
    
    def load(self) -> Optional[RoundsData]:
        """Load rounds history."""
        data = self._read_json(self.file_path)
        if data:
            return RoundsData.from_dict(data)
        return None
    
    def add_round(self, round_entry: RoundEntry) -> None:
        """Add a new round to history."""
        data = self.load()
        if data is None:
            data = RoundsData(
                league_id=self.league_id,
                total_rounds=0,
                current_round=0,
                rounds=[],
            )
        
        data.rounds.append(round_entry)
        data.current_round = round_entry.round_id
        self.save(data)
    
    def complete_round(self, round_id: int, results: List[Dict]) -> None:
        """Mark a round as complete with results."""
        data = self.load()
        if data:
            for round_entry in data.rounds:
                if round_entry.round_id == round_id:
                    round_entry.completed_at = datetime.utcnow().isoformat() + "Z"
                    round_entry.results = results
                    break
            self.save(data)


@dataclass
class MatchData:
    """Data for a single match."""
    
    match_id: str
    league_id: str
    round_id: int
    game_type: str = "even_odd"
    player_A_id: str = ""
    player_B_id: str = ""
    player_A_role: str = "odd"
    player_B_role: str = "even"
    status: str = "pending"  # pending, in_progress, completed, cancelled
    winner_id: Optional[str] = None
    player_A_score: int = 0
    player_B_score: int = 0
    rounds_played: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    round_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "MatchData":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class MatchRepository(Repository[MatchData]):
    """
    Repository for match data.
    
    File: data/matches/<league_id>/<match_id>.json
    Write access: Referee only
    """
    
    def __init__(self, base_path: Path, league_id: str):
        super().__init__(base_path / "matches" / league_id)
        self.league_id = league_id
    
    def _match_path(self, match_id: str) -> Path:
        return self.base_path / f"{match_id}.json"
    
    def save(self, data: MatchData) -> None:
        """Save match data."""
        self._write_json(self._match_path(data.match_id), data.to_dict())
        logger.debug(f"Saved match {data.match_id}")
    
    def load(self, match_id: str = "") -> Optional[MatchData]:
        """Load match data by ID."""
        path = self._match_path(match_id)
        data = self._read_json(path)
        if data:
            return MatchData.from_dict(data)
        return None
    
    def list_matches(self) -> List[str]:
        """List all match IDs."""
        if not self.base_path.exists():
            return []
        return [p.stem for p in self.base_path.glob("*.json")]
    
    def update_status(self, match_id: str, status: str) -> None:
        """Update match status."""
        data = self.load(match_id)
        if data:
            data.status = status
            if status == "in_progress" and not data.started_at:
                data.started_at = datetime.utcnow().isoformat() + "Z"
            elif status == "completed" and not data.completed_at:
                data.completed_at = datetime.utcnow().isoformat() + "Z"
            self.save(data)
    
    def record_result(
        self,
        match_id: str,
        winner_id: Optional[str],
        player_A_score: int,
        player_B_score: int,
        rounds_played: int,
    ) -> None:
        """Record match result."""
        data = self.load(match_id)
        if data:
            data.winner_id = winner_id
            data.player_A_score = player_A_score
            data.player_B_score = player_B_score
            data.rounds_played = rounds_played
            data.status = "completed"
            data.completed_at = datetime.utcnow().isoformat() + "Z"
            self.save(data)


@dataclass
class PlayerHistoryEntry:
    """A single game in player history."""
    
    match_id: str
    opponent_id: str
    opponent_name: str
    result: str  # "win", "loss", "draw"
    my_score: int
    opponent_score: int
    my_role: str
    played_at: str
    round_id: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PlayerHistoryData:
    """Player's game history."""
    
    player_id: str
    display_name: str
    total_games: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    games: List[PlayerHistoryEntry] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "player_id": self.player_id,
            "display_name": self.display_name,
            "total_games": self.total_games,
            "wins": self.wins,
            "losses": self.losses,
            "draws": self.draws,
            "games": [g.to_dict() for g in self.games],
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "PlayerHistoryData":
        games = [PlayerHistoryEntry(**g) for g in data.get("games", [])]
        return cls(
            player_id=data["player_id"],
            display_name=data.get("display_name", ""),
            total_games=data.get("total_games", 0),
            wins=data.get("wins", 0),
            losses=data.get("losses", 0),
            draws=data.get("draws", 0),
            games=games,
        )


class PlayerHistoryRepository(Repository[PlayerHistoryData]):
    """
    Repository for player game history.
    
    File: data/players/<player_id>/history.json
    Write access: Owning player only
    """
    
    def __init__(self, base_path: Path, player_id: str):
        super().__init__(base_path / "players" / player_id)
        self.player_id = player_id
        self.file_path = self.base_path / "history.json"
    
    def save(self, data: PlayerHistoryData) -> None:
        """Save player history."""
        self._write_json(self.file_path, data.to_dict())
        logger.debug(f"Saved history for player {self.player_id}")
    
    def load(self) -> Optional[PlayerHistoryData]:
        """Load player history."""
        data = self._read_json(self.file_path)
        if data:
            return PlayerHistoryData.from_dict(data)
        return None
    
    def add_game(self, entry: PlayerHistoryEntry) -> None:
        """Add a game to history."""
        data = self.load()
        if data is None:
            data = PlayerHistoryData(
                player_id=self.player_id,
                display_name="",
            )
        
        data.games.append(entry)
        data.total_games += 1
        
        if entry.result == "win":
            data.wins += 1
        elif entry.result == "loss":
            data.losses += 1
        else:
            data.draws += 1
        
        self.save(data)
    
    def get_recent_games(self, count: int = 10) -> List[PlayerHistoryEntry]:
        """Get most recent games."""
        data = self.load()
        if data:
            return data.games[-count:]
        return []
    
    def get_opponent_history(self, opponent_id: str) -> List[PlayerHistoryEntry]:
        """Get history against a specific opponent."""
        data = self.load()
        if data:
            return [g for g in data.games if g.opponent_id == opponent_id]
        return []


class DataManager:
    """
    Central data management class.
    
    Provides access to all repositories.
    """
    
    def __init__(self, base_path: str = "data"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Cache for repositories
        self._standings_repos: Dict[str, StandingsRepository] = {}
        self._rounds_repos: Dict[str, RoundsRepository] = {}
        self._match_repos: Dict[str, MatchRepository] = {}
        self._player_history_repos: Dict[str, PlayerHistoryRepository] = {}
    
    def standings(self, league_id: str) -> StandingsRepository:
        """Get standings repository for a league."""
        if league_id not in self._standings_repos:
            self._standings_repos[league_id] = StandingsRepository(
                self.base_path, league_id
            )
        return self._standings_repos[league_id]
    
    def rounds(self, league_id: str) -> RoundsRepository:
        """Get rounds repository for a league."""
        if league_id not in self._rounds_repos:
            self._rounds_repos[league_id] = RoundsRepository(
                self.base_path, league_id
            )
        return self._rounds_repos[league_id]
    
    def matches(self, league_id: str) -> MatchRepository:
        """Get match repository for a league."""
        if league_id not in self._match_repos:
            self._match_repos[league_id] = MatchRepository(
                self.base_path, league_id
            )
        return self._match_repos[league_id]
    
    def player_history(self, player_id: str) -> PlayerHistoryRepository:
        """Get player history repository."""
        if player_id not in self._player_history_repos:
            self._player_history_repos[player_id] = PlayerHistoryRepository(
                self.base_path, player_id
            )
        return self._player_history_repos[player_id]


# Global data manager instance
_data_manager: Optional[DataManager] = None


def get_data_manager(base_path: str = "data") -> DataManager:
    """Get global data manager instance."""
    global _data_manager
    if _data_manager is None:
        _data_manager = DataManager(base_path)
    return _data_manager

