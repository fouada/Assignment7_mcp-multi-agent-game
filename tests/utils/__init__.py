"""
Test Utilities Package
======================

Provides comprehensive utilities for testing including:
- Mocking framework
- Test data factories
- Fixture generators
- Assertion helpers
- Test decorators
"""

from tests.utils.assertions import (
    assert_game_completed,
    assert_player_registered,
    assert_protocol_message,
    assert_valid_move,
)
from tests.utils.factories import (
    GameFactory,
    MatchFactory,
    MessageFactory,
    PlayerFactory,
    RefereeFactory,
    TestDataFactory,
)
from tests.utils.fixtures import (
    async_test,
    capture_logs,
    mock_time,
    temp_directory,
)
from tests.utils.mocking import (
    MockGameSession,
    MockLeagueManager,
    MockMCPClient,
    MockPlayer,
    MockReferee,
    create_mock_event_bus,
    create_mock_transport,
)

__all__ = [
    # Mocking
    "MockMCPClient",
    "MockPlayer",
    "MockReferee",
    "MockLeagueManager",
    "MockGameSession",
    "create_mock_transport",
    "create_mock_event_bus",
    # Factories
    "TestDataFactory",
    "PlayerFactory",
    "RefereeFactory",
    "MatchFactory",
    "GameFactory",
    "MessageFactory",
    # Fixtures
    "async_test",
    "temp_directory",
    "capture_logs",
    "mock_time",
    # Assertions
    "assert_player_registered",
    "assert_game_completed",
    "assert_valid_move",
    "assert_protocol_message",
]
