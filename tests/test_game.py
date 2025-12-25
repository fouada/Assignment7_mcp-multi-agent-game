"""
Tests for game logic.
"""

import pytest

from src.game.match import Match, MatchScheduler
from src.game.odd_even import GamePhase, GameRole, Move, OddEvenGame, OddEvenRules


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
        """Test invalid move (too high allows 1-10)."""
        rules = OddEvenRules()
        move = Move(player_id="P1", value=11)  # 11 is above max_value=10
        assert rules.validate_move(move) is False

    def test_calculate_result_odd_wins(self):
        """Test calculation when odd player wins."""
        rules = OddEvenRules()
        move1 = Move(player_id="P1", value=2)
        move2 = Move(player_id="P2", value=3)

        # Sum = 5 (odd), P1 is ODD role -> P1 wins
        sum_value, is_odd, winner = rules.calculate_result(move1, move2, GameRole.ODD)

        assert sum_value == 5
        assert is_odd is True
        assert winner == "P1"

    def test_calculate_result_even_wins(self):
        """Test calculation when even player wins."""
        rules = OddEvenRules()
        move1 = Move(player_id="P1", value=2)
        move2 = Move(player_id="P2", value=4)

        # Sum = 6 (even), P1 is ODD role -> P2 wins
        sum_value, is_odd, winner = rules.calculate_result(move1, move2, GameRole.ODD)

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
        assert game.phase == GamePhase.WAITING_FOR_PLAYERS

    def test_game_start(self):
        """Test game start - transitions to COLLECTING_CHOICES."""
        game = OddEvenGame(player1_id="P1", player2_id="P2")
        game.start()

        assert game.phase == GamePhase.COLLECTING_CHOICES
        assert game.current_round == 1

    def test_submit_move(self):
        """Test move submission - transitions to DRAWING_NUMBER when both submit."""
        game = OddEvenGame(player1_id="P1", player2_id="P2")
        game.start()

        # First move
        both_received = game.submit_move("P1", 3)
        assert both_received is False

        # Second move
        both_received = game.submit_move("P2", 4)
        assert both_received is True
        assert game.phase == GamePhase.DRAWING_NUMBER

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
        match_counts = dict.fromkeys(players, 0)
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


class TestGameRegistry:
    """Test Game Registry."""

    def setup_method(self):
        """Setup for each test - ensure registry has default games."""
        from src.game.registry import register_default_games

        register_default_games()

    def test_default_game_registered(self):
        """Test that even_odd game is registered by default."""
        from src.game.registry import GameRegistry

        assert GameRegistry.is_registered("even_odd")

    def test_list_game_types(self):
        """Test listing registered game types."""
        from src.game.registry import GameRegistry

        types = GameRegistry.list_game_types()
        assert len(types) >= 1

        # Find even_odd
        even_odd = next((t for t in types if t["game_type"] == "even_odd"), None)
        assert even_odd is not None
        assert even_odd["display_name"] == "Even/Odd"
        assert even_odd["min_players"] == 2
        assert even_odd["max_players"] == 2

    def test_get_game_info(self):
        """Test getting game type info."""
        from src.game.registry import GameRegistry

        info = GameRegistry.get_game_info("even_odd")
        assert info is not None
        assert info.game_type == "even_odd"
        assert info.min_players == 2

    def test_create_game(self):
        """Test creating a game through the registry."""
        from src.game.registry import GameRegistry

        game = GameRegistry.create_game(
            "even_odd",
            player1_id="P01",
            player2_id="P02",
            total_rounds=3,
        )

        assert game is not None
        assert game.player1_id == "P01"
        assert game.player2_id == "P02"

    def test_create_unknown_game_raises(self):
        """Test that creating unknown game type raises error."""
        from src.game.registry import GameRegistry

        with pytest.raises(ValueError, match="Unknown game type"):
            GameRegistry.create_game("unknown_game")

    def test_validate_players(self):
        """Test player count validation."""
        from src.game.registry import GameRegistry

        # Valid
        is_valid, error = GameRegistry.validate_players("even_odd", 2)
        assert is_valid is True
        assert error is None

        # Too few
        is_valid, error = GameRegistry.validate_players("even_odd", 1)
        assert is_valid is False
        assert "Minimum" in error

        # Too many
        is_valid, error = GameRegistry.validate_players("even_odd", 3)
        assert is_valid is False
        assert "Maximum" in error

    def test_register_custom_game(self):
        """Test registering a custom game type."""
        from src.game.registry import GameRegistry

        # Simple mock game class
        class MockGame:
            game_type = "mock_game"
            min_players = 2
            max_players = 4

            def __init__(self, **kwargs):
                pass

        GameRegistry.register(
            game_type="mock_game",
            display_name="Mock Game",
            description="A mock game for testing",
            min_players=2,
            max_players=4,
            factory=MockGame,
        )

        assert GameRegistry.is_registered("mock_game")

        # Cleanup
        GameRegistry.unregister("mock_game")
        assert not GameRegistry.is_registered("mock_game")


class TestGameMove:
    """Test generic GameMove structure."""

    def test_game_move_creation(self):
        """Test creating a GameMove."""
        from src.game.registry import GameMove

        move = GameMove(
            player_id="P01",
            game_id="game_123",
            round_number=1,
            move_data={"value": 3},
        )

        assert move.player_id == "P01"
        assert move.game_id == "game_123"
        assert move.move_data["value"] == 3

    def test_game_move_to_dict(self):
        """Test converting GameMove to dict."""
        from src.game.registry import GameMove

        move = GameMove(
            player_id="P01",
            game_id="game_123",
            round_number=1,
            move_data={"value": 3},
        )

        data = move.to_dict()
        assert data["player_id"] == "P01"
        assert data["round_number"] == 1
        assert "timestamp" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
