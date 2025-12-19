"""
Tests for logging system (Section 7).
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path

from src.common.logger import (
    JSONLWriter,
    LeagueEventLogger,
    AgentEventLogger,
    get_logger,
    PerformanceTracker,
)


class TestJSONLWriter:
    """Test JSONL file writer."""
    
    def setup_method(self):
        """Setup temp directory."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.writer = JSONLWriter(str(self.temp_dir))
    
    def teardown_method(self):
        """Cleanup."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_creates_directory_structure(self):
        """Test directory creation."""
        assert (self.temp_dir / "league").exists()
        assert (self.temp_dir / "agents").exists()
        assert (self.temp_dir / "system").exists()
    
    def test_log_league_event(self):
        """Test logging league events."""
        self.writer.log_league_event(
            league_id="test_league",
            event_type="TEST_EVENT",
            data={"key": "value"},
        )
        
        log_file = self.temp_dir / "league" / "test_league" / "events.log.jsonl"
        assert log_file.exists()
        
        with open(log_file, 'r') as f:
            entry = json.loads(f.readline())
        
        assert entry["league_id"] == "test_league"
        assert entry["event_type"] == "TEST_EVENT"
        assert entry["key"] == "value"
        assert "timestamp" in entry
    
    def test_log_agent_event(self):
        """Test logging agent events."""
        self.writer.log_agent_event(
            agent_id="P01",
            agent_type="player",
            event_type="MESSAGE_SENT",
            data={"recipient": "referee"},
        )
        
        log_file = self.temp_dir / "agents" / "P01.log.jsonl"
        assert log_file.exists()
        
        with open(log_file, 'r') as f:
            entry = json.loads(f.readline())
        
        assert entry["agent_id"] == "P01"
        assert entry["agent_type"] == "player"
        assert entry["event_type"] == "MESSAGE_SENT"
    
    def test_log_system_event(self):
        """Test logging system events."""
        self.writer.log_system_event(
            event_type="STARTUP",
            data={"version": "1.0.0"},
        )
        
        log_file = self.temp_dir / "system" / "system.log.jsonl"
        assert log_file.exists()
    
    def test_log_match_event(self):
        """Test logging match events."""
        self.writer.log_match_event(
            league_id="test_league",
            match_id="R1M1",
            event_type="MOVE_SUBMITTED",
            data={"player_id": "P01", "move": 3},
        )
        
        log_file = self.temp_dir / "league" / "test_league" / "matches" / "R1M1.log.jsonl"
        assert log_file.exists()
    
    def test_multiple_events_append(self):
        """Test that multiple events append to the same file."""
        for i in range(3):
            self.writer.log_system_event(
                event_type=f"EVENT_{i}",
                data={"index": i},
            )
        
        log_file = self.temp_dir / "system" / "system.log.jsonl"
        
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) == 3
    
    def test_read_events(self):
        """Test reading events from JSONL file."""
        for i in range(5):
            self.writer.log_system_event(
                event_type=f"EVENT_{i}",
                data={"index": i},
            )
        
        log_file = self.temp_dir / "system" / "system.log.jsonl"
        events = self.writer.read_events(log_file)
        
        assert len(events) == 5
        assert events[0]["event_type"] == "EVENT_0"
    
    def test_read_events_with_limit(self):
        """Test reading events with limit."""
        for i in range(5):
            self.writer.log_system_event(
                event_type="TEST",
                data={"index": i},
            )
        
        log_file = self.temp_dir / "system" / "system.log.jsonl"
        events = self.writer.read_events(log_file, limit=3)
        
        assert len(events) == 3
    
    def test_read_events_with_filter(self):
        """Test reading events filtered by type."""
        self.writer.log_system_event("TYPE_A", {"data": 1})
        self.writer.log_system_event("TYPE_B", {"data": 2})
        self.writer.log_system_event("TYPE_A", {"data": 3})
        
        log_file = self.temp_dir / "system" / "system.log.jsonl"
        events = self.writer.read_events(log_file, event_type="TYPE_A")
        
        assert len(events) == 2


class TestLeagueEventLogger:
    """Test league event logger."""
    
    def setup_method(self):
        """Setup temp directory."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.logger = LeagueEventLogger("test_league", str(self.temp_dir))
    
    def teardown_method(self):
        """Cleanup."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_player_registered(self):
        """Test logging player registration."""
        self.logger.player_registered(
            player_id="P01",
            display_name="Alice",
            endpoint="http://localhost:8101/mcp",
        )
        
        log_file = self.temp_dir / "league" / "test_league" / "events.log.jsonl"
        with open(log_file, 'r') as f:
            entry = json.loads(f.readline())
        
        assert entry["event_type"] == "PLAYER_REGISTERED"
        assert entry["player_id"] == "P01"
    
    def test_round_started(self):
        """Test logging round start."""
        self.logger.round_started(round_id=1, match_count=2)
        
        log_file = self.temp_dir / "league" / "test_league" / "events.log.jsonl"
        with open(log_file, 'r') as f:
            entry = json.loads(f.readline())
        
        assert entry["event_type"] == "ROUND_STARTED"
        assert entry["round_id"] == 1
    
    def test_match_started(self):
        """Test logging match start."""
        self.logger.match_started(
            match_id="R1M1",
            player_A_id="P01",
            player_B_id="P02",
            referee_id="REF01",
        )
        
        log_file = self.temp_dir / "league" / "test_league" / "matches" / "R1M1.log.jsonl"
        assert log_file.exists()
    
    def test_move_submitted(self):
        """Test logging move submission."""
        self.logger.move_submitted(
            match_id="R1M1",
            player_id="P01",
            round_number=1,
            move_value=3,
        )
        
        log_file = self.temp_dir / "league" / "test_league" / "matches" / "R1M1.log.jsonl"
        with open(log_file, 'r') as f:
            entry = json.loads(f.readline())
        
        assert entry["event_type"] == "MOVE_SUBMITTED"
        assert entry["move_value"] == 3
    
    def test_round_result(self):
        """Test logging round result."""
        self.logger.round_result(
            match_id="R1M1",
            round_number=1,
            player_A_move=2,
            player_B_move=3,
            sum_value=5,
            winner_id="P01",
        )
        
        log_file = self.temp_dir / "league" / "test_league" / "matches" / "R1M1.log.jsonl"
        with open(log_file, 'r') as f:
            entry = json.loads(f.readline())
        
        assert entry["is_odd"] is True
        assert entry["winner_id"] == "P01"
    
    def test_error_occurred(self):
        """Test logging errors."""
        self.logger.error_occurred(
            error_code="E010",
            error_message="Invalid move",
            context={"player_id": "P01"},
        )
        
        log_file = self.temp_dir / "league" / "test_league" / "errors.log.jsonl"
        assert log_file.exists()


class TestAgentEventLogger:
    """Test agent event logger."""
    
    def setup_method(self):
        """Setup temp directory."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.logger = AgentEventLogger("P01", "player", str(self.temp_dir))
    
    def teardown_method(self):
        """Cleanup."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_started(self):
        """Test logging agent start."""
        self.logger.started()
        
        log_file = self.temp_dir / "agents" / "P01.log.jsonl"
        with open(log_file, 'r') as f:
            entry = json.loads(f.readline())
        
        assert entry["event_type"] == "AGENT_STARTED"
        assert entry["agent_id"] == "P01"
    
    def test_message_sent(self):
        """Test logging sent message."""
        self.logger.message_sent("MOVE_RESPONSE", "referee")
        
        log_file = self.temp_dir / "agents" / "P01.log.jsonl"
        with open(log_file, 'r') as f:
            entry = json.loads(f.readline())
        
        assert entry["event_type"] == "MESSAGE_SENT"
        assert entry["message_type"] == "MOVE_RESPONSE"


class TestPerformanceTracker:
    """Test performance tracker."""
    
    def test_tracks_duration(self):
        """Test duration tracking."""
        logger = get_logger("test")
        
        with PerformanceTracker("test_operation", logger) as tracker:
            import time
            time.sleep(0.01)  # 10ms
        
        assert tracker.duration_ms is not None
        assert tracker.duration_ms >= 10  # At least 10ms
    
    def test_logs_completion(self):
        """Test that completion is logged."""
        logger = get_logger("test")
        
        with PerformanceTracker("test_op", logger):
            pass
        
        # No exception means success


class TestGameLogger:
    """Test enhanced game logger."""
    
    def test_bind_context(self):
        """Test binding context to logger."""
        logger = get_logger("test_context")
        
        logger.bind(game_id="game_123", player_id="P01")
        logger.info("Test message")  # Should include context
        
        # Unbind
        logger.unbind("game_id")
        
        # No exception means success
    
    def test_log_with_extra(self):
        """Test logging with extra data."""
        logger = get_logger("test_extra")
        
        logger.info("Test message", move=3, round=1)
        
        # No exception means success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

