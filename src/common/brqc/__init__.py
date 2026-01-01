"""
BRQC: Byzantine-Resistant Quantum Consensus

World-first consensus algorithm achieving BOTH:
1. O(√n) quantum speedup
2. Byzantine fault tolerance (f < n/3)

Key components:
- BRQCAgent: Agent with quantum state + Byzantine detection
- QuantumOperators: Grover-like operators for amplification
- ByzantineDetector: Statistical anomaly detection
- BRQCConsensus: Main consensus protocol
"""

from .brqc_consensus import (
    BRQCAgent,
    QuantumOperators,
    ByzantineDetector,
    BRQCConsensus,
)

__all__ = [
    "BRQCAgent",
    "QuantumOperators",
    "ByzantineDetector",
    "BRQCConsensus",
]
