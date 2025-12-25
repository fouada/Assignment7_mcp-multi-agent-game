"""
Test Data Factories
===================

Provides comprehensive factories for generating test data including:
- Players, Referees, Matches, Games
- Protocol messages
- Game states
- Simulated scenarios
"""

import random
import uuid
from datetime import datetime
from typing import Any


class TestDataFactory:
    """
    Base factory class with common utilities.
    """

    @staticmethod
    def random_id(prefix: str = "") -> str:
        """Generate a random ID with optional prefix."""
        return f"{prefix}{uuid.uuid4().hex[:8]}" if prefix else uuid.uuid4().hex[:8]

    @staticmethod
    def random_port(start: int = 8000, end: int = 9000) -> int:
        """Generate a random port number."""
        return random.randint(start, end)

    @staticmethod
    def random_move() -> int:
        """Generate a random valid move (1-10)."""
        return random.randint(1, 10)

    @staticmethod
    def timestamp() -> str:
        """Generate ISO 8601 timestamp."""
        return datetime.utcnow().isoformat() + "Z"


class PlayerFactory(TestDataFactory):
    """
    Factory for creating test players with various configurations.
    """

    @classmethod
    def create(
        cls,
        player_id: str | None = None,
        name: str | None = None,
        strategy: str = "random",
        endpoint: str | None = None,
        port: int | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Create a player configuration.

        Args:
            player_id: Player ID (generated if not provided)
            name: Player name (defaults to player_id)
            strategy: Strategy type
            endpoint: Player endpoint URL
            port: Player port number
            **kwargs: Additional player attributes

        Returns:
            Player configuration dictionary
        """
        player_id = player_id or cls.random_id("P")
        port = port or cls.random_port()
        endpoint = endpoint or f"http://localhost:{port}"

        return {
            "player_id": player_id,
            "name": name or player_id,
            "strategy": strategy,
            "endpoint": endpoint,
            "port": port,
            "game_types": kwargs.get("game_types", ["even_odd"]),
            "stats": {
                "wins": kwargs.get("wins", 0),
                "losses": kwargs.get("losses", 0),
                "draws": kwargs.get("draws", 0),
                "points": kwargs.get("points", 0),
            },
            "created_at": cls.timestamp(),
            **{
                k: v
                for k, v in kwargs.items()
                if k not in ["wins", "losses", "draws", "points", "game_types"]
            },
        }

    @classmethod
    def create_batch(cls, count: int, **kwargs) -> list[dict[str, Any]]:
        """Create a batch of players."""
        return [cls.create(**kwargs) for _ in range(count)]

    @classmethod
    def create_with_strategy(cls, strategy: str, **kwargs) -> dict[str, Any]:
        """Create a player with specific strategy."""
        return cls.create(strategy=strategy, **kwargs)

    @classmethod
    def create_winner(cls, wins: int = 10, **kwargs) -> dict[str, Any]:
        """Create a player with winning record."""
        return cls.create(wins=wins, points=wins * 3, **kwargs)

    @classmethod
    def create_loser(cls, losses: int = 10, **kwargs) -> dict[str, Any]:
        """Create a player with losing record."""
        return cls.create(losses=losses, points=0, **kwargs)


class RefereeFactory(TestDataFactory):
    """
    Factory for creating test referees.
    """

    @classmethod
    def create(
        cls,
        referee_id: str | None = None,
        endpoint: str | None = None,
        port: int | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Create a referee configuration.

        Args:
            referee_id: Referee ID (generated if not provided)
            endpoint: Referee endpoint URL
            port: Referee port number
            **kwargs: Additional referee attributes

        Returns:
            Referee configuration dictionary
        """
        referee_id = referee_id or cls.random_id("R")
        port = port or cls.random_port()
        endpoint = endpoint or f"http://localhost:{port}"

        return {
            "referee_id": referee_id,
            "endpoint": endpoint,
            "port": port,
            "capacity": kwargs.get("capacity", 10),
            "active_matches": kwargs.get("active_matches", 0),
            "completed_matches": kwargs.get("completed_matches", 0),
            "created_at": cls.timestamp(),
            **{
                k: v
                for k, v in kwargs.items()
                if k not in ["capacity", "active_matches", "completed_matches"]
            },
        }

    @classmethod
    def create_batch(cls, count: int, **kwargs) -> list[dict[str, Any]]:
        """Create a batch of referees."""
        return [cls.create(**kwargs) for _ in range(count)]

    @classmethod
    def create_busy(cls, active_matches: int = 5, **kwargs) -> dict[str, Any]:
        """Create a busy referee."""
        return cls.create(active_matches=active_matches, **kwargs)


class MatchFactory(TestDataFactory):
    """
    Factory for creating test matches.
    """

    @classmethod
    def create(
        cls,
        match_id: str | None = None,
        player1_id: str | None = None,
        player2_id: str | None = None,
        referee_id: str | None = None,
        rounds: int = 5,
        status: str = "pending",
        **kwargs,
    ) -> dict[str, Any]:
        """
        Create a match configuration.

        Args:
            match_id: Match ID (generated if not provided)
            player1_id: First player ID
            player2_id: Second player ID
            referee_id: Referee ID
            rounds: Number of rounds
            status: Match status
            **kwargs: Additional match attributes

        Returns:
            Match configuration dictionary
        """
        match_id = match_id or cls.random_id("M")
        player1_id = player1_id or cls.random_id("P")
        player2_id = player2_id or cls.random_id("P")
        referee_id = referee_id or cls.random_id("R")

        return {
            "match_id": match_id,
            "player1_id": player1_id,
            "player2_id": player2_id,
            "referee_id": referee_id,
            "rounds": rounds,
            "status": status,
            "current_round": kwargs.get("current_round", 0),
            "scores": kwargs.get("scores", {player1_id: 0, player2_id: 0}),
            "winner_id": kwargs.get("winner_id"),
            "started_at": kwargs.get("started_at"),
            "completed_at": kwargs.get("completed_at"),
            "created_at": cls.timestamp(),
            **{
                k: v
                for k, v in kwargs.items()
                if k not in ["current_round", "scores", "winner_id", "started_at", "completed_at"]
            },
        }

    @classmethod
    def create_completed(cls, winner_id: str | None = None, **kwargs) -> dict[str, Any]:
        """Create a completed match."""
        match = cls.create(status="completed", **kwargs)
        match["winner_id"] = winner_id or match["player1_id"]
        match["completed_at"] = cls.timestamp()
        return match

    @classmethod
    def create_in_progress(cls, current_round: int = 3, **kwargs) -> dict[str, Any]:
        """Create a match in progress."""
        return cls.create(
            status="in_progress", current_round=current_round, started_at=cls.timestamp(), **kwargs
        )


class GameFactory(TestDataFactory):
    """
    Factory for creating test games.
    """

    @classmethod
    def create(
        cls,
        game_id: str | None = None,
        game_type: str = "even_odd",
        rounds: int = 5,
        odd_player: str | None = None,
        even_player: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Create a game configuration.

        Args:
            game_id: Game ID (generated if not provided)
            game_type: Type of game
            rounds: Number of rounds
            odd_player: Odd player ID
            even_player: Even player ID
            **kwargs: Additional game attributes

        Returns:
            Game configuration dictionary
        """
        game_id = game_id or cls.random_id("G")
        odd_player = odd_player or cls.random_id("P")
        even_player = even_player or cls.random_id("P")

        return {
            "game_id": game_id,
            "game_type": game_type,
            "rounds": rounds,
            "odd_player": odd_player,
            "even_player": even_player,
            "current_round": kwargs.get("current_round", 0),
            "scores": kwargs.get("scores", {odd_player: 0, even_player: 0}),
            "history": kwargs.get("history", []),
            "status": kwargs.get("status", "pending"),
            "created_at": cls.timestamp(),
            **{
                k: v
                for k, v in kwargs.items()
                if k not in ["current_round", "scores", "history", "status"]
            },
        }

    @classmethod
    def create_with_history(cls, rounds_played: int = 3, **kwargs) -> dict[str, Any]:
        """Create a game with simulated history."""
        game = cls.create(**kwargs)

        history = []
        for round_num in range(1, rounds_played + 1):
            move1 = cls.random_move()
            move2 = cls.random_move()
            total = move1 + move2
            is_odd = total % 2 == 1
            winner = game["odd_player"] if is_odd else game["even_player"]

            history.append(
                {"round": round_num, "move1": move1, "move2": move2, "sum": total, "winner": winner}
            )

            game["scores"][winner] += 1

        game["history"] = history
        game["current_round"] = rounds_played
        game["status"] = "in_progress" if rounds_played < game["rounds"] else "completed"

        return game


class MessageFactory(TestDataFactory):
    """
    Factory for creating protocol messages.
    """

    @classmethod
    def create_player_register(
        cls,
        player_id: str | None = None,
        endpoint: str | None = None,
        game_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a player registration message."""
        player_id = player_id or cls.random_id("P")
        return {
            "type": "player_register",
            "player_id": player_id,
            "endpoint": endpoint or f"http://localhost:{cls.random_port()}",
            "game_types": game_types or ["even_odd"],
            "timestamp": cls.timestamp(),
        }

    @classmethod
    def create_game_invite(
        cls, game_id: str | None = None, player_id: str | None = None, role: str = "odd"
    ) -> dict[str, Any]:
        """Create a game invitation message."""
        return {
            "type": "game_invite",
            "game_id": game_id or cls.random_id("G"),
            "player_id": player_id or cls.random_id("P"),
            "role": role,
            "game_type": "even_odd",
            "rounds": 5,
            "timestamp": cls.timestamp(),
        }

    @classmethod
    def create_move_request(
        cls, game_id: str | None = None, player_id: str | None = None, round_num: int = 1
    ) -> dict[str, Any]:
        """Create a move request message."""
        return {
            "type": "move_request",
            "game_id": game_id or cls.random_id("G"),
            "player_id": player_id or cls.random_id("P"),
            "round": round_num,
            "timestamp": cls.timestamp(),
        }

    @classmethod
    def create_move_response(
        cls, game_id: str | None = None, player_id: str | None = None, move: int | None = None
    ) -> dict[str, Any]:
        """Create a move response message."""
        return {
            "type": "move_response",
            "game_id": game_id or cls.random_id("G"),
            "player_id": player_id or cls.random_id("P"),
            "move": move if move is not None else cls.random_move(),
            "timestamp": cls.timestamp(),
        }

    @classmethod
    def create_round_result(
        cls, game_id: str | None = None, round_num: int = 1, winner_id: str | None = None
    ) -> dict[str, Any]:
        """Create a round result message."""
        move1 = cls.random_move()
        move2 = cls.random_move()
        return {
            "type": "round_result",
            "game_id": game_id or cls.random_id("G"),
            "round": round_num,
            "move1": move1,
            "move2": move2,
            "sum": move1 + move2,
            "winner_id": winner_id or cls.random_id("P"),
            "timestamp": cls.timestamp(),
        }

    @classmethod
    def create_game_over(
        cls,
        game_id: str | None = None,
        winner_id: str | None = None,
        final_scores: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Create a game over message."""
        return {
            "type": "game_over",
            "game_id": game_id or cls.random_id("G"),
            "winner_id": winner_id or cls.random_id("P"),
            "final_scores": final_scores or {"P1": 3, "P2": 2},
            "timestamp": cls.timestamp(),
        }

    @classmethod
    def create_match_result(
        cls, match_id: str | None = None, winner_id: str | None = None, loser_id: str | None = None
    ) -> dict[str, Any]:
        """Create a match result message."""
        return {
            "type": "match_result",
            "match_id": match_id or cls.random_id("M"),
            "winner_id": winner_id or cls.random_id("P"),
            "loser_id": loser_id or cls.random_id("P"),
            "timestamp": cls.timestamp(),
        }


class ScenarioFactory(TestDataFactory):
    """
    Factory for creating complete test scenarios.
    """

    @classmethod
    def create_simple_match_scenario(cls) -> dict[str, Any]:
        """Create a simple 2-player match scenario."""
        player1 = PlayerFactory.create(player_id="P1")
        player2 = PlayerFactory.create(player_id="P2")
        referee = RefereeFactory.create(referee_id="R1")
        match = MatchFactory.create(
            match_id="M1", player1_id="P1", player2_id="P2", referee_id="R1"
        )

        return {"players": [player1, player2], "referee": referee, "match": match}

    @classmethod
    def create_league_scenario(cls, num_players: int = 4) -> dict[str, Any]:
        """Create a league scenario with multiple players."""
        players = PlayerFactory.create_batch(num_players)
        referees = RefereeFactory.create_batch(2)

        # Generate round-robin matches
        matches = []
        for i, p1 in enumerate(players):
            for p2 in players[i + 1 :]:
                match = MatchFactory.create(
                    player1_id=p1["player_id"],
                    player2_id=p2["player_id"],
                    referee_id=random.choice(referees)["referee_id"],
                )
                matches.append(match)

        return {
            "players": players,
            "referees": referees,
            "matches": matches,
            "num_rounds": len(players) - 1,
        }

    @classmethod
    def create_stress_test_scenario(cls, num_players: int = 50) -> dict[str, Any]:
        """Create a large-scale stress test scenario."""
        players = PlayerFactory.create_batch(num_players)
        referees = RefereeFactory.create_batch(num_players // 5)  # 1 referee per 5 players

        return {
            "players": players,
            "referees": referees,
            "total_matches": (num_players * (num_players - 1)) // 2,
        }
