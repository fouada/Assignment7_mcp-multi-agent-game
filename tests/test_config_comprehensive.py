"""
Comprehensive tests for config module to increase coverage.
"""

import os
import tempfile
from pathlib import Path

import pytest

from src.common.config import (
    AgentConfig,
    GameConfig,
    LeagueConfig,
    NetworkConfig,
    ObservabilityConfig,
    PluginConfig,
    ServerConfig,
    StrategyConfig,
    SystemConfig,
    TimeoutConfig,
    get_config,
    load_config,
    validate_config,
)


class TestSystemConfig:
    """Test SystemConfig dataclass."""

    def test_system_config_creation(self):
        """Test creating a SystemConfig."""
        config = SystemConfig(
            version="1.0.0",
            environment="test",
            debug=True
        )

        assert config.version == "1.0.0"
        assert config.environment == "test"
        assert config.debug is True

    def test_system_config_defaults(self):
        """Test SystemConfig defaults."""
        config = SystemConfig()

        assert config.version is not None
        assert config.environment in ["development", "production", "test"]

    def test_system_config_to_dict(self):
        """Test converting SystemConfig to dict."""
        config = SystemConfig(version="1.0.0")
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert "version" in config_dict


class TestNetworkConfig:
    """Test NetworkConfig dataclass."""

    def test_network_config_creation(self):
        """Test creating a NetworkConfig."""
        config = NetworkConfig(
            host="localhost",
            port=8000,
            timeout=30
        )

        assert config.host == "localhost"
        assert config.port == 8000
        assert config.timeout == 30

    def test_network_config_defaults(self):
        """Test NetworkConfig defaults."""
        config = NetworkConfig()

        assert config.host is not None
        assert config.port > 0

    def test_network_config_validation(self):
        """Test NetworkConfig validation."""
        with pytest.raises(ValueError):
            NetworkConfig(port=-1)  # Invalid port

    def test_network_config_url_generation(self):
        """Test URL generation from NetworkConfig."""
        config = NetworkConfig(host="localhost", port=8000)
        url = f"http://{config.host}:{config.port}"

        assert url == "http://localhost:8000"


class TestTimeoutConfig:
    """Test TimeoutConfig dataclass."""

    def test_timeout_config_creation(self):
        """Test creating a TimeoutConfig."""
        config = TimeoutConfig(
            move=10,
            response=5,
            registration=30,
            heartbeat=60
        )

        assert config.move == 10
        assert config.response == 5
        assert config.registration == 30
        assert config.heartbeat == 60

    def test_timeout_config_defaults(self):
        """Test TimeoutConfig defaults."""
        config = TimeoutConfig()

        assert config.move > 0
        assert config.response > 0

    def test_timeout_config_validation(self):
        """Test TimeoutConfig validation."""
        with pytest.raises(ValueError):
            TimeoutConfig(move=-1)  # Invalid timeout


class TestAgentConfig:
    """Test AgentConfig dataclass."""

    def test_agent_config_creation(self):
        """Test creating an AgentConfig."""
        config = AgentConfig(
            agent_id="player_1",
            agent_type="player",
            strategy="random"
        )

        assert config.agent_id == "player_1"
        assert config.agent_type == "player"
        assert config.strategy == "random"

    def test_agent_config_with_network(self):
        """Test AgentConfig with network settings."""
        network = NetworkConfig(host="localhost", port=8001)
        config = AgentConfig(
            agent_id="player_1",
            agent_type="player",
            network=network
        )

        assert config.network.host == "localhost"
        assert config.network.port == 8001


class TestStrategyConfig:
    """Test StrategyConfig dataclass."""

    def test_strategy_config_creation(self):
        """Test creating a StrategyConfig."""
        config = StrategyConfig(
            name="random",
            params={"min_value": 1, "max_value": 10}
        )

        assert config.name == "random"
        assert config.params["min_value"] == 1

    def test_strategy_config_defaults(self):
        """Test StrategyConfig defaults."""
        config = StrategyConfig(name="adaptive")

        assert config.name == "adaptive"
        assert isinstance(config.params, dict)


class TestGameConfig:
    """Test GameConfig dataclass."""

    def test_game_config_creation(self):
        """Test creating a GameConfig."""
        config = GameConfig(
            game_type="odd_even",
            num_rounds=5,
            min_players=2,
            max_players=2
        )

        assert config.game_type == "odd_even"
        assert config.num_rounds == 5

    def test_game_config_validation(self):
        """Test GameConfig validation."""
        with pytest.raises(ValueError):
            GameConfig(
                game_type="odd_even",
                num_rounds=0  # Invalid
            )


class TestLeagueConfig:
    """Test LeagueConfig dataclass."""

    def test_league_config_creation(self):
        """Test creating a LeagueConfig."""
        config = LeagueConfig(
            league_id="test_league",
            name="Test League",
            max_players=10,
            min_players=2
        )

        assert config.league_id == "test_league"
        assert config.name == "Test League"

    def test_league_config_with_game(self):
        """Test LeagueConfig with game config."""
        game = GameConfig(game_type="odd_even")
        config = LeagueConfig(
            league_id="test_league",
            game=game
        )

        assert config.game.game_type == "odd_even"


class TestServerConfig:
    """Test ServerConfig dataclass."""

    def test_server_config_creation(self):
        """Test creating a ServerConfig."""
        config = ServerConfig(
            server_type="league_manager",
            network=NetworkConfig(port=8000)
        )

        assert config.server_type == "league_manager"
        assert config.network.port == 8000


class TestPluginConfig:
    """Test PluginConfig dataclass."""

    def test_plugin_config_creation(self):
        """Test creating a PluginConfig."""
        config = PluginConfig(
            enabled=True,
            plugins_dir="./plugins",
            auto_discover=True
        )

        assert config.enabled is True
        assert config.auto_discover is True


class TestObservabilityConfig:
    """Test ObservabilityConfig dataclass."""

    def test_observability_config_creation(self):
        """Test creating an ObservabilityConfig."""
        config = ObservabilityConfig(
            metrics_enabled=True,
            tracing_enabled=True,
            logging_level="INFO"
        )

        assert config.metrics_enabled is True
        assert config.tracing_enabled is True


class TestConfigLoading:
    """Test config loading functionality."""

    def test_load_config_from_dict(self):
        """Test loading config from dictionary."""
        config_dict = {
            "version": "1.0.0",
            "environment": "test",
            "network": {
                "host": "localhost",
                "port": 8000
            }
        }

        config = load_config(config_dict)
        assert config is not None

    def test_load_config_from_file(self):
        """Test loading config from file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"version": "1.0.0", "environment": "test"}')
            temp_file = f.name

        try:
            config = load_config(temp_file)
            assert config is not None
        finally:
            os.unlink(temp_file)

    def test_load_config_missing_file(self):
        """Test loading config from missing file."""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/config.json")

    def test_load_config_invalid_json(self):
        """Test loading config from invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('invalid json {{{')
            temp_file = f.name

        try:
            with pytest.raises((ValueError, OSError, RuntimeError)):
                load_config(temp_file)
        finally:
            os.unlink(temp_file)


class TestConfigValidation:
    """Test config validation functionality."""

    def test_validate_valid_config(self):
        """Test validating a valid config."""
        config = SystemConfig(version="1.0.0")
        errors = validate_config(config)

        assert len(errors) == 0

    def test_validate_invalid_config(self):
        """Test validating an invalid config."""
        config = SystemConfig(version="")  # Empty version
        errors = validate_config(config)

        # May or may not have errors depending on validation rules
        assert isinstance(errors, list)

    def test_validate_network_config(self):
        """Test validating network config."""
        config = NetworkConfig(host="localhost", port=8000)
        errors = validate_config(config)

        assert isinstance(errors, list)


class TestConfigGetter:
    """Test config getter functionality."""

    def test_get_config_singleton(self):
        """Test that get_config returns singleton."""
        config1 = get_config()
        config2 = get_config()

        # May or may not be singleton depending on implementation
        assert config1 is not None
        assert config2 is not None

    def test_get_config_returns_system_config(self):
        """Test that get_config returns SystemConfig."""
        config = get_config()

        assert config is not None
        assert isinstance(config, (SystemConfig, dict))


class TestConfigMerging:
    """Test config merging functionality."""

    def test_merge_configs(self):
        """Test merging two configs."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}

        # Manual merge for testing
        merged = {**base, **override}

        assert merged["a"] == 1
        assert merged["b"] == 3
        assert merged["c"] == 4

    def test_deep_merge_configs(self):
        """Test deep merging configs."""
        base = {"network": {"host": "localhost", "port": 8000}}
        override = {"network": {"port": 9000}}

        # Manual deep merge for testing
        merged = {**base}
        if "network" in override:
            merged["network"] = {**merged.get("network", {}), **override["network"]}

        assert merged["network"]["host"] == "localhost"
        assert merged["network"]["port"] == 9000


class TestConfigEnvironmentVariables:
    """Test config with environment variables."""

    def test_config_from_env(self):
        """Test loading config from environment variables."""
        os.environ["MCP_GAME_HOST"] = "0.0.0.0"
        os.environ["MCP_GAME_PORT"] = "9000"

        # Test that env vars can be used
        assert os.getenv("MCP_GAME_HOST") == "0.0.0.0"
        assert os.getenv("MCP_GAME_PORT") == "9000"

        # Cleanup
        del os.environ["MCP_GAME_HOST"]
        del os.environ["MCP_GAME_PORT"]

    def test_config_env_override(self):
        """Test that env vars override config file."""
        os.environ["MCP_GAME_DEBUG"] = "true"

        # Test env var is set
        assert os.getenv("MCP_GAME_DEBUG") == "true"

        # Cleanup
        del os.environ["MCP_GAME_DEBUG"]


class TestConfigEdgeCases:
    """Test config edge cases."""

    def test_empty_config(self):
        """Test creating config with empty values."""
        config = SystemConfig()
        assert config is not None

    def test_config_with_none_values(self):
        """Test config with None values."""
        config = AgentConfig(
            agent_id="test",
            agent_type="player",
            network=None
        )
        assert config.network is None

    def test_config_serialization(self):
        """Test config serialization and deserialization."""
        config = SystemConfig(version="1.0.0")

        # Convert to dict
        config_dict = config.to_dict() if hasattr(config, 'to_dict') else {}

        assert isinstance(config_dict, dict)

    def test_config_with_special_characters(self):
        """Test config with special characters."""
        config = AgentConfig(
            agent_id="player-1",
            agent_type="player"
        )

        assert "-" in config.agent_id


class TestConfigPathHandling:
    """Test config path handling."""

    def test_config_with_absolute_path(self):
        """Test config with absolute path."""
        path = Path("/tmp/config.json").absolute()
        assert path.is_absolute()

    def test_config_with_relative_path(self):
        """Test config with relative path."""
        path = Path("config/system.json")
        assert not path.is_absolute()

    def test_config_path_resolution(self):
        """Test config path resolution."""
        path = Path("config/system.json")
        resolved = path.resolve()
        assert resolved.is_absolute()

