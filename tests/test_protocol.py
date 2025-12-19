"""
Tests for protocol messages.
"""

import pytest
from src.common.protocol import (
    PROTOCOL_VERSION,
    MessageType,
    MessageFactory,
    validate_message,
    create_message,
)


class TestProtocol:
    """Test protocol validation and message creation."""
    
    def test_protocol_version(self):
        """Test protocol version constant."""
        assert PROTOCOL_VERSION == "league.v2"
    
    def test_validate_valid_message(self):
        """Test validation of valid message."""
        message = {
            "protocol": "league.v2",
            "message_type": "GAME_START",
            "league_id": "test_league",
            "conversation_id": "123",
            "sender": "referee",
            "timestamp": "2024-12-12T10:00:00Z",
        }
        
        is_valid, error = validate_message(message)
        assert is_valid is True
        assert error is None
    
    def test_validate_invalid_protocol(self):
        """Test validation with wrong protocol version."""
        message = {
            "protocol": "league.v1",  # Old version should be invalid
            "message_type": "GAME_START",
            "league_id": "test_league",
            "conversation_id": "123",
            "sender": "referee",
            "timestamp": "2024-12-12T10:00:00Z",
        }
        
        is_valid, error = validate_message(message)
        assert is_valid is False
        assert "league.v2" in error  # Should mention expected version
    
    def test_validate_missing_field(self):
        """Test validation with missing required field."""
        message = {
            "protocol": "league.v2",
            "message_type": "GAME_START",
            # Missing league_id, conversation_id, sender, timestamp
        }
        
        is_valid, error = validate_message(message)
        assert is_valid is False
    
    def test_validate_invalid_message_type(self):
        """Test validation with invalid message type."""
        message = {
            "protocol": "league.v2",
            "message_type": "INVALID_TYPE",
            "league_id": "test_league",
            "conversation_id": "123",
            "sender": "referee",
            "timestamp": "2024-12-12T10:00:00Z",
        }
        
        is_valid, error = validate_message(message)
        assert is_valid is False
        assert "message type" in error.lower()


class TestMessageFactory:
    """Test message factory."""
    
    def setup_method(self):
        """Setup for each test."""
        self.factory = MessageFactory(
            sender="test_sender",
            league_id="test_league",
        )
    
    def test_register_request(self):
        """Test registration request creation."""
        msg = self.factory.register_request(
            display_name="Test Player",
            version="1.0.0",
            endpoint="http://localhost:8101/mcp",
        )
        
        assert msg["protocol"] == PROTOCOL_VERSION
        assert msg["message_type"] == "LEAGUE_REGISTER_REQUEST"
        assert msg["sender"] == "test_sender"
        assert msg["player_meta"]["display_name"] == "Test Player"
        assert "even_odd" in msg["player_meta"]["game_types"]
    
    def test_register_response(self):
        """Test registration response creation."""
        msg = self.factory.register_response(
            status="ACCEPTED",
            player_id="P01",
        )
        
        assert msg["message_type"] == "LEAGUE_REGISTER_RESPONSE"
        assert msg["status"] == "ACCEPTED"
        assert msg["player_id"] == "P01"
    
    def test_game_invite(self):
        """Test game invitation creation."""
        msg = self.factory.game_invite(
            game_id="game_123",
            opponent_id="P02",
            role="odd",
            rounds=5,
        )
        
        assert msg["message_type"] == "GAME_INVITE"
        assert msg["game_id"] == "game_123"
        assert msg["opponent_id"] == "P02"
        assert msg["assigned_role"] == "odd"
        assert msg["rounds_to_play"] == 5
    
    def test_move_request(self):
        """Test move request creation."""
        msg = self.factory.move_request(
            game_id="game_123",
            round_number=3,
            role="even",
            current_score={"P01": 1, "P02": 2},
        )
        
        assert msg["message_type"] == "MOVE_REQUEST"
        assert msg["game_id"] == "game_123"
        assert msg["round_number"] == 3
        assert msg["your_role"] == "even"
    
    def test_move_response(self):
        """Test move response creation."""
        msg = self.factory.move_response(
            game_id="game_123",
            round_number=3,
            move=4,
        )
        
        assert msg["message_type"] == "MOVE_RESPONSE"
        assert msg["move"] == 4
    
    def test_move_result(self):
        """Test move result creation."""
        msg = self.factory.move_result(
            game_id="game_123",
            round_number=3,
            your_move=2,
            opponent_move=3,
            winner_id="P01",
            your_score=2,
            opponent_score=1,
        )
        
        assert msg["message_type"] == "MOVE_RESULT"
        assert msg["sum_value"] == 5
        assert msg["sum_is_odd"] is True
        assert msg["round_winner_id"] == "P01"
    
    def test_game_end(self):
        """Test game end creation."""
        msg = self.factory.game_end(
            game_id="game_123",
            winner_id="P01",
            final_score={"P01": 3, "P02": 2},
        )
        
        assert msg["message_type"] == "GAME_END"
        assert msg["winner_id"] == "P01"
        assert msg["final_score"]["P01"] == 3
    
    def test_heartbeat(self):
        """Test heartbeat creation."""
        msg = self.factory.heartbeat()
        
        assert msg["message_type"] == "HEARTBEAT"
    
    def test_error_message(self):
        """Test error message creation."""
        msg = self.factory.error(
            error_code="INVALID_MOVE",
            error_message="Move out of range",
            recoverable=True,
        )
        
        assert msg["message_type"] == "ERROR"
        assert msg["error_code"] == "INVALID_MOVE"
        assert msg["recoverable"] is True
    
    def test_game_invite_response(self):
        """Test game invite response creation."""
        msg = self.factory.game_invite_response(
            game_id="game_123",
            accepted=True,
        )
        
        assert msg["message_type"] == "GAME_INVITE_RESPONSE"
        assert msg["game_id"] == "game_123"
        assert msg["accepted"] is True
    
    def test_game_invite_response_declined(self):
        """Test game invite response declined."""
        msg = self.factory.game_invite_response(
            game_id="game_123",
            accepted=False,
            reason="Player busy",
        )
        
        assert msg["message_type"] == "GAME_INVITE_RESPONSE"
        assert msg["accepted"] is False
        assert msg["reason"] == "Player busy"
    
    def test_match_result(self):
        """Test match result creation (legacy format)."""
        msg = self.factory.match_result(
            match_id="R1M1",
            winner_id="P01",
            player_A_id="P01",
            player_A_score=3,
            player_B_id="P02",
            player_B_score=2,
            rounds_played=5,
        )
        
        assert msg["message_type"] == "MATCH_RESULT_REPORT"
        assert msg["match_id"] == "R1M1"
        assert msg["winner_id"] == "P01"
        assert msg["player_A_score"] == 3
        assert msg["player_B_score"] == 2
    
    def test_game_over(self):
        """Test GAME_OVER message creation."""
        msg = self.factory.game_over(
            match_id="R1M1",
            game_type="even_odd",
            status="WIN",
            winner_player_id="P01",
            drawn_number=8,
            number_parity="even",
            choices={"P01": "even", "P02": "odd"},
            reason="P01 chose even, number was 8 (even)",
        )
        
        assert msg["message_type"] == "GAME_OVER"
        assert msg["match_id"] == "R1M1"
        assert msg["game_type"] == "even_odd"
        assert msg["game_result"]["status"] == "WIN"
        assert msg["game_result"]["winner_player_id"] == "P01"
        assert msg["game_result"]["drawn_number"] == 8
        assert msg["game_result"]["number_parity"] == "even"
        assert msg["game_result"]["choices"]["P01"] == "even"
    
    def test_match_result_report(self):
        """Test MATCH_RESULT_REPORT message creation."""
        msg = self.factory.match_result_report(
            league_id="league_2025_even_odd",
            round_id=1,
            match_id="R1M1",
            game_type="even_odd",
            winner_id="P01",
            score={"P01": 3, "P02": 0},
            details={"drawn_number": 8, "choices": {"P01": "even", "P02": "odd"}},
        )
        
        assert msg["message_type"] == "MATCH_RESULT_REPORT"
        assert msg["league_id"] == "league_2025_even_odd"
        assert msg["round_id"] == 1
        assert msg["match_id"] == "R1M1"
        assert msg["game_type"] == "even_odd"
        assert msg["result"]["winner"] == "P01"
        assert msg["result"]["score"]["P01"] == 3
        assert msg["result"]["details"]["drawn_number"] == 8
    
    def test_round_announcement(self):
        """Test round announcement creation."""
        matches = [
            {
                "match_id": "R1M1",
                "game_type": "even_odd",
                "player_A_id": "P01",
                "player_B_id": "P02",
                "referee_endpoint": "http://localhost:8001/mcp",
            }
        ]
        msg = self.factory.round_announcement(
            round_id=1,
            matches=matches,
        )
        
        assert msg["message_type"] == "ROUND_ANNOUNCEMENT"
        assert msg["round_id"] == 1
        assert len(msg["matches"]) == 1
        assert msg["matches"][0]["game_type"] == "even_odd"
    
    def test_standings_update(self):
        """Test standings update creation."""
        standings = [
            {
                "rank": 1,
                "player_id": "P01",
                "display_name": "Player 1",
                "played": 2,
                "wins": 2,
                "draws": 0,
                "losses": 0,
                "points": 6,
            }
        ]
        msg = self.factory.standings_update(
            round_id=1,
            standings=standings,
        )
        
        assert msg["message_type"] == "LEAGUE_STANDINGS_UPDATE"
        assert msg["round_id"] == 1
        assert len(msg["standings"]) == 1
        assert msg["standings"][0]["played"] == 2
    
    def test_league_query(self):
        """Test league query message creation."""
        msg = self.factory.league_query(
            league_id="league_2025_even_odd",
            query_type="GET_STANDINGS",
            conversation_id="conv-001",
            auth_token="tok-xyz",
        )
        
        assert msg["message_type"] == "LEAGUE_QUERY"
        assert msg["league_id"] == "league_2025_even_odd"
        assert msg["query_type"] == "GET_STANDINGS"
        assert msg["conversation_id"] == "conv-001"
        assert msg["auth_token"] == "tok-xyz"
    
    def test_league_query_minimal(self):
        """Test league query with minimal params."""
        msg = self.factory.league_query(
            league_id="league_2025",
            query_type="GET_SCHEDULE",
        )
        
        assert msg["message_type"] == "LEAGUE_QUERY"
        assert msg["league_id"] == "league_2025"
        assert msg["query_type"] == "GET_SCHEDULE"
        # conversation_id is generated by _base_fields
        assert "conversation_id" in msg
        assert "auth_token" not in msg
    
    def test_league_error(self):
        """Test league error message creation."""
        msg = self.factory.league_error(
            error_code="E007",
            error_name="ALREADY_REGISTERED",
            error_description="Player already registered",
            retryable=False,
        )
        
        assert msg["message_type"] == "LEAGUE_ERROR"
        assert msg["error_code"] == "E007"
        assert msg["error_name"] == "ALREADY_REGISTERED"
        assert msg["retryable"] is False
    
    def test_game_error(self):
        """Test game error message creation."""
        msg = self.factory.game_error(
            error_code="E001",
            error_description="TIMEOUT_ERROR",
            match_id="R1M1",
            affected_player="P02",
            action_required="CHOOSE_PARITY_RESPONSE",
            retry_count=0,
            max_retries=3,
            consequence="Technical loss if no response after retries",
        )
        
        assert msg["message_type"] == "GAME_ERROR"
        assert msg["error_code"] == "E001"
        assert msg["error_description"] == "TIMEOUT_ERROR"
        assert msg["match_id"] == "R1M1"
        assert msg["affected_player"] == "P02"
        assert msg["action_required"] == "CHOOSE_PARITY_RESPONSE"
        assert msg["retry_count"] == 0
        assert msg["max_retries"] == 3
    
    def test_round_start(self):
        """Test round start message creation."""
        matches = [
            {"match_id": "R1M1", "player_A_id": "P01", "player_B_id": "P02"},
        ]
        msg = self.factory.round_start(
            round_id=1,
            total_rounds=3,
            matches=matches,
        )
        
        assert msg["message_type"] == "ROUND_START"
        assert msg["round_id"] == 1
        assert msg["total_rounds"] == 3
        assert len(msg["matches"]) == 1
    
    def test_round_end(self):
        """Test round end message creation."""
        results = [
            {"match_id": "R1M1", "winner_id": "P01", "player_A_score": 3, "player_B_score": 2},
        ]
        msg = self.factory.round_end(
            round_id=1,
            results=results,
            next_round_id=2,
        )
        
        assert msg["message_type"] == "ROUND_END"
        assert msg["round_id"] == 1
        assert len(msg["results"]) == 1
        assert msg["next_round_id"] == 2
    
    def test_round_result(self):
        """Test round result message creation."""
        results = [
            {"match_id": "R1M1", "winner_id": "P01"},
            {"match_id": "R1M2", "winner_id": "P04"},
        ]
        msg = self.factory.round_result(
            round_id=1,
            match_results=results,
        )
        
        assert msg["message_type"] == "ROUND_RESULT"
        assert msg["round_id"] == 1
        assert len(msg["results"]) == 2


class TestCreateMessage:
    """Test create_message helper function."""
    
    def test_create_message(self):
        """Test basic message creation."""
        msg = create_message(
            message_type=MessageType.GAME_START,
            sender="referee",
            league_id="test_league",
            game_id="game_123",
        )
        
        assert msg["protocol"] == PROTOCOL_VERSION
        assert msg["message_type"] == "GAME_START"
        assert msg["sender"] == "referee"
        assert msg["game_id"] == "game_123"
        assert "conversation_id" in msg
        assert "timestamp" in msg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

