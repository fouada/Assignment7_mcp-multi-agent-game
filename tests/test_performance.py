"""
Performance and Stress Tests
============================

Comprehensive performance testing including:
- Load testing
- Stress testing
- Endurance testing
- Scalability testing
- Benchmarking
"""

import asyncio
import time

import pytest

from tests.utils import (
    MockLeagueManager,
    MockPlayer,
    MockReferee,
    PerformanceTimer,
    PlayerFactory,
    ScenarioFactory,
)


@pytest.mark.slow
@pytest.mark.benchmark
class TestPerformanceBasics:
    """Basic performance tests for individual operations."""

    @pytest.mark.asyncio
    async def test_player_registration_performance(self):
        """Test performance of player registration."""
        league = MockLeagueManager(max_players=100)

        with PerformanceTimer("100 player registrations"):
            tasks = []
            for i in range(100):
                player_data = PlayerFactory.create(player_id=f"P{i:03d}")
                task = league.register_player(
                    player_data["player_id"], player_data["endpoint"], ["even_odd"]
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks)

        # Assert all successful
        assert all(r["success"] for r in results)
        assert len(league.players) == 100

    @pytest.mark.asyncio
    async def test_move_generation_performance(self):
        """Test performance of move generation."""
        player = MockPlayer("P1", strategy="random")

        start_time = time.perf_counter()

        moves = []
        for i in range(1000):
            move = await player.make_move(f"G{i}", "odd")
            moves.append(move)

        end_time = time.perf_counter()
        duration = end_time - start_time

        # Assert performance
        assert duration < 1.0, f"1000 moves took {duration}s, should be < 1s"
        assert len(moves) == 1000
        assert all(1 <= m <= 10 for m in moves)

    @pytest.mark.asyncio
    async def test_concurrent_match_starts_performance(self):
        """Test performance of starting multiple matches concurrently."""
        referee = MockReferee("R1")

        with PerformanceTimer("Starting 50 concurrent matches"):
            tasks = []
            for i in range(50):
                task = referee.start_match(f"M{i:03d}", f"P{i * 2:03d}", f"P{i * 2 + 1:03d}")
                tasks.append(task)

            results = await asyncio.gather(*tasks)

        assert len(results) == 50
        assert all(r["status"] == "started" for r in results)


@pytest.mark.slow
@pytest.mark.benchmark
class TestLoadTesting:
    """Load testing with realistic scenarios."""

    @pytest.mark.asyncio
    async def test_small_league_load(self):
        """Test load with small league (10 players)."""
        scenario = ScenarioFactory.create_league_scenario(num_players=10)
        league = MockLeagueManager(max_players=20)

        # Register players
        start_time = time.perf_counter()

        for player_data in scenario["players"]:
            await league.register_player(
                player_data["player_id"], player_data["endpoint"], ["even_odd"]
            )

        reg_time = time.perf_counter() - start_time

        # Assert
        assert len(league.players) == 10
        assert reg_time < 2.0, f"Registration took {reg_time}s, should be < 2s"

    @pytest.mark.asyncio
    async def test_medium_league_load(self):
        """Test load with medium league (50 players)."""
        scenario = ScenarioFactory.create_stress_test_scenario(num_players=50)
        league = MockLeagueManager(max_players=100)

        start_time = time.perf_counter()

        # Register all players concurrently
        tasks = [
            league.register_player(p["player_id"], p["endpoint"], ["even_odd"])
            for p in scenario["players"]
        ]
        results = await asyncio.gather(*tasks)

        total_time = time.perf_counter() - start_time

        # Assert
        assert all(r["success"] for r in results)
        assert len(league.players) == 50
        assert total_time < 5.0, f"Registration took {total_time}s, should be < 5s"

        # Calculate throughput
        throughput = len(results) / total_time
        print(f"\n  Throughput: {throughput:.2f} registrations/second")
        assert throughput > 10, "Should handle at least 10 registrations/second"

    @pytest.mark.asyncio
    async def test_large_league_load(self):
        """Test load with large league (100 players)."""
        scenario = ScenarioFactory.create_stress_test_scenario(num_players=100)
        league = MockLeagueManager(max_players=150)

        start_time = time.perf_counter()

        # Register in batches for better control
        batch_size = 20
        for i in range(0, len(scenario["players"]), batch_size):
            batch = scenario["players"][i : i + batch_size]
            tasks = [
                league.register_player(p["player_id"], p["endpoint"], ["even_odd"]) for p in batch
            ]
            await asyncio.gather(*tasks)

        total_time = time.perf_counter() - start_time

        # Assert
        assert len(league.players) == 100
        assert total_time < 10.0, f"Registration took {total_time}s, should be < 10s"


@pytest.mark.slow
@pytest.mark.benchmark
class TestStressTesting:
    """Stress testing to find system limits."""

    @pytest.mark.asyncio
    async def test_maximum_concurrent_matches(self):
        """Test maximum number of concurrent matches."""
        referee = MockReferee("R1")

        # Try to start many matches
        num_matches = 100

        start_time = time.perf_counter()

        tasks = [
            referee.start_match(f"M{i:04d}", f"P{i * 2:04d}", f"P{i * 2 + 1:04d}")
            for i in range(num_matches)
        ]
        results = await asyncio.gather(*tasks)

        total_time = time.perf_counter() - start_time

        # Assert
        assert len(results) == num_matches
        assert len(referee.matches) == num_matches
        print(f"\n  Started {num_matches} matches in {total_time:.2f}s")
        print(f"  Average: {total_time / num_matches * 1000:.2f}ms per match")

    @pytest.mark.asyncio
    async def test_rapid_move_submission(self):
        """Test rapid move submissions."""
        player = MockPlayer("P1")

        num_moves = 10000
        start_time = time.perf_counter()

        for i in range(num_moves):
            await player.make_move(f"G{i % 100}", "odd")

        total_time = time.perf_counter() - start_time
        moves_per_second = num_moves / total_time

        print(f"\n  {num_moves} moves in {total_time:.2f}s")
        print(f"  {moves_per_second:.2f} moves/second")

        assert moves_per_second > 1000, "Should handle >1000 moves/second"

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self):
        """Test memory usage with many objects."""
        import sys

        # Create many players
        players = [MockPlayer(f"P{i:05d}") for i in range(1000)]

        # Record memory (approximate)
        total_size = sum(sys.getsizeof(p) for p in players)
        avg_size = total_size / len(players)

        print(f"\n  1000 players: {total_size / 1024:.2f} KB")
        print(f"  Average per player: {avg_size:.2f} bytes")

        # Assert reasonable memory usage
        assert avg_size < 10000, "Each player should use < 10KB"


@pytest.mark.slow
@pytest.mark.benchmark
class TestEnduranceTesting:
    """Endurance testing for long-running operations."""

    @pytest.mark.asyncio
    async def test_long_running_league(self):
        """Test league over extended period."""
        league = MockLeagueManager(max_players=20)
        players = {}

        # Register players
        for i in range(20):
            player_data = PlayerFactory.create(player_id=f"P{i:02d}")
            player = MockPlayer(player_data["player_id"])
            players[player.player_id] = player

            await league.register_player(player.player_id, player_data["endpoint"], ["even_odd"])

        # Simulate many rounds
        num_rounds = 100
        start_time = time.perf_counter()

        for round_num in range(num_rounds):
            # Generate matches for this round
            player_ids = list(players.keys())
            for i in range(0, len(player_ids) - 1, 2):
                p1_id = player_ids[i]
                p2_id = player_ids[i + 1]

                # Simulate match
                winner_id = p1_id if (i + round_num) % 2 == 0 else p2_id
                loser_id = p2_id if winner_id == p1_id else p1_id

                league.players[winner_id]["wins"] += 1
                league.players[winner_id]["points"] += 3
                league.players[loser_id]["losses"] += 1

        total_time = time.perf_counter() - start_time

        # Assert
        standings = league.get_standings()
        assert len(standings) == 20
        print(f"\n  {num_rounds} rounds completed in {total_time:.2f}s")
        print(f"  Average: {total_time / num_rounds * 1000:.2f}ms per round")

    @pytest.mark.asyncio
    async def test_continuous_operation(self):
        """Test continuous operations over time."""
        league = MockLeagueManager(max_players=50)

        duration = 5.0  # Run for 5 seconds
        start_time = time.perf_counter()
        operations = 0

        while time.perf_counter() - start_time < duration:
            # Continuously register players (cycling through)
            player_id = f"P{operations % 50:03d}"

            if player_id in league.players:
                # Player already exists, skip
                operations += 1
                continue

            player_data = PlayerFactory.create(player_id=player_id)
            await league.register_player(player_id, player_data["endpoint"], ["even_odd"])
            operations += 1

        ops_per_second = operations / duration

        print(f"\n  {operations} operations in {duration}s")
        print(f"  {ops_per_second:.2f} operations/second")

        assert ops_per_second > 5, "Should handle >5 ops/second"


@pytest.mark.slow
@pytest.mark.benchmark
class TestScalabilityTesting:
    """Test system scalability."""

    @pytest.mark.asyncio
    async def test_scaling_with_players(self):
        """Test how performance scales with number of players."""
        results = []

        for num_players in [10, 25, 50, 100]:
            league = MockLeagueManager(max_players=num_players + 10)

            start_time = time.perf_counter()

            tasks = [
                league.register_player(f"P{i:04d}", f"http://localhost:{8000 + i}", ["even_odd"])
                for i in range(num_players)
            ]
            await asyncio.gather(*tasks)

            duration = time.perf_counter() - start_time
            throughput = num_players / duration

            results.append({"players": num_players, "time": duration, "throughput": throughput})

        # Print results
        print("\n  Scalability Results:")
        print("  Players | Time (s) | Throughput (ops/s)")
        print("  --------|----------|-------------------")
        for r in results:
            print(f"  {r['players']:7d} | {r['time']:8.3f} | {r['throughput']:17.2f}")

        # Assert reasonable scaling
        # As we double players, time should not quadruple
        assert results[1]["time"] < results[0]["time"] * 3
        assert results[2]["time"] < results[1]["time"] * 3

    @pytest.mark.asyncio
    async def test_scaling_with_matches(self):
        """Test how performance scales with number of matches."""
        referee = MockReferee("R1")

        results = []

        for num_matches in [10, 50, 100, 200]:
            start_time = time.perf_counter()

            tasks = [
                referee.start_match(f"M{i:05d}", f"P{i * 2:05d}", f"P{i * 2 + 1:05d}")
                for i in range(num_matches)
            ]
            await asyncio.gather(*tasks)

            duration = time.perf_counter() - start_time
            throughput = num_matches / duration

            results.append({"matches": num_matches, "time": duration, "throughput": throughput})

        # Print results
        print("\n  Match Scalability Results:")
        print("  Matches | Time (s) | Throughput (matches/s)")
        print("  --------|----------|----------------------")
        for r in results:
            print(f"  {r['matches']:7d} | {r['time']:8.3f} | {r['throughput']:21.2f}")


@pytest.mark.slow
@pytest.mark.benchmark
class TestBenchmarking:
    """Benchmark specific operations."""

    def test_benchmark_move_validation(self, benchmark):
        """Benchmark move validation."""
        from tests.utils import assert_valid_move

        def validate_moves():
            for move in range(1, 11):
                assert_valid_move(move)

        benchmark(validate_moves)

    @pytest.mark.asyncio
    async def test_benchmark_player_creation(self):
        """Benchmark player creation."""
        num_iterations = 1000

        start_time = time.perf_counter()

        for i in range(num_iterations):
            player = MockPlayer(f"P{i:05d}")
            assert player.player_id == f"P{i:05d}"

        duration = time.perf_counter() - start_time
        per_operation = duration / num_iterations * 1000000  # microseconds

        print(f"\n  Created {num_iterations} players in {duration:.4f}s")
        print(f"  Average: {per_operation:.2f}μs per player")

        assert per_operation < 100, "Player creation should take < 100μs"


"""
PERFORMANCE METRICS TESTED:

1. Registration Performance:
   - 100 player registrations
   - Concurrent registration throughput
   - Batch registration performance

2. Move Generation:
   - 1000 moves generation speed
   - Rapid move submission (10,000 moves)
   - Moves per second throughput

3. Match Operations:
   - Concurrent match starts (50-100 matches)
   - Match start latency
   - Match throughput

4. Load Testing:
   - Small league (10 players)
   - Medium league (50 players)
   - Large league (100 players)

5. Stress Testing:
   - Maximum concurrent matches (100+)
   - Rapid operations
   - Memory usage under load

6. Endurance Testing:
   - Long-running league (100 rounds)
   - Continuous operations (5s+)
   - Sustained throughput

7. Scalability:
   - Scaling with player count
   - Scaling with match count
   - Linear vs quadratic scaling

8. Benchmarks:
   - Move validation speed
   - Player creation speed
   - Operation latencies
"""
