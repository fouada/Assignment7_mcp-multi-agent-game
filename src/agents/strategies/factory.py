"""
Strategy Factory
================

Factory for creating strategy instances with configuration.

Provides:
- StrategyType enum for type-safe strategy selection
- StrategyFactory for creating strategies
- Default configurations for each strategy type
"""

from enum import Enum
from typing import Any

from ...common.config import LLMConfig
from ...common.logger import get_logger
from .base import Strategy, StrategyConfig
from .classic import (
    LLMStrategy,
    PatternStrategy,
    RandomStrategy,
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
from .plugin_registry import get_strategy_plugin_registry

logger = get_logger(__name__)


class StrategyType(Enum):
    """
    Available strategy types.

    Categories:
    - CLASSIC: Original strategies (Random, Pattern, LLM)
    - GAME_THEORY: Game-theoretic strategies (Nash, Best Response, etc.)
    """

    # Classic strategies
    RANDOM = "random"
    PATTERN = "pattern"
    LLM = "llm"

    # Game Theory strategies
    NASH = "nash"
    BEST_RESPONSE = "best_response"
    ADAPTIVE_BAYESIAN = "adaptive_bayesian"
    FICTITIOUS_PLAY = "fictitious_play"
    REGRET_MATCHING = "regret_matching"
    UCB = "ucb"
    THOMPSON_SAMPLING = "thompson_sampling"

    @classmethod
    def from_string(cls, s: str) -> "StrategyType":
        """
        Convert string to StrategyType.

        Supports various formats:
        - Exact enum value: "random"
        - With underscores: "best_response"
        - With dashes: "best-response"
        - Case insensitive: "NASH", "Nash"
        """
        normalized = s.lower().replace("-", "_").strip()
        for member in cls:
            if member.value == normalized:
                return member
        raise ValueError(f"Unknown strategy type: {s}")

    @classmethod
    def list_all(cls) -> dict[str, str]:
        """List all strategies with descriptions."""
        descriptions = {
            cls.RANDOM: "Uniform random selection (Nash-like)",
            cls.PATTERN: "Exploits opponent patterns",
            cls.LLM: "LLM-powered decisions (Claude/GPT)",
            cls.NASH: "Nash equilibrium (50/50 parity)",
            cls.BEST_RESPONSE: "Exploits opponent bias",
            cls.ADAPTIVE_BAYESIAN: "Learns and adapts (RECOMMENDED)",
            cls.FICTITIOUS_PLAY: "Classic game theory learning",
            cls.REGRET_MATCHING: "CFR-inspired regret minimization",
            cls.UCB: "Multi-armed bandit (UCB1)",
            cls.THOMPSON_SAMPLING: "Bayesian bandit sampling",
        }
        return {st.value: descriptions.get(st, "") for st in cls}

    def is_game_theory(self) -> bool:
        """Check if this is a game theory strategy."""
        return self in {
            StrategyType.NASH,
            StrategyType.BEST_RESPONSE,
            StrategyType.ADAPTIVE_BAYESIAN,
            StrategyType.FICTITIOUS_PLAY,
            StrategyType.REGRET_MATCHING,
            StrategyType.UCB,
            StrategyType.THOMPSON_SAMPLING,
        }


class StrategyFactory:
    """
    Factory for creating strategy instances.

    Usage:
        # Create with defaults
        strategy = StrategyFactory.create(StrategyType.ADAPTIVE_BAYESIAN)

        # Create with custom config
        strategy = StrategyFactory.create(
            StrategyType.UCB,
            exploration_constant=2.0,
        )

        # Create from string
        strategy = StrategyFactory.create_from_string("adaptive-bayesian")
    """

    # Strategy class mapping
    _STRATEGY_CLASSES: dict[StrategyType, type[Strategy]] = {
        StrategyType.RANDOM: RandomStrategy,
        StrategyType.PATTERN: PatternStrategy,
        StrategyType.LLM: LLMStrategy,
        StrategyType.NASH: NashEquilibriumStrategy,
        StrategyType.BEST_RESPONSE: BestResponseStrategy,
        StrategyType.ADAPTIVE_BAYESIAN: AdaptiveBayesianStrategy,
        StrategyType.FICTITIOUS_PLAY: FictitiousPlayStrategy,
        StrategyType.REGRET_MATCHING: RegretMatchingStrategy,
        StrategyType.UCB: UCBStrategy,
        StrategyType.THOMPSON_SAMPLING: ThompsonSamplingStrategy,
    }

    # Default configurations per strategy type
    _DEFAULT_CONFIGS: dict[StrategyType, dict[str, Any]] = {
        StrategyType.RANDOM: {
            "min_value": 1,
            "max_value": 10,
        },
        StrategyType.PATTERN: {
            "min_value": 1,
            "max_value": 10,
        },
        StrategyType.LLM: {
            "min_value": 1,
            "max_value": 10,
        },
        StrategyType.NASH: {
            "min_value": 1,
            "max_value": 10,
        },
        StrategyType.BEST_RESPONSE: {
            "min_value": 1,
            "max_value": 10,
            "min_observations": 3,
        },
        StrategyType.ADAPTIVE_BAYESIAN: {
            "min_value": 1,
            "max_value": 10,
            "exploration_rate": 0.15,
            "confidence_threshold": 0.7,
            "min_observations": 3,
            "prior_alpha": 1.0,
            "prior_beta": 1.0,
        },
        StrategyType.FICTITIOUS_PLAY: {
            "min_value": 1,
            "max_value": 10,
        },
        StrategyType.REGRET_MATCHING: {
            "min_value": 1,
            "max_value": 10,
            "learning_rate": 0.1,
        },
        StrategyType.UCB: {
            "min_value": 1,
            "max_value": 10,
            "ucb_exploration_constant": 1.414,  # sqrt(2)
        },
        StrategyType.THOMPSON_SAMPLING: {
            "min_value": 1,
            "max_value": 10,
            "prior_alpha": 1.0,
            "prior_beta": 1.0,
        },
    }

    @classmethod
    def create(
        cls,
        strategy_type: StrategyType,
        config: StrategyConfig | None = None,
        llm_config: LLMConfig | None = None,
        **kwargs,
    ) -> Strategy:
        """
        Create a strategy instance.

        Args:
            strategy_type: Type of strategy to create
            config: Strategy configuration (optional)
            llm_config: LLM configuration for LLM strategy (optional)
            **kwargs: Additional arguments merged into config

        Returns:
            Strategy instance

        Example:
            # Basic creation
            strategy = StrategyFactory.create(StrategyType.NASH)

            # With custom config
            config = StrategyConfig(exploration_rate=0.1)
            strategy = StrategyFactory.create(StrategyType.ADAPTIVE_BAYESIAN, config=config)

            # With kwargs (merged into config)
            strategy = StrategyFactory.create(
                StrategyType.UCB,
                ucb_exploration_constant=2.0,
            )
        """
        # Get strategy class
        strategy_class = cls._STRATEGY_CLASSES.get(strategy_type)
        if strategy_class is None:
            raise ValueError(f"Unknown strategy type: {strategy_type}")

        # Build config
        if config is None:
            # Start with defaults
            default_config = cls._DEFAULT_CONFIGS.get(strategy_type, {}).copy()
            # Override with kwargs
            default_config.update(kwargs)
            config = StrategyConfig(
                **{
                    k: v
                    for k, v in default_config.items()
                    if k in StrategyConfig.__dataclass_fields__
                }
            )

        # Create strategy
        if strategy_type == StrategyType.LLM:
            return strategy_class(config=config, llm_config=llm_config)
        elif strategy_type == StrategyType.NASH:
            # Nash has extra parameter
            odd_probability = kwargs.get("odd_probability", 0.5)
            return strategy_class(config=config, odd_probability=odd_probability)
        elif strategy_type == StrategyType.BEST_RESPONSE:
            deterministic = kwargs.get("deterministic", False)
            return strategy_class(config=config, deterministic=deterministic)
        elif strategy_type == StrategyType.FICTITIOUS_PLAY:
            smoothing = kwargs.get("smoothing", 0.0)
            return strategy_class(config=config, smoothing=smoothing)
        else:
            return strategy_class(config=config)

    @classmethod
    def create_from_string(
        cls,
        strategy_name: str,
        **kwargs,
    ) -> Strategy:
        """
        Create a strategy from a string name.

        Checks plugin registry first for custom strategies, then falls back
        to built-in enum-based strategies. This maintains backward compatibility
        while enabling plugin extensibility.

        Args:
            strategy_name: Strategy type as string (e.g., "adaptive-bayesian" or "my-custom-strategy")
            **kwargs: Additional configuration

        Returns:
            Strategy instance

        Raises:
            ValueError: If strategy name is not found in plugins or built-in strategies
        """
        # 1. Check plugin registry first (new plugin system)
        plugin_registry = get_strategy_plugin_registry()
        if plugin_registry.is_registered(strategy_name):
            logger.debug(f"Creating strategy from plugin: {strategy_name}")

            # Build config
            config = kwargs.get("config")
            if config is None:
                config_dict = {
                    k: v for k, v in kwargs.items() if k in StrategyConfig.__dataclass_fields__
                }
                if config_dict:
                    config = StrategyConfig(**config_dict)

            return plugin_registry.create_strategy(strategy_name, config=config, **kwargs)

        # 2. Fall back to enum-based system (backward compatible)
        try:
            logger.debug(f"Creating strategy from built-in: {strategy_name}")
            strategy_type = StrategyType.from_string(strategy_name)
            return cls.create(strategy_type, **kwargs)
        except ValueError:
            # Not found in either system
            available_plugins = list(plugin_registry.list_strategies().keys())
            available_builtin = [st.value for st in StrategyType]
            raise ValueError(
                f"Unknown strategy: '{strategy_name}'. "
                f"Available plugins: {available_plugins}. "
                f"Available built-in: {available_builtin}"
            ) from None

    @classmethod
    def get_default_config(cls, strategy_type: StrategyType) -> dict[str, Any]:
        """Get default configuration for a strategy type."""
        return cls._DEFAULT_CONFIGS.get(strategy_type, {}).copy()

    @classmethod
    def list_strategies(cls, include_plugins: bool = True) -> dict[str, str]:
        """
        List all available strategies with descriptions.

        Args:
            include_plugins: Whether to include plugin strategies (default: True)

        Returns:
            Dictionary mapping strategy names to descriptions
        """
        strategies = StrategyType.list_all()

        # Add plugin strategies if requested
        if include_plugins:
            plugin_registry = get_strategy_plugin_registry()
            for name, metadata in plugin_registry.list_strategies().items():
                description = metadata.get("description", f"Plugin: {name}")
                strategies[name] = description

        return strategies

    @classmethod
    def get_recommended_strategy(cls) -> Strategy:
        """
        Get the recommended strategy for most scenarios.

        Returns AdaptiveBayesianStrategy with optimized defaults.
        """
        return cls.create(StrategyType.ADAPTIVE_BAYESIAN)


# =============================================================================
# Convenience functions
# =============================================================================


def create_strategy(strategy_name: str, **kwargs) -> Strategy:
    """
    Convenience function to create a strategy.

    Args:
        strategy_name: Strategy type as string
        **kwargs: Configuration options

    Returns:
        Strategy instance

    Example:
        strategy = create_strategy("adaptive-bayesian", exploration_rate=0.1)
    """
    return StrategyFactory.create_from_string(strategy_name, **kwargs)


def list_strategies() -> dict[str, str]:
    """List all available strategies."""
    return StrategyFactory.list_strategies()


def get_recommended() -> Strategy:
    """Get the recommended strategy."""
    return StrategyFactory.get_recommended_strategy()
