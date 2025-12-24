"""
Quantum Strategy Plugin Example
================================

Demonstrates how to create a custom strategy plugin using the @strategy_plugin decorator.

This strategy uses quantum-inspired superposition and wave function collapse concepts
to make decisions. It's a creative interpretation, not actual quantum computing!

Usage:
    # 1. Register the plugin (just import this module)
    from examples.plugins import quantum_strategy_plugin

    # 2. Use it like any other strategy
    from src.agents.strategies import create_strategy
    strategy = create_strategy("quantum")

    # Or with StrategyFactory
    from src.agents.strategies import StrategyFactory
    strategy = StrategyFactory.create_from_string("quantum")
"""

import random
import math
from typing import List, Dict, Any

# Import from the main project
from src.agents.strategies import Strategy, StrategyConfig, strategy_plugin
from src.agents.player import GameRole
from src.common.plugins import PluginInterface, PluginMetadata, PluginContext
from src.common.logger import get_logger

logger = get_logger(__name__)


@strategy_plugin(
    name="quantum",
    version="1.0.0",
    description="Quantum-inspired superposition strategy with wave function collapse",
    category="experimental"
)
class QuantumStrategy(Strategy):
    """
    Quantum-inspired strategy that maintains multiple potential moves in superposition.

    Concept:
    - Each possible move has an "amplitude" (probability amplitude, quantum-inspired)
    - Amplitudes are influenced by game history (constructive/destructive interference)
    - On decision time, the "wave function collapses" to a single move
    - Uses interference patterns to avoid opponent's observed tendencies

    This is a creative interpretation for educational purposes, not actual quantum computing!
    """

    def __init__(self, config: StrategyConfig = None):
        """
        Initialize quantum strategy.

        Args:
            config: Strategy configuration
        """
        super().__init__(config)
        self._name = "QuantumStrategy"

        # Quantum-inspired parameters
        self.superposition_size = 5  # Number of moves in superposition
        self.decoherence_rate = 0.1  # Rate at which superposition decays
        self.entanglement_factor = 0.3  # How much opponent history affects our state

        logger.info("QuantumStrategy initialized")

    async def decide_move(
        self,
        game_id: str,
        round_number: int,
        my_role: GameRole,
        my_score: int,
        opponent_score: int,
        history: List[Dict[str, Any]],
    ) -> int:
        """
        Decide move using quantum-inspired superposition collapse.

        Args:
            game_id: Game identifier
            round_number: Current round number
            my_role: Our role (ODD or EVEN)
            my_score: Our current score
            opponent_score: Opponent's score
            history: Game history

        Returns:
            Selected move (1-10)
        """
        # All possible moves (in superposition)
        moves = list(range(self.config.min_value, self.config.max_value + 1))

        # Calculate quantum amplitude for each move
        amplitudes = self._calculate_amplitudes(moves, history, my_role)

        # Apply decoherence (noise)
        amplitudes = self._apply_decoherence(amplitudes)

        # Normalize to probabilities (Born rule: |amplitude|^2)
        probabilities = self._amplitudes_to_probabilities(amplitudes)

        # Collapse wave function (weighted random choice)
        move = self._collapse_wave_function(moves, probabilities)

        logger.debug(
            f"Quantum collapse: selected {move} from superposition",
            game_id=game_id,
            round=round_number,
        )

        return move

    def _calculate_amplitudes(
        self,
        moves: List[int],
        history: List[Dict[str, Any]],
        my_role: GameRole,
    ) -> Dict[int, float]:
        """
        Calculate quantum amplitudes for each move.

        Uses interference patterns based on game history.

        Args:
            moves: List of possible moves
            history: Game history
            my_role: Our role

        Returns:
            Dictionary mapping moves to amplitudes
        """
        amplitudes = {}

        for move in moves:
            # Start with base amplitude (equal superposition)
            amplitude = 1.0

            # Apply interference from history
            for h in history[-5:]:  # Last 5 rounds (limited memory)
                opponent_move = h.get("opponent_move", 0)
                if opponent_move == 0:
                    continue

                # Calculate phase difference
                phase_diff = abs(move - opponent_move)

                # Constructive/destructive interference
                # cos gives oscillation between constructive (+1) and destructive (-1)
                interference = math.cos(phase_diff * math.pi / 5)

                # Apply entanglement factor
                amplitude *= (1 + self.entanglement_factor * interference)

            # Ensure positive amplitude
            amplitudes[move] = max(abs(amplitude), 0.01)

        return amplitudes

    def _apply_decoherence(self, amplitudes: Dict[int, float]) -> Dict[int, float]:
        """
        Apply quantum decoherence (noise/uncertainty).

        Args:
            amplitudes: Original amplitudes

        Returns:
            Noisy amplitudes
        """
        noisy_amplitudes = {}

        for move, amplitude in amplitudes.items():
            # Add random noise (decoherence)
            noise = random.gauss(0, self.decoherence_rate)
            noisy_amplitude = amplitude * (1 + noise)
            noisy_amplitudes[move] = max(noisy_amplitude, 0.01)

        return noisy_amplitudes

    def _amplitudes_to_probabilities(
        self, amplitudes: Dict[int, float]
    ) -> Dict[int, float]:
        """
        Convert amplitudes to probabilities using Born rule.

        Born rule: probability = |amplitude|^2

        Args:
            amplitudes: Amplitude dictionary

        Returns:
            Probability dictionary (normalized)
        """
        # Square amplitudes (Born rule)
        probabilities = {move: amp**2 for move, amp in amplitudes.items()}

        # Normalize
        total = sum(probabilities.values())
        if total > 0:
            probabilities = {move: prob / total for move, prob in probabilities.items()}
        else:
            # Fallback to uniform
            uniform_prob = 1.0 / len(probabilities)
            probabilities = {move: uniform_prob for move in probabilities.keys()}

        return probabilities

    def _collapse_wave_function(
        self, moves: List[int], probabilities: Dict[int, float]
    ) -> int:
        """
        Collapse wave function to single move (measurement).

        Args:
            moves: List of possible moves
            probabilities: Probability for each move

        Returns:
            Selected move
        """
        # Weighted random choice
        return random.choices(
            population=moves, weights=[probabilities[m] for m in moves], k=1
        )[0]


# Optional: Wrap in PluginInterface for full plugin lifecycle support


class QuantumStrategyPlugin(PluginInterface):
    """
    Full plugin wrapper for quantum strategy.

    This demonstrates how to create a complete plugin with lifecycle management.
    The @strategy_plugin decorator is sufficient for most cases, but this shows
    the full plugin interface.
    """

    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="quantum-strategy-plugin",
            version="1.0.0",
            author="Example Author",
            description="Quantum-inspired game strategy plugin demonstrating wave function collapse and interference",
            dependencies=[],
            entry_point="quantum_strategy_plugin:QuantumStrategyPlugin",
        )

    async def on_load(self, context: PluginContext) -> None:
        """Called when plugin is loaded."""
        await super().on_load(context)
        context.logger.info("Quantum strategy plugin loaded")

    async def on_enable(self, context: PluginContext) -> None:
        """Called when plugin is enabled."""
        await super().on_enable(context)
        context.logger.info("Quantum strategy plugin enabled")

        # Register strategy with registry (already done by decorator)
        from src.agents.strategies import get_strategy_plugin_registry

        registry = get_strategy_plugin_registry()
        if not registry.is_registered("quantum"):
            context.logger.warning("Quantum strategy not registered!")

    async def on_disable(self, context: PluginContext) -> None:
        """Called when plugin is disabled."""
        await super().on_disable(context)
        context.logger.info("Quantum strategy plugin disabled")

    async def on_unload(self, context: PluginContext) -> None:
        """Called before plugin is unloaded."""
        await super().on_unload(context)
        context.logger.info("Quantum strategy plugin unloaded")


# Example usage
if __name__ == "__main__":
    import asyncio

    async def test_quantum_strategy():
        """Test the quantum strategy."""
        print("Testing Quantum Strategy Plugin...")

        # Create strategy
        config = StrategyConfig(min_value=1, max_value=10)
        strategy = QuantumStrategy(config=config)

        # Simulate a decision
        history = [
            {"round": 1, "my_move": 5, "opponent_move": 7, "winner": "opponent"},
            {"round": 2, "my_move": 3, "opponent_move": 4, "winner": "me"},
            {"round": 3, "my_move": 8, "opponent_move": 2, "winner": "opponent"},
        ]

        move = await strategy.decide_move(
            game_id="test_game",
            round_number=4,
            my_role=GameRole.ODD,
            my_score=1,
            opponent_score=2,
            history=history,
        )

        print(f"Quantum strategy selected move: {move}")
        print("✅ Quantum strategy works!")

    # Run test
    asyncio.run(test_quantum_strategy())
