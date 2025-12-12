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
        assert PROTOCOL_VERSION == "league.v1"
    
    def test_validate_valid_message(self):
        """Test validation of valid message."""
        message = {
            "protocol": "league.v1",
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
            "protocol": "league.v2",
            "message_type": "GAME_START",
            "league_id": "test_league",
            "conversation_id": "123",
            "sender": "referee",
            "timestamp": "2024-12-12T10:00:00Z",
        }
        
        is_valid, error = validate_message(message)
        assert is_valid is False
        assert "league.v1" in error
    
    def test_validate_missing_field(self):
        """Test validation with missing required field."""
        message = {
            "protocol": "league.v1",
            "message_type": "GAME_START",
            # Missing league_id, conversation_id, sender, timestamp
        }
        
        is_valid, error = validate_message(message)
        assert is_valid is False
    
    def test_validate_invalid_message_type(self):
        """Test validation with invalid message type."""
        message = {
            "protocol": "league.v1",
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

