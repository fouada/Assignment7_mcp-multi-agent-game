"""
Strategy Framework
==================

Complete strategy framework for player agents including:
- Classic strategies (Random, Pattern, LLM)
- Game theory strategies (Nash, Best Response, Bayesian, etc.)

Usage:
    from src.agents.strategies import StrategyFactory, StrategyType
    
    # Create a strategy
    strategy = StrategyFactory.create(StrategyType.ADAPTIVE_BAYESIAN)
    
    # Or use convenience function
    from src.agents.strategies import create_strategy
    strategy = create_strategy("adaptive-bayesian")
"""

from .base import (
    Strategy,
    GameTheoryStrategy,
    StrategyConfig,
    OpponentModel,
    ParityChoice,
)

from .classic import (
    RandomStrategy,
    PatternStrategy,
    LLMStrategy,
)

from .game_theory import (
    NashEquilibriumStrategy,
    BestResponseStrategy,
    AdaptiveBayesianStrategy,
    FictitiousPlayStrategy,
    RegretMatchingStrategy,
    UCBStrategy,
    ThompsonSamplingStrategy,
)

from .factory import (
    StrategyType,
    StrategyFactory,
    create_strategy,
    list_strategies,
    get_recommended,
)

__all__ = [
    # Base classes
    "Strategy",
    "GameTheoryStrategy",
    "StrategyConfig",
    "OpponentModel",
    "ParityChoice",
    # Classic strategies
    "RandomStrategy",
    "PatternStrategy",
    "LLMStrategy",
    # Game theory strategies
    "NashEquilibriumStrategy",
    "BestResponseStrategy",
    "AdaptiveBayesianStrategy",
    "FictitiousPlayStrategy",
    "RegretMatchingStrategy",
    "UCBStrategy",
    "ThompsonSamplingStrategy",
    # Factory
    "StrategyType",
    "StrategyFactory",
    "create_strategy",
    "list_strategies",
    "get_recommended",
]
