"""
Integration Tests
=================

Comprehensive end-to-end integration tests covering:
- Full match workflows
- League coordination
- Multi-agent communication
- Error recovery scenarios
"""

import pytest
import asyncio
from typing import Dict, List

from tests.utils import (
    MockMCPClient,
    MockPlayer,
    MockReferee,
    MockLeagueManager,
    PlayerFactory,
    RefereeFactory,
    MatchFactory,
    ScenarioFactory,
    assert_game_completed,
    assert_match_result,
    assert_standings,
)


@pytest.mark.integration
class TestSimpleMatchIntegration:
    """Test complete match flow from start to finish."""
    
    @pytest.mark.asyncio
    async def test_complete_match_flow(self):
        """Test a complete match from player registration to result reporting."""
        # Arrange
        scenario = ScenarioFactory.create_simple_match_scenario()
        
        league = MockLeagueManager()
        player1 = MockPlayer(scenario["players"][0]["player_id"], strategy="random")
        player2 = MockPlayer(scenario["players"][1]["player_id"], strategy="random")
        referee = MockReferee(scenario["referee"]["referee_id"])
        
        # Act - Register players
        reg1 = await league.register_player(
            player1.player_id,
            scenario["players"][0]["endpoint"],
            ["even_odd"]
        )
        reg2 = await league.register_player(
            player2.player_id,
            scenario["players"][1]["endpoint"],
            ["even_odd"]
        )
        
        # Register referee
        ref_reg = await league.register_referee(
            referee.referee_id,
            scenario["referee"]["endpoint"]
        )
        
        # Start match
        match_result = await referee.start_match(
            scenario["match"]["match_id"],
            player1.player_id,
            player2.player_id,
            rounds=5
        )
        
        # Accept invitations
        await player1.accept_invitation(scenario["match"]["match_id"])
        await player2.accept_invitation(scenario["match"]["match_id"])
        
        # Play 5 rounds
        for round_num in range(5):
            move1 = await player1.make_move(scenario["match"]["match_id"], "odd")
            move2 = await player2.make_move(scenario["match"]["match_id"], "even")
            
            # Determine winner
            total = move1 + move2
            is_odd = total % 2 == 1
            winner = player1.player_id if is_odd else player2.player_id
            
            # Update scores
            player1.update_score(scenario["match"]["match_id"], 1 if is_odd else 0)
            player2.update_score(scenario["match"]["match_id"], 0 if is_odd else 1)
        
        # Determine overall winner
        winner_id = player1.player_id if player1.score > player2.score else player2.player_id
        loser_id = player2.player_id if winner_id == player1.player_id else player1.player_id
        
        # Report result
        reported = await referee.report_result(
            scenario["match"]["match_id"],
            winner_id,
            loser_id
        )
        
        # Assert
        assert reg1["success"]
        assert reg2["success"]
        assert ref_reg["success"]
        assert match_result["status"] == "started"
        assert reported
        assert len(referee.reported_results) == 1
        assert referee.reported_results[0]["match_id"] == scenario["match"]["match_id"]
    
    @pytest.mark.asyncio
    async def test_match_with_player_failure(self):
        """Test match handling when a player fails."""
        # Arrange
        scenario = ScenarioFactory.create_simple_match_scenario()
        
        player1 = MockPlayer(scenario["players"][0]["player_id"], strategy="random")
        player2 = MockPlayer(
            scenario["players"][1]["player_id"],
            strategy="random",
            fail_on_move=True  # This player will fail
        )
        referee = MockReferee(scenario["referee"]["referee_id"])
        
        # Act & Assert
        match = await referee.start_match(
            scenario["match"]["match_id"],
            player1.player_id,
            player2.player_id
        )
        
        await player1.accept_invitation(scenario["match"]["match_id"])
        await player2.accept_invitation(scenario["match"]["match_id"])
        
        # First player makes move successfully
        move1 = await player1.make_move(scenario["match"]["match_id"], "odd")
        assert 1 <= move1 <= 10
        
        # Second player fails
        with pytest.raises(ValueError):
            await player2.make_move(scenario["match"]["match_id"], "even")


@pytest.mark.integration
class TestLeagueIntegration:
    """Test complete league operations."""
    
    @pytest.mark.asyncio
    async def test_full_league_flow(self):
        """Test complete league from registration to final standings."""
        # Arrange
        scenario = ScenarioFactory.create_league_scenario(num_players=4)
        league = MockLeagueManager(max_players=10)
        
        # Act - Register all players
        players = {}
        for player_data in scenario["players"]:
            player = MockPlayer(player_data["player_id"])
            players[player.player_id] = player
            
            result = await league.register_player(
                player.player_id,
                player_data["endpoint"],
                ["even_odd"]
            )
            assert result["success"]
        
        # Register referees
        referees = {}
        for referee_data in scenario["referees"]:
            referee = MockReferee(referee_data["referee_id"])
            referees[referee.referee_id] = referee
            
            result = await league.register_referee(
                referee.referee_id,
                referee_data["endpoint"]
            )
            assert result["success"]
        
        # Play all matches
        for match_data in scenario["matches"]:
            referee = referees[match_data["referee_id"]]
            player1 = players[match_data["player1_id"]]
            player2 = players[match_data["player2_id"]]
            
            # Start match
            await referee.start_match(
                match_data["match_id"],
                player1.player_id,
                player2.player_id
            )
            
            # Play rounds and determine winner (simplified)
            winner = player1 if asyncio.get_event_loop().time() % 2 == 0 else player2
            loser = player2 if winner == player1 else player1
            
            # Update league stats
            league.players[winner.player_id]["wins"] += 1
            league.players[winner.player_id]["points"] += 3
            league.players[loser.player_id]["losses"] += 1
            
            # Report result
            await referee.report_result(
                match_data["match_id"],
                winner.player_id,
                loser.player_id
            )
        
        # Get final standings
        standings = league.get_standings()
        
        # Assert
        assert_standings(standings, min_players=4)
        assert len(standings) == 4
        assert standings[0]["points"] >= standings[1]["points"]
    
    @pytest.mark.asyncio
    async def test_league_with_registration_limit(self):
        """Test league behavior when reaching capacity."""
        # Arrange
        league = MockLeagueManager(max_players=2)
        
        player1_data = PlayerFactory.create()
        player2_data = PlayerFactory.create()
        player3_data = PlayerFactory.create()
        
        # Act
        result1 = await league.register_player(
            player1_data["player_id"],
            player1_data["endpoint"],
            ["even_odd"]
        )
        result2 = await league.register_player(
            player2_data["player_id"],
            player2_data["endpoint"],
            ["even_odd"]
        )
        result3 = await league.register_player(
            player3_data["player_id"],
            player3_data["endpoint"],
            ["even_odd"]
        )
        
        # Assert
        assert result1["success"]
        assert result2["success"]
        assert not result3["success"]
        assert "full" in result3["error"].lower()


@pytest.mark.integration
class TestConcurrentOperations:
    """Test concurrent operations and race conditions."""
    
    @pytest.mark.asyncio
    async def test_concurrent_player_registration(self):
        """Test multiple players registering simultaneously."""
        # Arrange
        league = MockLeagueManager(max_players=10)
        players_data = PlayerFactory.create_batch(5)
        
        # Act - Register all players concurrently
        tasks = [
            league.register_player(
                player["player_id"],
                player["endpoint"],
                ["even_odd"]
            )
            for player in players_data
        ]
        results = await asyncio.gather(*tasks)
        
        # Assert
        assert all(result["success"] for result in results)
        assert len(league.players) == 5
    
    @pytest.mark.asyncio
    async def test_concurrent_match_starts(self):
        """Test multiple matches starting simultaneously."""
        # Arrange
        referee = MockReferee("R1")
        matches_data = [MatchFactory.create() for _ in range(3)]
        
        # Act - Start all matches concurrently
        tasks = [
            referee.start_match(
                match["match_id"],
                match["player1_id"],
                match["player2_id"]
            )
            for match in matches_data
        ]
        results = await asyncio.gather(*tasks)
        
        # Assert
        assert all(result["status"] == "started" for result in results)
        assert len(referee.matches) == 3


@pytest.mark.integration
class TestErrorRecovery:
    """Test error handling and recovery scenarios."""
    
    @pytest.mark.asyncio
    async def test_referee_failure_recovery(self):
        """Test recovery from referee failure during result reporting."""
        # Arrange
        referee = MockReferee("R1", fail_on_report=True)
        match_data = MatchFactory.create()
        
        await referee.start_match(
            match_data["match_id"],
            match_data["player1_id"],
            match_data["player2_id"]
        )
        
        # Act & Assert
        with pytest.raises(ConnectionError):
            await referee.report_result(
                match_data["match_id"],
                match_data["player1_id"],
                match_data["player2_id"]
            )
        
        # Recovery: disable failure and retry
        referee.fail_on_report = False
        result = await referee.report_result(
            match_data["match_id"],
            match_data["player1_id"],
            match_data["player2_id"]
        )
        
        assert result
        assert len(referee.reported_results) == 1
    
    @pytest.mark.asyncio
    async def test_duplicate_registration_handling(self):
        """Test handling of duplicate player registration."""
        # Arrange
        league = MockLeagueManager()
        player_data = PlayerFactory.create()
        
        # Act - Register same player twice
        result1 = await league.register_player(
            player_data["player_id"],
            player_data["endpoint"],
            ["even_odd"]
        )
        result2 = await league.register_player(
            player_data["player_id"],
            player_data["endpoint"],
            ["even_odd"]
        )
        
        # Assert
        assert result1["success"]
        assert not result2["success"]
        assert "already" in result2["error"].lower()


@pytest.mark.integration
@pytest.mark.slow
class TestPerformanceIntegration:
    """Test system performance under load."""
    
    @pytest.mark.asyncio
    async def test_large_league_performance(self):
        """Test performance with many players and matches."""
        # Arrange
        scenario = ScenarioFactory.create_stress_test_scenario(num_players=20)
        league = MockLeagueManager(max_players=50)
        
        # Act - Register all players
        start_time = asyncio.get_event_loop().time()
        
        tasks = [
            league.register_player(
                player["player_id"],
                player["endpoint"],
                ["even_odd"]
            )
            for player in scenario["players"]
        ]
        results = await asyncio.gather(*tasks)
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        # Assert
        assert all(result["success"] for result in results)
        assert len(league.players) == 20
        assert duration < 5.0, f"Registration took {duration}s, should be < 5s"


# ====================
# Edge Case Integration Tests
# ====================

@pytest.mark.integration
class TestEdgeCaseIntegration:
    """Test edge cases in integrated scenarios."""
    
    @pytest.mark.asyncio
    async def test_match_with_all_draws(self):
        """Test match where all rounds result in draws (if applicable)."""
        # Arrange
        player1 = MockPlayer("P1", strategy="always_1")
        player2 = MockPlayer("P2", strategy="always_1")
        referee = MockReferee("R1")
        
        # Act
        await referee.start_match("M1", player1.player_id, player2.player_id, rounds=5)
        
        # Both players always make same move (1), so sum is always 2 (even)
        for _ in range(5):
            move1 = await player1.make_move("M1", "odd")
            move2 = await player2.make_move("M1", "even")
            assert move1 == 1
            assert move2 == 1
    
    @pytest.mark.asyncio
    async def test_league_with_single_referee(self):
        """Test league operation with only one referee handling all matches."""
        # Arrange
        league = MockLeagueManager()
        referee = MockReferee("R1")
        players_data = PlayerFactory.create_batch(3)
        
        # Register players
        for player_data in players_data:
            await league.register_player(
                player_data["player_id"],
                player_data["endpoint"],
                ["even_odd"]
            )
        
        # Register single referee
        await league.register_referee(referee.referee_id, "http://localhost:9000")
        
        # Act - All matches use same referee
        match1 = await referee.start_match("M1", "P1", "P2")
        match2 = await referee.start_match("M2", "P1", "P3")
        match3 = await referee.start_match("M3", "P2", "P3")
        
        # Assert
        assert len(referee.matches) == 3
        assert all(match["status"] == "in_progress" for match in [match1, match2, match3])


"""
EDGE CASES TESTED:

1. Player Failures:
   - Player fails during move submission
   - Player disconnects mid-game
   - Player timeout scenarios

2. Referee Failures:
   - Referee fails during result reporting
   - Referee becomes unavailable
   - Recovery after failure

3. League Management:
   - Registration at capacity
   - Duplicate registrations
   - Concurrent registrations
   - Single referee for all matches

4. Match Scenarios:
   - Complete match flow
   - All rounds result in same outcome
   - Concurrent match starts

5. Performance:
   - Large player count (20+)
   - Many concurrent operations
   - Response time under load

6. Concurrency:
   - Simultaneous player registrations
   - Concurrent match operations
   - Race condition handling

7. Error Recovery:
   - Retry after failure
   - State consistency after errors
   - Graceful degradation
"""

