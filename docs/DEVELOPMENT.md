# Development Guide

This guide provides information for developers contributing to the MCP Multi-Agent Game League system.

---

## Table of Contents

- [Development Environment](#development-environment)
- [Project Structure](#project-structure)
- [Code Style](#code-style)
- [Testing](#testing)
- [Adding New Features](#adding-new-features)
- [Protocol Extensions](#protocol-extensions)
- [Git Workflow](#git-workflow)
- [Debugging](#debugging)

---

## Development Environment

### Prerequisites

- Python 3.11+
- UV package manager
- Git
- VS Code (recommended) or preferred IDE

### Setup

```bash
# Clone repository
git clone <repository-url>
cd MCP_Multi_Agent_Game

# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create environment and install all dependencies (including dev)
uv sync --all-extras

# Activate virtual environment
source .venv/bin/activate

# Verify setup
make test
```

### IDE Setup (VS Code)

Recommended extensions:

```json
// .vscode/extensions.json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "charliermarsh.ruff",
    "ms-python.mypy-type-checker",
    "tamasfe.even-better-toml"
  ]
}
```

Settings:

```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.analysis.typeCheckingMode": "basic",
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "explicit",
      "source.organizeImports.ruff": "explicit"
    }
  }
}
```

---

## Project Structure

```
src/
├── client/                 # MCP Client components
│   ├── mcp_client.py       # Main client class
│   ├── session_manager.py  # Session lifecycle
│   ├── tool_registry.py    # Tool discovery
│   ├── connection_manager.py # Health/retry
│   ├── message_queue.py    # Message handling
│   └── resource_manager.py # Resource/subscription
│
├── server/                 # MCP Server components
│   ├── mcp_server.py       # Main server class
│   ├── base_server.py      # Base server utilities
│   ├── tools/              # Tool implementations
│   └── resources/          # Resource providers
│
├── transport/              # Transport layer
│   ├── base.py             # Abstract transport
│   ├── json_rpc.py         # JSON-RPC 2.0
│   └── http_transport.py   # HTTP transport
│
├── game/                   # Game logic
│   ├── odd_even.py         # Odd/Even game
│   └── match.py            # Match management
│
├── agents/                 # AI Agents
│   ├── league_manager.py   # League orchestration
│   ├── referee.py          # Game referee
│   └── player.py           # Player agent
│
├── common/                 # Shared utilities
│   ├── config.py           # Configuration
│   ├── logger.py           # Logging
│   ├── exceptions.py       # Custom exceptions
│   └── protocol.py         # Protocol schemas
│
└── main.py                 # Entry point
```

---

## Code Style

### Formatting

We use **Ruff** for linting and formatting:

```bash
# Check for issues
uv run ruff check src/ tests/

# Auto-fix issues
uv run ruff check src/ tests/ --fix

# Format code
uv run ruff format src/ tests/

# Or use Makefile
make lint
make format
```

### Type Checking

We use **MyPy** for type checking:

```bash
uv run mypy src/

# Or use Makefile
make typecheck
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `MCPClient`, `LeagueManager` |
| Functions | snake_case | `register_player`, `make_move` |
| Constants | UPPER_SNAKE | `MAX_PLAYERS`, `DEFAULT_PORT` |
| Private | _prefix | `_internal_method` |
| Modules | snake_case | `session_manager.py` |

### Docstrings

Use Google-style docstrings:

```python
def register_player(
    self,
    player_name: str,
    endpoint: str,
    version: str = "1.0.0"
) -> PlayerRegistration:
    """Register a new player to the league.

    Args:
        player_name: Display name for the player.
        endpoint: MCP endpoint URL.
        version: Player agent version.

    Returns:
        PlayerRegistration with assigned player_id.

    Raises:
        RegistrationError: If registration fails.
        ProtocolError: If endpoint is invalid.
    """
    ...
```

---

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_game.py -v

# Run specific test
uv run pytest tests/test_game.py::test_odd_even_game -v

# Run with debug output
uv run pytest tests/ -v -s

# Or use Makefile
make test
```

### Test Structure

```
tests/
├── __init__.py
├── conftest.py          # Shared fixtures
├── test_game.py         # Game logic tests
├── test_transport.py    # Transport layer tests
├── test_protocol.py     # Protocol validation tests
├── test_client.py       # Client tests
├── test_server.py       # Server tests
└── integration/         # Integration tests
    └── test_full_game.py
```

### Writing Tests

```python
# tests/test_game.py
import pytest
from src.game.odd_even import OddEvenGame

class TestOddEvenGame:
    """Tests for Odd/Even game logic."""

    @pytest.fixture
    def game(self) -> OddEvenGame:
        """Create a fresh game instance."""
        return OddEvenGame()

    def test_odd_sum_winner(self, game: OddEvenGame):
        """Test that ODD player wins on odd sum."""
        result = game.evaluate_round(
            odd_player_move=3,
            even_player_move=2
        )
        assert result.sum == 5
        assert result.winner == "ODD"

    def test_even_sum_winner(self, game: OddEvenGame):
        """Test that EVEN player wins on even sum."""
        result = game.evaluate_round(
            odd_player_move=2,
            even_player_move=2
        )
        assert result.sum == 4
        assert result.winner == "EVEN"

    @pytest.mark.parametrize("move", [0, 6, -1, 10])
    def test_invalid_move_rejected(self, game: OddEvenGame, move: int):
        """Test that invalid moves are rejected."""
        with pytest.raises(ValueError):
            game.validate_move(move)
```

### Fixtures

```python
# tests/conftest.py
import pytest
from src.client.mcp_client import MCPClient
from src.server.mcp_server import MCPServer

@pytest.fixture
async def client():
    """Create test MCP client."""
    client = MCPClient()
    yield client
    await client.disconnect()

@pytest.fixture
async def server():
    """Create test MCP server."""
    server = MCPServer(port=0)  # Random port
    await server.start()
    yield server
    await server.stop()
```

---

## Adding New Features

### Adding a New Game Type

1. Create game module in `src/game/`:

```python
# src/game/tic_tac_toe.py
from dataclasses import dataclass
from typing import List, Optional
from src.game.base import BaseGame

@dataclass
class TicTacToeState:
    board: List[List[Optional[str]]]
    current_player: str

class TicTacToeGame(BaseGame):
    """Tic-Tac-Toe game implementation."""

    game_type = "tic_tac_toe"

    def __init__(self):
        self.state = TicTacToeState(
            board=[[None] * 3 for _ in range(3)],
            current_player="X"
        )

    def validate_move(self, row: int, col: int) -> bool:
        """Validate if move is legal."""
        if not (0 <= row < 3 and 0 <= col < 3):
            return False
        return self.state.board[row][col] is None

    def make_move(self, row: int, col: int) -> None:
        """Make a move on the board."""
        if not self.validate_move(row, col):
            raise ValueError("Invalid move")
        self.state.board[row][col] = self.state.current_player
        self.state.current_player = "O" if self.state.current_player == "X" else "X"

    def check_winner(self) -> Optional[str]:
        """Check for a winner."""
        # Implementation...
        pass
```

2. Register game type in `src/game/__init__.py`:

```python
from src.game.odd_even import OddEvenGame
from src.game.tic_tac_toe import TicTacToeGame

GAME_TYPES = {
    "even_odd": OddEvenGame,
    "tic_tac_toe": TicTacToeGame,
}
```

3. Add tests:

```python
# tests/test_tic_tac_toe.py
from src.game.tic_tac_toe import TicTacToeGame

class TestTicTacToe:
    def test_valid_move(self):
        game = TicTacToeGame()
        assert game.validate_move(0, 0)
        game.make_move(0, 0)
        assert not game.validate_move(0, 0)
```

### Adding a New Tool

1. Create tool in `src/server/tools/`:

```python
# src/server/tools/statistics.py
from src.server.tools.base import BaseTool

class StatisticsTool(BaseTool):
    """Tool for player statistics."""

    name = "get_player_stats"
    description = "Get statistics for a player"
    input_schema = {
        "type": "object",
        "properties": {
            "player_id": {"type": "string"}
        },
        "required": ["player_id"]
    }

    async def execute(self, arguments: dict) -> dict:
        """Execute the tool."""
        player_id = arguments["player_id"]
        # Fetch stats...
        return {
            "player_id": player_id,
            "games_played": 10,
            "win_rate": 0.7
        }
```

2. Register tool in server:

```python
# src/server/mcp_server.py
from src.server.tools.statistics import StatisticsTool

class MCPServer:
    def __init__(self):
        self.tools = [
            StatisticsTool(),
            # ... other tools
        ]
```

---

## Protocol Extensions

### Adding a New Message Type

1. Define schema in `src/common/protocol.py`:

```python
@dataclass
class TournamentStartMessage(BaseMessage):
    """Message to start a tournament."""

    message_type: str = "TOURNAMENT_START"
    tournament_id: str
    participants: List[str]
    format: str  # "round_robin", "knockout", etc.

    def validate(self) -> bool:
        """Validate message structure."""
        if not super().validate():
            return False
        if len(self.participants) < 2:
            return False
        return True
```

2. Add handler:

```python
# src/agents/league_manager.py
class LeagueManager:
    async def handle_message(self, message: dict) -> dict:
        msg_type = message.get("message_type")

        if msg_type == "TOURNAMENT_START":
            return await self._handle_tournament_start(message)
        # ... other handlers
```

---

## Git Workflow

### Branch Naming

```
feature/add-tic-tac-toe
bugfix/fix-timeout-handling
docs/update-api-documentation
refactor/simplify-message-queue
```

### Commit Messages

Follow conventional commits:

```
feat: add tic-tac-toe game implementation
fix: handle timeout in move request
docs: update API documentation
refactor: simplify message queue logic
test: add tests for tournament brackets
chore: update dependencies
```

### Pull Request Process

1. Create feature branch from `main`
2. Make changes with meaningful commits
3. Ensure all tests pass: `make test`
4. Ensure code is formatted: `make lint`
5. Update documentation if needed
6. Create PR with description
7. Request review

---

## Debugging

### Debug Logging

```python
import logging

logger = logging.getLogger(__name__)

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Log with context
logger.debug(
    "Processing move",
    extra={
        "player_id": player_id,
        "move": move,
        "game_state": state
    }
)
```

### Running with Debug Mode

```bash
# Set log level
LOG_LEVEL=DEBUG uv run python -m src.main --run --players 4

# Or in code
import os
os.environ["LOG_LEVEL"] = "DEBUG"
```

### Using Debugger

```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use breakpoint() in Python 3.7+
breakpoint()
```

### VS Code Debug Configuration

```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Run League",
      "type": "debugpy",
      "request": "launch",
      "module": "src.main",
      "args": ["--run", "--players", "4"],
      "cwd": "${workspaceFolder}",
      "env": {
        "LOG_LEVEL": "DEBUG"
      }
    },
    {
      "name": "Run Tests",
      "type": "debugpy",
      "request": "launch",
      "module": "pytest",
      "args": ["tests/", "-v", "-s"],
      "cwd": "${workspaceFolder}"
    }
  ]
}
```

---

## Performance Profiling

### CPU Profiling

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Code to profile
await run_league()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats("cumulative")
stats.print_stats(20)
```

### Memory Profiling

```bash
# Install memory profiler
uv add memory-profiler

# Run with profiling
uv run python -m memory_profiler src/main.py
```

---

## Common Patterns

### Async Context Manager

```python
class MCPClient:
    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

# Usage
async with MCPClient() as client:
    await client.call_tool("register_player", {...})
```

### Error Handling

```python
from src.common.exceptions import (
    MCPError,
    ProtocolError,
    TimeoutError,
    ConnectionError
)

async def make_request(self, method: str, params: dict) -> dict:
    try:
        response = await self._send_request(method, params)
        return response
    except TimeoutError:
        logger.warning("Request timed out, retrying...")
        return await self._retry_request(method, params)
    except ConnectionError as e:
        logger.error(f"Connection failed: {e}")
        raise
    except ProtocolError as e:
        logger.error(f"Protocol error: {e}")
        raise MCPError(f"Invalid response: {e}") from e
```

### Retry with Backoff

```python
import asyncio
import random

async def retry_with_backoff(
    func,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0
):
    """Retry function with exponential backoff and jitter."""
    for attempt in range(max_attempts):
        try:
            return await func()
        except Exception as e:
            if attempt == max_attempts - 1:
                raise

            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter = random.uniform(0, delay * 0.1)
            await asyncio.sleep(delay + jitter)

            logger.warning(
                f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}"
            )
```

---

*Last Updated: December 2024*

