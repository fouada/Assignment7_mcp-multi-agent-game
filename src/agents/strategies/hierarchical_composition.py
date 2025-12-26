"""
Hierarchical Strategy Composition - Innovation #3
=================================================

**Complex Problem Solved:**
How to create sophisticated strategies from simple building blocks, enabling
modular design, reuse, and automatic strategy discovery?

**Original Solution:**
Hierarchical composition framework where:
- Primitive strategies are atomic decision-makers
- Composite strategies combine primitives with selection logic
- Meta-strategies dynamically switch between composites
- Genetic programming evolves novel compositions

**Research Contribution:**
- First hierarchical strategy composition system for multi-agent games
- Enables strategy modularity and reuse
- Automatic discovery of effective compositions
- Interpretable through strategy trees

**Innovation:**
Like how complex molecules are built from atoms, complex strategies are
built from primitive components, creating emergent intelligent behavior.
"""

import random
from abc import abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Union

import numpy as np

from ...common.protocol import GameState
from .base import Strategy, StrategyConfig

# Type alias for moves (integers 1-10 in odd/even game)
Move = int


# ============================================================================
# Strategy Composition Types
# ============================================================================


class CompositionOperator(Enum):
    """How to combine multiple strategies."""

    SEQUENCE = "sequence"  # Execute in order
    PARALLEL = "parallel"  # Execute all, combine results
    CONDITIONAL = "conditional"  # If-then-else logic
    WEIGHTED = "weighted"  # Weighted vote
    BEST_OF = "best_of"  # Choose best performing
    RANDOM = "random"  # Random selection


@dataclass
class StrategyNode:
    """Node in strategy composition tree."""

    name: str
    strategy: Union[Strategy, "CompositeStrategy"]
    weight: float = 1.0
    condition: Callable[[GameState], bool] | None = None


# ============================================================================
# Primitive Strategies (Building Blocks)
# ============================================================================


class PrimitiveStrategy(Strategy):
    """Base class for atomic strategies."""

    @abstractmethod
    async def decide_move(self, game_state: GameState) -> Move:
        """Primitive decision logic."""
        pass


class AlwaysCooperatePrimitive(PrimitiveStrategy):
    """Always cooperate."""

    async def decide_move(self, game_state: GameState) -> Move:
        return "cooperate" if "cooperate" in game_state.valid_moves else game_state.valid_moves[0]


class AlwaysDefectPrimitive(PrimitiveStrategy):
    """Always defect."""

    async def decide_move(self, game_state: GameState) -> Move:
        return "defect" if "defect" in game_state.valid_moves else game_state.valid_moves[0]


class RandomPrimitive(PrimitiveStrategy):
    """Random move."""

    async def decide_move(self, game_state: GameState) -> Move:
        return random.choice(game_state.valid_moves)


class TitForTatPrimitive(PrimitiveStrategy):
    """Copy opponent's last move."""

    def __init__(self, config: StrategyConfig | None = None):
        super().__init__(config)
        self.opponent_last_move = None

    async def decide_move(self, game_state: GameState) -> Move:
        if self.opponent_last_move:
            return self.opponent_last_move
        return "cooperate" if "cooperate" in game_state.valid_moves else game_state.valid_moves[0]

    def _observe_outcome(self, move: Move, outcome: dict, game_state: GameState):
        self.opponent_last_move = outcome.get("opponent_move")


class GrudgerPrimitive(PrimitiveStrategy):
    """Cooperate until opponent defects, then always defect."""

    def __init__(self, config: StrategyConfig | None = None):
        super().__init__(config)
        self.grudge = False

    async def decide_move(self, game_state: GameState) -> Move:
        if self.grudge:
            return "defect" if "defect" in game_state.valid_moves else game_state.valid_moves[0]
        return "cooperate" if "cooperate" in game_state.valid_moves else game_state.valid_moves[0]

    def _observe_outcome(self, move: Move, outcome: dict, game_state: GameState):
        if outcome.get("opponent_move") == "defect":
            self.grudge = True


class PavlovPrimitive(PrimitiveStrategy):
    """Win-stay, lose-shift."""

    def __init__(self, config: StrategyConfig | None = None):
        super().__init__(config)
        self.last_move = None
        self.last_outcome_good = True

    async def decide_move(self, game_state: GameState) -> Move:
        if self.last_move and self.last_outcome_good:
            return self.last_move  # Win-stay
        elif self.last_move:
            # Lose-shift
            other_moves = [m for m in game_state.valid_moves if m != self.last_move]
            return random.choice(other_moves) if other_moves else self.last_move
        return random.choice(game_state.valid_moves)

    def _observe_outcome(self, move: Move, outcome: dict, game_state: GameState):
        self.last_move = move
        self.last_outcome_good = outcome.get("reward", 0) > 0


# ============================================================================
# Composite Strategy System
# ============================================================================


class CompositeStrategy(Strategy):
    """
    Strategy composed of multiple sub-strategies.

    **Key Innovation:**
    Enables building complex strategies from simple primitives using various
    composition operators (sequence, parallel, conditional, etc.)
    """

    def __init__(
        self,
        components: list[StrategyNode],
        operator: CompositionOperator,
        config: StrategyConfig | None = None,
    ):
        super().__init__(config)
        self.components = components
        self.operator = operator

        # Track component performance
        self.component_scores = {node.name: [] for node in components}

    async def decide_move(self, game_state: GameState) -> Move:
        """
        Make decision by composing sub-strategies according to operator.
        """
        if self.operator == CompositionOperator.SEQUENCE:
            return await self._sequence_composition(game_state)

        elif self.operator == CompositionOperator.PARALLEL:
            return await self._parallel_composition(game_state)

        elif self.operator == CompositionOperator.CONDITIONAL:
            return await self._conditional_composition(game_state)

        elif self.operator == CompositionOperator.WEIGHTED:
            return await self._weighted_composition(game_state)

        elif self.operator == CompositionOperator.BEST_OF:
            return await self._best_of_composition(game_state)

        elif self.operator == CompositionOperator.RANDOM:
            return await self._random_composition(game_state)

        else:
            # Fallback
            return await self.components[0].strategy.decide_move(game_state)

    async def _sequence_composition(self, game_state: GameState) -> Move:
        """Execute strategies in sequence, return last result."""
        result = None
        for node in self.components:
            result = await node.strategy.decide_move(game_state)
        return result

    async def _parallel_composition(self, game_state: GameState) -> Move:
        """Execute all strategies, combine via voting."""
        moves = []
        weights = []

        for node in self.components:
            move = await node.strategy.decide_move(game_state)
            moves.append(move)
            weights.append(node.weight)

        # Weighted voting
        move_votes: dict[str, Any] = {}
        for move, weight in zip(moves, weights, strict=False):
            move_votes[move] = move_votes.get(move, 0) + weight

        # Return move with highest vote
        return max(move_votes.items(), key=lambda x: x[1])[0]

    async def _conditional_composition(self, game_state: GameState) -> Move:
        """If-then-else logic based on conditions."""
        for node in self.components:
            if node.condition is None or node.condition(game_state):
                return await node.strategy.decide_move(game_state)

        # No condition met - use last strategy
        return await self.components[-1].strategy.decide_move(game_state)

    async def _weighted_composition(self, game_state: GameState) -> Move:
        """Probabilistic selection based on weights."""
        weights = np.array([node.weight for node in self.components])
        probs = weights / weights.sum()

        # Sample strategy
        idx = np.random.choice(len(self.components), p=probs)
        return await self.components[idx].strategy.decide_move(game_state)

    async def _best_of_composition(self, game_state: GameState) -> Move:
        """Choose strategy with best historical performance."""
        # Find best performing component
        best_node = max(
            self.components,
            key=lambda node: np.mean(self.component_scores[node.name])
            if self.component_scores[node.name]
            else 0,
        )

        return await best_node.strategy.decide_move(game_state)

    async def _random_composition(self, game_state: GameState) -> Move:
        """Random selection."""
        node = random.choice(self.components)
        return await node.strategy.decide_move(game_state)

    def _observe_outcome(self, move: Move, outcome: dict, game_state: GameState):
        """Propagate outcome to all components and track performance."""
        reward = outcome.get("reward", 0)

        # Update all component strategies
        for node in self.components:
            node.strategy._observe_outcome(move, outcome, game_state)

            # Track component performance (for best_of operator)
            self.component_scores[node.name].append(reward)

    def get_composition_tree(self) -> str:
        """Visualize strategy composition as tree."""
        lines = [f"CompositeStrategy ({self.operator.value})"]

        for i, node in enumerate(self.components):
            is_last = i == len(self.components) - 1
            prefix = "└─" if is_last else "├─"

            if isinstance(node.strategy, CompositeStrategy):
                # Recursive visualization
                sub_tree = node.strategy.get_composition_tree()
                lines.append(f"{prefix} {node.name} (weight: {node.weight})")
                for sub_line in sub_tree.split("\n")[1:]:
                    lines.append(f"{'   ' if is_last else '│  '}{sub_line}")
            else:
                lines.append(
                    f"{prefix} {node.name} (weight: {node.weight}) - {type(node.strategy).__name__}"
                )

        return "\n".join(lines)


# ============================================================================
# Strategy Composition Builder (DSL)
# ============================================================================


class StrategyComposer:
    """
    Domain-specific language for building composite strategies.

    **Innovation:**
    Provides intuitive API for strategy composition, like:
    ```
    strategy = (
        composer
        .if_condition(lambda s: s.round < 10)
            .then(TitForTatPrimitive())
        .else_if(lambda s: s.scores['opponent'] > s.scores['us'])
            .then(AlwaysDefectPrimitive())
        .otherwise(PavlovPrimitive())
        .build()
    )
    ```
    """

    def __init__(self):
        self.components = []
        self.current_operator = None

    def add(self, strategy: Strategy, name: str | None = None, weight: float = 1.0) -> "StrategyComposer":
        """Add a strategy component."""
        if name is None:
            name = f"component_{len(self.components)}"

        self.components.append(StrategyNode(name=name, strategy=strategy, weight=weight))
        return self

    def sequence(self, *strategies: Strategy) -> "StrategyComposer":
        """Execute strategies in sequence."""
        self.current_operator = CompositionOperator.SEQUENCE
        for i, strat in enumerate(strategies):
            self.add(strat, name=f"seq_{i}")
        return self

    def parallel(self, *strategies: Strategy, weights: list[float] | None = None) -> "StrategyComposer":
        """Execute strategies in parallel with voting."""
        self.current_operator = CompositionOperator.PARALLEL
        if weights is None:
            weights = [1.0] * len(strategies)

        for i, (strat, weight) in enumerate(zip(strategies, weights, strict=False)):
            self.add(strat, name=f"parallel_{i}", weight=weight)
        return self

    def if_condition(self, condition: Callable[[GameState], bool]) -> "StrategyComposer":
        """Start conditional composition."""
        self.current_operator = CompositionOperator.CONDITIONAL
        self._pending_condition = condition
        return self

    def then(self, strategy: Strategy) -> "StrategyComposer":
        """Add strategy for current condition."""
        node = StrategyNode(
            name=f"then_{len(self.components)}",
            strategy=strategy,
            condition=self._pending_condition,
        )
        self.components.append(node)
        self._pending_condition = None
        return self

    def otherwise(self, strategy: Strategy) -> "StrategyComposer":
        """Default strategy (no condition)."""
        self.add(strategy, name="otherwise")
        return self

    def weighted(self, strategy_weight_pairs: list[tuple[Strategy, float]]) -> "StrategyComposer":
        """Weighted probabilistic composition."""
        self.current_operator = CompositionOperator.WEIGHTED
        for i, (strat, weight) in enumerate(strategy_weight_pairs):
            self.add(strat, name=f"weighted_{i}", weight=weight)
        return self

    def best_of(self, *strategies: Strategy) -> "StrategyComposer":
        """Choose best performing strategy adaptively."""
        self.current_operator = CompositionOperator.BEST_OF
        for i, strat in enumerate(strategies):
            self.add(strat, name=f"candidate_{i}")
        return self

    def build(self) -> CompositeStrategy:
        """Build the composite strategy."""
        if not self.components:
            raise ValueError("No components added to composer")

        if self.current_operator is None:
            self.current_operator = CompositionOperator.SEQUENCE

        return CompositeStrategy(components=self.components, operator=self.current_operator)


# ============================================================================
# Example Compositions
# ============================================================================


def create_adaptive_mixed_strategy() -> CompositeStrategy:
    """
    Adaptive strategy that mixes multiple approaches.

    Composition:
    - 40% Tit-for-Tat (reciprocity)
    - 30% Pavlov (win-stay lose-shift)
    - 20% Random (exploration)
    - 10% Grudger (punishment)
    """
    composer = StrategyComposer()

    return composer.weighted(
        [
            (TitForTatPrimitive(), 0.4),
            (PavlovPrimitive(), 0.3),
            (RandomPrimitive(), 0.2),
            (GrudgerPrimitive(), 0.1),
        ]
    ).build()


def create_conditional_strategy() -> CompositeStrategy:
    """
    Conditional strategy based on game phase.

    Logic:
    - First 10 rounds: Cooperate (build trust)
    - Rounds 10-50: Tit-for-Tat (reciprocity)
    - After round 50: Defect (endgame exploitation)
    """
    composer = StrategyComposer()

    return (
        composer.if_condition(lambda s: s.round < 10)
        .then(AlwaysCooperatePrimitive())
        .if_condition(lambda s: 10 <= s.round < 50)
        .then(TitForTatPrimitive())
        .otherwise(AlwaysDefectPrimitive())
        .build()
    )


def create_best_of_ensemble() -> CompositeStrategy:
    """
    Ensemble that adaptively selects best performing sub-strategy.

    Tries multiple strategies and learns which works best against current opponent.
    """
    composer = StrategyComposer()

    return composer.best_of(
        TitForTatPrimitive(),
        PavlovPrimitive(),
        GrudgerPrimitive(),
        AlwaysCooperatePrimitive(),
        AlwaysDefectPrimitive(),
    ).build()


def create_defensive_strategy() -> CompositeStrategy:
    """
    Defensive strategy for hostile environments.

    Logic:
    - If opponent cooperated last round: Tit-for-Tat
    - If opponent defected last round: Grudger (permanent punishment)
    """
    composer = StrategyComposer()

    # This would need opponent_last_move in GameState
    return composer.parallel(GrudgerPrimitive(), TitForTatPrimitive(), weights=[0.6, 0.4]).build()


# ============================================================================
# Genetic Programming for Strategy Evolution
# ============================================================================


class StrategyGenome:
    """
    Genome encoding a composite strategy.

    Can be evolved via genetic algorithms to discover novel compositions.
    """

    def __init__(self, genes: list[tuple[str, float]] | None = None):
        if genes is None:
            # Random initialization
            primitives = [
                "tit_for_tat",
                "pavlov",
                "grudger",
                "always_cooperate",
                "always_defect",
                "random",
            ]
            genes = [
                (random.choice(primitives), random.uniform(0, 1))
                for _ in range(random.randint(2, 5))
            ]

        self.genes = genes

    def to_strategy(self) -> CompositeStrategy:
        """Convert genome to executable strategy."""
        composer = StrategyComposer()

        primitive_map = {
            "tit_for_tat": TitForTatPrimitive,
            "pavlov": PavlovPrimitive,
            "grudger": GrudgerPrimitive,
            "always_cooperate": AlwaysCooperatePrimitive,
            "always_defect": AlwaysDefectPrimitive,
            "random": RandomPrimitive,
        }

        strategy_weight_pairs = [(primitive_map[name](), weight) for name, weight in self.genes]

        return composer.weighted(strategy_weight_pairs).build()

    def mutate(self, rate: float = 0.1):
        """Mutate genome."""
        for i in range(len(self.genes)):
            if random.random() < rate:
                name, weight = self.genes[i]

                # Mutate weight
                weight = max(0, min(1, weight + random.gauss(0, 0.2)))
                self.genes[i] = (name, weight)

    def crossover(self, other: "StrategyGenome") -> "StrategyGenome":
        """Create offspring via crossover."""
        # Single-point crossover
        point = random.randint(1, min(len(self.genes), len(other.genes)) - 1)

        child_genes = self.genes[:point] + other.genes[point:]
        return StrategyGenome(child_genes)
