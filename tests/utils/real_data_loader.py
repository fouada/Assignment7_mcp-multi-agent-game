"""
Real Data Loader for MIT-Level Testing
=======================================

Loads real data from the actual game system (data/ directory) to use in tests.
This ensures tests run against realistic scenarios and data patterns.
"""

import json
from pathlib import Path
from typing import Any


class RealDataLoader:
    """Load real data from the game system for testing."""

    def __init__(self, base_path: Path = None):
        """
        Initialize the data loader.

        Args:
            base_path: Base path to data directory. If None, auto-detects from project structure.
        """
        if base_path is None:
            # Auto-detect: go up from tests/utils to project root, then to data/
            base_path = Path(__file__).parent.parent.parent / "data"

        self.base_path = base_path
        self.leagues_path = base_path / "leagues"
        self.matches_path = base_path / "matches"
        self.players_path = base_path / "players"

    def load_league_standings(self, league_id: str = "league_2025_even_odd") -> dict[str, Any]:
        """
        Load real league standings data.

        Args:
            league_id: League identifier

        Returns:
            League standings data as dict
        """
        standings_file = self.leagues_path / league_id / "standings.json"
        if standings_file.exists():
            with open(standings_file) as f:
                return json.load(f)
        return self._create_default_standings(league_id)

    def load_league_rounds(self, league_id: str = "league_2025_even_odd") -> dict[str, Any]:
        """
        Load real league rounds data.

        Args:
            league_id: League identifier

        Returns:
            League rounds data as dict
        """
        rounds_file = self.leagues_path / league_id / "rounds.json"
        if rounds_file.exists():
            with open(rounds_file) as f:
                return json.load(f)
        return self._create_default_rounds(league_id)

    def load_player_history(self, player_id: str) -> dict[str, Any]:
        """
        Load real player history data.

        Args:
            player_id: Player identifier (e.g., "P01", "P02")

        Returns:
            Player history data as dict
        """
        history_file = self.players_path / player_id / "history.json"
        if history_file.exists():
            with open(history_file) as f:
                return json.load(f)
        return self._create_default_player_history(player_id)

    def get_all_players(self) -> list[str]:
        """
        Get list of all player IDs from data directory.

        Returns:
            List of player IDs
        """
        if not self.players_path.exists():
            return []

        players = []
        for player_dir in self.players_path.iterdir():
            if player_dir.is_dir() and (player_dir / "history.json").exists():
                players.append(player_dir.name)
        return sorted(players)

    def get_all_leagues(self) -> list[str]:
        """
        Get list of all league IDs from data directory.

        Returns:
            List of league IDs
        """
        if not self.leagues_path.exists():
            return []

        leagues = []
        for league_dir in self.leagues_path.iterdir():
            if league_dir.is_dir() and (league_dir / "standings.json").exists():
                leagues.append(league_dir.name)
        return sorted(leagues)

    def get_match_files(self, league_id: str = "league_2025_even_odd") -> list[Path]:
        """
        Get all match files for a league.

        Args:
            league_id: League identifier

        Returns:
            List of match file paths
        """
        match_dir = self.matches_path / league_id
        if not match_dir.exists():
            return []

        return sorted(match_dir.glob("*.json"))

    def load_match_data(self, match_file: Path) -> dict[str, Any]:
        """
        Load match data from file.

        Args:
            match_file: Path to match JSON file

        Returns:
            Match data as dict
        """
        if match_file.exists():
            with open(match_file) as f:
                return json.load(f)
        return {}

    def create_realistic_player_data(self, count: int = 10) -> list[dict[str, Any]]:
        """
        Create realistic player data based on actual patterns.

        Args:
            count: Number of players to create

        Returns:
            List of player data dicts
        """
        players = []
        for i in range(count):
            player_id = f"P{i + 1:02d}"
            players.append(
                {
                    "player_id": player_id,
                    "endpoint": f"http://localhost:{8000 + i}",
                    "game_types": ["even_odd"],
                    "strategy": self._get_realistic_strategy(i),
                    "stats": {"total_matches": 0, "wins": 0, "losses": 0, "draws": 0},
                }
            )
        return players

    def create_realistic_match_data(
        self, player1_id: str, player2_id: str, rounds: int = 5
    ) -> dict[str, Any]:
        """
        Create realistic match data based on actual patterns.

        Args:
            player1_id: First player ID
            player2_id: Second player ID
            rounds: Number of rounds

        Returns:
            Match data dict
        """
        import time

        match_id = f"match_{int(time.time() * 1000)}"

        return {
            "match_id": match_id,
            "game_type": "even_odd",
            "player1_id": player1_id,
            "player2_id": player2_id,
            "rounds": rounds,
            "status": "pending",
            "created_at": time.time(),
        }

    def load_all_real_data(self) -> dict[str, Any]:
        """
        Load all available real data from the system.

        Returns:
            Dict containing all real data
        """
        return {
            "leagues": {
                league_id: {
                    "standings": self.load_league_standings(league_id),
                    "rounds": self.load_league_rounds(league_id),
                }
                for league_id in self.get_all_leagues()
            },
            "players": {
                player_id: self.load_player_history(player_id)
                for player_id in self.get_all_players()
            },
            "player_ids": self.get_all_players(),
            "league_ids": self.get_all_leagues(),
        }

    def _create_default_standings(self, league_id: str) -> dict[str, Any]:
        """Create default standings structure."""
        return {
            "schema_version": "1.0.0",
            "league_id": league_id,
            "version": 0,
            "rounds_completed": 0,
            "standings": [],
        }

    def _create_default_rounds(self, league_id: str) -> dict[str, Any]:
        """Create default rounds structure."""
        return {
            "schema_version": "1.0.0",
            "league_id": league_id,
            "version": 0,
            "total_rounds": 0,
            "current_round": 0,
            "rounds": [],
        }

    def _create_default_player_history(self, player_id: str) -> dict[str, Any]:
        """Create default player history structure."""
        return {
            "player_id": player_id,
            "stats": {"total_matches": 0, "wins": 0, "losses": 0, "draws": 0},
            "matches": [],
        }

    def _get_realistic_strategy(self, index: int) -> str:
        """Get realistic strategy based on index."""
        strategies = [
            "random",
            "nash",
            "adaptive",
            "best_response",
            "fictitious_play",
            "regret_matching",
            "ucb",
            "thompson_sampling",
            "pattern_detection",
        ]
        return strategies[index % len(strategies)]


# Global instance for easy access
real_data_loader = RealDataLoader()


def get_real_data_loader() -> RealDataLoader:
    """Get the global real data loader instance."""
    return real_data_loader
