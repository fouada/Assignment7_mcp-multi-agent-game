"""
Base Strategy Classes
=====================

Defines the core interfaces and base classes for all game strategies.

Key Concepts:
- Strategy: Abstract base class for all strategies
- GameTheoryStrategy: Base class with opponent modeling for game theory strategies
- ParityChoice: Enum for ODD/EVEN parity decisions
- OpponentModel: Tracks opponent's behavior for exploitation
"""

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ...common.logger import get_logger
from ..player import GameRole

logger = get_logger(__name__)


class ParityChoice(Enum):
    """
    Represents the parity of a move.

    In Odd/Even game, what matters is not the specific number,
    but whether it's odd or even.
    """

    ODD = "odd"
    EVEN = "even"

    @classmethod
    def from_number(cls, n: int) -> "ParityChoice":
        """Convert a number to its parity."""
        return cls.ODD if n % 2 == 1 else cls.EVEN

    def to_number(self, min_val: int = 1, max_val: int = 10) -> int:
        """
        Convert parity choice to a random number with that parity.

        Args:
            min_val: Minimum value (default 1)
            max_val: Maximum value (default 10)

        Returns:
            Random number with the desired parity
        """
        if self == ParityChoice.ODD:
            candidates = [n for n in range(min_val, max_val + 1) if n % 2 == 1]
        else:
            candidates = [n for n in range(min_val, max_val + 1) if n % 2 == 0]
        return random.choice(candidates) if candidates else min_val

    def opposite(self) -> "ParityChoice":
        """Return the opposite parity."""
        return ParityChoice.EVEN if self == ParityChoice.ODD else ParityChoice.ODD


@dataclass
class OpponentModel:
    """
    Model of opponent's behavior for exploitation.

    Tracks:
    - Parity frequency (how often they play odd vs even)
    - Sequence patterns (do they alternate? repeat?)
    - Conditional patterns (what do they play after winning/losing?)
    """

    # Parity counts
    odd_count: int = 0
    even_count: int = 0

    # Sequential patterns
    last_parities: list[ParityChoice] = field(default_factory=list)
    max_history: int = 20

    # Conditional patterns
    after_win_odd: int = 0
    after_win_even: int = 0
    after_loss_odd: int = 0
    after_loss_even: int = 0

    # Last outcome for conditional tracking
    last_won: bool | None = None

    def update(self, opponent_move: int, i_won: bool) -> None:
        """
        Update model with opponent's move and outcome.

        Args:
            opponent_move: The number opponent played
            i_won: Whether we won this round
        """
        parity = ParityChoice.from_number(opponent_move)

        # Update basic counts
        if parity == ParityChoice.ODD:
            self.odd_count += 1
        else:
            self.even_count += 1

        # Update conditional patterns (based on previous outcome)
        if self.last_won is not None:
            if self.last_won:  # Opponent lost last round
                if parity == ParityChoice.ODD:
                    self.after_loss_odd += 1
                else:
                    self.after_loss_even += 1
            else:  # Opponent won last round
                if parity == ParityChoice.ODD:
                    self.after_win_odd += 1
                else:
                    self.after_win_even += 1

        # Update sequence
        self.last_parities.append(parity)
        if len(self.last_parities) > self.max_history:
            self.last_parities.pop(0)

        # Remember outcome for next update
        self.last_won = i_won

    @property
    def total_observations(self) -> int:
        """Total number of opponent moves observed."""
        return self.odd_count + self.even_count

    @property
    def odd_probability(self) -> float:
        """
        Estimated probability that opponent plays odd.

        Returns 0.5 if no observations (prior).
        """
        total = self.total_observations
        if total == 0:
            return 0.5
        return self.odd_count / total

    @property
    def even_probability(self) -> float:
        """Estimated probability that opponent plays even."""
        return 1.0 - self.odd_probability

    def conditional_odd_probability(self, i_won_last: bool) -> float:
        """
        Probability opponent plays odd given last outcome.

        Args:
            i_won_last: Whether we won the last round
        """
        if i_won_last:
            # Opponent lost last round
            total = self.after_loss_odd + self.after_loss_even
            if total == 0:
                return 0.5
            return self.after_loss_odd / total
        else:
            # Opponent won last round
            total = self.after_win_odd + self.after_win_even
            if total == 0:
                return 0.5
            return self.after_win_odd / total

    def get_bias_strength(self) -> float:
        """
        How biased is the opponent? 0 = perfectly balanced, 1 = always one parity.

        Uses absolute deviation from 0.5.
        """
        return abs(self.odd_probability - 0.5) * 2

    def reset(self) -> None:
        """Reset all observations."""
        self.odd_count = 0
        self.even_count = 0
        self.last_parities.clear()
        self.after_win_odd = 0
        self.after_win_even = 0
        self.after_loss_odd = 0
        self.after_loss_even = 0
        self.last_won = None


@dataclass
class StrategyConfig:
    """
    Configuration for strategy behavior.

    Used to tune strategy parameters without code changes.
    """

    # Number range for moves
    min_value: int = 1
    max_value: int = 10

    # Exploration vs exploitation
    exploration_rate: float = 0.2  # ε for ε-greedy

    # Confidence thresholds
    confidence_threshold: float = 0.7  # When to switch from Nash to exploitive
    min_observations: int = 3  # Minimum data before exploiting

    # Learning rates
    learning_rate: float = 0.1  # For regret matching
    decay_rate: float = 0.99  # For time-weighted observations

    # UCB specific
    ucb_exploration_constant: float = 1.414  # sqrt(2) is theoretically optimal

    # Thompson Sampling specific
    prior_alpha: float = 1.0  # Beta distribution prior
    prior_beta: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "min_value": self.min_value,
            "max_value": self.max_value,
            "exploration_rate": self.exploration_rate,
            "confidence_threshold": self.confidence_threshold,
            "min_observations": self.min_observations,
            "learning_rate": self.learning_rate,
            "decay_rate": self.decay_rate,
            "ucb_exploration_constant": self.ucb_exploration_constant,
            "prior_alpha": self.prior_alpha,
            "prior_beta": self.prior_beta,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StrategyConfig":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class Strategy(ABC):
    """
    Abstract base class for all player strategies.

    Defines the interface that all strategies must implement.
    """

    def __init__(self, config: StrategyConfig | None = None):
        self.config = config or StrategyConfig()
        self._name = self.__class__.__name__
        self._player_id: str | None = None  # Set by player agent
        self._event_bus = None  # Set by player agent

    @property
    def name(self) -> str:
        """Strategy name for logging and display."""
        return self._name

    def set_player_context(self, player_id: str, event_bus: Any = None) -> None:
        """
        Set player context for event emission.
        
        Args:
            player_id: ID of the player using this strategy
            event_bus: Event bus for emitting learning events
        """
        self._player_id = player_id
        self._event_bus = event_bus

    @abstractmethod
    async def decide_move(
        self,
        game_id: str,
        round_number: int,
        my_role: GameRole,
        my_score: int,
        opponent_score: int,
        history: list[dict],
    ) -> int:
        """
        Decide what move to make.

        Args:
            game_id: Current game ID
            round_number: Current round number (1-indexed)
            my_role: My assigned role (ODD or EVEN)
            my_score: My current score in this match
            opponent_score: Opponent's current score
            history: List of previous rounds with keys:
                     - round: round number
                     - my_move: our move
                     - opponent_move: their move
                     - sum: sum of moves
                     - winner: winner's player_id

        Returns:
            Move value (within config.min_value to config.max_value)
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset strategy state for a new game."""
        pass

    def get_stats(self) -> dict[str, Any]:
        """Get strategy statistics for debugging/analysis."""
        return {"strategy": self.name}


class GameTheoryStrategy(Strategy):
    """
    Base class for game-theory-informed strategies.

    Provides:
    - Opponent modeling
    - Parity-based decision making
    - Common utilities for game theory calculations
    """

    def __init__(self, config: StrategyConfig | None = None):
        super().__init__(config)
        self.opponent_model = OpponentModel()
        self._games: dict[str, OpponentModel] = {}  # Per-game models

    def _get_opponent_model(self, game_id: str) -> OpponentModel:
        """Get or create opponent model for a specific game."""
        if game_id not in self._games:
            self._games[game_id] = OpponentModel()
        return self._games[game_id]

    def _update_opponent_model(
        self,
        game_id: str,
        history: list[dict],
        my_role: GameRole,
    ) -> OpponentModel:
        """
        Update opponent model from game history.

        Returns the updated model.
        """
        model = self._get_opponent_model(game_id)

        # Find new observations (not yet processed)
        processed = model.total_observations
        new_history = history[processed:]

        for h in new_history:
            opponent_move = h.get("opponent_move")
            h.get("winner")

            if opponent_move is not None:
                # Determine if we won
                # This is tricky - we need to know our player_id
                # For now, use parity logic
                my_move = h.get("my_move", 0)
                total = my_move + opponent_move
                sum_is_odd = total % 2 == 1

                if my_role == GameRole.ODD:
                    i_won = sum_is_odd
                else:
                    i_won = not sum_is_odd

                model.update(opponent_move, i_won)

        return model

    def _decide_parity(
        self,
        my_role: GameRole,
        opponent_model: OpponentModel,
    ) -> ParityChoice:
        """
        Decide which parity to play based on role and opponent model.

        This is the core game theory logic - subclasses can override.

        Args:
            my_role: Our assigned role (ODD or EVEN)
            opponent_model: Model of opponent's behavior

        Returns:
            ParityChoice indicating what parity we should play
        """
        # Default: Nash equilibrium (50/50)
        return ParityChoice.ODD if random.random() < 0.5 else ParityChoice.EVEN

    def _parity_to_move(self, parity: ParityChoice) -> int:
        """Convert parity choice to actual move number."""
        return parity.to_number(self.config.min_value, self.config.max_value)

    def _calculate_best_response_parity(
        self,
        my_role: GameRole,
        prob_opponent_odd: float,
    ) -> ParityChoice:
        """
        Calculate the best response parity given opponent's tendencies.

        Game theory logic:
        - ODD player wins when sum is odd
          - ODD + EVEN = ODD (we win)
          - EVEN + ODD = ODD (we win)
          - So: play opposite of opponent's likely parity

        - EVEN player wins when sum is even
          - ODD + ODD = EVEN (we win)
          - EVEN + EVEN = EVEN (we win)
          - So: play same as opponent's likely parity

        Args:
            my_role: Our assigned role
            prob_opponent_odd: Probability opponent plays odd

        Returns:
            Best response parity
        """
        opponent_likely_odd = prob_opponent_odd > 0.5

        if my_role == GameRole.ODD:
            # We want sum to be odd
            # Play OPPOSITE of opponent's likely parity
            if opponent_likely_odd:
                return ParityChoice.EVEN  # ODD + EVEN = ODD ✓
            else:
                return ParityChoice.ODD  # ODD + EVEN = ODD ✓
        else:
            # We want sum to be even
            # Play SAME as opponent's likely parity
            if opponent_likely_odd:
                return ParityChoice.ODD  # ODD + ODD = EVEN ✓
            else:
                return ParityChoice.EVEN  # EVEN + EVEN = EVEN ✓

    async def decide_move(
        self,
        game_id: str,
        round_number: int,
        my_role: GameRole,
        my_score: int,
        opponent_score: int,
        history: list[dict],
    ) -> int:
        """
        Main decision method using game theory.

        1. Update opponent model
        2. Decide parity using game theory
        3. Convert to actual move
        """
        # Update opponent model
        model = self._update_opponent_model(game_id, history, my_role)

        # Decide parity (subclasses implement specific logic)
        parity = self._decide_parity(my_role, model)

        # Convert to move
        move = self._parity_to_move(parity)

        logger.debug(
            f"[{self.name}] Game {game_id} R{round_number}: "
            f"role={my_role.value}, parity={parity.value}, move={move}"
        )

        return move

    def reset(self) -> None:
        """Reset all game models."""
        self._games.clear()
        self.opponent_model.reset()

    def get_stats(self) -> dict[str, Any]:
        """Get strategy statistics."""
        stats = super().get_stats()
        stats.update(
            {
                "games_tracked": len(self._games),
                "total_observations": sum(m.total_observations for m in self._games.values()),
            }
        )
        return stats
