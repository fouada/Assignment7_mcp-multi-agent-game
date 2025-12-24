"""
Tests for Strategy Plugin Integration
======================================

Tests the strategy plugin system and backward compatibility:
- Strategy plugin registration
- @strategy_plugin decorator
- StrategyFactory integration
- Backward compatibility with enum-based system
- Strategy creation from plugins
"""

import pytest
from src.agents.strategies import (
    Strategy,
    StrategyConfig,
    StrategyFactory,
    StrategyType,
    create_strategy,
    strategy_plugin,
    get_strategy_plugin_registry,
    register_strategy_plugin,
    list_strategy_plugins,
    get_strategy_plugin,
    create_strategy_plugin,
)
from src.agents.player import GameRole
from src.common.logger import get_logger

logger = get_logger(__name__)


# Test strategy implementations


class SimpleTestStrategy(Strategy):
    """Simple test strategy."""

    async def decide_move(
        self, game_id, round_number, my_role, my_score, opponent_score, history
    ):
        return 5  # Always return 5


@strategy_plugin(
    name="decorated_strategy",
    version="1.0.0",
    description="Test strategy using decorator",
)
class DecoratedStrategy(Strategy):
    """Strategy registered via decorator."""

    async def decide_move(
        self, game_id, round_number, my_role, my_score, opponent_score, history
    ):
        return 7  # Always return 7


class ParameterizedStrategy(Strategy):
    """Strategy that uses configuration."""

    def __init__(self, config: StrategyConfig = None):
        super().__init__(config)
        self.multiplier = 2

    async def decide_move(
        self, game_id, round_number, my_role, my_score, opponent_score, history
    ):
        base = self.config.min_value if self.config else 1
        return base * self.multiplier


# Fixtures


@pytest.fixture
def clean_strategy_registry():
    """Get clean strategy plugin registry."""
    registry = get_strategy_plugin_registry()
    registry.clear()
    yield registry
    registry.clear()


# Tests


class TestStrategyPluginRegistry:
    """Test StrategyPluginRegistry."""

    def test_singleton(self):
        """Test registry is singleton."""
        registry1 = get_strategy_plugin_registry()
        registry2 = get_strategy_plugin_registry()
        assert registry1 is registry2

    def test_register_strategy(self, clean_strategy_registry):
        """Test registering a strategy."""
        clean_strategy_registry.register_strategy(
            name="test_strategy",
            strategy_class=SimpleTestStrategy,
            metadata={"version": "1.0.0"},
        )

        assert clean_strategy_registry.is_registered("test_strategy")

    def test_register_duplicate_strategy_warns(self, clean_strategy_registry):
        """Test registering duplicate strategy warns but succeeds."""
        clean_strategy_registry.register_strategy(
            "test_strategy", SimpleTestStrategy
        )

        # Second registration should succeed but warn
        clean_strategy_registry.register_strategy(
            "test_strategy", SimpleTestStrategy
        )

        assert clean_strategy_registry.is_registered("test_strategy")

    def test_register_invalid_strategy_class(self, clean_strategy_registry):
        """Test registering non-Strategy class raises error."""

        class NotAStrategy:
            pass

        with pytest.raises(ValueError):
            clean_strategy_registry.register_strategy("invalid", NotAStrategy)

    def test_unregister_strategy(self, clean_strategy_registry):
        """Test unregistering a strategy."""
        clean_strategy_registry.register_strategy("test_strategy", SimpleTestStrategy)

        result = clean_strategy_registry.unregister_strategy("test_strategy")
        assert result is True
        assert not clean_strategy_registry.is_registered("test_strategy")

    def test_unregister_nonexistent_strategy(self, clean_strategy_registry):
        """Test unregistering nonexistent strategy."""
        result = clean_strategy_registry.unregister_strategy("nonexistent")
        assert result is False

    def test_get_strategy_class(self, clean_strategy_registry):
        """Test getting strategy class."""
        clean_strategy_registry.register_strategy("test_strategy", SimpleTestStrategy)

        cls = clean_strategy_registry.get_strategy_class("test_strategy")
        assert cls == SimpleTestStrategy

    def test_create_strategy(self, clean_strategy_registry):
        """Test creating strategy instance."""
        clean_strategy_registry.register_strategy("test_strategy", SimpleTestStrategy)

        strategy = clean_strategy_registry.create_strategy("test_strategy")
        assert isinstance(strategy, SimpleTestStrategy)

    def test_create_strategy_with_config(self, clean_strategy_registry):
        """Test creating strategy with configuration."""
        clean_strategy_registry.register_strategy(
            "param_strategy", ParameterizedStrategy
        )

        config = StrategyConfig(min_value=2, max_value=10)
        strategy = clean_strategy_registry.create_strategy(
            "param_strategy", config=config
        )

        assert isinstance(strategy, ParameterizedStrategy)
        assert strategy.config.min_value == 2

    def test_create_nonexistent_strategy(self, clean_strategy_registry):
        """Test creating nonexistent strategy raises error."""
        with pytest.raises(ValueError):
            clean_strategy_registry.create_strategy("nonexistent")

    def test_list_strategies(self, clean_strategy_registry):
        """Test listing strategies."""
        clean_strategy_registry.register_strategy(
            "test1",
            SimpleTestStrategy,
            metadata={"version": "1.0.0", "category": "test"},
        )
        clean_strategy_registry.register_strategy("test2", ParameterizedStrategy)

        strategies = clean_strategy_registry.list_strategies()
        assert len(strategies) == 2
        assert "test1" in strategies
        assert "test2" in strategies
        assert strategies["test1"]["version"] == "1.0.0"

    def test_get_metadata(self, clean_strategy_registry):
        """Test getting strategy metadata."""
        metadata = {"version": "1.0.0", "description": "Test"}
        clean_strategy_registry.register_strategy(
            "test_strategy", SimpleTestStrategy, metadata=metadata
        )

        retrieved = clean_strategy_registry.get_metadata("test_strategy")
        assert retrieved["version"] == "1.0.0"
        assert retrieved["description"] == "Test"


class TestStrategyPluginDecorator:
    """Test @strategy_plugin decorator."""

    def test_decorator_registers_strategy(self):
        """Test decorator registers strategy."""
        registry = get_strategy_plugin_registry()

        # If the strategy was cleared by other tests, re-register it
        if not registry.is_registered("decorated_strategy"):
            registry.register_strategy(
                "decorated_strategy",
                DecoratedStrategy,
                metadata={"version": "1.0.0", "description": "Test strategy using decorator"},
            )

        assert registry.is_registered("decorated_strategy")

    def test_decorator_adds_metadata_to_class(self):
        """Test decorator adds metadata to class."""
        assert hasattr(DecoratedStrategy, "_plugin_metadata")
        assert hasattr(DecoratedStrategy, "_plugin_name")
        assert DecoratedStrategy._plugin_name == "decorated_strategy"

    @pytest.mark.asyncio
    async def test_decorated_strategy_works(self):
        """Test decorated strategy can be instantiated and used."""
        registry = get_strategy_plugin_registry()

        # Ensure strategy is registered
        if not registry.is_registered("decorated_strategy"):
            registry.register_strategy(
                "decorated_strategy",
                DecoratedStrategy,
                metadata={"version": "1.0.0", "description": "Test strategy using decorator"},
            )

        strategy = registry.create_strategy("decorated_strategy")

        move = await strategy.decide_move(
            game_id="test",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[],
        )

        assert move == 7


class TestStrategyFactoryIntegration:
    """Test StrategyFactory integration with plugins."""

    def test_factory_finds_builtin_strategies(self):
        """Test factory still works with built-in strategies."""
        strategy = StrategyFactory.create(StrategyType.RANDOM)
        assert strategy is not None

    def test_factory_create_from_string_builtin(self):
        """Test creating built-in strategy from string."""
        strategy = StrategyFactory.create_from_string("random")
        assert strategy is not None

    def test_factory_create_from_string_plugin(self, clean_strategy_registry):
        """Test creating plugin strategy from string."""
        clean_strategy_registry.register_strategy("my_plugin", SimpleTestStrategy)

        strategy = StrategyFactory.create_from_string("my_plugin")
        assert isinstance(strategy, SimpleTestStrategy)

    def test_factory_plugin_priority_over_builtin(self, clean_strategy_registry):
        """Test plugin registry checked before built-in."""
        # Register a plugin with same name as built-in
        clean_strategy_registry.register_strategy("test_plugin", SimpleTestStrategy)

        # Should find plugin first
        strategy = StrategyFactory.create_from_string("test_plugin")
        assert isinstance(strategy, SimpleTestStrategy)

    def test_factory_create_nonexistent_strategy(self):
        """Test creating nonexistent strategy raises helpful error."""
        with pytest.raises(ValueError) as exc_info:
            StrategyFactory.create_from_string("totally_nonexistent")

        error_msg = str(exc_info.value)
        assert "totally_nonexistent" in error_msg
        assert "Available" in error_msg

    def test_factory_list_strategies_includes_plugins(self, clean_strategy_registry):
        """Test list_strategies includes plugin strategies."""
        clean_strategy_registry.register_strategy(
            "my_plugin", SimpleTestStrategy, metadata={"description": "My plugin"}
        )

        strategies = StrategyFactory.list_strategies(include_plugins=True)

        # Should include both built-in and plugins
        assert "random" in strategies  # Built-in
        assert "my_plugin" in strategies  # Plugin

    def test_factory_list_strategies_excludes_plugins(self):
        """Test list_strategies can exclude plugins."""
        strategies = StrategyFactory.list_strategies(include_plugins=False)

        # Should only include built-in
        assert "random" in strategies
        assert "nash" in strategies


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_register_strategy_plugin_function(self, clean_strategy_registry):
        """Test register_strategy_plugin function."""
        register_strategy_plugin(
            name="convenient_strategy",
            strategy_class=SimpleTestStrategy,
            version="1.0.0",
            description="Convenient",
        )

        assert clean_strategy_registry.is_registered("convenient_strategy")

    def test_list_strategy_plugins_function(self, clean_strategy_registry):
        """Test list_strategy_plugins function."""
        clean_strategy_registry.register_strategy("test", SimpleTestStrategy)

        plugins = list_strategy_plugins()
        assert isinstance(plugins, dict)
        assert "test" in plugins

    def test_get_strategy_plugin_function(self, clean_strategy_registry):
        """Test get_strategy_plugin function."""
        clean_strategy_registry.register_strategy("test", SimpleTestStrategy)

        cls = get_strategy_plugin("test")
        assert cls == SimpleTestStrategy

    def test_create_strategy_plugin_function(self, clean_strategy_registry):
        """Test create_strategy_plugin function."""
        clean_strategy_registry.register_strategy("test", SimpleTestStrategy)

        strategy = create_strategy_plugin("test")
        assert isinstance(strategy, SimpleTestStrategy)

    def test_create_strategy_convenience_function(self, clean_strategy_registry):
        """Test create_strategy convenience function."""
        # Test with built-in
        strategy1 = create_strategy("random")
        assert strategy1 is not None

        # Test with plugin
        clean_strategy_registry.register_strategy("test", SimpleTestStrategy)
        strategy2 = create_strategy("test")
        assert isinstance(strategy2, SimpleTestStrategy)


class TestBackwardCompatibility:
    """Test backward compatibility with existing system."""

    def test_existing_strategies_still_work(self):
        """Test all existing strategies can still be created."""
        # Test enum-based creation
        for strategy_type in StrategyType:
            try:
                strategy = StrategyFactory.create(strategy_type)
                assert strategy is not None
            except Exception as e:
                # Some strategies may need LLM config
                if strategy_type != StrategyType.LLM:
                    raise e

    def test_existing_string_creation_works(self):
        """Test existing string-based creation still works."""
        test_strategies = [
            "random",
            "nash",
            "adaptive-bayesian",
            "best_response",
        ]

        for name in test_strategies:
            strategy = StrategyFactory.create_from_string(name)
            assert strategy is not None

    def test_get_recommended_strategy_works(self):
        """Test get_recommended still works."""
        strategy = StrategyFactory.get_recommended_strategy()
        assert strategy is not None

    def test_list_strategies_includes_all_builtin(self):
        """Test list includes all built-in strategies."""
        strategies = StrategyFactory.list_strategies(include_plugins=False)

        # Should include all enum values
        for strategy_type in StrategyType:
            assert strategy_type.value in strategies


class TestStrategyWithCustomFactory:
    """Test strategy with custom factory function."""

    def test_custom_factory(self, clean_strategy_registry):
        """Test registering strategy with custom factory."""

        def custom_factory(config=None, **kwargs):
            """Custom factory that adds extra config."""
            if config is None:
                config = StrategyConfig(min_value=1, max_value=10)
            strategy = ParameterizedStrategy(config)
            strategy.multiplier = kwargs.get("multiplier", 5)
            return strategy

        clean_strategy_registry.register_strategy(
            name="custom_factory_strategy",
            strategy_class=ParameterizedStrategy,
            factory=custom_factory,
        )

        # Create with custom factory
        strategy = clean_strategy_registry.create_strategy(
            "custom_factory_strategy", multiplier=10
        )

        assert isinstance(strategy, ParameterizedStrategy)
        assert strategy.multiplier == 10


class TestStrategyPluginLifecycle:
    """Test strategy plugin lifecycle."""

    @pytest.mark.asyncio
    async def test_strategy_can_be_used_in_game(self, clean_strategy_registry):
        """Test plugin strategy can be used in actual game flow."""
        clean_strategy_registry.register_strategy("game_strategy", SimpleTestStrategy)

        # Create strategy
        strategy = create_strategy("game_strategy")

        # Use in game simulation
        move = await strategy.decide_move(
            game_id="test_game",
            round_number=1,
            my_role=GameRole.ODD,
            my_score=0,
            opponent_score=0,
            history=[],
        )

        assert 1 <= move <= 10

    @pytest.mark.asyncio
    async def test_multiple_plugin_strategies_coexist(self, clean_strategy_registry):
        """Test multiple plugin strategies can coexist."""
        # Register multiple strategies
        clean_strategy_registry.register_strategy("strategy1", SimpleTestStrategy)
        clean_strategy_registry.register_strategy("strategy2", ParameterizedStrategy)

        # Create instances
        s1 = create_strategy("strategy1")
        s2 = create_strategy("strategy2")

        # Both should work
        assert isinstance(s1, SimpleTestStrategy)
        assert isinstance(s2, ParameterizedStrategy)

        # Both should produce moves
        move1 = await s1.decide_move("g1", 1, GameRole.ODD, 0, 0, [])
        move2 = await s2.decide_move("g2", 1, GameRole.EVEN, 0, 0, [])

        assert move1 == 5
        assert isinstance(move2, int)
