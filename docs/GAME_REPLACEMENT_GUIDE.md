# Game Replacement Guide: True Game-Agnostic Architecture

This guide demonstrates how the MCP Game League system's **game-agnostic architecture** allows you to swap games in minutes without touching core infrastructure.

## Quick Start: Add a New Game in 5 Minutes

### Example: Adding Rock-Paper-Scissors

**1. Create game implementation** (`src/game/implementations/rock_paper_scissors.py`):

```python
from src.game.base import Game
from src.game.registry import register_game
from src.game.types import GameState, Move, Outcome

@register_game(name="rock_paper_scissors", min_players=2, max_players=2)
class RockPaperScissors(Game):
    """Rock-Paper-Scissors game implementation."""

    def __init__(self, game_id: str, players: list, config: dict = None):
        super().__init__(game_id, players, config)
        self.max_rounds = config.get("max_rounds", 10)

    def get_valid_moves(self) -> list:
        """Return all valid moves."""
        return ["rock", "paper", "scissors"]

    def is_valid_move(self, move: Move, game_state: GameState) -> bool:
        """Check if move is valid."""
        return move in self.get_valid_moves()

    def initialize_game(self) -> GameState:
        """Create initial game state."""
        return GameState(
            game_id=self.game_id,
            game_type="rock_paper_scissors",
            round=0,
            players=self.players,
            scores={p: 0 for p in self.players},
            valid_moves=self.get_valid_moves(),
            terminal=False,
            metadata={}
        )

    def update_state(
        self,
        current_state: GameState,
        moves: dict  # {player_id: move}
    ) -> Tuple[GameState, Outcome]:
        """Process moves and return new state + outcome."""

        # Determine winner
        p1, p2 = list(moves.keys())
        move1, move2 = moves[p1], moves[p2]

        winner = self._determine_winner(move1, move2)

        # Update scores
        new_scores = current_state.scores.copy()
        if winner == p1:
            new_scores[p1] += 1
        elif winner == p2:
            new_scores[p2] += 1
        # Tie: no score change

        # Create outcome
        outcome = Outcome(
            round=current_state.round + 1,
            moves=moves,
            winner=winner,
            scores=new_scores,
            rewards={
                p1: 1 if winner == p1 else (-1 if winner == p2 else 0),
                p2: 1 if winner == p2 else (-1 if winner == p1 else 0)
            },
            terminal=(current_state.round + 1 >= self.max_rounds),
            metadata={'move1': move1, 'move2': move2}
        )

        # Create new state
        new_state = GameState(
            game_id=self.game_id,
            game_type="rock_paper_scissors",
            round=current_state.round + 1,
            players=self.players,
            scores=new_scores,
            valid_moves=self.get_valid_moves(),
            terminal=outcome.terminal,
            metadata=current_state.metadata
        )

        return new_state, outcome

    def _determine_winner(self, move1: str, move2: str) -> Optional[str]:
        """Determine winner of RPS round."""
        if move1 == move2:
            return None  # Tie

        wins = {
            ('rock', 'scissors'): True,
            ('scissors', 'paper'): True,
            ('paper', 'rock'): True,
        }

        p1, p2 = self.players
        return p1 if wins.get((move1, move2), False) else p2
```

**2. Register in `__init__.py`**:

```python
# src/game/implementations/__init__.py
from .rock_paper_scissors import RockPaperScissors

__all__ = ['RockPaperScissors']
```

**3. Run tournament**:

```bash
python -m src.main --game rock_paper_scissors --players 4 --rounds 20 --run
```

**That's it!** All existing infrastructure works:
- ✅ Tournament scheduling
- ✅ Score tracking
- ✅ Logging and metrics
- ✅ Strategy plugins
- ✅ Event emission
- ✅ Health checks
- ✅ Observability

---

## Supported Games

### Currently Implemented

1. **Prisoner's Dilemma** (`prisoner_dilemma`)
   - Classic 2-player iterated game
   - Moves: `cooperate`, `defect`
   - Payoff matrix configurable

### Ready to Add (Examples Provided)

2. **Rock-Paper-Scissors** (`rock_paper_scissors`)
   - 2-player simultaneous move
   - Moves: `rock`, `paper`, `scissors`

3. **Tic-Tac-Toe** (`tic_tac_toe`)
   - 2-player turn-based
   - Moves: board positions (0-8)

4. **Connect Four** (`connect_four`)
   - 2-player drop-piece
   - Moves: column numbers (0-6)

5. **Poker** (`poker`)
   - 2-6 players
   - Moves: `fold`, `call`, `raise`

### Adding More Games

The system supports:
- **2+ player games**
- **Simultaneous** or **turn-based**
- **Perfect information** or **hidden information**
- **Discrete** or **continuous** action spaces
- **Zero-sum**, **cooperative**, or **mixed-motive**

---

## Game Interface Requirements

To add a new game, implement the `Game` interface:

```python
from abc import ABC, abstractmethod

class Game(ABC):
    """Abstract base class for all games."""

    @abstractmethod
    def get_valid_moves(self) -> list:
        """Return list of all possible moves."""
        pass

    @abstractmethod
    def is_valid_move(self, move: Move, game_state: GameState) -> bool:
        """Check if a move is valid in current state."""
        pass

    @abstractmethod
    def initialize_game(self) -> GameState:
        """Create and return initial game state."""
        pass

    @abstractmethod
    def update_state(
        self,
        current_state: GameState,
        moves: dict
    ) -> Tuple[GameState, Outcome]:
        """
        Process player moves and return:
        - Updated game state
        - Outcome (winner, scores, terminal)
        """
        pass
```

### Universal Types

All games use these standard types:

```python
@dataclass
class GameState:
    """Universal game state representation."""
    game_id: str
    game_type: str
    round: int
    players: List[str]
    scores: Dict[str, float]
    valid_moves: List[str]
    terminal: bool
    metadata: Dict[str, Any]

@dataclass
class Outcome:
    """Universal outcome representation."""
    round: int
    moves: Dict[str, str]
    winner: Optional[str]
    scores: Dict[str, float]
    rewards: Dict[str, float]
    terminal: bool
    metadata: Dict[str, Any]
```

---

## Example: Tic-Tac-Toe Implementation

```python
@register_game(name="tic_tac_toe", min_players=2, max_players=2)
class TicTacToe(Game):
    """Tic-Tac-Toe game implementation."""

    def __init__(self, game_id: str, players: list, config: dict = None):
        super().__init__(game_id, players, config)
        self.board_size = 3

    def get_valid_moves(self) -> list:
        """Return all board positions."""
        return [f"{r},{c}" for r in range(3) for c in range(3)]

    def is_valid_move(self, move: Move, game_state: GameState) -> bool:
        """Check if position is empty."""
        board = game_state.metadata.get('board', [[None]*3 for _ in range(3)])
        r, c = map(int, move.split(','))
        return board[r][c] is None

    def initialize_game(self) -> GameState:
        """Create initial state with empty board."""
        return GameState(
            game_id=self.game_id,
            game_type="tic_tac_toe",
            round=0,
            players=self.players,
            scores={p: 0 for p in self.players},
            valid_moves=self.get_valid_moves(),
            terminal=False,
            metadata={
                'board': [[None]*3 for _ in range(3)],
                'current_player': self.players[0]
            }
        )

    def update_state(
        self,
        current_state: GameState,
        moves: dict
    ) -> Tuple[GameState, Outcome]:
        """Process move and check for winner."""
        # Get current player's move
        current_player = current_state.metadata['current_player']
        move = moves[current_player]

        # Update board
        board = [row.copy() for row in current_state.metadata['board']]
        r, c = map(int, move.split(','))
        board[r][c] = current_player

        # Check for winner
        winner = self._check_winner(board)

        # Check for draw
        is_full = all(board[r][c] is not None for r in range(3) for c in range(3))
        terminal = (winner is not None) or is_full

        # Update scores
        new_scores = current_state.scores.copy()
        if winner:
            new_scores[winner] += 1

        # Switch player
        next_player = self.players[1] if current_player == self.players[0] else self.players[0]

        # Create outcome
        outcome = Outcome(
            round=current_state.round + 1,
            moves=moves,
            winner=winner,
            scores=new_scores,
            rewards={current_player: (1 if winner == current_player else 0)},
            terminal=terminal,
            metadata={'board': board}
        )

        # Create new state
        new_state = GameState(
            game_id=self.game_id,
            game_type="tic_tac_toe",
            round=current_state.round + 1,
            players=self.players,
            scores=new_scores,
            valid_moves=[
                f"{r},{c}" for r in range(3) for c in range(3)
                if board[r][c] is None
            ],
            terminal=terminal,
            metadata={'board': board, 'current_player': next_player}
        )

        return new_state, outcome

    def _check_winner(self, board) -> Optional[str]:
        """Check all winning conditions."""
        # Rows
        for row in board:
            if row[0] == row[1] == row[2] and row[0] is not None:
                return row[0]

        # Columns
        for c in range(3):
            if board[0][c] == board[1][c] == board[2][c] and board[0][c] is not None:
                return board[0][c]

        # Diagonals
        if board[0][0] == board[1][1] == board[2][2] and board[0][0] is not None:
            return board[0][0]
        if board[0][2] == board[1][1] == board[2][0] and board[0][2] is not None:
            return board[0][2]

        return None
```

---

## Strategy Compatibility

### Strategies Work Across Games

Because strategies use **universal state representation**, they automatically work with any game:

```python
@strategy_plugin(name="adaptive", version="1.0.0")
class AdaptiveStrategy(Strategy):
    """Works with Prisoner's Dilemma, RPS, Tic-Tac-Toe, etc."""

    async def decide_move(self, game_state: GameState) -> Move:
        # Extract universal features (works for ANY game)
        features = self._extract_features(game_state)

        # Make decision (game-agnostic)
        if self.model:
            move_idx = self.model.predict(features)
            return game_state.valid_moves[move_idx]
        else:
            return random.choice(game_state.valid_moves)

    def _extract_features(self, game_state: GameState) -> np.ndarray:
        """Extract features that work for any game."""
        return np.array([
            game_state.round,
            len(game_state.valid_moves),
            game_state.scores[self.player_id],
            max(game_state.scores.values()) - min(game_state.scores.values()),
            # ... more universal features
        ])
```

### Testing Strategy Across Games

```python
# Test strategy on multiple games
strategy = AdaptiveStrategy()

# Test on Prisoner's Dilemma
game1 = GameRegistry.create_game("prisoner_dilemma", ["p1", "p2"])
result1 = await run_tournament(game1, [strategy])

# Test on Rock-Paper-Scissors (same strategy!)
game2 = GameRegistry.create_game("rock_paper_scissors", ["p1", "p2"])
result2 = await run_tournament(game2, [strategy])

# Test on Tic-Tac-Toe (still works!)
game3 = GameRegistry.create_game("tic_tac_toe", ["p1", "p2"])
result3 = await run_tournament(game3, [strategy])
```

---

## Configuration

### Game Configuration

**`config/games/games_config.json`**:

```json
{
  "games": {
    "prisoner_dilemma": {
      "enabled": true,
      "max_rounds": 100,
      "payoff_matrix": {
        "cooperate_cooperate": [3, 3],
        "cooperate_defect": [0, 5],
        "defect_cooperate": [5, 0],
        "defect_defect": [1, 1]
      }
    },
    "rock_paper_scissors": {
      "enabled": true,
      "max_rounds": 20
    },
    "tic_tac_toe": {
      "enabled": true,
      "board_size": 3
    }
  },
  "default_game": "prisoner_dilemma"
}
```

---

## Running Tournaments with Different Games

### Command Line

```bash
# Prisoner's Dilemma tournament
python -m src.main --game prisoner_dilemma --players 4 --run

# Rock-Paper-Scissors tournament
python -m src.main --game rock_paper_scissors --players 4 --run

# Tic-Tac-Toe tournament
python -m src.main --game tic_tac_toe --players 2 --run
```

### Programmatic

```python
from src.game.registry import GameRegistry
from src.tournament import TournamentManager

# Create game
game = GameRegistry.create_game(
    "rock_paper_scissors",
    players=["player1", "player2", "player3", "player4"]
)

# Run tournament
tournament = TournamentManager(game=game)
results = await tournament.run_round_robin()
```

---

## Game Development Checklist

When adding a new game, ensure:

- [ ] Implements `Game` interface
- [ ] Returns valid `GameState` objects
- [ ] Returns valid `Outcome` objects
- [ ] Validates moves correctly
- [ ] Handles terminal states
- [ ] Updates scores properly
- [ ] Includes metadata as needed
- [ ] Registered with `@register_game` decorator
- [ ] Has configuration file
- [ ] Has unit tests
- [ ] Documented in README

---

## Testing New Games

### Unit Tests

```python
@pytest.mark.asyncio
async def test_rock_paper_scissors_game():
    """Test RPS game implementation."""
    game = RockPaperScissors(
        game_id="test-1",
        players=["p1", "p2"],
        config={"max_rounds": 10}
    )

    # Test initialization
    state = game.initialize_game()
    assert state.round == 0
    assert not state.terminal
    assert len(state.valid_moves) == 3

    # Test rock beats scissors
    moves = {"p1": "rock", "p2": "scissors"}
    new_state, outcome = game.update_state(state, moves)

    assert outcome.winner == "p1"
    assert new_state.scores["p1"] == 1
    assert new_state.scores["p2"] == 0

    # Test tie
    moves = {"p1": "rock", "p2": "rock"}
    new_state, outcome = game.update_state(new_state, moves)

    assert outcome.winner is None
    assert new_state.scores["p1"] == 1
    assert new_state.scores["p2"] == 0
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_rps_tournament():
    """Test full RPS tournament."""
    from src.tournament import TournamentManager

    # Create game
    game = GameRegistry.create_game("rock_paper_scissors", ["p1", "p2"])

    # Create tournament
    tournament = TournamentManager(game=game)

    # Run tournament
    results = await tournament.run_round_robin()

    # Verify results
    assert len(results.matches) > 0
    assert all(match.completed for match in results.matches)
    assert len(results.final_standings) == 2
```

---

## Migration Guide: Swapping Games

### Migrating from Prisoner's Dilemma to RPS

**Before (Prisoner's Dilemma)**:
```bash
python -m src.main --game prisoner_dilemma --players 4 --run
```

**After (Rock-Paper-Scissors)**:
```bash
python -m src.main --game rock_paper_scissors --players 4 --run
```

**What Changes:**
- ✅ Game rules
- ✅ Valid moves
- ✅ Scoring logic

**What Stays the Same:**
- ✅ Tournament structure
- ✅ Player agents
- ✅ Strategies (universal)
- ✅ Logging/metrics
- ✅ Event system
- ✅ Middleware
- ✅ Observability
- ✅ Health checks

---

## Advanced: Multi-Game Tournaments

Run tournaments across **multiple games** to find universally strong strategies:

```python
class MultiGameTournament:
    """Tournament across multiple game types."""

    def __init__(self, games: List[str]):
        self.games = [
            GameRegistry.create_game(game_name, players)
            for game_name in games
        ]

    async def run(self, strategies: List[Strategy]):
        """Run tournament on all games."""
        results = {}

        for game in self.games:
            tournament = TournamentManager(game=game)
            game_results = await tournament.run_round_robin()
            results[game.game_type] = game_results

        # Aggregate scores across games
        total_scores = self._aggregate_scores(results)

        return total_scores

# Usage
tournament = MultiGameTournament([
    "prisoner_dilemma",
    "rock_paper_scissors",
    "tic_tac_toe"
])

results = await tournament.run([
    NashStrategy(),
    QLearningStrategy(),
    MetaLearningStrategy()
])
```

---

## Resources

- [Game Registry Implementation](../src/game/registry.py)
- [Game Base Classes](../src/game/base.py)
- [Example Games](../src/game/implementations/)
- [Strategy Plugin Development](./PLUGIN_DEVELOPMENT.md)
- [Innovation Features](./INNOVATION.md)

## Support

Questions about game development? See:
- [Architecture Documentation](./ARCHITECTURE.md)
- [Testing Guide](./TESTING.md)
- GitHub Issues: https://github.com/your-org/mcp-game-league/issues
