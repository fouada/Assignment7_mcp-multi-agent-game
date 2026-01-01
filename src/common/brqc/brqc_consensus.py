"""
BRQC: Byzantine-Resistant Quantum Consensus - Implementation

This module implements the BRQC algorithm proven in proofs/brqc_algorithm.md

Key Theorems Implemented:
- Theorem 4.1 (Safety): Never converges to incorrect strategy
- Theorem 5.1 (Liveness): Converges in O(√m log m) iterations
- Theorem 6.1 (Complexity): O(√m log m) time, O(n²m) messages/round
- Theorem 8.1 (Byzantine Tolerance): Tolerates f < n/3 Byzantine agents
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
import math


@dataclass
class BRQCAgent:
    """
    BRQC agent with quantum state and Byzantine detection

    Attributes:
        agent_id: Unique identifier for this agent
        num_strategies: Total number of strategies (m)
        optimal_strategy: Index of optimal strategy (known to honest agents only)
        is_byzantine: Whether this agent is Byzantine
        quantum_state: Complex amplitudes for each strategy (shape: m)
        confidence: Trust scores for other agents (confidence[j] ∈ [0,1])
        received_states: Quantum states received from other agents
        lambda_decay: Confidence decay rate for anomalies
        epsilon: Convergence threshold
    """

    agent_id: int
    num_strategies: int
    optimal_strategy: Optional[int] = None
    is_byzantine: bool = False

    # Quantum state: complex amplitudes
    quantum_state: np.ndarray = field(default=None, repr=False)

    # Byzantine detection
    confidence: Dict[int, float] = field(default_factory=dict, repr=False)

    # Received states from other agents
    received_states: Dict[int, np.ndarray] = field(default_factory=dict, repr=False)

    # Parameters
    lambda_decay: float = 0.15  # Confidence decay rate (higher = faster detection)
    epsilon: float = 0.01  # Convergence threshold

    def __post_init__(self):
        if self.quantum_state is None:
            # Initialize uniform superposition: |ψ⟩ = (1/√m, 1/√m, ..., 1/√m)
            self.quantum_state = np.ones(self.num_strategies, dtype=complex)
            self.quantum_state /= np.linalg.norm(self.quantum_state)

    def get_dominant_strategy(self) -> Tuple[int, float]:
        """
        Get the strategy with highest probability

        Returns:
            (strategy_index, probability)
        """
        probs = np.abs(self.quantum_state) ** 2
        dominant_idx = np.argmax(probs)
        return dominant_idx, probs[dominant_idx]

    def reset_confidence(self, num_agents: int):
        """Initialize confidence to full trust for all agents"""
        self.confidence = {j: 1.0 for j in range(num_agents)}
        self.confidence[self.agent_id] = 1.0  # Always trust self


class QuantumOperators:
    """
    Quantum operators for BRQC

    Implements Grover-like operators that amplify the optimal strategy's amplitude
    while suppressing others, providing O(√m) convergence speedup.
    """

    @staticmethod
    def grover_operator(state: np.ndarray, target: int) -> np.ndarray:
        """
        Apply Grover operator to amplify target strategy

        The operator consists of two steps:
        1. Phase flip: Flip phase of target amplitude
        2. Diffusion: Reflect around average amplitude

        This amplifies |target⟩ while suppressing others.

        Args:
            state: Current quantum state (normalized complex vector)
            target: Index of strategy to amplify

        Returns:
            New quantum state after Grover operator (normalized)
        """
        m = len(state)
        state = state.copy()

        # Step 1: Phase flip target
        # |ψ'⟩ = (I - 2|target⟩⟨target|)|ψ⟩
        state[target] *= -1

        # Step 2: Diffusion operator
        # D = 2|ψ_avg⟩⟨ψ_avg| - I
        # This reflects around the average amplitude
        avg = np.mean(state)
        state = 2 * avg - state

        # Normalize
        norm = np.linalg.norm(state)
        if norm > 0:
            state /= norm

        return state

    @staticmethod
    def apply_multiple_grover_steps(
        state: np.ndarray, target: int, num_steps: int = 1
    ) -> np.ndarray:
        """
        Apply multiple Grover iterations

        Each iteration amplifies target amplitude by O(1/√m).
        After O(√m) steps, target has amplitude ≈ 1.

        Args:
            state: Initial quantum state
            target: Target strategy index
            num_steps: Number of Grover iterations

        Returns:
            Quantum state after num_steps applications
        """
        for _ in range(num_steps):
            state = QuantumOperators.grover_operator(state, target)
        return state

    @staticmethod
    def weighted_average(
        states: Dict[int, np.ndarray], weights: Dict[int, float]
    ) -> np.ndarray:
        """
        Compute weighted average of quantum states

        This is the key fusion mechanism in BRQC:
        ψ̄ = Σ_j C(j) · ψ_j / Σ_j C(j)

        where C(j) is confidence in agent j.

        Args:
            states: Dictionary mapping agent_id -> quantum_state
            weights: Dictionary mapping agent_id -> confidence weight

        Returns:
            Weighted average quantum state (normalized)
        """
        # Handle edge case: no valid states
        if not states or not weights:
            m = len(next(iter(states.values()))) if states else 1
            return np.ones(m, dtype=complex) / np.sqrt(m)

        # Compute total weight
        total_weight = sum(weights.get(j, 0) for j in states.keys())
        if total_weight == 0:
            # If all weights zero, return uniform superposition
            m = len(next(iter(states.values())))
            return np.ones(m, dtype=complex) / np.sqrt(m)

        # Compute weighted sum
        weighted_sum = np.zeros_like(next(iter(states.values())), dtype=complex)
        for agent_id, state in states.items():
            weight = weights.get(agent_id, 0)
            weighted_sum += weight * state

        # Normalize by total weight
        weighted_sum /= total_weight

        # Renormalize to unit vector
        norm = np.linalg.norm(weighted_sum)
        if norm > 0:
            weighted_sum /= norm

        return weighted_sum


class ByzantineDetector:
    """
    Byzantine agent detection via statistical anomaly detection

    Detects Byzantine agents by:
    1. Computing majority quantum state from trusted agents
    2. Measuring deviation of each agent from majority
    3. Flagging agents with large deviations as suspicious
    """

    @staticmethod
    def detect_anomaly(
        agent_state: np.ndarray, majority_state: np.ndarray, threshold: float = 0.3
    ) -> float:
        """
        Compute anomaly score for an agent's state

        Measures L2 distance from majority state. Large distance indicates
        potential Byzantine behavior.

        Args:
            agent_state: Agent's reported quantum state
            majority_state: Consensus state from trusted agents
            threshold: Distance threshold for suspicion

        Returns:
            Anomaly score ∈ [0, 1]
            - 0.0 = perfectly aligned with majority
            - 1.0 = maximum deviation (likely Byzantine)
        """
        # L2 distance between quantum states
        distance = np.linalg.norm(agent_state - majority_state)

        # Maximum possible distance for normalized states = √2
        max_distance = np.sqrt(2)
        normalized_distance = distance / max_distance

        # Convert to anomaly score
        if normalized_distance < threshold:
            return 0.0
        else:
            # Linear scaling above threshold
            return min(1.0, (normalized_distance - threshold) / (1 - threshold))

    @staticmethod
    def is_normalized(state: np.ndarray, tolerance: float = 1e-6) -> bool:
        """
        Check if quantum state is properly normalized (||ψ|| = 1)

        Invalid normalization indicates Byzantine agent sending
        malformed states.

        Args:
            state: Quantum state to validate
            tolerance: Numerical tolerance for normalization check

        Returns:
            True if ||state|| ≈ 1, False otherwise
        """
        norm = np.linalg.norm(state)
        return abs(norm - 1.0) < tolerance

    @staticmethod
    def compute_majority_state(
        states: Dict[int, np.ndarray], confidence: Dict[int, float], min_confidence: float = 0.5
    ) -> np.ndarray:
        """
        Compute majority quantum state from trusted agents

        Only includes agents with confidence > min_confidence.

        Args:
            states: Agent quantum states
            confidence: Confidence scores for each agent
            min_confidence: Minimum confidence to include agent

        Returns:
            Weighted average of trusted agents' states
        """
        # Filter to trusted agents
        trusted_states = {
            j: s for j, s in states.items() if confidence.get(j, 0) > min_confidence
        }

        if not trusted_states:
            # No trusted agents - return uniform
            m = len(next(iter(states.values())))
            return np.ones(m, dtype=complex) / np.sqrt(m)

        # Weighted average
        return QuantumOperators.weighted_average(trusted_states, confidence)


class BRQCConsensus:
    """
    Main BRQC consensus protocol

    Implements the complete BRQC algorithm with:
    - Quantum superposition layer for O(√m) convergence
    - Byzantine detection layer for fault tolerance
    - Fusion layer combining both

    Guarantees (proven in proofs/brqc_algorithm.md):
    - Safety: Never converges to wrong strategy
    - Liveness: Converges in O(√m log m) iterations (f < n/3)
    - Optimality: Matches quantum lower bound
    - Byzantine Tolerance: f < n/3 (tight bound)
    """

    def __init__(
        self,
        num_agents: int,
        num_strategies: int,
        num_byzantine: int,
        optimal_strategy: int,
        byzantine_strategy: str = "random",
    ):
        """
        Initialize BRQC consensus

        Args:
            num_agents: Total number of agents (n)
            num_strategies: Number of strategies (m)
            num_byzantine: Number of Byzantine agents (f)
            optimal_strategy: Index of optimal strategy
            byzantine_strategy: Byzantine behavior type
                - "random": Random quantum states
                - "adversarial": Coordinated attack
                - "misleading": Favor wrong strategy
        """
        # Validate Byzantine tolerance bound: f < n/3
        if num_byzantine >= num_agents / 3:
            raise ValueError(
                f"Byzantine tolerance violated: f={num_byzantine} >= n/3={num_agents/3}. "
                f"BRQC requires f < n/3 (Theorem 8.1)"
            )

        self.num_agents = num_agents
        self.num_strategies = num_strategies
        self.num_byzantine = num_byzantine
        self.optimal_strategy = optimal_strategy
        self.byzantine_strategy = byzantine_strategy

        # Initialize agents
        self.agents: List[BRQCAgent] = []
        for i in range(num_agents):
            # First f agents are Byzantine
            is_byz = i < num_byzantine
            agent = BRQCAgent(
                agent_id=i,
                num_strategies=num_strategies,
                optimal_strategy=optimal_strategy if not is_byz else None,
                is_byzantine=is_byz,
            )
            agent.reset_confidence(num_agents)
            self.agents.append(agent)

        # Tracking
        self.iteration = 0
        self.convergence_history = []

    def run_iteration(self) -> bool:
        """
        Execute one iteration of BRQC protocol

        Protocol phases:
        1. Broadcast: Each agent broadcasts quantum state
        2. Receive & Validate: Validate received states
        3. Anomaly Detection: Update confidence scores
        4. Quantum Update: Apply Grover operator with weighted states
        5. Convergence Check: Check if consensus achieved

        Returns:
            True if converged, False otherwise
        """
        t = self.iteration

        # Phase 1: Broadcast
        messages = {}
        for agent in self.agents:
            if agent.is_byzantine:
                # Byzantine agents send adversarial messages
                msg = self._generate_byzantine_message(agent, t)
            else:
                # Honest agents send true quantum state
                msg = agent.quantum_state.copy()
            messages[agent.agent_id] = msg

        # Phase 2: Receive & Validate
        for agent in self.agents:
            if agent.is_byzantine:
                continue  # Byzantine agents don't update honestly

            agent.received_states = {}
            for j, msg in messages.items():
                # Validate normalization
                if not ByzantineDetector.is_normalized(msg):
                    # Invalid state - mark as Byzantine
                    agent.confidence[j] = 0.0
                    continue

                # Store received state
                agent.received_states[j] = msg

        # Phase 3: Anomaly Detection
        for agent in self.agents:
            if agent.is_byzantine:
                continue

            # Compute majority state from trusted agents
            majority = ByzantineDetector.compute_majority_state(
                agent.received_states, agent.confidence, min_confidence=0.5
            )

            # Update confidence based on deviation from majority
            for j, state in agent.received_states.items():
                anomaly = ByzantineDetector.detect_anomaly(
                    state, majority, threshold=0.3
                )

                # Decay confidence based on anomaly score
                # C(j, t+1) = C(j, t) · (1 - λ · anomaly)
                agent.confidence[j] *= 1 - agent.lambda_decay * anomaly

                # Clamp to [0, 1]
                agent.confidence[j] = max(0.0, min(1.0, agent.confidence[j]))

        # Phase 4: Quantum Update
        for agent in self.agents:
            if agent.is_byzantine:
                continue

            # Compute weighted average of received states
            # ψ̄ = Σ_j C(j) · ψ_j
            weighted_state = QuantumOperators.weighted_average(
                agent.received_states, agent.confidence
            )

            # Apply Grover operator to amplify optimal strategy
            # ψ' = G(ψ̄) where G is Grover operator
            new_state = QuantumOperators.grover_operator(
                weighted_state, agent.optimal_strategy
            )

            agent.quantum_state = new_state

        # Phase 5: Convergence Check
        converged = self._check_convergence()

        # Track convergence metrics
        self._record_iteration_metrics()

        self.iteration += 1
        return converged

    def _generate_byzantine_message(
        self, agent: BRQCAgent, t: int
    ) -> np.ndarray:
        """
        Generate Byzantine agent's message

        Different strategies:
        - "random": Random normalized quantum state
        - "adversarial": Coordinate to favor wrong strategy
        - "misleading": Send state favoring suboptimal strategy
        """
        if self.byzantine_strategy == "random":
            # Random state
            random_state = np.random.randn(self.num_strategies) + \
                          1j * np.random.randn(self.num_strategies)
            random_state /= np.linalg.norm(random_state)
            return random_state

        elif self.byzantine_strategy == "adversarial":
            # Favor wrong strategy (opposite of optimal)
            wrong_strategy = (self.optimal_strategy + 1) % self.num_strategies
            state = np.zeros(self.num_strategies, dtype=complex)
            state[wrong_strategy] = 1.0
            return state

        elif self.byzantine_strategy == "misleading":
            # Send plausible but wrong state
            state = np.ones(self.num_strategies, dtype=complex) / np.sqrt(
                self.num_strategies
            )
            # Slightly favor wrong strategy
            wrong = (self.optimal_strategy + 1) % self.num_strategies
            state[wrong] *= 1.5
            state /= np.linalg.norm(state)
            return state

        else:
            # Default: random
            return self._generate_byzantine_message(agent, t)

    def _check_convergence(self) -> bool:
        """
        Check if consensus achieved

        Consensus criterion (from Theorem 5.1):
        - At least 2f+1 honest agents agree on optimal strategy
        - Dominant strategy probability > 0.9
        - All agreeing agents have mutual confidence > 0.9
        """
        honest_agents = [a for a in self.agents if not a.is_byzantine]

        # Count agents with dominant strategy = optimal
        agreement_count = 0
        high_confidence_count = 0

        for agent in honest_agents:
            dominant, prob = agent.get_dominant_strategy()

            # Check if dominant strategy is optimal with high probability
            if dominant == self.optimal_strategy and prob > 0.9:
                agreement_count += 1

                # Check if agent has high confidence in other agreeing agents
                trusted_count = sum(
                    1
                    for j, conf in agent.confidence.items()
                    if conf > 0.9 and not self.agents[j].is_byzantine
                )

                if trusted_count >= self.num_agents - self.num_byzantine - 1:
                    high_confidence_count += 1

        # Need 2f+1 agreement for Byzantine quorum
        quorum = 2 * self.num_byzantine + 1

        # Convergence achieved if quorum reached with high confidence
        return agreement_count >= quorum and high_confidence_count >= quorum

    def _record_iteration_metrics(self):
        """Record metrics for analysis"""
        honest_agents = [a for a in self.agents if not a.is_byzantine]

        # Compute agreement on optimal strategy
        agreement = sum(
            1 for a in honest_agents if a.get_dominant_strategy()[0] == self.optimal_strategy
        )

        # Average confidence in honest agents
        avg_confidence = np.mean(
            [
                a.confidence[j]
                for a in honest_agents
                for j in range(self.num_agents)
                if not self.agents[j].is_byzantine and j != a.agent_id
            ]
        )

        # Average confidence in Byzantine agents (should decrease)
        avg_byz_confidence = np.mean(
            [
                a.confidence[j]
                for a in honest_agents
                for j in range(self.num_byzantine)
            ]
        ) if self.num_byzantine > 0 else 0.0

        self.convergence_history.append(
            {
                "iteration": self.iteration,
                "agreement": agreement,
                "avg_confidence_honest": avg_confidence,
                "avg_confidence_byzantine": avg_byz_confidence,
            }
        )

    def run(self, max_iterations: int = 1000) -> Tuple[bool, int, Optional[int]]:
        """
        Run BRQC until convergence or timeout

        Args:
            max_iterations: Maximum iterations before timeout

        Returns:
            (converged, iterations, consensus_strategy)
            - converged: True if consensus achieved
            - iterations: Number of iterations taken
            - consensus_strategy: Agreed strategy (or None if timeout)
        """
        for _ in range(max_iterations):
            if self.run_iteration():
                # Convergence achieved
                # Extract consensus from honest agents
                honest = [a for a in self.agents if not a.is_byzantine]
                consensus_strategy = honest[0].get_dominant_strategy()[0]
                return True, self.iteration, consensus_strategy

        # Timeout
        return False, max_iterations, None

    def get_theoretical_bound(self) -> float:
        """
        Compute theoretical convergence bound from Theorem 5.1

        T = O(√m log m)

        Returns:
            Theoretical upper bound on iterations
        """
        m = self.num_strategies
        # Use constants from empirical calibration (similar to Theorem 1)
        C = 2.5  # Constant factor
        bound = C * math.sqrt(m) * math.log(max(2, m))
        return bound
