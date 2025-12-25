"""
Mocking Framework for Testing
==============================

Provides comprehensive mocking utilities for all major components.
Includes simulated behavior, state management, and error injection.
"""

import asyncio
import random
from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, Mock


class MockMCPClient:
    """
    Mock MCP Client for testing agent communication.

    Features:
    - Simulates successful and failed calls
    - Tracks call history
    - Configurable delays
    - Error injection
    """

    def __init__(self, fail_rate: float = 0.0, delay: float = 0.0):
        """
        Initialize mock client.

        Args:
            fail_rate: Probability of failure (0.0 to 1.0)
            delay: Simulated network delay in seconds
        """
        self.fail_rate = fail_rate
        self.delay = delay
        self.call_history: list[dict[str, Any]] = []
        self.registered_tools: dict[str, Callable] = {}

    async def call_tool(self, tool_name: str, **kwargs) -> dict[str, Any]:
        """Simulate tool call with configurable behavior."""
        # Record call
        self.call_history.append({
            "tool": tool_name,
            "kwargs": kwargs,
            "timestamp": asyncio.get_event_loop().time()
        })

        # Simulate delay
        if self.delay > 0:
            await asyncio.sleep(self.delay)

        # Simulate failure
        if random.random() < self.fail_rate:
            raise ConnectionError(f"Simulated failure calling {tool_name}")

        # Return mock response
        if tool_name in self.registered_tools:
            return await self.registered_tools[tool_name](**kwargs)

        return {"success": True, "result": f"Mock result for {tool_name}"}

    def register_tool_response(self, tool_name: str, handler: Callable):
        """Register custom response handler for a tool."""
        self.registered_tools[tool_name] = handler

    def get_call_count(self, tool_name: str | None = None) -> int:
        """Get number of calls made (optionally filtered by tool name)."""
        if tool_name:
            return sum(1 for call in self.call_history if call["tool"] == tool_name)
        return len(self.call_history)

    def reset(self):
        """Reset mock state."""
        self.call_history.clear()
        self.registered_tools.clear()


class MockPlayer:
    """
    Mock Player Agent for testing game scenarios.

    Features:
    - Configurable strategy
    - Move history tracking
    - State simulation
    - Error injection
    """

    def __init__(
        self,
        player_id: str,
        strategy: str = "random",
        fail_on_move: bool = False
    ):
        """Initialize mock player."""
        self.player_id = player_id
        self.strategy = strategy
        self.fail_on_move = fail_on_move
        self.move_history: list[int] = []
        self.games: dict[str, dict[str, Any]] = {}
        self.score = 0

    async def make_move(self, game_id: str, role: str) -> int:
        """Simulate making a move."""
        if self.fail_on_move:
            raise ValueError(f"Player {self.player_id} failed to make move")

        # Generate move based on strategy
        if self.strategy == "random":
            move = random.randint(1, 10)
        elif self.strategy == "always_1":
            move = 1
        elif self.strategy == "always_10":
            move = 10
        elif self.strategy == "pattern_1_2_3":
            move = (len(self.move_history) % 3) + 1
        else:
            move = random.randint(1, 10)

        self.move_history.append(move)
        return move

    async def accept_invitation(self, game_id: str) -> bool:
        """Simulate accepting game invitation."""
        self.games[game_id] = {
            "accepted": True,
            "score": 0,
            "rounds": 0
        }
        return True

    def update_score(self, game_id: str, points: int):
        """Update player score for a game."""
        if game_id in self.games:
            self.games[game_id]["score"] += points
        self.score += points


class MockReferee:
    """
    Mock Referee Agent for testing match coordination.

    Features:
    - Match state management
    - Result reporting simulation
    - Error injection
    """

    def __init__(self, referee_id: str, fail_on_report: bool = False):
        """Initialize mock referee."""
        self.referee_id = referee_id
        self.fail_on_report = fail_on_report
        self.matches: dict[str, dict[str, Any]] = {}
        self.reported_results: list[dict[str, Any]] = []

    async def start_match(
        self,
        match_id: str,
        player1_id: str,
        player2_id: str,
        rounds: int = 5
    ) -> dict[str, Any]:
        """Simulate starting a match."""
        self.matches[match_id] = {
            "players": [player1_id, player2_id],
            "rounds": rounds,
            "current_round": 0,
            "status": "in_progress"
        }
        return {"match_id": match_id, "status": "started"}

    async def report_result(
        self,
        match_id: str,
        winner_id: str,
        loser_id: str
    ) -> bool:
        """Simulate reporting match result."""
        if self.fail_on_report:
            raise ConnectionError("Failed to report result")

        result = {
            "match_id": match_id,
            "winner": winner_id,
            "loser": loser_id
        }
        self.reported_results.append(result)

        if match_id in self.matches:
            self.matches[match_id]["status"] = "completed"

        return True


class MockLeagueManager:
    """
    Mock League Manager for testing league coordination.

    Features:
    - Player registration simulation
    - Match scheduling
    - Standings tracking
    """

    def __init__(self, max_players: int = 10):
        """Initialize mock league manager."""
        self.max_players = max_players
        self.players: dict[str, dict[str, Any]] = {}
        self.referees: dict[str, dict[str, Any]] = {}
        self.matches: list[dict[str, Any]] = []
        self.rounds_completed = 0

    async def register_player(
        self,
        player_id: str,
        endpoint: str,
        game_types: list[str]
    ) -> dict[str, Any]:
        """Simulate player registration."""
        if len(self.players) >= self.max_players:
            return {
                "success": False,
                "error": "League is full"
            }

        if player_id in self.players:
            return {
                "success": False,
                "error": "Already registered"
            }

        self.players[player_id] = {
            "endpoint": endpoint,
            "game_types": game_types,
            "wins": 0,
            "losses": 0,
            "points": 0
        }

        return {
            "success": True,
            "player_id": player_id,
            "auth_token": f"token_{player_id}"
        }

    async def register_referee(
        self,
        referee_id: str,
        endpoint: str
    ) -> dict[str, Any]:
        """Simulate referee registration."""
        self.referees[referee_id] = {
            "endpoint": endpoint,
            "matches_handled": 0
        }
        return {
            "success": True,
            "referee_id": referee_id
        }

    def get_standings(self) -> list[dict[str, Any]]:
        """Get current league standings."""
        standings = []
        for player_id, data in self.players.items():
            standings.append({
                "player_id": player_id,
                "wins": data["wins"],
                "losses": data["losses"],
                "points": data["points"]
            })
        # Sort by points descending
        standings.sort(key=lambda x: x["points"], reverse=True)
        return standings


class MockGameSession:
    """
    Mock Game Session for testing game logic.

    Features:
    - Move submission
    - Round resolution
    - Winner determination
    - State tracking
    """

    def __init__(
        self,
        game_id: str,
        rounds: int = 5,
        odd_player: str = "P1",
        even_player: str = "P2"
    ):
        """Initialize mock game session."""
        self.game_id = game_id
        self.rounds = rounds
        self.odd_player = odd_player
        self.even_player = even_player
        self.current_round = 0
        self.scores = {odd_player: 0, even_player: 0}
        self.history: list[dict[str, Any]] = []
        self.completed = False

    async def submit_move(self, player_id: str, move: int) -> bool:
        """Submit a move for current round."""
        if not (1 <= move <= 10):
            raise ValueError("Move must be between 1 and 10")

        if player_id not in self.scores:
            raise ValueError(f"Unknown player: {player_id}")

        return True

    async def resolve_round(self, move1: int, move2: int) -> dict[str, Any]:
        """Resolve current round."""
        total = move1 + move2
        is_odd = total % 2 == 1

        winner = self.odd_player if is_odd else self.even_player
        self.scores[winner] += 1

        round_result = {
            "round": self.current_round + 1,
            "move1": move1,
            "move2": move2,
            "sum": total,
            "winner": winner,
            "scores": dict(self.scores)
        }

        self.history.append(round_result)
        self.current_round += 1

        if self.current_round >= self.rounds:
            self.completed = True

        return round_result

    def get_winner(self) -> str | None:
        """Determine overall winner."""
        if not self.completed:
            return None

        if self.scores[self.odd_player] > self.scores[self.even_player]:
            return self.odd_player
        elif self.scores[self.even_player] > self.scores[self.odd_player]:
            return self.even_player
        else:
            return "tie"


def create_mock_transport() -> Mock:
    """Create a mock transport layer."""
    transport = Mock()
    transport.send = AsyncMock(return_value={"success": True})
    transport.receive = AsyncMock(return_value={"type": "test", "data": {}})
    transport.connect = AsyncMock()
    transport.disconnect = AsyncMock()
    transport.is_connected = Mock(return_value=True)
    return transport


def create_mock_event_bus() -> Mock:
    """Create a mock event bus."""
    event_bus = Mock()
    event_bus.publish = AsyncMock()
    event_bus.subscribe = Mock()
    event_bus.unsubscribe = Mock()
    event_bus.get_subscribers = Mock(return_value=[])
    return event_bus


# ====================
# Error Injection Utilities
# ====================

class NetworkErrorInjector:
    """Inject network errors for testing resilience."""

    def __init__(self, error_rate: float = 0.1):
        """Initialize with error rate (0.0 to 1.0)."""
        self.error_rate = error_rate
        self.error_count = 0

    async def maybe_fail(self, operation: str = "network"):
        """Randomly fail based on error rate."""
        if random.random() < self.error_rate:
            self.error_count += 1
            raise ConnectionError(f"Injected {operation} error")


class TimeoutSimulator:
    """Simulate timeouts for testing timeout handling."""

    def __init__(self, timeout_probability: float = 0.1):
        """Initialize with timeout probability."""
        self.timeout_probability = timeout_probability

    async def maybe_timeout(self, duration: float = 5.0):
        """Randomly timeout based on probability."""
        if random.random() < self.timeout_probability:
            await asyncio.sleep(duration)
            raise TimeoutError("Simulated timeout")


# ====================
# Test Fixtures
# ====================

def create_mock_player_client(player_id: str = "TestPlayer") -> MockMCPClient:
    """Create a configured mock player client."""
    client = MockMCPClient()

    async def mock_register(**kwargs):
        return {
            "success": True,
            "player_id": player_id,
            "auth_token": f"token_{player_id}"
        }

    async def mock_make_move(**kwargs):
        return {
            "success": True,
            "move": random.randint(1, 10)
        }

    client.register_tool_response("register_player", mock_register)
    client.register_tool_response("make_move", mock_make_move)

    return client


def create_mock_referee_client(referee_id: str = "TestReferee") -> MockMCPClient:
    """Create a configured mock referee client."""
    client = MockMCPClient()

    async def mock_register(**kwargs):
        return {
            "success": True,
            "referee_id": referee_id
        }

    async def mock_report_result(**kwargs):
        return {
            "success": True,
            "acknowledged": True
        }

    client.register_tool_response("register_referee", mock_register)
    client.register_tool_response("report_match_result", mock_report_result)

    return client

