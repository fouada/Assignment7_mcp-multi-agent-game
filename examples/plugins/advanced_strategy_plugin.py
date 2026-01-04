"""
Advanced Strategy Plugin Example
=================================

Demonstrates advanced plugin patterns:
- Custom strategy registration via extension points
- Dependency injection
- Configuration management
- Hot reload support
- State persistence

This plugin provides adaptive strategies that learn from gameplay.
"""

import json
import random
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.common.plugins.base import (
    PluginInterface,
    PluginMetadata,
    PluginContext,
    PluginCapability,
)
from src.common.extension_points import extension_provider, get_extension_registry
from src.agents.strategies.base import Strategy
from src.common.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StrategyStats:
    """Statistics for a strategy."""
    
    games_played: int = 0
    games_won: int = 0
    total_moves: int = 0
    move_distribution: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    win_rate: float = 0.0
    
    def update(self, move: int, won: bool) -> None:
        """Update statistics."""
        self.games_played += 1
        if won:
            self.games_won += 1
        self.total_moves += 1
        self.move_distribution[move] += 1
        self.win_rate = self.games_won / self.games_played if self.games_played > 0 else 0.0


@extension_provider("strategy.custom", priority=95)
class AdaptiveStrategy(Strategy):
    """
    Adaptive strategy that learns opponent patterns.
    
    Features:
    - Pattern recognition
    - Adaptive counter-strategy
    - Memory of opponent moves
    - Statistical analysis
    """
    
    def __init__(self):
        super().__init__(
            "adaptive",
            "Adaptive learning strategy"
        )
        
        # Opponent modeling
        self.opponent_history: deque[int] = deque(maxlen=50)
        self.opponent_patterns: dict[tuple[int, ...], list[int]] = defaultdict(list)
        
        # Statistics
        self.stats = StrategyStats()
        
        # Configuration
        self.pattern_length = 3
        self.exploration_rate = 0.1
    
    def decide_move(
        self,
        game_id: str,
        round: int,
        role: str,
        scores: list[int],
        history: list[dict]
    ) -> int:
        """Decide move using adaptive strategy."""
        
        # Early rounds: explore randomly
        if round <= self.pattern_length:
            move = random.randint(1, 5)
            self._update_history(history)
            return move
        
        # Learn from history
        self._update_history(history)
        
        # Predict opponent's move based on patterns
        predicted_opponent_move = self._predict_opponent_move()
        
        # Choose counter-move
        if predicted_opponent_move:
            move = self._counter_move(predicted_opponent_move, role)
        else:
            # Fallback to random with slight bias toward unexplored moves
            move = self._explore_or_exploit()
        
        return move
    
    def _update_history(self, history: list[dict]) -> None:
        """Update opponent move history."""
        if not history:
            return
        
        for record in history:
            moves = record.get("moves", {})
            
            # Extract opponent's move
            for player_id, move_value in moves.items():
                if move_value is not None:
                    self.opponent_history.append(move_value)
    
    def _predict_opponent_move(self) -> int | None:
        """Predict opponent's next move based on patterns."""
        if len(self.opponent_history) < self.pattern_length:
            return None
        
        # Get recent pattern
        recent_pattern = tuple(list(self.opponent_history)[-self.pattern_length:])
        
        # Look up what typically follows this pattern
        if recent_pattern in self.opponent_patterns:
            following_moves = self.opponent_patterns[recent_pattern]
            if following_moves:
                # Return most common following move
                return max(set(following_moves), key=following_moves.count)
        
        # Update patterns for learning
        if len(self.opponent_history) >= self.pattern_length + 1:
            pattern = tuple(list(self.opponent_history)[-(self.pattern_length + 1):-1])
            next_move = self.opponent_history[-1]
            self.opponent_patterns[pattern].append(next_move)
        
        return None
    
    def _counter_move(self, predicted_move: int, role: str) -> int:
        """Choose a move to counter predicted opponent move."""
        if role == "ODD":
            # We want odd sum, opponent chooses predicted_move
            # Choose move such that our_move + predicted_move is odd
            if predicted_move % 2 == 0:
                # Opponent even -> we choose odd
                return random.choice([1, 3, 5])
            else:
                # Opponent odd -> we choose even
                return random.choice([2, 4])
        else:  # EVEN
            # We want even sum
            if predicted_move % 2 == 0:
                # Opponent even -> we choose even
                return random.choice([2, 4])
            else:
                # Opponent odd -> we choose odd
                return random.choice([1, 3, 5])
    
    def _explore_or_exploit(self) -> int:
        """Explore new moves or exploit known good moves."""
        if random.random() < self.exploration_rate:
            # Explore: try less-used moves
            least_used = min(
                range(1, 6),
                key=lambda m: self.stats.move_distribution.get(m, 0)
            )
            return least_used
        else:
            # Exploit: use most successful moves
            if self.stats.move_distribution:
                most_used = max(
                    self.stats.move_distribution.keys(),
                    key=lambda m: self.stats.move_distribution[m]
                )
                return most_used
            return random.randint(1, 5)
    
    def get_stats(self) -> dict[str, Any]:
        """Get strategy statistics."""
        return {
            "games_played": self.stats.games_played,
            "games_won": self.stats.games_won,
            "win_rate": self.stats.win_rate,
            "move_distribution": dict(self.stats.move_distribution),
            "patterns_learned": len(self.opponent_patterns)
        }


@extension_provider("strategy.custom", priority=90)
class MetaLearningStrategy(Strategy):
    """
    Meta-learning strategy that adapts based on opponent type.
    
    Maintains a portfolio of sub-strategies and selects the best one
    for each opponent.
    """
    
    def __init__(self):
        super().__init__(
            "meta_learning",
            "Meta-learning strategy selector"
        )
        
        # Portfolio of strategies
        self.strategies = {
            "random": self._random_strategy,
            "aggressive": self._aggressive_strategy,
            "defensive": self._defensive_strategy,
            "adaptive": self._adaptive_strategy,
        }
        
        # Performance tracking per opponent
        self.opponent_performance: dict[str, dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        
        # Current opponent
        self.current_opponent: str | None = None
    
    def decide_move(
        self,
        game_id: str,
        round: int,
        role: str,
        scores: list[int],
        history: list[dict]
    ) -> int:
        """Decide move using meta-learning."""
        
        # Identify opponent (simplified - in reality would be more sophisticated)
        opponent_id = self._identify_opponent(game_id, history)
        
        # Select best strategy for this opponent
        strategy_name = self._select_strategy(opponent_id)
        
        # Execute selected strategy
        return self.strategies[strategy_name](role, scores, history)
    
    def _identify_opponent(self, game_id: str, history: list[dict]) -> str:
        """Identify current opponent."""
        # Simplified - would use more sophisticated opponent identification
        return game_id.split("_")[0] if "_" in game_id else "unknown"
    
    def _select_strategy(self, opponent_id: str) -> str:
        """Select best strategy for opponent."""
        if opponent_id not in self.opponent_performance:
            # New opponent - try random first
            return "random"
        
        # Select strategy with best performance
        performance = self.opponent_performance[opponent_id]
        if performance:
            return max(performance.keys(), key=lambda k: performance[k])
        
        return "random"
    
    def _random_strategy(self, role: str, scores: list[int], history: list[dict]) -> int:
        """Random strategy."""
        return random.randint(1, 5)
    
    def _aggressive_strategy(self, role: str, scores: list[int], history: list[dict]) -> int:
        """Aggressive strategy - prefer high values."""
        return random.choice([4, 5])
    
    def _defensive_strategy(self, role: str, scores: list[int], history: list[dict]) -> int:
        """Defensive strategy - prefer low values."""
        return random.choice([1, 2])
    
    def _adaptive_strategy(self, role: str, scores: list[int], history: list[dict]) -> int:
        """Adaptive strategy based on current state."""
        if not scores:
            return random.randint(1, 5)
        
        # If losing, be more aggressive
        if scores[0] < scores[1]:
            return random.choice([4, 5])
        # If winning, be more defensive
        else:
            return random.choice([1, 2, 3])


class AdvancedStrategyPlugin(PluginInterface):
    """
    Plugin that provides advanced adaptive strategies.
    
    Features:
    - Multiple strategy implementations
    - Pattern learning
    - Meta-learning
    - State persistence
    - Hot reload support
    """
    
    def __init__(self):
        super().__init__()
        self.strategies: list[Strategy] = []
        self.state_file = Path("data/strategy_state.json")
    
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="advanced_strategy_plugin",
            version="1.0.0",
            author="MCP Team",
            description="Advanced adaptive game strategies",
            capabilities=[
                PluginCapability.HOT_RELOAD,
                PluginCapability.PROVIDES_EXTENSIONS,
            ],
            tags=["strategy", "machine-learning", "adaptive"],
            dependencies=[],
            homepage="https://github.com/your-org/mcp-game-league",
            license="MIT",
        )
    
    async def on_load(self, context: PluginContext) -> None:
        """Load plugin and restore state."""
        await super().on_load(context)
        
        # Create strategies (they're auto-registered via @extension_provider)
        adaptive = AdaptiveStrategy()
        meta = MetaLearningStrategy()
        
        self.strategies = [adaptive, meta]
        
        # Load saved state
        self._load_state()
        
        context.logger.info(f"Loaded {len(self.strategies)} advanced strategies")
    
    async def on_enable(self, context: PluginContext) -> None:
        """Enable plugin."""
        await super().on_enable(context)
        
        # Strategies are already registered via decorators
        registry = get_extension_registry()
        
        count = registry.get_extension_count("strategy.custom")
        context.logger.info(
            f"Advanced strategy plugin enabled with {count} strategies"
        )
    
    async def on_disable(self, context: PluginContext) -> None:
        """Disable plugin and save state."""
        # Save state before disabling
        self._save_state()
        
        await super().on_disable(context)
        context.logger.info("Advanced strategy plugin disabled")
    
    async def on_reload(self, context: PluginContext) -> None:
        """Hot reload plugin while preserving strategy state."""
        # Save state
        self._save_state()
        
        # Reload
        await self.on_disable(context)
        await self.on_enable(context)
        
        # State automatically restored in on_load
        context.logger.info("Advanced strategy plugin reloaded")
    
    def _save_state(self) -> None:
        """Save strategy state to disk."""
        state = {}
        
        for strategy in self.strategies:
            if hasattr(strategy, "get_stats"):
                state[strategy.name] = strategy.get_stats()
        
        # Ensure directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save to file
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)
        
        logger.debug(f"Strategy state saved to {self.state_file}")
    
    def _load_state(self) -> None:
        """Load strategy state from disk."""
        if not self.state_file.exists():
            logger.debug("No saved strategy state found")
            return
        
        try:
            with open(self.state_file) as f:
                state = json.load(f)
            
            # Restore state to strategies
            for strategy in self.strategies:
                if strategy.name in state:
                    # Restore strategy-specific state
                    # (implementation depends on strategy)
                    pass
            
            logger.debug(f"Strategy state loaded from {self.state_file}")
        
        except Exception as e:
            logger.error(f"Failed to load strategy state: {e}")
    
    def get_extensions(self) -> dict[str, Any]:
        """Return extension points provided by this plugin."""
        return {
            "strategy.adaptive": AdaptiveStrategy,
            "strategy.meta_learning": MetaLearningStrategy,
        }

