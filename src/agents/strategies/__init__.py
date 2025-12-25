"""
Strategy Framework
==================

Complete strategy framework for player agents including:
- Classic strategies (Random, Pattern, LLM)
- Game theory strategies (Nash, Best Response, Bayesian, etc.)
- Plugin system for custom strategies

Usage:
    from src.agents.strategies import StrategyFactory, StrategyType

    # Create a built-in strategy
    strategy = StrategyFactory.create(StrategyType.ADAPTIVE_BAYESIAN)

    # Or use convenience function
    from src.agents.strategies import create_strategy
    strategy = create_strategy("adaptive-bayesian")

    # Create a custom plugin strategy
    @strategy_plugin(name="my_strategy", version="1.0.0")
    class MyStrategy(Strategy):
        async def decide_move(self, ...):
            pass
"""

from .base import (
    GameTheoryStrategy,
    OpponentModel,
    ParityChoice,
    Strategy,
    StrategyConfig,
)
from .classic import (
    LLMStrategy,
    PatternStrategy,
    RandomStrategy,
)
from .factory import (
    StrategyFactory,
    StrategyType,
    create_strategy,
    get_recommended,
    list_strategies,
)
from .game_theory import (
    AdaptiveBayesianStrategy,
    BestResponseStrategy,
    FictitiousPlayStrategy,
    NashEquilibriumStrategy,
    RegretMatchingStrategy,
    ThompsonSamplingStrategy,
    UCBStrategy,
)
from .plugin_registry import (
    StrategyPluginRegistry,
    create_strategy_plugin,
    get_strategy_plugin,
    get_strategy_plugin_registry,
    list_strategy_plugins,
    register_strategy_plugin,
    strategy_plugin,
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
    # Plugin system
    "StrategyPluginRegistry",
    "get_strategy_plugin_registry",
    "strategy_plugin",
    "register_strategy_plugin",
    "list_strategy_plugins",
    "get_strategy_plugin",
    "create_strategy_plugin",
]
