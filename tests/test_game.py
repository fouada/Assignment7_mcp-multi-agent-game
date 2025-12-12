"""
Tests for game logic.
"""

import pytest
from src.game.odd_even import OddEvenGame, OddEvenRules, GameRole, Move, GamePhase
from src.game.match import Match, MatchScheduler


class TestOddEvenRules:
    """Test the Odd/Even game rules."""
    
    def test_validate_valid_move(self):
        """Test valid move validation."""
        rules = OddEvenRules()
        move = Move(player_id="P1", value=3)
        assert rules.validate_move(move) is True
    
    def test_validate_invalid_move_too_low(self):
        """Test invalid move (too low)."""
        rules = OddEvenRules()
        move = Move(player_id="P1", value=0)
        assert rules.validate_move(move) is False
    
    def test_validate_invalid_move_too_high(self):
        """Test invalid move (too high)."""
        rules = OddEvenRules()
        move = Move(player_id="P1", value=10)
        assert rules.validate_move(move) is False
    
    def test_calculate_result_odd_wins(self):
        """Test calculation when odd player wins."""
        rules = OddEvenRules()
        move1 = Move(player_id="P1", value=2)
        move2 = Move(player_id="P2", value=3)
        
        # Sum = 5 (odd), P1 is ODD role -> P1 wins
        sum_value, is_odd, winner = rules.calculate_result(
            move1, move2, GameRole.ODD
        )
        
        assert sum_value == 5
        assert is_odd is True
        assert winner == "P1"
    
    def test_calculate_result_even_wins(self):
        """Test calculation when even player wins."""
        rules = OddEvenRules()
        move1 = Move(player_id="P1", value=2)
        move2 = Move(player_id="P2", value=4)
        
        # Sum = 6 (even), P1 is ODD role -> P2 wins
        sum_value, is_odd, winner = rules.calculate_result(
            move1, move2, GameRole.ODD
        )
        
        assert sum_value == 6
        assert is_odd is False
        assert winner == "P2"


class TestOddEvenGame:
    """Test the Odd/Even game."""
    
    def test_game_creation(self):
        """Test game creation."""
        game = OddEvenGame(
            player1_id="P1",
            player2_id="P2",
            total_rounds=5,
        )
        
        assert game.player1_id == "P1"
        assert game.player2_id == "P2"
        assert game.total_rounds == 5
        assert game.phase == GamePhase.NOT_STARTED
    
    def test_game_start(self):
        """Test game start."""
        game = OddEvenGame(player1_id="P1", player2_id="P2")
        game.start()
        
        assert game.phase == GamePhase.AWAITING_MOVES
        assert game.current_round == 1
    
    def test_submit_move(self):
        """Test move submission."""
        game = OddEvenGame(player1_id="P1", player2_id="P2")
        game.start()
        
        # First move
        both_received = game.submit_move("P1", 3)
        assert both_received is False
        
        # Second move
        both_received = game.submit_move("P2", 4)
        assert both_received is True
        assert game.phase == GamePhase.MOVES_RECEIVED
    
    def test_resolve_round(self):
        """Test round resolution."""
        game = OddEvenGame(
            player1_id="P1",
            player2_id="P2",
            player1_role=GameRole.ODD,
        )
        game.start()
        
        # Submit moves
        game.submit_move("P1", 2)
        game.submit_move("P2", 3)
        
        # Resolve
        result = game.resolve_round()
        
        assert result.sum_value == 5
        assert result.sum_is_odd is True
        assert result.winner_id == "P1"  # P1 has ODD role, sum is odd
        assert game.player1_score == 1
        assert game.player2_score == 0
    
    def test_complete_game(self):
        """Test complete game flow."""
        game = OddEvenGame(
            player1_id="P1",
            player2_id="P2",
            player1_role=GameRole.ODD,
            total_rounds=3,
        )
        game.start()
        
        # Round 1: P1 wins (sum=5, odd)
        game.submit_move("P1", 2)
        game.submit_move("P2", 3)
        game.resolve_round()
        
        # Round 2: P2 wins (sum=6, even)
        game.submit_move("P1", 2)
        game.submit_move("P2", 4)
        game.resolve_round()
        
        # Round 3: P1 wins (sum=7, odd)
        game.submit_move("P1", 3)
        game.submit_move("P2", 4)
        game.resolve_round()
        
        assert game.is_complete
        result = game.get_result()
        assert result.player1_score == 2
        assert result.player2_score == 1
        assert result.winner_id == "P1"


class TestMatchScheduler:
    """Test match scheduling."""
    
    def test_round_robin_4_players(self):
        """Test round-robin for 4 players."""
        players = ["P1", "P2", "P3", "P4"]
        schedule = MatchScheduler.create_round_robin_schedule(players)
        
        # 4 players = 3 rounds
        assert len(schedule) == 3
        
        # Each round has 2 matches
        for round_matches in schedule:
            assert len(round_matches) == 2
        
        # Count total matches per player
        match_counts = {p: 0 for p in players}
        for round_matches in schedule:
            for p1, p2 in round_matches:
                match_counts[p1] += 1
                match_counts[p2] += 1
        
        # Each player plays 3 matches
        for count in match_counts.values():
            assert count == 3
    
    def test_round_robin_3_players(self):
        """Test round-robin for 3 players (odd number)."""
        players = ["P1", "P2", "P3"]
        schedule = MatchScheduler.create_round_robin_schedule(players)
        
        # 3 players = 3 rounds (with bye)
        assert len(schedule) == 3
        
        # Total matches should be 3 (each pair plays once)
        total_matches = sum(len(r) for r in schedule)
        assert total_matches == 3
    
    def test_create_matches_for_round(self):
        """Test match creation for a round."""
        pairings = [("P1", "P2"), ("P3", "P4")]
        endpoints = {
            "P1": "http://localhost:8101/mcp",
            "P2": "http://localhost:8102/mcp",
            "P3": "http://localhost:8103/mcp",
            "P4": "http://localhost:8104/mcp",
        }
        
        matches = MatchScheduler.create_matches_for_round(
            league_id="test_league",
            round_id=1,
            pairings=pairings,
            player_endpoints=endpoints,
        )
        
        assert len(matches) == 2
        assert matches[0].match_id == "R1M1"
        assert matches[1].match_id == "R1M2"
        assert matches[0].player1.player_id == "P1"
        assert matches[0].player2.player_id == "P2"


class TestMatch:
    """Test Match class."""
    
    def test_match_lifecycle(self):
        """Test match lifecycle."""
        match = Match(match_id="test_match", league_id="test_league")
        
        # Set players
        match.set_players(
            player1_id="P1",
            player1_endpoint="http://localhost:8101/mcp",
            player2_id="P2",
            player2_endpoint="http://localhost:8102/mcp",
        )
        
        assert match.player1.player_id == "P1"
        assert match.player2.player_id == "P2"
        
        # Mark players ready
        match.mark_player_ready("P1")
        assert not match.player2.ready
        
        both_ready = match.mark_player_ready("P2")
        assert both_ready
        
        # Create and start game
        match.create_game(total_rounds=5)
        match.start()
        
        assert match.is_active
        assert match.game is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

