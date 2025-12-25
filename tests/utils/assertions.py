"""
Custom Assertions for Testing
==============================

Provides domain-specific assertion helpers for comprehensive testing.
"""

from typing import Any


def assert_player_registered(
    response: dict[str, Any],
    expected_player_id: str | None = None
) -> None:
    """
    Assert player registration was successful.

    Args:
        response: Registration response
        expected_player_id: Expected player ID (if known)

    Raises:
        AssertionError: If registration is invalid
    """
    assert "success" in response, "Response missing 'success' field"
    assert response["success"] is True, f"Registration failed: {response.get('error', 'unknown')}"
    assert "player_id" in response, "Response missing 'player_id'"
    assert "auth_token" in response, "Response missing 'auth_token'"

    if expected_player_id:
        assert response["player_id"] == expected_player_id, \
            f"Expected player_id {expected_player_id}, got {response['player_id']}"

    # Validate auth token format
    auth_token = response["auth_token"]
    assert isinstance(auth_token, str), "auth_token must be a string"
    assert len(auth_token) > 0, "auth_token cannot be empty"


def assert_game_completed(
    game_state: dict[str, Any],
    expected_winner: str | None = None,
    expected_rounds: int | None = None
) -> None:
    """
    Assert game completed successfully.

    Args:
        game_state: Game state dictionary
        expected_winner: Expected winner ID (if known)
        expected_rounds: Expected number of rounds (if known)

    Raises:
        AssertionError: If game state is invalid
    """
    assert "status" in game_state, "Game state missing 'status'"
    assert game_state["status"] == "completed", \
        f"Game not completed, status: {game_state['status']}"

    assert "winner_id" in game_state, "Game state missing 'winner_id'"
    assert "scores" in game_state, "Game state missing 'scores'"

    if expected_winner:
        assert game_state["winner_id"] == expected_winner, \
            f"Expected winner {expected_winner}, got {game_state['winner_id']}"

    if expected_rounds:
        assert game_state.get("current_round") == expected_rounds, \
            f"Expected {expected_rounds} rounds, got {game_state.get('current_round')}"

    # Validate scores
    scores = game_state["scores"]
    assert isinstance(scores, dict), "Scores must be a dictionary"
    assert len(scores) >= 2, "Scores must have at least 2 players"

    for player_id, score in scores.items():
        assert isinstance(score, int), f"Score for {player_id} must be an integer"
        assert score >= 0, f"Score for {player_id} must be non-negative"


def assert_valid_move(
    move: int,
    min_value: int = 1,
    max_value: int = 10
) -> None:
    """
    Assert move is valid.

    Args:
        move: Move value
        min_value: Minimum valid value
        max_value: Maximum valid value

    Raises:
        AssertionError: If move is invalid
    """
    assert isinstance(move, int), f"Move must be an integer, got {type(move)}"
    assert min_value <= move <= max_value, \
        f"Move must be between {min_value} and {max_value}, got {move}"


def assert_protocol_message(
    message: dict[str, Any],
    expected_type: str,
    required_fields: list[str] | None = None
) -> None:
    """
    Assert protocol message is valid.

    Args:
        message: Protocol message
        expected_type: Expected message type
        required_fields: List of required fields

    Raises:
        AssertionError: If message is invalid
    """
    assert isinstance(message, dict), "Message must be a dictionary"
    assert "type" in message, "Message missing 'type' field"
    assert message["type"] == expected_type, \
        f"Expected message type {expected_type}, got {message['type']}"

    if required_fields:
        for field in required_fields:
            assert field in message, f"Message missing required field: {field}"


def assert_match_result(
    result: dict[str, Any],
    expected_winner: str | None = None,
    expected_loser: str | None = None
) -> None:
    """
    Assert match result is valid.

    Args:
        result: Match result dictionary
        expected_winner: Expected winner ID
        expected_loser: Expected loser ID

    Raises:
        AssertionError: If result is invalid
    """
    assert "match_id" in result, "Result missing 'match_id'"
    assert "winner_id" in result, "Result missing 'winner_id'"
    assert "loser_id" in result, "Result missing 'loser_id'"

    # Validate winner and loser are different
    assert result["winner_id"] != result["loser_id"], \
        "Winner and loser cannot be the same"

    if expected_winner:
        assert result["winner_id"] == expected_winner, \
            f"Expected winner {expected_winner}, got {result['winner_id']}"

    if expected_loser:
        assert result["loser_id"] == expected_loser, \
            f"Expected loser {expected_loser}, got {result['loser_id']}"


def assert_standings(
    standings: list[dict[str, Any]],
    min_players: int = 2,
    check_order: bool = True
) -> None:
    """
    Assert standings are valid.

    Args:
        standings: List of player standings
        min_players: Minimum number of players
        check_order: Whether to check if standings are properly ordered

    Raises:
        AssertionError: If standings are invalid
    """
    assert isinstance(standings, list), "Standings must be a list"
    assert len(standings) >= min_players, \
        f"Standings must have at least {min_players} players, got {len(standings)}"

    # Check each standing entry
    for i, standing in enumerate(standings):
        assert "player_id" in standing, f"Standing {i} missing 'player_id'"
        assert "points" in standing, f"Standing {i} missing 'points'"
        assert "wins" in standing, f"Standing {i} missing 'wins'"
        assert "losses" in standing, f"Standing {i} missing 'losses'"

        # Validate values
        assert isinstance(standing["points"], (int, float)), \
            f"Points must be numeric for {standing['player_id']}"
        assert standing["points"] >= 0, \
            f"Points must be non-negative for {standing['player_id']}"
        assert standing["wins"] >= 0, \
            f"Wins must be non-negative for {standing['player_id']}"
        assert standing["losses"] >= 0, \
            f"Losses must be non-negative for {standing['player_id']}"

    # Check ordering if requested
    if check_order and len(standings) > 1:
        for i in range(len(standings) - 1):
            assert standings[i]["points"] >= standings[i + 1]["points"], \
                f"Standings not properly ordered: {standings[i]['player_id']} " \
                f"({standings[i]['points']}) should be >= {standings[i+1]['player_id']} " \
                f"({standings[i+1]['points']})"


def assert_round_robin_schedule(
    schedule: list[list[tuple]],
    num_players: int,
    allow_byes: bool = True
) -> None:
    """
    Assert round-robin schedule is valid.

    Args:
        schedule: Schedule as list of rounds, each round is list of (p1, p2) tuples
        num_players: Number of players
        allow_byes: Whether to allow bye rounds (for odd number of players)

    Raises:
        AssertionError: If schedule is invalid
    """
    # Check expected number of rounds
    expected_rounds = num_players if num_players % 2 == 1 else num_players - 1
    assert len(schedule) == expected_rounds, \
        f"Expected {expected_rounds} rounds for {num_players} players, got {len(schedule)}"

    # Track all matchups
    all_matchups = set()

    for round_num, round_matches in enumerate(schedule):
        # Check players in this round
        players_in_round = set()

        for match in round_matches:
            assert isinstance(match, tuple), f"Match must be a tuple in round {round_num}"
            assert len(match) == 2, f"Match must have 2 players in round {round_num}"

            p1, p2 = match

            # Check no self-matches
            assert p1 != p2, f"Self-match not allowed: {p1} vs {p2} in round {round_num}"

            # Check players not already in this round
            assert p1 not in players_in_round, \
                f"Player {p1} appears multiple times in round {round_num}"
            assert p2 not in players_in_round, \
                f"Player {p2} appears multiple times in round {round_num}"

            players_in_round.add(p1)
            players_in_round.add(p2)

            # Track matchup (sorted to handle both orderings)
            matchup = tuple(sorted([p1, p2]))
            assert matchup not in all_matchups, \
                f"Duplicate matchup: {p1} vs {p2}"
            all_matchups.add(matchup)

    # Check total number of matchups
    if not allow_byes:
        expected_matchups = (num_players * (num_players - 1)) // 2
        assert len(all_matchups) == expected_matchups, \
            f"Expected {expected_matchups} unique matchups, got {len(all_matchups)}"


def assert_event_published(
    event_bus_mock: Any,
    event_type: str,
    min_count: int = 1
) -> None:
    """
    Assert event was published to event bus.

    Args:
        event_bus_mock: Mocked event bus
        event_type: Expected event type
        min_count: Minimum number of times event should be published

    Raises:
        AssertionError: If event was not published
    """
    # Get all calls to publish
    publish_calls = list(event_bus_mock.publish.call_args_list)

    # Check if event_type was published
    matching_calls = [
        call for call in publish_calls
        if len(call[0]) > 0 and call[0][0] == event_type
    ]

    assert len(matching_calls) >= min_count, \
        f"Expected event '{event_type}' to be published at least {min_count} times, " \
        f"but was published {len(matching_calls)} times"


def assert_within_tolerance(
    actual: float,
    expected: float,
    tolerance: float = 0.01
) -> None:
    """
    Assert value is within tolerance of expected.

    Args:
        actual: Actual value
        expected: Expected value
        tolerance: Allowed tolerance (as fraction of expected)

    Raises:
        AssertionError: If value is outside tolerance
    """
    allowed_diff = abs(expected * tolerance)
    actual_diff = abs(actual - expected)

    assert actual_diff <= allowed_diff, \
        f"Expected {expected} ± {allowed_diff}, got {actual} (diff: {actual_diff})"


def assert_no_duplicates(items: list[Any], field: str | None = None) -> None:
    """
    Assert list has no duplicates.

    Args:
        items: List of items
        field: If items are dicts, field to check for duplicates

    Raises:
        AssertionError: If duplicates found
    """
    if field:
        values = [item[field] for item in items]
    else:
        values = items

    seen = set()
    duplicates = []

    for value in values:
        if value in seen:
            duplicates.append(value)
        seen.add(value)

    assert len(duplicates) == 0, \
        f"Found duplicates: {duplicates}"

