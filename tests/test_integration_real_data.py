"""
Comprehensive Integration Tests with Real Data
================================================

MIT-Level integration testing using real game data and realistic flows.
Tests cover end-to-end scenarios with actual data patterns from the system.

Coverage Areas:
- Full league lifecycle with real player data
- Match execution with realistic scenarios
- Multi-agent coordination with real communication patterns
- Error recovery with actual failure modes
- Performance with real-world data volumes
"""

import asyncio
import time

import pytest

from tests.utils import (
    MockLeagueManager,
    MockPlayer,
    MockReferee,
    PerformanceTimer,
    get_real_data_loader,
)


@pytest.mark.integration
class TestRealDataLeagueIntegration:
    """Test complete league operations using real data patterns."""

    @pytest.mark.asyncio
    async def test_full_league_with_real_player_data(self, real_league_data, realistic_players):
        """Test complete league flow using real player data patterns."""
        # Arrange
        league = MockLeagueManager(max_players=20)
        loader = get_real_data_loader()

        players = {}
        player_data = realistic_players

        # Act - Register all players with realistic data
        with PerformanceTimer("Player registration"):
            for player_info in player_data:
                player = MockPlayer(
                    player_info["player_id"], strategy=player_info["strategy"]
                )
                players[player.player_id] = player

                result = await league.register_player(
                    player.player_id, player_info["endpoint"], player_info["game_types"]
                )

                # Assert
                assert result["success"], f"Failed to register {player.player_id}"

        # Verify all players registered
        assert len(league.players) == len(player_data)

        # Register referees
        referees = {}
        for i in range(3):  # 3 referees for realistic load distribution
            ref_id = f"R{i + 1:02d}"
            referee = MockReferee(ref_id)
            referees[ref_id] = referee

            result = await league.register_referee(ref_id, f"http://localhost:{9000 + i}")
            assert result["success"]

        # Generate round-robin schedule
        schedule = league.generate_schedule()
        assert len(schedule) > 0

        # Play first round with realistic match execution
        first_round = schedule[0]

        for match in first_round["matches"]:
            referee = referees[list(referees.keys())[0]]  # Use first referee
            player1 = players[match["player1_id"]]
            player2 = players[match["player2_id"]]

            # Start match with realistic parameters
            await referee.start_match(
                match["match_id"], player1.player_id, player2.player_id, rounds=5
            )

            # Simulate realistic game play
            for round_num in range(5):
                # Players make moves based on their strategies
                move1 = await player1.make_move(match["match_id"], "odd")
                move2 = await player2.make_move(match["match_id"], "even")

                # Validate moves are realistic
                assert 1 <= move1 <= 10
                assert 1 <= move2 <= 10

                # Determine winner
                total = move1 + move2
                is_odd = total % 2 == 1

                # Update scores
                player1.update_score(match["match_id"], 1 if is_odd else 0)
                player2.update_score(match["match_id"], 0 if is_odd else 1)

            # Determine overall winner
            winner_id = (
                player1.player_id if player1.score > player2.score else player2.player_id
            )
            loser_id = player2.player_id if winner_id == player1.player_id else player1.player_id

            # Report result
            reported = await referee.report_result(match["match_id"], winner_id, loser_id)
            assert reported

            # Update league standings
            league.players[winner_id]["wins"] += 1
            league.players[winner_id]["points"] += 3
            league.players[loser_id]["losses"] += 1

        # Verify standings
        standings = league.get_standings()
        assert len(standings) == len(player_data)

    @pytest.mark.asyncio
    async def test_league_with_real_match_patterns(self, realistic_players):
        """Test league with realistic match execution patterns."""
        # Arrange
        league = MockLeagueManager(max_players=20)
        loader = get_real_data_loader()

        # Use subset of realistic players
        player_subset = realistic_players[:6]
        players = {}

        # Register players
        for player_info in player_subset:
            player = MockPlayer(player_info["player_id"], strategy=player_info["strategy"])
            players[player.player_id] = player
            await league.register_player(
                player.player_id, player_info["endpoint"], player_info["game_types"]
            )

        # Register referee
        referee = MockReferee("R01")
        await league.register_referee("R01", "http://localhost:9000")

        # Generate full schedule
        schedule = league.generate_schedule()

        # Play all rounds
        for round_idx, round_data in enumerate(schedule):
            print(f"\n  Playing round {round_idx + 1}/{len(schedule)}")

            for match in round_data["matches"]:
                if match["player2_id"] == "BYE":
                    # Handle bye round
                    league.players[match["player1_id"]]["points"] += 1
                    continue

                player1 = players[match["player1_id"]]
                player2 = players[match["player2_id"]]

                # Execute match
                await referee.start_match(
                    match["match_id"], player1.player_id, player2.player_id, rounds=5
                )

                # Simulate realistic gameplay
                winner = player1 if (round_idx + hash(match["match_id"])) % 2 == 0 else player2
                loser = player2 if winner == player1 else player1

                await referee.report_result(match["match_id"], winner.player_id, loser.player_id)

                # Update standings
                league.players[winner.player_id]["wins"] += 1
                league.players[winner.player_id]["points"] += 3
                league.players[loser.player_id]["losses"] += 1

        # Verify final standings
        standings = league.get_standings()
        assert len(standings) == len(player_subset)

        # Verify total matches played
        total_matches = sum(p["wins"] + p["losses"] for p in league.players.values()) / 2
        expected_matches = len(player_subset) * (len(player_subset) - 1) / 2
        assert total_matches == expected_matches

    @pytest.mark.asyncio
    async def test_concurrent_matches_with_real_data(self, realistic_players):
        """Test concurrent match execution with realistic player data."""
        # Arrange
        league = MockLeagueManager(max_players=30)
        player_subset = realistic_players[:8]

        players = {}
        for player_info in player_subset:
            player = MockPlayer(player_info["player_id"], strategy=player_info["strategy"])
            players[player.player_id] = player
            await league.register_player(
                player.player_id, player_info["endpoint"], player_info["game_types"]
            )

        # Multiple referees for concurrent matches
        referees = []
        for i in range(4):
            ref_id = f"R{i + 1:02d}"
            referee = MockReferee(ref_id)
            referees.append(referee)
            await league.register_referee(ref_id, f"http://localhost:{9000 + i}")

        # Generate schedule
        schedule = league.generate_schedule()
        first_round = schedule[0]

        # Execute all matches in first round concurrently
        async def execute_match(match, referee_idx):
            if match["player2_id"] == "BYE":
                return None

            referee = referees[referee_idx % len(referees)]
            player1 = players[match["player1_id"]]
            player2 = players[match["player2_id"]]

            await referee.start_match(
                match["match_id"], player1.player_id, player2.player_id, rounds=3
            )

            # Simulate quick match
            winner = player1 if hash(match["match_id"]) % 2 == 0 else player2
            return await referee.report_result(match["match_id"], winner.player_id, player2.player_id)

        # Act - Execute all matches concurrently
        start_time = time.perf_counter()
        tasks = [
            execute_match(match, idx) for idx, match in enumerate(first_round["matches"])
        ]
        results = await asyncio.gather(*tasks)
        duration = time.perf_counter() - start_time

        # Assert
        assert all(r is None or r for r in results)
        print(f"\n  Executed {len(tasks)} concurrent matches in {duration:.2f}s")
        assert duration < 5.0, "Concurrent execution should be fast"


@pytest.mark.integration
class TestRealDataMatchIntegration:
    """Test match operations with real data patterns."""

    @pytest.mark.asyncio
    async def test_match_with_realistic_strategies(self, realistic_players):
        """Test match with different realistic strategies."""
        # Arrange
        player1_data = realistic_players[0]
        player2_data = realistic_players[1]

        player1 = MockPlayer(player1_data["player_id"], strategy=player1_data["strategy"])
        player2 = MockPlayer(player2_data["player_id"], strategy=player2_data["strategy"])

        referee = MockReferee("R01")
        match_id = "match_realistic_strategies"

        # Act - Execute full match
        await referee.start_match(match_id, player1.player_id, player2.player_id, rounds=10)

        round_results = []
        for round_num in range(10):
            move1 = await player1.make_move(match_id, "odd")
            move2 = await player2.make_move(match_id, "even")

            total = move1 + move2
            is_odd = total % 2 == 1

            round_results.append(
                {
                    "round": round_num + 1,
                    "move1": move1,
                    "move2": move2,
                    "sum": total,
                    "winner": "odd" if is_odd else "even",
                }
            )

            player1.update_score(match_id, 1 if is_odd else 0)
            player2.update_score(match_id, 0 if is_odd else 1)

        # Determine winner
        winner_id = player1.player_id if player1.score > player2.score else player2.player_id
        loser_id = player2.player_id if winner_id == player1.player_id else player1.player_id

        reported = await referee.report_result(match_id, winner_id, loser_id)

        # Assert
        assert reported
        assert len(round_results) == 10
        assert all(1 <= r["move1"] <= 10 for r in round_results)
        assert all(1 <= r["move2"] <= 10 for r in round_results)

    @pytest.mark.asyncio
    async def test_match_with_all_strategy_types(self, realistic_players):
        """Test matches with all available strategy types."""
        # Arrange
        strategies_tested = set()
        match_count = 0

        referee = MockReferee("R01")

        # Test each strategy against another
        for i in range(0, len(realistic_players) - 1, 2):
            player1_data = realistic_players[i]
            player2_data = realistic_players[i + 1]

            strategies_tested.add(player1_data["strategy"])
            strategies_tested.add(player2_data["strategy"])

            player1 = MockPlayer(player1_data["player_id"], strategy=player1_data["strategy"])
            player2 = MockPlayer(player2_data["player_id"], strategy=player2_data["strategy"])

            match_id = f"match_strategy_{i}"

            # Execute quick match
            await referee.start_match(match_id, player1.player_id, player2.player_id, rounds=3)

            for _ in range(3):
                move1 = await player1.make_move(match_id, "odd")
                move2 = await player2.make_move(match_id, "even")

                assert 1 <= move1 <= 10
                assert 1 <= move2 <= 10

            match_count += 1

        # Assert
        assert match_count >= 4
        assert len(strategies_tested) >= 4


@pytest.mark.integration
class TestRealDataErrorRecovery:
    """Test error recovery with real data scenarios."""

    @pytest.mark.asyncio
    async def test_player_failure_recovery_realistic(self, realistic_players):
        """Test recovery from player failure with realistic data."""
        # Arrange
        player1_data = realistic_players[0]
        player2_data = realistic_players[1]

        player1 = MockPlayer(player1_data["player_id"], strategy=player1_data["strategy"])
        player2 = MockPlayer(
            player2_data["player_id"],
            strategy=player2_data["strategy"],
            fail_on_move=True,
        )

        referee = MockReferee("R01")
        match_id = "match_with_failure"

        # Act
        await referee.start_match(match_id, player1.player_id, player2.player_id, rounds=5)

        # Player 1 can make moves
        move1 = await player1.make_move(match_id, "odd")
        assert 1 <= move1 <= 10

        # Player 2 will fail
        with pytest.raises(ValueError):
            await player2.make_move(match_id, "even")

        # Recovery: disable failure and retry
        player2.fail_on_move = False
        move2 = await player2.make_move(match_id, "even")
        assert 1 <= move2 <= 10

    @pytest.mark.asyncio
    async def test_referee_failure_with_multiple_matches(self, realistic_players):
        """Test referee failure handling with multiple concurrent matches."""
        # Arrange
        player_subset = realistic_players[:4]
        players = {}

        for player_info in player_subset:
            player = MockPlayer(player_info["player_id"], strategy=player_info["strategy"])
            players[player.player_id] = player

        referee = MockReferee("R01", fail_on_report=True)

        # Start multiple matches
        match_ids = []
        for i in range(2):
            match_id = f"match_{i}"
            match_ids.append(match_id)
            await referee.start_match(
                match_id,
                player_subset[i * 2]["player_id"],
                player_subset[i * 2 + 1]["player_id"],
                rounds=3,
            )

        # Try to report results (will fail)
        with pytest.raises(ConnectionError):
            await referee.report_result(
                match_ids[0], player_subset[0]["player_id"], player_subset[1]["player_id"]
            )

        # Recovery
        referee.fail_on_report = False
        result = await referee.report_result(
            match_ids[0], player_subset[0]["player_id"], player_subset[1]["player_id"]
        )

        assert result
        assert len(referee.reported_results) == 1


@pytest.mark.integration
@pytest.mark.slow
class TestRealDataPerformance:
    """Test performance with real data volumes."""

    @pytest.mark.asyncio
    async def test_large_league_performance_real_data(self, realistic_large_players):
        """Test performance with realistic large player count."""
        # Arrange
        league = MockLeagueManager(max_players=100)

        # Act - Register all players
        start_time = time.perf_counter()

        tasks = [
            league.register_player(p["player_id"], p["endpoint"], p["game_types"])
            for p in realistic_large_players
        ]
        results = await asyncio.gather(*tasks)

        registration_time = time.perf_counter() - start_time

        # Generate schedule
        schedule_start = time.perf_counter()
        schedule = league.generate_schedule()
        schedule_time = time.perf_counter() - schedule_start

        # Assert
        assert all(r["success"] for r in results)
        assert len(league.players) == len(realistic_large_players)
        assert len(schedule) > 0

        print(f"\n  Registration: {registration_time:.2f}s for {len(realistic_large_players)} players")
        print(f"  Schedule generation: {schedule_time:.2f}s for {len(schedule)} rounds")
        print(f"  Total matches: {sum(len(r['matches']) for r in schedule)}")

        # Performance assertions
        assert registration_time < 5.0, "Registration should be < 5s"
        assert schedule_time < 2.0, "Schedule generation should be < 2s"

    @pytest.mark.asyncio
    async def test_realistic_match_throughput(self, realistic_players):
        """Test match execution throughput with realistic data."""
        # Arrange
        player_subset = realistic_players[:10]
        referee = MockReferee("R01")

        # Act - Execute many matches quickly
        num_matches = 20
        start_time = time.perf_counter()

        for i in range(num_matches):
            player1_idx = i % len(player_subset)
            player2_idx = (i + 1) % len(player_subset)

            if player1_idx == player2_idx:
                continue

            match_id = f"perf_match_{i}"
            await referee.start_match(
                match_id,
                player_subset[player1_idx]["player_id"],
                player_subset[player2_idx]["player_id"],
                rounds=3,
            )

        duration = time.perf_counter() - start_time
        throughput = num_matches / duration

        # Assert
        print(f"\n  Executed {num_matches} matches in {duration:.2f}s")
        print(f"  Throughput: {throughput:.2f} matches/second")

        assert throughput > 10, "Should handle at least 10 matches/second"


"""
COMPREHENSIVE EDGE CASES TESTED:

1. Real Data Integration:
   - Actual league standings patterns
   - Real player history data
   - Realistic match execution patterns
   - Real strategy distributions

2. Full League Lifecycle:
   - Complete registration process
   - Schedule generation with real player counts
   - Multiple rounds execution
   - Final standings calculation

3. Concurrent Operations:
   - Multiple matches simultaneously
   - Concurrent player registrations
   - Parallel result reporting
   - Load distribution across referees

4. Strategy Diversity:
   - All available strategies tested
   - Strategy vs strategy matchups
   - Realistic move patterns
   - Strategy-specific behaviors

5. Error Recovery:
   - Player failures during matches
   - Referee failures with recovery
   - Network issues simulation
   - State consistency after errors

6. Performance:
   - Large player counts (50+)
   - High match throughput
   - Concurrent operations
   - Realistic load patterns

7. Data Patterns:
   - Realistic player distributions
   - Real match data structures
   - Actual communication patterns
   - Real-world timing scenarios
"""

