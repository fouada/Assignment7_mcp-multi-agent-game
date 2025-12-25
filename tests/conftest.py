"""
PyTest Configuration and Fixtures
==================================

Global configuration and shared fixtures for all tests.
"""

import asyncio
import logging
from pathlib import Path

import pytest

# ====================
# PyTest Configuration
# ====================

def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    # Register custom markers
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test (requires running services)"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow (takes > 1 second)"
    )
    config.addinivalue_line(
        "markers",
        "benchmark: mark test as a benchmark test"
    )
    config.addinivalue_line(
        "markers",
        "unit: mark test as a unit test (default)"
    )

    # Configure logging
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add 'unit' marker to tests without other markers
        if not any(marker.name in ['integration', 'slow', 'benchmark']
                   for marker in item.iter_markers()):
            item.add_marker(pytest.mark.unit)


# ====================
# Async Fixtures
# ====================

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the entire test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_setup_teardown():
    """Fixture for async setup and teardown."""
    # Setup
    setup_data = {}
    yield setup_data
    # Teardown
    await asyncio.sleep(0)  # Allow pending tasks to complete


# ====================
# Directory Fixtures
# ====================

@pytest.fixture
def tmp_path(tmp_path):
    """Provide a temporary directory for tests."""
    return tmp_path


@pytest.fixture
def test_data_dir():
    """Provide path to test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture
def mock_config_dir(tmp_path):
    """Create a temporary config directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


# ====================
# Logging Fixtures
# ====================

@pytest.fixture
def caplog_debug(caplog):
    """Capture logs at DEBUG level."""
    caplog.set_level(logging.DEBUG)
    return caplog


@pytest.fixture
def suppress_logs():
    """Suppress all logging during test."""
    logger = logging.getLogger()
    original_level = logger.level
    logger.setLevel(logging.CRITICAL + 1)
    yield
    logger.setLevel(original_level)


# ====================
# Mock Fixtures
# ====================

@pytest.fixture
def mock_mcp_client():
    """Provide a mock MCP client."""
    from tests.utils import MockMCPClient
    return MockMCPClient()


@pytest.fixture
def mock_league():
    """Provide a mock league manager."""
    from tests.utils import MockLeagueManager
    return MockLeagueManager()


@pytest.fixture
def mock_player():
    """Provide a mock player."""
    from tests.utils import MockPlayer
    return MockPlayer("TestPlayer")


@pytest.fixture
def mock_referee():
    """Provide a mock referee."""
    from tests.utils import MockReferee
    return MockReferee("TestReferee")


# ====================
# Factory Fixtures
# ====================

@pytest.fixture
def player_factory():
    """Provide player factory."""
    from tests.utils import PlayerFactory
    return PlayerFactory


@pytest.fixture
def referee_factory():
    """Provide referee factory."""
    from tests.utils import RefereeFactory
    return RefereeFactory


@pytest.fixture
def match_factory():
    """Provide match factory."""
    from tests.utils import MatchFactory
    return MatchFactory


@pytest.fixture
def game_factory():
    """Provide game factory."""
    from tests.utils import GameFactory
    return GameFactory


@pytest.fixture
def message_factory():
    """Provide message factory."""
    from tests.utils import MessageFactory
    return MessageFactory


@pytest.fixture
def scenario_factory():
    """Provide scenario factory."""
    from tests.utils import ScenarioFactory
    return ScenarioFactory


# ====================
# Performance Fixtures
# ====================

@pytest.fixture
def performance_timer():
    """Provide performance timer."""
    from tests.utils import PerformanceTimer
    return PerformanceTimer


@pytest.fixture
def benchmark_threshold():
    """Provide benchmark thresholds."""
    return {
        "fast": 0.01,      # < 10ms
        "medium": 0.1,     # < 100ms
        "slow": 1.0,       # < 1s
        "very_slow": 5.0   # < 5s
    }


# ====================
# Test Data Fixtures
# ====================

@pytest.fixture
def sample_moves():
    """Provide sample move data."""
    return [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


@pytest.fixture
def sample_game_history():
    """Provide sample game history."""
    return [
        {"round": 1, "move1": 5, "move2": 3, "sum": 8, "winner": "even"},
        {"round": 2, "move1": 2, "move2": 4, "sum": 6, "winner": "even"},
        {"round": 3, "move1": 7, "move2": 2, "sum": 9, "winner": "odd"},
        {"round": 4, "move1": 1, "move2": 8, "sum": 9, "winner": "odd"},
        {"round": 5, "move1": 6, "move2": 4, "sum": 10, "winner": "even"},
    ]


# ====================
# Cleanup Fixtures
# ====================

@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Auto cleanup after each test."""
    yield
    # Cleanup code here
    asyncio.set_event_loop_policy(None)
    # Reset any global state


@pytest.fixture(scope="session", autouse=True)
def cleanup_after_session():
    """Auto cleanup after entire test session."""
    yield
    # Session-level cleanup
    logging.shutdown()


# ====================
# Parametrize Helpers
# ====================

# Common parametrize data
VALID_MOVES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
INVALID_MOVES = [0, -1, 11, 15, 100, -100]
STRATEGIES = ["random", "nash", "adaptive", "pattern"]

