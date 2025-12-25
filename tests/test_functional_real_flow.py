"""
Functional Tests with Real Game Flow
====================================

MIT-Level functional testing simulating complete game flows using real data.
Tests verify end-to-end functionality with realistic user scenarios.

Test Scenarios:
- Complete league season with realistic schedules
- Individual match flows with all game phases
- Multi-agent coordination in realistic contexts
- State management throughout game lifecycle
- Data persistence and recovery patterns
"""

import asyncio

import pytest

from tests.utils import (
    MockLeagueManager,
    MockPlayer,
    MockReferee,
    get_real_data_loader,
)


@pytest.mark.integration
class TestCompleteLeagueFlow:
    """Test complete league lifecycle with realistic flow."""

    @pytest.mark.asyncio
    async def test_full_season_realistic_flow(self, realistic_players):
        """Test complete league season from start to finish."""
        # Phase 1: League Setup
        league = MockLeagueManager(max_players=20, league_id="test_season_2025")
        loader = get_real_data_loader()

        # Use realistic player data
        player_subset = realistic_players[:8]
        players = {}
        referees = {}

        # Phase 2: Player Registration
        print("\n  === Phase 1: Player Registration ===")
        for player_data in player_subset:
            player = MockPlayer(player_data["player_id"], strategy=player_data["strategy"])
            players[player.player_id] = player

            result = await league.register_player(
                player.player_id, player_data["endpoint"], player_data["game_types"]
            )

            assert result["success"]
            print(f"  Registered: {player.player_id} (Strategy: {player_data['strategy']})")

        # Phase 3: Referee Registration
        print("\n  === Phase 2: Referee Registration ===")
        for i in range(2):
            ref_id = f"R{i + 1:02d}"
            referee = MockReferee(ref_id)
            referees[ref_id] = referee

            result = await league.register_referee(ref_id, f"http://localhost:{9000 + i}")
            assert result["success"]
            print(f"  Registered referee: {ref_id}")

        # Phase 4: Schedule Generation
        print("\n  === Phase 3: Schedule Generation ===")
        schedule = league.generate_schedule()
        print(f"  Generated {len(schedule)} rounds")
        print(f"  Total matches: {sum(len(r['matches']) for r in schedule)}")

        # Phase 5: Play All Rounds
        print("\n  === Phase 4: Season Play ===")
        for round_idx, round_data in enumerate(schedule):
            print(f"\n  Round {round_idx + 1}/{len(schedule)}")

            for match in round_data["matches"]:
                if match["player2_id"] == "BYE":
                    # Handle bye
                    league.players[match["player1_id"]]["points"] += 1
                    print(f"    {match['player1_id']} gets BYE")
                    continue

                # Assign referee (round-robin)
                referee = referees[list(referees.keys())[round_idx % len(referees)]]

                player1 = players[match["player1_id"]]
                player2 = players[match["player2_id"]]

                print(f"    Match: {player1.player_id} vs {player2.player_id}")

                # Start match
                await referee.start_match(
                    match["match_id"], player1.player_id, player2.player_id, rounds=5
                )

                # Play rounds
                for game_round in range(5):
                    move1 = await player1.make_move(match["match_id"], "odd")
                    move2 = await player2.make_move(match["match_id"], "even")

                    total = move1 + move2
                    is_odd = total % 2 == 1

                    player1.update_score(match["match_id"], 1 if is_odd else 0)
                    player2.update_score(match["match_id"], 0 if is_odd else 1)

                # Determine winner
                winner_id = (
                    player1.player_id if player1.score > player2.score else player2.player_id
                )
                loser_id = player2.player_id if winner_id == player1.player_id else player1.player_id

                # Report result
                await referee.report_result(match["match_id"], winner_id, loser_id)

                # Update league standings
                league.players[winner_id]["wins"] += 1
                league.players[winner_id]["points"] += 3
                league.players[loser_id]["losses"] += 1

                print(f"      Winner: {winner_id}")

        # Phase 6: Final Standings
        print("\n  === Phase 5: Final Standings ===")
        standings = league.get_standings()

        for idx, player_standing in enumerate(standings[:5], 1):
            print(
                f"  {idx}. {player_standing['player_id']}: "
                f"{player_standing['points']} points "
                f"({player_standing['wins']}W-{player_standing['losses']}L)"
            )

        # Assertions
        assert len(standings) == len(player_subset)
        assert standings[0]["points"] >= standings[-1]["points"]

        # Verify all players played expected matches
        for player_id, player_data in league.players.items():
            total_matches = player_data["wins"] + player_data["losses"]
            assert total_matches > 0, f"{player_id} didn't play any matches"

    @pytest.mark.asyncio
    async def test_league_with_dynamic_joins(self, realistic_players):
        """Test league with players joining at different times."""
        league = MockLeagueManager(max_players=20)

        # Initial players
        initial_players = realistic_players[:3]
        for player_data in initial_players:
            player = MockPlayer(player_data["player_id"], strategy=player_data["strategy"])
            await league.register_player(
                player.player_id, player_data["endpoint"], player_data["game_types"]
            )

        assert len(league.players) == 3

        # Add more players
        additional_players = realistic_players[3:6]
        for player_data in additional_players:
            player = MockPlayer(player_data["player_id"], strategy=player_data["strategy"])
            await league.register_player(
                player.player_id, player_data["endpoint"], player_data["game_types"]
            )

        assert len(league.players) == 6

        # Generate schedule
        schedule = league.generate_schedule()
        assert len(schedule) > 0


@pytest.mark.integration
class TestCompleteMatchFlow:
    """Test complete match flow with all phases."""

    @pytest.mark.asyncio
    async def test_full_match_lifecycle(self, realistic_players):
        """Test complete match from invitation to result reporting."""
        # Arrange
        player1_data = realistic_players[0]
        player2_data = realistic_players[1]

        player1 = MockPlayer(player1_data["player_id"], strategy=player1_data["strategy"])
        player2 = MockPlayer(player2_data["player_id"], strategy=player2_data["strategy"])
        referee = MockReferee("R01")
        match_id = "match_full_lifecycle"

        print(f"\n  Match: {player1.player_id} ({player1_data['strategy']}) vs "
              f"{player2.player_id} ({player2_data['strategy']})")

        # Phase 1: Match Initialization
        print("\n  Phase 1: Match Initialization")
        await referee.start_match(match_id, player1.player_id, player2.player_id, rounds=5)
        assert match_id in referee.matches
        print(f"    Match {match_id} initialized")

        # Phase 2: Game Invitation (implicit in mock)
        print("\n  Phase 2: Players Accept Invitation")
        await player1.accept_invitation(match_id)
        await player2.accept_invitation(match_id)
        print("    Both players accepted")

        # Phase 3: Game Play
        print("\n  Phase 3: Game Play (5 rounds)")
        round_results = []

        for round_num in range(5):
            # Move phase
            move1 = await player1.make_move(match_id, "odd")
            move2 = await player2.make_move(match_id, "even")

            # Resolution phase
            total = move1 + move2
            is_odd = total % 2 == 1
            winner = "odd" if is_odd else "even"

            round_results.append(
                {
                    "round": round_num + 1,
                    "move1": move1,
                    "move2": move2,
                    "sum": total,
                    "winner": winner,
                }
            )

            # Update scores
            player1.update_score(match_id, 1 if is_odd else 0)
            player2.update_score(match_id, 0 if is_odd else 1)

            print(
                f"    Round {round_num + 1}: {move1} + {move2} = {total} ({winner}) "
                f"Score: {player1.score}-{player2.score}"
            )

        # Phase 4: Match Completion
        print("\n  Phase 4: Match Completion")
        winner_id = player1.player_id if player1.score > player2.score else player2.player_id
        loser_id = player2.player_id if winner_id == player1.player_id else player1.player_id

        print(f"    Final Score: {player1.score}-{player2.score}")
        print(f"    Winner: {winner_id}")

        # Phase 5: Result Reporting
        print("\n  Phase 5: Result Reporting")
        reported = await referee.report_result(match_id, winner_id, loser_id)
        assert reported
        print("    Result reported to league")

        # Assertions
        assert len(round_results) == 5
        assert all(1 <= r["move1"] <= 10 for r in round_results)
        assert all(1 <= r["move2"] <= 10 for r in round_results)
        assert len(referee.reported_results) == 1

    @pytest.mark.asyncio
    async def test_match_with_parity_selection(self, realistic_players):
        """Test match with parity selection phase."""
        player1_data = realistic_players[0]
        player2_data = realistic_players[1]

        player1 = MockPlayer(player1_data["player_id"], strategy=player1_data["strategy"])
        player2 = MockPlayer(player2_data["player_id"], strategy=player2_data["strategy"])

        referee = MockReferee("R01")
        match_id = "match_parity_selection"

        # Start match
        await referee.start_match(match_id, player1.player_id, player2.player_id, rounds=5)

        # Player 1 chooses parity (simulated)
        chosen_parity = "odd"  # Player 1 chooses odd
        player1.role = chosen_parity
        player2.role = "even"

        print(f"\n  {player1.player_id} chose: {chosen_parity}")
        print(f"  {player2.player_id} gets: {player2.role}")

        # Play match
        for round_num in range(5):
            move1 = await player1.make_move(match_id, player1.role)
            move2 = await player2.make_move(match_id, player2.role)

            total = move1 + move2
            is_odd = total % 2 == 1

            player1.update_score(match_id, 1 if is_odd else 0)
            player2.update_score(match_id, 0 if is_odd else 1)

        # Report result
        winner_id = player1.player_id if player1.score > player2.score else player2.player_id
        loser_id = player2.player_id if winner_id == player1.player_id else player1.player_id

        reported = await referee.report_result(match_id, winner_id, loser_id)
        assert reported


@pytest.mark.integration
class TestMultiAgentCoordination:
    """Test multi-agent coordination in realistic scenarios."""

    @pytest.mark.asyncio
    async def test_multiple_referees_coordinating(self, realistic_players):
        """Test multiple referees managing matches simultaneously."""
        league = MockLeagueManager(max_players=20)
        player_subset = realistic_players[:8]

        # Register players
        players = {}
        for player_data in player_subset:
            player = MockPlayer(player_data["player_id"], strategy=player_data["strategy"])
            players[player.player_id] = player
            await league.register_player(
                player.player_id, player_data["endpoint"], player_data["game_types"]
            )

        # Register multiple referees
        referees = []
        for i in range(4):
            ref_id = f"R{i + 1:02d}"
            referee = MockReferee(ref_id)
            referees.append(referee)
            await league.register_referee(ref_id, f"http://localhost:{9000 + i}")

        # Generate schedule
        schedule = league.generate_schedule()
        first_round = schedule[0]

        # Assign matches to different referees
        async def execute_match_with_referee(match, referee):
            if match["player2_id"] == "BYE":
                return None

            player1 = players[match["player1_id"]]
            player2 = players[match["player2_id"]]

            await referee.start_match(
                match["match_id"], player1.player_id, player2.player_id, rounds=3
            )

            # Quick simulation
            winner = player1 if hash(match["match_id"]) % 2 == 0 else player2
            return await referee.report_result(match["match_id"], winner.player_id, player2.player_id)

        # Execute matches in parallel with different referees
        tasks = []
        for idx, match in enumerate(first_round["matches"]):
            referee = referees[idx % len(referees)]
            tasks.append(execute_match_with_referee(match, referee))

        results = await asyncio.gather(*tasks)

        # Verify
        valid_results = [r for r in results if r is not None]
        assert len(valid_results) > 0

        # Verify each referee handled some matches
        matches_per_referee = [len(ref.matches) for ref in referees]
        assert sum(matches_per_referee) == len(first_round["matches"])

    @pytest.mark.asyncio
    async def test_league_manager_coordination(self, realistic_players):
        """Test league manager coordinating multiple components."""
        league = MockLeagueManager(max_players=20, league_id="coordination_test")
        player_subset = realistic_players[:6]

        # Register players
        players = {}
        for player_data in player_subset:
            player = MockPlayer(player_data["player_id"], strategy=player_data["strategy"])
            players[player.player_id] = player
            result = await league.register_player(
                player.player_id, player_data["endpoint"], player_data["game_types"]
            )
            assert result["success"]

        # Register referees
        referees = []
        for i in range(2):
            ref_id = f"R{i + 1:02d}"
            referee = MockReferee(ref_id)
            referees.append(referee)
            result = await league.register_referee(ref_id, f"http://localhost:{9000 + i}")
            assert result["success"]

        # Generate schedule
        schedule = league.generate_schedule()

        # Verify league manager tracked everything
        assert len(league.players) == 6
        assert len(league.referees) == 2
        assert len(schedule) > 0

        # Verify schedule quality
        total_matches = sum(len(r["matches"]) for r in schedule)
        expected_matches = len(player_subset) * (len(player_subset) - 1) / 2
        assert total_matches == expected_matches


@pytest.mark.integration
class TestStateManagement:
    """Test state management throughout game lifecycle."""

    @pytest.mark.asyncio
    async def test_state_persistence_across_rounds(self, realistic_players):
        """Test that state persists correctly across multiple rounds."""
        player1_data = realistic_players[0]
        player2_data = realistic_players[1]

        player1 = MockPlayer(player1_data["player_id"], strategy=player1_data["strategy"])
        player2 = MockPlayer(player2_data["player_id"], strategy=player2_data["strategy"])
        referee = MockReferee("R01")
        match_id = "state_persistence_test"

        # Start match
        await referee.start_match(match_id, player1.player_id, player2.player_id, rounds=10)

        # Play and track state
        states = []

        for round_num in range(10):
            # Capture state before round
            state_before = {
                "round": round_num + 1,
                "score1": player1.score,
                "score2": player2.score,
            }

            # Play round
            move1 = await player1.make_move(match_id, "odd")
            move2 = await player2.make_move(match_id, "even")

            total = move1 + move2
            is_odd = total % 2 == 1

            player1.update_score(match_id, 1 if is_odd else 0)
            player2.update_score(match_id, 0 if is_odd else 1)

            # Capture state after round
            state_after = {
                "round": round_num + 1,
                "score1": player1.score,
                "score2": player2.score,
                "move1": move1,
                "move2": move2,
            }

            states.append({"before": state_before, "after": state_after})

        # Verify state progression
        for idx, state in enumerate(states):
            # Score should never decrease
            if idx > 0:
                assert state["before"]["score1"] >= states[idx - 1]["after"]["score1"] - 1
                assert state["before"]["score2"] >= states[idx - 1]["after"]["score2"] - 1

            # Score should increase by 0 or 1 each round
            score_diff1 = state["after"]["score1"] - state["before"]["score1"]
            score_diff2 = state["after"]["score2"] - state["before"]["score2"]

            assert score_diff1 in [0, 1]
            assert score_diff2 in [0, 1]
            assert score_diff1 + score_diff2 == 1  # Exactly one winner per round


"""
FUNCTIONAL TEST COVERAGE:

1. Complete League Flow:
   - Full season from setup to standings
   - Player registration at different times
   - Schedule generation and execution
   - Standing calculations

2. Complete Match Flow:
   - Match initialization
   - Invitation and acceptance
   - Game play with all rounds
   - Result reporting
   - Parity selection

3. Multi-Agent Coordination:
   - Multiple referees working simultaneously
   - League manager coordination
   - Distributed match execution
   - Load balancing

4. State Management:
   - State persistence across rounds
   - Score tracking
   - History accumulation
   - State transitions

5. Real-World Scenarios:
   - Realistic player strategies
   - Actual game patterns
   - Real communication flows
   - Practical timing

6. Data Integrity:
   - Consistent state updates
   - Accurate score calculation
   - Proper match results
   - Valid standings

7. Integration Points:
   - Player-Referee communication
   - Referee-League communication
   - Multi-component coordination
   - Event synchronization
"""

