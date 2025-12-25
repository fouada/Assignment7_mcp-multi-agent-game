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

from tests.utils.mocking import (
    MockMCPClient,
    MockPlayer,
    MockReferee,
    MockLeagueManager,
    MockGameSession,
    create_mock_transport,
    create_mock_event_bus,
)

from tests.utils.factories import (
    TestDataFactory,
    PlayerFactory,
    RefereeFactory,
    MatchFactory,
    GameFactory,
    MessageFactory,
)

from tests.utils.fixtures import (
    async_test,
    temp_directory,
    capture_logs,
    mock_time,
)

from tests.utils.assertions import (
    assert_player_registered,
    assert_game_completed,
    assert_valid_move,
    assert_protocol_message,
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

