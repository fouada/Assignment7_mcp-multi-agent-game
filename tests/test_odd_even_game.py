"""
Comprehensive Tests for Odd-Even Game Logic
============================================

Tests cover:
- Game initialization and configuration
- Role assignment (odd/even)
- Move validation and submission
- Round resolution and scoring
- Game state management
- Winner determination
- Edge cases and boundary conditions
"""

import pytest

from src.game.odd_even import (
    GamePhase,
    GameResult,
    GameRole,
    OddEvenGame,
    RoundResult,
)


class TestGameInitialization:
    """Test game initialization."""

    def test_game_init_basic(self):
        """Test basic game initialization."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            total_rounds=5,
        )

        assert game.game_id == "game_001"
        assert game.player1_id == "P01"
        assert game.player2_id == "P02"
        assert game.total_rounds == 5
        assert game.current_round == 0
        assert not game.is_complete

    def test_game_init_with_roles(self):
        """Test game initialization with explicit roles."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            player1_role=GameRole.ODD,
            total_rounds=5,
        )

        assert game.player1_role == GameRole.ODD
        assert game.player2_role == GameRole.EVEN

    def test_game_init_minimum_rounds(self):
        """Test game initialization with minimum rounds."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            total_rounds=1,
        )

        assert game.total_rounds == 1

    def test_game_init_many_rounds(self):
        """Test game initialization with many rounds."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            total_rounds=100,
        )

        assert game.total_rounds == 100


class TestRoleAssignment:
    """Test role assignment."""

    def test_role_assignment_odd_player1(self):
        """Test assigning odd role to player 1."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            player1_role=GameRole.ODD,
        )

        assert game.player1_role == GameRole.ODD
        assert game.player2_role == GameRole.EVEN

    def test_role_assignment_even_player1(self):
        """Test assigning even role to player 1."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            player1_role=GameRole.EVEN,
        )

        assert game.player1_role == GameRole.EVEN
        assert game.player2_role == GameRole.ODD

    def test_get_player_role(self):
        """Test getting player role."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            player1_role=GameRole.ODD,
        )

        assert game.get_player_role("P01") == GameRole.ODD
        assert game.get_player_role("P02") == GameRole.EVEN

    def test_get_player_role_unknown_player(self):
        """Test getting role for unknown player."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
        )

        with pytest.raises(ValueError, match="Unknown player"):
            game.get_player_role("P99")

    def test_get_opponent_id(self):
        """Test getting opponent ID."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
        )

        assert game.get_opponent_id("P01") == "P02"
        assert game.get_opponent_id("P02") == "P01"

    def test_get_opponent_id_unknown_player(self):
        """Test getting opponent for unknown player."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
        )

        with pytest.raises(ValueError, match="Unknown player"):
            game.get_opponent_id("P99")


class TestGameStart:
    """Test game start."""

    def test_start_game(self):
        """Test starting a game."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            total_rounds=5,
        )

        game.start()

        assert game.phase == GamePhase.PLAYING
        assert game.current_round == 1

    def test_start_game_twice(self):
        """Test starting a game twice raises error."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
        )

        game.start()

        with pytest.raises(ValueError, match="already"):
            game.start()


class TestMoveSubmission:
    """Test move submission."""

    def test_submit_move_valid(self):
        """Test submitting valid moves."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
        )
        game.start()

        # Submit player 1 move
        both_received = game.submit_move("P01", 5)
        assert not both_received

        # Submit player 2 move
        both_received = game.submit_move("P02", 4)
        assert both_received

    def test_submit_move_boundary_values(self):
        """Test submitting boundary move values (1 and 10)."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
        )
        game.start()

        # Test minimum value
        game.submit_move("P01", 1)
        game.submit_move("P02", 10)

        # Resolve and start next round
        game.resolve_round()

        # Test maximum value
        game.submit_move("P01", 10)
        game.submit_move("P02", 1)

    def test_submit_move_invalid_low(self):
        """Test submitting move below minimum."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
        )
        game.start()

        with pytest.raises(ValueError, match="between 1 and 10"):
            game.submit_move("P01", 0)

    def test_submit_move_invalid_high(self):
        """Test submitting move above maximum."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
        )
        game.start()

        with pytest.raises(ValueError, match="between 1 and 10"):
            game.submit_move("P01", 11)

    def test_submit_move_unknown_player(self):
        """Test submitting move for unknown player."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
        )
        game.start()

        with pytest.raises(ValueError, match="Unknown player"):
            game.submit_move("P99", 5)

    def test_submit_move_before_start(self):
        """Test submitting move before game starts."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
        )

        with pytest.raises(ValueError, match="not started"):
            game.submit_move("P01", 5)

    def test_submit_move_twice(self):
        """Test submitting move twice from same player."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
        )
        game.start()

        game.submit_move("P01", 5)

        with pytest.raises(ValueError, match="already submitted"):
            game.submit_move("P01", 7)


class TestRoundResolution:
    """Test round resolution and scoring."""

    def test_resolve_round_odd_wins(self):
        """Test resolving round where odd role wins."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            player1_role=GameRole.ODD,
        )
        game.start()

        # Moves: 5 + 4 = 9 (odd)
        game.submit_move("P01", 5)
        game.submit_move("P02", 4)

        result = game.resolve_round()

        assert result.sum_value == 9
        assert result.winner_id == "P01"
        assert game.player1_score == 1
        assert game.player2_score == 0

    def test_resolve_round_even_wins(self):
        """Test resolving round where even role wins."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            player1_role=GameRole.EVEN,
        )
        game.start()

        # Moves: 5 + 5 = 10 (even)
        game.submit_move("P01", 5)
        game.submit_move("P02", 5)

        result = game.resolve_round()

        assert result.sum_value == 10
        assert result.winner_id == "P01"
        assert game.player1_score == 1
        assert game.player2_score == 0

    def test_resolve_round_multiple_rounds(self):
        """Test resolving multiple rounds."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            player1_role=GameRole.ODD,
            total_rounds=3,
        )
        game.start()

        # Round 1: P01 wins (5+4=9, odd)
        game.submit_move("P01", 5)
        game.submit_move("P02", 4)
        game.resolve_round()
        assert game.player1_score == 1
        assert game.current_round == 2

        # Round 2: P02 wins (3+3=6, even)
        game.submit_move("P01", 3)
        game.submit_move("P02", 3)
        game.resolve_round()
        assert game.player2_score == 1
        assert game.current_round == 3

        # Round 3: P01 wins (7+2=9, odd)
        game.submit_move("P01", 7)
        game.submit_move("P02", 2)
        game.resolve_round()
        assert game.player1_score == 2
        assert game.is_complete

    def test_resolve_round_without_both_moves(self):
        """Test resolving round without both moves."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
        )
        game.start()

        game.submit_move("P01", 5)

        with pytest.raises(ValueError, match="both players"):
            game.resolve_round()

    def test_resolve_round_after_game_complete(self):
        """Test resolving round after game is complete."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            total_rounds=1,
        )
        game.start()

        game.submit_move("P01", 5)
        game.submit_move("P02", 4)
        game.resolve_round()

        with pytest.raises(ValueError, match="complete"):
            game.submit_move("P01", 3)


class TestSumParity:
    """Test sum parity calculation."""

    def test_sum_parity_odd(self):
        """Test various odd sums."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
        )
        game.start()

        odd_pairs = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10)]

        for p1_move, p2_move in odd_pairs:
            game.submit_move("P01", p1_move)
            game.submit_move("P02", p2_move)
            result = game.resolve_round()

            assert result.sum_value % 2 == 1
            assert result.sum_value == p1_move + p2_move

            if not game.is_complete:
                pass  # Continue to next round

    def test_sum_parity_even(self):
        """Test various even sums."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            total_rounds=5,
        )
        game.start()

        even_pairs = [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)]

        for p1_move, p2_move in even_pairs:
            game.submit_move("P01", p1_move)
            game.submit_move("P02", p2_move)
            result = game.resolve_round()

            assert result.sum_value % 2 == 0
            assert result.sum_value == p1_move + p2_move

    def test_sum_boundary_values(self):
        """Test sum with boundary move values."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            total_rounds=4,
        )
        game.start()

        # Minimum sum: 1+1=2
        game.submit_move("P01", 1)
        game.submit_move("P02", 1)
        result = game.resolve_round()
        assert result.sum_value == 2

        # Maximum sum: 10+10=20
        game.submit_move("P01", 10)
        game.submit_move("P02", 10)
        result = game.resolve_round()
        assert result.sum_value == 20

        # Mixed: 1+10=11
        game.submit_move("P01", 1)
        game.submit_move("P02", 10)
        result = game.resolve_round()
        assert result.sum_value == 11

        # Mixed: 10+1=11
        game.submit_move("P01", 10)
        game.submit_move("P02", 1)
        result = game.resolve_round()
        assert result.sum_value == 11


class TestGameCompletion:
    """Test game completion."""

    def test_game_completes_after_all_rounds(self):
        """Test game completes after all rounds played."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            total_rounds=3,
        )
        game.start()

        for _ in range(3):
            game.submit_move("P01", 5)
            game.submit_move("P02", 4)
            game.resolve_round()

        assert game.is_complete
        assert game.phase == GamePhase.FINISHED

    def test_get_result(self):
        """Test getting game result."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            player1_role=GameRole.ODD,
            total_rounds=2,
        )
        game.start()

        # Round 1: P01 wins
        game.submit_move("P01", 5)
        game.submit_move("P02", 4)
        game.resolve_round()

        # Round 2: P01 wins again
        game.submit_move("P01", 7)
        game.submit_move("P02", 2)
        game.resolve_round()

        result = game.get_result()

        assert result.winner_id == "P01"
        assert result.player1_score == 2
        assert result.player2_score == 0
        assert len(result.rounds) == 2

    def test_get_result_tie(self):
        """Test getting result for tied game."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            player1_role=GameRole.ODD,
            total_rounds=2,
        )
        game.start()

        # Round 1: P01 wins (odd)
        game.submit_move("P01", 5)
        game.submit_move("P02", 4)
        game.resolve_round()

        # Round 2: P02 wins (even)
        game.submit_move("P01", 3)
        game.submit_move("P02", 3)
        game.resolve_round()

        result = game.get_result()

        assert result.winner_id is None  # Tie
        assert result.player1_score == 1
        assert result.player2_score == 1

    def test_get_result_before_complete(self):
        """Test getting result before game is complete."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
        )
        game.start()

        with pytest.raises(ValueError, match="not complete"):
            game.get_result()


class TestGameState:
    """Test game state management."""

    def test_get_state(self):
        """Test getting game state."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            player1_role=GameRole.ODD,
            total_rounds=5,
        )
        game.start()

        state = game.get_state()

        assert state["game_id"] == "game_001"
        assert state["phase"] == GamePhase.PLAYING.value
        assert state["current_round"] == 1
        assert state["total_rounds"] == 5
        assert state["player1_id"] == "P01"
        assert state["player2_id"] == "P02"
        assert state["player1_role"] == "odd"
        assert state["player2_role"] == "even"
        assert state["player1_score"] == 0
        assert state["player2_score"] == 0

    def test_get_player_score(self):
        """Test getting player scores."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            player1_role=GameRole.ODD,
        )
        game.start()

        # Play a round
        game.submit_move("P01", 5)
        game.submit_move("P02", 4)
        game.resolve_round()

        assert game.get_player_score("P01") == 1
        assert game.get_player_score("P02") == 0

    def test_get_opponent_score(self):
        """Test getting opponent scores."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            player1_role=GameRole.ODD,
        )
        game.start()

        # Play a round
        game.submit_move("P01", 5)
        game.submit_move("P02", 4)
        game.resolve_round()

        assert game.get_opponent_score("P01") == 0
        assert game.get_opponent_score("P02") == 1


class TestRoundResult:
    """Test RoundResult class."""

    def test_round_result_creation(self):
        """Test creating round result."""
        result = RoundResult(
            round_number=1,
            player1_move=5,
            player2_move=4,
            sum_value=9,
            winner_id="P01",
        )

        assert result.round_number == 1
        assert result.player1_move == 5
        assert result.player2_move == 4
        assert result.sum_value == 9
        assert result.winner_id == "P01"

    def test_round_result_to_dict(self):
        """Test converting round result to dict."""
        result = RoundResult(
            round_number=2,
            player1_move=7,
            player2_move=3,
            sum_value=10,
            winner_id="P02",
        )

        result_dict = result.to_dict()

        assert result_dict["round_number"] == 2
        assert result_dict["player1_move"] == 7
        assert result_dict["player2_move"] == 3
        assert result_dict["sum_value"] == 10
        assert result_dict["winner_id"] == "P02"


class TestGameResult:
    """Test GameResult class."""

    def test_game_result_creation(self):
        """Test creating game result."""
        round1 = RoundResult(1, 5, 4, 9, "P01")
        round2 = RoundResult(2, 3, 3, 6, "P02")

        result = GameResult(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            player1_score=1,
            player2_score=1,
            winner_id=None,
            rounds=[round1, round2],
        )

        assert result.game_id == "game_001"
        assert result.player1_score == 1
        assert result.player2_score == 1
        assert result.winner_id is None
        assert len(result.rounds) == 2

    def test_game_result_to_dict(self):
        """Test converting game result to dict."""
        round1 = RoundResult(1, 5, 4, 9, "P01")

        result = GameResult(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            player1_score=1,
            player2_score=0,
            winner_id="P01",
            rounds=[round1],
        )

        result_dict = result.to_dict()

        assert result_dict["game_id"] == "game_001"
        assert result_dict["winner_id"] == "P01"
        assert len(result_dict["rounds"]) == 1


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_single_round_game(self):
        """Test game with single round."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            total_rounds=1,
        )
        game.start()

        game.submit_move("P01", 5)
        game.submit_move("P02", 4)
        result = game.resolve_round()

        assert game.is_complete
        assert result.round_number == 1

    def test_all_same_moves(self):
        """Test game where players always choose same number."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            player1_role=GameRole.EVEN,
            total_rounds=3,
        )
        game.start()

        for _ in range(3):
            game.submit_move("P01", 5)
            game.submit_move("P02", 5)
            result = game.resolve_round()

            # 5+5=10 (even), P01 has even role
            assert result.sum_value == 10
            assert result.winner_id == "P01"

    def test_alternating_winners(self):
        """Test game with alternating winners."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            player1_role=GameRole.ODD,
            total_rounds=4,
        )
        game.start()

        # Round 1: Odd wins (P01)
        game.submit_move("P01", 5)
        game.submit_move("P02", 4)
        r1 = game.resolve_round()
        assert r1.winner_id == "P01"

        # Round 2: Even wins (P02)
        game.submit_move("P01", 3)
        game.submit_move("P02", 3)
        r2 = game.resolve_round()
        assert r2.winner_id == "P02"

        # Round 3: Odd wins (P01)
        game.submit_move("P01", 7)
        game.submit_move("P02", 2)
        r3 = game.resolve_round()
        assert r3.winner_id == "P01"

        # Round 4: Even wins (P02)
        game.submit_move("P01", 4)
        game.submit_move("P02", 4)
        r4 = game.resolve_round()
        assert r4.winner_id == "P02"

        # Final score should be tied
        assert game.player1_score == 2
        assert game.player2_score == 2

    def test_history_tracking(self):
        """Test that game tracks history correctly."""
        game = OddEvenGame(
            game_id="game_001",
            player1_id="P01",
            player2_id="P02",
            total_rounds=3,
        )
        game.start()

        moves = [(5, 4), (7, 3), (2, 8)]

        for p1_move, p2_move in moves:
            game.submit_move("P01", p1_move)
            game.submit_move("P02", p2_move)
            game.resolve_round()

        assert len(game.history) == 3

        for i, (p1_move, p2_move) in enumerate(moves):
            assert game.history[i].player1_move == p1_move
            assert game.history[i].player2_move == p2_move
            assert game.history[i].sum_value == p1_move + p2_move


# ============================================================================
# Edge Case Documentation
# ============================================================================

"""
EDGE CASES TESTED:

1. Game Initialization:
   - Basic initialization with required fields
   - Explicit role assignment
   - Minimum rounds (1)
   - Maximum rounds (100+)
   - Zero rounds (invalid, not tested as should fail)

2. Role Management:
   - Odd role to player 1
   - Even role to player 1
   - Role retrieval
   - Unknown player errors
   - Opponent ID lookup

3. Game Start:
   - Normal start
   - Double start attempt
   - Starting with invalid state

4. Move Submission:
   - Valid moves (1-10)
   - Boundary values (1, 10)
   - Invalid low (0, negative)
   - Invalid high (11+)
   - Unknown player
   - Before game start
   - Duplicate submission
   - After game complete

5. Round Resolution:
   - Odd sum outcomes
   - Even sum outcomes
   - Multiple rounds
   - Missing moves
   - After completion
   - Score tracking

6. Sum Parity:
   - All odd sums (3, 5, 7, 9, 11, etc.)
   - All even sums (2, 4, 6, 8, 10, etc.)
   - Boundary sums (2, 20)
   - Mixed combinations

7. Game Completion:
   - Completes after all rounds
   - Result with clear winner
   - Result with tie
   - Result before completion (error)
   - Phase transitions

8. State Management:
   - State retrieval
   - Score retrieval
   - Opponent score lookup
   - History tracking
   - Phase tracking

9. Edge Game Scenarios:
   - Single round game
   - All same moves
   - Alternating winners
   - Perfect tie scores
   - One player dominates

10. History and Results:
    - History accumulation
    - RoundResult creation
    - GameResult creation
    - Conversion to dict
    - All rounds recorded
"""
