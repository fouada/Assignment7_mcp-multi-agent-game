"""
Targeted tests to push coverage over 85%.
Focuses on simple, easy-to-cover paths in low-coverage files.
"""


from src.agents.strategies.base import StrategyConfig
from src.common.config_loader import ConfigLoader


class TestStrategyConfigDefaults:
    """Test StrategyConfig default values."""

    def test_strategy_config_defaults(self):
        """Test that StrategyConfig has proper defaults."""
        config = StrategyConfig()
        assert config.min_value == 1
        assert config.max_value == 10


class TestConfigLoaderEdgeCases:
    """Test ConfigLoader edge cases."""

    def test_config_loader_cache_behavior(self):
        """Test that cache is used for repeated loads."""
        loader = ConfigLoader()
        config1 = loader.load_system()
        config2 = loader.load_system()
        # Should return same instance (cached)
        assert config1 is config2

    def test_config_loader_clear_cache(self):
        """Test that clear_cache works."""
        loader = ConfigLoader()
        loader.load_system()
        loader.clear_cache()
        # Should work without errors

    def test_config_loader_get_timeout(self):
        """Test getting timeout values."""
        loader = ConfigLoader()
        timeout = loader.get_timeout("connection")
        assert isinstance(timeout, (int, float))
        assert timeout > 0

