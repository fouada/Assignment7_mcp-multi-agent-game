"""
Agent implementations.

This module provides:
- LeagueManager: Manages the league, scheduling, and standings
- RefereeAgent: Manages individual matches between players
- PlayerAgent: AI player with configurable strategies

Strategy Framework:
- Classic: RandomStrategy, PatternStrategy, LLMStrategy
- Game Theory: NashEquilibriumStrategy, BestResponseStrategy,
               AdaptiveBayesianStrategy, FictitiousPlayStrategy,
               RegretMatchingStrategy, UCBStrategy, ThompsonSamplingStrategy

Usage:
    from src.agents import PlayerAgent, create_player, StrategyType

    # Create with default random strategy
    player = create_player("Bot1", 8101)

    # Create with game theory strategy
    player = create_player("Bot2", 8102, strategy_type="adaptive_bayesian")
"""

from .league_manager import LeagueManager
from .player import (
    PlayerAgent,
    create_player,
    get_recommended_strategy,
    list_available_strategies,
)
from .referee import RefereeAgent

# Import strategy types for convenience
from .strategies import (
    # Game Theory
    AdaptiveBayesianStrategy,
    BestResponseStrategy,
    FictitiousPlayStrategy,
    # Classic
    LLMStrategy,
    NashEquilibriumStrategy,
    PatternStrategy,
    RandomStrategy,
    RegretMatchingStrategy,
    # Base
    Strategy,
    StrategyConfig,
    StrategyFactory,
    StrategyType,
    ThompsonSamplingStrategy,
    UCBStrategy,
)

__all__ = [
    # Agents
    "LeagueManager",
    "RefereeAgent",
    "PlayerAgent",
    # Factory functions
    "create_player",
    "list_available_strategies",
    "get_recommended_strategy",
    # Strategy framework
    "Strategy",
    "StrategyFactory",
    "StrategyType",
    "StrategyConfig",
    # Classic strategies
    "RandomStrategy",
    "PatternStrategy",
    "LLMStrategy",
    # Game Theory strategies
    "NashEquilibriumStrategy",
    "BestResponseStrategy",
    "AdaptiveBayesianStrategy",
    "FictitiousPlayStrategy",
    "RegretMatchingStrategy",
    "UCBStrategy",
    "ThompsonSamplingStrategy",
]

