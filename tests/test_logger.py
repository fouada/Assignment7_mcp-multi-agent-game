"""
Tests for logging system.
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from src.common.logger import (
    AgentEventLogger,
    JSONLWriter,
    LeagueEventLogger,
    PerformanceTracker,
    get_logger,
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

        with open(log_file) as f:
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

        with open(log_file) as f:
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

        with open(log_file) as f:
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
        with open(log_file) as f:
            entry = json.loads(f.readline())

        assert entry["event_type"] == "PLAYER_REGISTERED"
        assert entry["player_id"] == "P01"

    def test_round_started(self):
        """Test logging round start."""
        self.logger.round_started(round_id=1, match_count=2)

        log_file = self.temp_dir / "league" / "test_league" / "events.log.jsonl"
        with open(log_file) as f:
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
        with open(log_file) as f:
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
        with open(log_file) as f:
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
        with open(log_file) as f:
            entry = json.loads(f.readline())

        assert entry["event_type"] == "AGENT_STARTED"
        assert entry["agent_id"] == "P01"

    def test_message_sent(self):
        """Test logging sent message."""
        self.logger.message_sent("MOVE_RESPONSE", "referee")

        log_file = self.temp_dir / "agents" / "P01.log.jsonl"
        with open(log_file) as f:
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


class TestGameLoggerAdvanced:
    """Advanced tests for GameLogger."""

    def test_logger_warning_level(self):
        """Test warning level logging."""
        logger = get_logger("test_warning")
        logger.bind(test_id="warn_test")
        logger.warning("Warning message", severity="high")
        # Should not raise

    def test_logger_error_level(self):
        """Test error level logging."""
        logger = get_logger("test_error")
        logger.bind(test_id="error_test")
        logger.error("Error message", code="E001")
        # Should not raise

    def test_logger_critical_level(self):
        """Test critical level logging."""
        logger = get_logger("test_critical")
        logger.bind(test_id="critical_test")
        logger.critical("Critical message", system="core")
        # Should not raise

    def test_logger_with_multiple_extra_args(self):
        """Test logging with multiple extra arguments."""
        logger = get_logger("test_multi_extra")
        logger.info("Multi-arg message", arg1="val1", arg2="val2", arg3="val3")
        # Should not raise

    def test_logger_unbind_nonexistent_key(self):
        """Test unbinding a key that doesn't exist."""
        logger = get_logger("test_unbind_none")
        logger.bind(key1="value1")
        logger.unbind("nonexistent_key")  # Should not raise
        assert "key1" in logger._context


class TestJSONFormatterAdvanced:
    """Advanced tests for JSONFormatter."""

    def test_formatter_with_none_exc_info(self):
        """Test formatter when exc_info is explicitly None."""
        from src.common.logger import JSONFormatter
        import logging

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py",
            lineno=1, msg="Test", args=(), exc_info=None
        )

        formatted = formatter.format(record)
        assert formatted  # Should not crash


class TestColorFormatterAdvanced:
    """Advanced tests for ColorFormatter."""

    def test_color_formatter_debug_level(self):
        """Test color formatter for DEBUG level."""
        from src.common.logger import ColorFormatter
        import logging

        formatter = ColorFormatter()
        record = logging.LogRecord(
            name="test", level=logging.DEBUG, pathname="test.py",
            lineno=1, msg="Debug msg", args=(), exc_info=None
        )

        formatted = formatter.format(record)
        assert "Debug msg" in formatted

    def test_color_formatter_without_extra_data(self):
        """Test color formatter without extra_data attribute."""
        from src.common.logger import ColorFormatter
        import logging

        formatter = ColorFormatter()
        record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname="test.py",
            lineno=1, msg="Warning", args=(), exc_info=None
        )
        # Don't add extra_data attribute

        formatted = formatter.format(record)
        assert "Warning" in formatted


class TestAgentEventLoggerAdvanced:
    """Advanced agent event logger tests."""

    def setup_method(self):
        """Setup temp directory."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.logger = AgentEventLogger("P001", "player", str(self.temp_dir))

    def teardown_method(self):
        """Cleanup."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_agent_logger_multiple_message_types(self):
        """Test logging multiple message types."""
        self.logger.message_sent("MOVE_REQUEST", "referee")
        self.logger.message_sent("HEARTBEAT", "server")
        self.logger.message_sent("STATUS_UPDATE", "league_manager")

        log_file = self.temp_dir / "agents" / "P001.log.jsonl"
        with open(log_file) as f:
            lines = f.readlines()

        assert len(lines) == 3


class TestLeagueEventLoggerAdvanced:
    """Advanced league event logger tests."""

    def setup_method(self):
        """Setup temp directory."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.logger = LeagueEventLogger("adv_league", str(self.temp_dir))

    def teardown_method(self):
        """Cleanup."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_league_logger_match_complete(self):
        """Test logging match completion."""
        self.logger.match_started("M001", "P01", "P02", "REF01")

        log_file = self.temp_dir / "league" / "adv_league" / "matches" / "M001.log.jsonl"
        assert log_file.exists()

    def test_league_logger_multiple_rounds(self):
        """Test logging multiple rounds."""
        for round_id in range(1, 6):
            self.logger.round_started(round_id, match_count=3)

        log_file = self.temp_dir / "league" / "adv_league" / "events.log.jsonl"
        with open(log_file) as f:
            lines = f.readlines()

        assert len(lines) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
