"""
Causal Multi-Agent Reasoning (CMAR)

First framework applying Pearl's causal inference to multi-agent games.

Key components:
- CausalGraph: DAG representation of causal relationships
- StructuralCausalModel: SCM with structural equations
- CausalDiscovery: PC algorithm for learning causal graphs
- CausalInference: Do-calculus and effect estimation
- CausalAgent: Agent with causal reasoning capabilities
"""

from .causal_framework import (
    CausalGraph,
    StructuralCausalModel,
    CausalInference,
    CausalAgent,
    CausalLearningMetrics,
    create_game_causal_graph,
    create_synthetic_scm,
)

__all__ = [
    "CausalGraph",
    "StructuralCausalModel",
    "CausalInference",
    "CausalAgent",
    "CausalLearningMetrics",
    "create_game_causal_graph",
    "create_synthetic_scm",
]
