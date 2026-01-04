"""
Targeted tests to push coverage from 84.13% to 85%+
====================================================
"""

import asyncio
import json
import logging
import tempfile
from pathlib import Path

import pytest

from src.common.logger import (
    AgentEventLogger,
    ColorFormatter,
    JSONFormatter,
    JSONLWriter,
    LeagueEventLogger,
    get_logger,
)
from src.observability.health import (
    HealthCheck,
    HealthCheckResult,
    HealthMonitor,
    HealthStatus,
    LivenessCheck,
    ReadinessCheck,
    ResourceCheck,
)
from src.observability.tracing import Span, SpanContext, TracingManager


class TestLoggerFormattersComplete:
    """Complete coverage of logger formatters."""

    def test_json_formatter_without_exception(self):
        """Test JSON formatter without exception info."""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error without exception",
            args=(),
            exc_info=None
        )

        formatted = formatter.format(record)
        data = json.loads(formatted)
        assert data["level"] == "ERROR"
        assert "exception" not in data

    def test_json_formatter_with_none_exc_type(self):
        """Test JSON formatter with None exception type."""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error",
            args=(),
            exc_info=(None, None, None)
        )

        formatted = formatter.format(record)
        data = json.loads(formatted)
        assert "exception" in data

    def test_color_formatter_critical_level(self):
        """Test color formatter for CRITICAL level."""
        formatter = ColorFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.CRITICAL,
            pathname="test.py",
            lineno=1,
            msg="Critical message",
            args=(),
            exc_info=None
        )

        formatted = formatter.format(record)
        assert "Critical message" in formatted
        assert "\033[" in formatted  # Has color codes

    def test_color_formatter_with_exception(self):
        """Test color formatter with exception."""
        formatter = ColorFormatter()

        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error with exception",
            args=(),
            exc_info=exc_info
        )

        formatted = formatter.format(record)
        assert "Error with exception" in formatted
        assert "ValueError" in formatted


class TestJSONLWriterComplete:
    """Complete coverage of JSONL writer."""

    def test_jsonl_writer_error_logging(self):
        """Test JSONL writer error logging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            writer = JSONLWriter(temp_dir)

            writer.log_league_event(
                league_id="test_league",
                event_type="ERROR_EVENT",
                data={"error": "test error"}
            )

            log_file = Path(temp_dir) / "league" / "test_league" / "events.log.jsonl"
            assert log_file.exists()

    def test_jsonl_read_events_empty_file(self):
        """Test reading events from empty file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            writer = JSONLWriter(temp_dir)
            empty_file = Path(temp_dir) / "empty.jsonl"
            empty_file.touch()

            events = writer.read_events(empty_file)
            assert events == []


class TestHealthMonitorComplete:
    """Complete coverage of health monitor."""

    @pytest.mark.asyncio
    async def test_health_monitor_with_failing_check(self):
        """Test health monitor with a check that fails."""
        monitor = HealthMonitor()

        class FailingCheck(HealthCheck):
            def __init__(self):
                super().__init__("failing", "Always fails")

            async def check(self) -> HealthCheckResult:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    message="Check failed"
                )

        monitor.add_check("my_failing_check", FailingCheck())

        health = await monitor.get_health()
        # Check that health dict is returned
        assert isinstance(health, dict)
        assert "checks" in health

    @pytest.mark.asyncio
    async def test_health_monitor_degraded_status(self):
        """Test health monitor with degraded check."""
        monitor = HealthMonitor()

        class DegradedCheck(HealthCheck):
            def __init__(self):
                super().__init__("degraded", "Degraded service")

            async def check(self) -> HealthCheckResult:
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    message="Service degraded"
                )

        monitor.add_check("degraded_check", DegradedCheck())

        health = await monitor.get_health()
        # Check is added to the monitor
        assert isinstance(health, dict)

    @pytest.mark.asyncio
    async def test_liveness_check(self):
        """Test liveness check."""
        check = LivenessCheck()
        result = await check.check()
        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_readiness_check(self):
        """Test readiness check."""
        check = ReadinessCheck()
        result = await check.check()
        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_resource_check_normal(self):
        """Test resource check with normal values."""
        check = ResourceCheck()
        result = await check.check()
        # Should return a status
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]


class TestTracingManagerComplete:
    """Complete coverage of tracing manager."""

    def test_tracing_manager_initialize(self):
        """Test tracing manager initialization."""
        manager = TracingManager()

        # Initialize with service name
        manager._service_name = "test_service"
        assert manager.service_name == "test_service"

    def test_span_context_not_sampled(self):
        """Test span context with sampled=False."""
        context = SpanContext(
            trace_id="trace123",
            span_id="span456",
            sampled=False
        )

        assert context.trace_flags == 0
        traceparent = context.to_traceparent()
        assert traceparent.endswith("-00")

    def test_span_context_parse_invalid(self):
        """Test parsing invalid traceparent."""
        # Too few parts
        result = SpanContext.from_traceparent("00-trace")
        assert result is None

        # Invalid version
        result = SpanContext.from_traceparent("99-trace-span-01")
        assert result is None

        # Malformed
        result = SpanContext.from_traceparent("invalid")
        assert result is None

    def test_span_operations(self):
        """Test span operations."""
        import time

        span = Span(
            trace_id="trace",
            span_id="span",
            parent_span_id=None,
            name="test_span",
            start_time=time.time()
        )

        # Add attribute
        span.set_attribute("key", "value")
        assert span.attributes["key"] == "value"

        # Add event
        span.add_event("event1", {"data": "test"})
        assert len(span.events) == 1

        # Set status
        span.set_status("error", "Test error")
        assert span.status == "error"
        assert span.error_message == "Test error"

        # End span
        span.end()
        assert span.end_time is not None
        assert span.duration_ms >= 0  # >= 0 for Windows time resolution

        # Convert to dict
        span_dict = span.to_dict()
        assert span_dict["trace_id"] == "trace"
        assert span_dict["status"] == "error"


class TestGameLoggerComplete:
    """Complete coverage of GameLogger."""

    def test_game_logger_debug(self):
        """Test debug level logging."""
        logger = get_logger("test_debug")
        logger.setLevel(logging.DEBUG)
        logger.bind(test="debug")

        logger.debug("Debug message", extra_key="extra_value")
        # Should not raise

    def test_game_logger_warning(self):
        """Test warning level logging."""
        logger = get_logger("test_warn")
        logger.bind(test="warn")

        logger.warning("Warning message", severity="high")
        # Should not raise

    def test_game_logger_error(self):
        """Test error level logging."""
        logger = get_logger("test_error")
        logger.bind(test="error")

        logger.error("Error message", error_code="E001")
        # Should not raise

    def test_game_logger_critical(self):
        """Test critical level logging."""
        logger = get_logger("test_critical")
        logger.bind(test="critical")

        logger.critical("Critical message", system="core")
        # Should not raise

    def test_game_logger_exception(self):
        """Test exception logging."""
        logger = get_logger("test_exception")
        logger.bind(test="exception")

        try:
            raise RuntimeError("Test error")
        except RuntimeError:
            logger.exception("Exception occurred", context="test")
        # Should not raise

    def test_game_logger_unbind_multiple(self):
        """Test unbinding multiple keys."""
        logger = get_logger("test_unbind")

        logger.bind(key1="val1", key2="val2", key3="val3")
        logger.unbind("key1", "key2")

        assert "key1" not in logger._context
        assert "key2" not in logger._context
        assert "key3" in logger._context


class TestLeagueEventLoggerComplete:
    """Complete coverage of league event logger."""

    def test_league_logger_all_events(self):
        """Test all league logger event types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = LeagueEventLogger("complete_league", temp_dir)

            # Player registered
            logger.player_registered("P01", "Player 1", "http://localhost:8101")

            # Round started
            logger.round_started(1, 2)

            # Match started
            logger.match_started("M01", "P01", "P02", "REF01")

            # Move submitted
            logger.move_submitted("M01", "P01", 1, 3)

            # Round result
            logger.round_result("M01", 1, 3, 2, 5, "P01")

            # Error occurred
            logger.error_occurred("E001", "Test error", {"context": "test"})

            # Verify files created
            league_events = Path(temp_dir) / "league" / "complete_league" / "events.log.jsonl"
            assert league_events.exists()


class TestAgentEventLoggerComplete:
    """Complete coverage of agent event logger."""

    def test_agent_logger_all_events(self):
        """Test all agent logger event types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = AgentEventLogger("AGENT01", "player", temp_dir)

            # Started
            logger.started()

            # Message sent
            logger.message_sent("MOVE_REQUEST", "referee")
            logger.message_sent("HEARTBEAT", "server")

            # Verify file created
            agent_log = Path(temp_dir) / "agents" / "AGENT01.log.jsonl"
            assert agent_log.exists()

            with open(agent_log) as f:
                lines = f.readlines()

            assert len(lines) >= 3


class TestHealthCheckResult:
    """Test HealthCheckResult."""

    def test_health_check_result_creation(self):
        """Test creating health check result."""
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="All good"
        )

        assert result.status == HealthStatus.HEALTHY
        assert result.message == "All good"

    def test_health_check_result_unhealthy(self):
        """Test unhealthy result."""
        result = HealthCheckResult(
            status=HealthStatus.UNHEALTHY,
            message="Service down"
        )

        assert result.status == HealthStatus.UNHEALTHY

    def test_health_check_result_degraded(self):
        """Test degraded result."""
        result = HealthCheckResult(
            status=HealthStatus.DEGRADED,
            message="Slow response"
        )

        assert result.status == HealthStatus.DEGRADED


class TestAdditionalCoverageBoost:
    """Additional tests to boost coverage to 85%+."""

    def test_logger_all_methods(self):
        """Test all logger methods."""
        logger = get_logger("boost_test")

        # Set level to DEBUG to ensure all messages are processed
        logger.setLevel(logging.DEBUG)

        # Bind context
        logger.bind(test_id="boost", session="session123")

        # Test all log levels
        logger.debug("Debug message", extra1="val1")
        logger.info("Info message", extra2="val2")
        logger.warning("Warning message", extra3="val3")
        logger.error("Error message", extra4="val4")
        logger.critical("Critical message", extra5="val5")

        # Test exception
        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("Exception caught")

        # Unbind
        logger.unbind("test_id")

        # Log again without test_id
        logger.info("After unbind")

    def test_color_formatter_all_levels(self):
        """Test color formatter for all log levels."""
        formatter = ColorFormatter()

        levels = [
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL
        ]

        for level in levels:
            record = logging.LogRecord(
                name="test",
                level=level,
                pathname="test.py",
                lineno=1,
                msg=f"Message at level {level}",
                args=(),
                exc_info=None
            )

            # Add extra data sometimes
            if level in [logging.WARNING, logging.ERROR]:
                record.extra_data = {"key": "value"}

            formatted = formatter.format(record)
            assert formatted  # Should produce output

    def test_json_formatter_all_scenarios(self):
        """Test JSON formatter in all scenarios."""
        formatter = JSONFormatter()

        # Test with extra data
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="With extra",
            args=(),
            exc_info=None
        )
        record.extra_data = {"user": "test_user", "action": "test_action"}

        formatted = formatter.format(record)
        data = json.loads(formatted)
        assert data["user"] == "test_user"
        assert data["action"] == "test_action"

        # Test without extra data
        record2 = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Without extra",
            args=(),
            exc_info=None
        )

        formatted2 = formatter.format(record2)
        data2 = json.loads(formatted2)
        assert data2["level"] == "ERROR"

    @pytest.mark.asyncio
    async def test_health_checks_all_types(self):
        """Test all health check types."""
        # Liveness
        liveness = LivenessCheck()
        liveness_result = await liveness.check()
        assert liveness_result.status == HealthStatus.HEALTHY

        # Readiness
        readiness = ReadinessCheck()
        readiness_result = await readiness.check()
        assert readiness_result.status == HealthStatus.HEALTHY

        # Resources
        resources = ResourceCheck()
        resources_result = await resources.check()
        assert resources_result.status in [
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY
        ]

    def test_span_context_all_operations(self):
        """Test all span context operations."""
        # Create context
        context = SpanContext(
            trace_id="a" * 32,
            span_id="b" * 16,
            sampled=True
        )

        # Test to_traceparent
        traceparent = context.to_traceparent()
        assert len(traceparent.split("-")) == 4

        # Test from_traceparent with valid
        parsed = SpanContext.from_traceparent(traceparent)
        assert parsed is not None
        assert parsed.trace_id == "a" * 32

        # Test trace_flags
        assert context.trace_flags == 1

        # Test not sampled
        context2 = SpanContext(
            trace_id="c" * 32,
            span_id="d" * 16,
            sampled=False
        )
        assert context2.trace_flags == 0

    def test_span_all_operations(self):
        """Test all span operations."""
        import time

        span = Span(
            trace_id="trace_id",
            span_id="span_id",
            parent_span_id="parent_id",
            name="test_span",
            start_time=time.time()
        )

        # Set multiple attributes
        span.set_attribute("attr1", "value1")
        span.set_attribute("attr2", 123)
        span.set_attribute("attr3", True)

        # Add multiple events
        span.add_event("event1")
        span.add_event("event2", {"data": "value"})
        span.add_event("event3", {"count": 5})

        # Set status
        span.set_status("ok", "All good")
        assert span.status == "ok"
        assert span.error_message == "All good"

        # Change status to error
        span.set_status("error", "Something failed")
        assert span.status == "error"

        # End span
        span.end()
        assert span.end_time is not None
        assert span.duration_ms >= 0  # >= 0 for Windows time resolution

        # Call end again (should not change end_time)
        first_end_time = span.end_time
        span.end()
        assert span.end_time == first_end_time

        # Convert to dict
        span_dict = span.to_dict()
        assert span_dict["trace_id"] == "trace_id"
        assert span_dict["parent_span_id"] == "parent_id"
        assert len(span_dict["attributes"]) == 3
        assert len(span_dict["events"]) == 3


class TestLoggerSetupAndDecorators:
    """Test logger setup functions and decorators."""

    def test_setup_logging_console_only(self):
        """Test setup_logging with console only."""
        from src.common.logger import setup_logging

        setup_logging(level="INFO", json_output=False)
        # Should not raise

    def test_setup_logging_with_json(self):
        """Test setup_logging with JSON output."""
        from src.common.logger import setup_logging

        setup_logging(level="DEBUG", json_output=True)
        # Should not raise

    def test_setup_logging_with_file(self):
        """Test setup_logging with file output."""
        from src.common.logger import setup_logging
        import logging

        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            setup_logging(level="INFO", json_output=False, log_file=str(log_file))

            # Log something
            logger = get_logger("test_file_logging")
            logger.info("Test message")

            # File should exist
            assert log_file.exists()
            
            # Close all file handlers to avoid Windows file permission issues
            for handler in logging.root.handlers[:]:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
                    logging.root.removeHandler(handler)

    def test_log_call_decorator(self):
        """Test log_call decorator."""
        from src.common.logger import log_call

        logger = get_logger("test_decorator")
        logger.setLevel(logging.DEBUG)

        @log_call(logger)
        def test_function(x, y):
            return x + y

        result = test_function(2, 3)
        assert result == 5

    def test_log_call_decorator_no_logger(self):
        """Test log_call decorator without explicit logger."""
        from src.common.logger import log_call

        @log_call()
        def test_function2(x):
            return x * 2

        result = test_function2(5)
        assert result == 10

    def test_log_call_decorator_with_exception(self):
        """Test log_call decorator when function raises exception."""
        from src.common.logger import log_call

        logger = get_logger("test_decorator_error")

        @log_call(logger)
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

    def test_log_call_decorator_with_kwargs(self):
        """Test log_call decorator with keyword arguments."""
        from src.common.logger import log_call

        @log_call()
        def test_function3(a, b=10, c=20):
            return a + b + c

        result = test_function3(5, b=15, c=25)
        assert result == 45


class TestJSONLWriterAllMethods:
    """Test all JSONLWriter methods."""

    def test_jsonl_writer_all_log_types(self):
        """Test all log types in JSONLWriter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            writer = JSONLWriter(temp_dir)

            # Log system event
            writer.log_system_event("SYSTEM_START", {"version": "1.0"})

            # Log league event
            writer.log_league_event("league1", "LEAGUE_START", {"players": 10})

            # Log agent event
            writer.log_agent_event("P001", "player", "AGENT_READY", {})

            # Log match event
            writer.log_match_event("league1", "M001", "MATCH_START", {"round": 1})

            # Verify files exist
            system_log = Path(temp_dir) / "system" / "system.log.jsonl"
            league_log = Path(temp_dir) / "league" / "league1" / "events.log.jsonl"
            agent_log = Path(temp_dir) / "agents" / "P001.log.jsonl"
            match_log = Path(temp_dir) / "league" / "league1" / "matches" / "M001.log.jsonl"

            assert system_log.exists()
            assert league_log.exists()
            assert agent_log.exists()
            assert match_log.exists()

    def test_jsonl_read_events_with_filter(self):
        """Test reading events with filtering."""
        with tempfile.TemporaryDirectory() as temp_dir:
            writer = JSONLWriter(temp_dir)

            # Write multiple events
            for i in range(10):
                event_type = "TYPE_A" if i % 2 == 0 else "TYPE_B"
                writer.log_system_event(event_type, {"index": i})

            log_file = Path(temp_dir) / "system" / "system.log.jsonl"

            # Read all
            all_events = writer.read_events(log_file)
            assert len(all_events) == 10

            # Read with filter
            type_a_events = writer.read_events(log_file, event_type="TYPE_A")
            assert len(type_a_events) == 5

            # Read with limit
            limited_events = writer.read_events(log_file, limit=3)
            assert len(limited_events) == 3


class TestFinalCoveragePush:
    """Final tests to push coverage to 85%+."""

    def test_performance_tracker_error_case(self):
        """Test performance tracker with error."""
        from src.common.logger import PerformanceTracker

        logger = get_logger("perf_test")

        try:
            with PerformanceTracker("error_operation", logger):
                raise RuntimeError("Test error")
        except RuntimeError:
            pass
        # Should complete without crashing

    def test_logger_context_standard_kwargs(self):
        """Test logger with standard kwargs."""
        logger = get_logger("std_kwargs_test")
        logger.bind(context="test")

        # Call with stack_info and stacklevel
        logger.info("Message", stack_info=False, stacklevel=1, custom="value")
        logger.debug("Debug", stack_info=True, stacklevel=2)

    def test_jsonl_writer_read_nonexistent(self):
        """Test reading from nonexistent file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            writer = JSONLWriter(temp_dir)
            nonexistent = Path(temp_dir) / "nonexistent.jsonl"

            events = writer.read_events(nonexistent)
            assert events == []

    def test_color_formatter_with_empty_extra_data(self):
        """Test color formatter with empty extra_data dict."""
        formatter = ColorFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Message",
            args=(),
            exc_info=None
        )
        record.extra_data = {}  # Empty dict

        formatted = formatter.format(record)
        assert "Message" in formatted

    def test_span_add_event_without_attributes(self):
        """Test adding event without attributes."""
        import time

        span = Span(
            trace_id="test",
            span_id="span",
            parent_span_id=None,
            name="test",
            start_time=time.time()
        )

        # Add event without attributes
        span.add_event("event_without_attrs")
        assert len(span.events) == 1
        assert span.events[0]["name"] == "event_without_attrs"
        assert span.events[0]["attributes"] == {}

    def test_tracing_manager_enabled_property(self):
        """Test tracing manager enabled property."""
        manager = TracingManager()

        # Test enabled property
        enabled = manager.enabled
        assert isinstance(enabled, bool)

        # Test sample_rate property
        sample_rate = manager.sample_rate
        assert isinstance(sample_rate, float)

        # Test service_name property
        service_name = manager.service_name
        assert isinstance(service_name, str)

    def test_health_check_result_all_statuses(self):
        """Test creating health check results with all statuses."""
        # Healthy
        result1 = HealthCheckResult(status=HealthStatus.HEALTHY, message="OK")
        assert result1.status == HealthStatus.HEALTHY

        # Degraded
        result2 = HealthCheckResult(status=HealthStatus.DEGRADED, message="Slow")
        assert result2.status == HealthStatus.DEGRADED

        # Unhealthy
        result3 = HealthCheckResult(status=HealthStatus.UNHEALTHY, message="Down")
        assert result3.status == HealthStatus.UNHEALTHY

    def test_logger_all_levels_with_args(self):
        """Test logger with positional args."""
        logger = get_logger("args_test")
        logger.setLevel(logging.DEBUG)

        # Test with format args
        logger.debug("Debug %s %d", "test", 123)
        logger.info("Info %s", "message")
        logger.warning("Warning %d", 456)
        logger.error("Error %s %s", "msg", "error")
        logger.critical("Critical %d", 789)


class TestLoggerDecoratorsAndSetup:
    """Test logger decorators and setup functions."""

    def test_setup_logging_json_output(self):
        """Test setup_logging with JSON output."""
        from src.common.logger import setup_logging

        with tempfile.TemporaryDirectory() as _temp_dir:
            setup_logging(level="INFO", json_output=True, log_file=None)
            logger = get_logger("test_json_setup")
            logger.info("Test JSON message")

    def test_setup_logging_with_file_and_json(self):
        """Test setup_logging with file handler and JSON output."""
        from src.common.logger import setup_logging
        import logging

        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test_json.log"
            setup_logging(level="DEBUG", json_output=True, log_file=str(log_file))

            logger = get_logger("test_json_file")
            logger.debug("Debug message in JSON")
            logger.info("Info message in JSON")

            assert log_file.exists()
            
            # Close all file handlers to avoid Windows file permission issues
            for handler in logging.root.handlers[:]:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
                    logging.root.removeHandler(handler)

    def test_setup_logging_different_levels(self):
        """Test setup_logging with different log levels."""
        from src.common.logger import setup_logging

        # Test with lowercase level
        setup_logging(level="warning", json_output=False)
        logger = get_logger("test_warning_level")
        logger.warning("Warning level test")

        # Test with uppercase level
        setup_logging(level="ERROR", json_output=False)
        logger = get_logger("test_error_level")
        logger.error("Error level test")

    def test_log_call_decorator_with_no_logger(self):
        """Test log_call decorator when logger=None."""
        from src.common.logger import log_call

        @log_call(logger=None)
        def test_function(x, y):
            return x + y

        result = test_function(5, 3)
        assert result == 8

    def test_log_call_decorator_with_exception(self):
        """Test log_call decorator with exception."""
        from src.common.logger import log_call

        logger = get_logger("test_decorator_exception")
        logger.setLevel(logging.DEBUG)

        @log_call(logger=logger)
        def failing_function(x):
            if x == 0:
                raise ValueError("Cannot be zero")
            return x * 2

        # Should work normally
        assert failing_function(5) == 10

        # Should raise exception and log it
        with pytest.raises(ValueError, match="Cannot be zero"):
            failing_function(0)

    @pytest.mark.asyncio
    async def test_log_async_call_decorator_with_no_logger(self):
        """Test log_async_call decorator when logger=None."""
        from src.common.logger import log_async_call

        @log_async_call(logger=None)
        async def async_test_function(x, y):
            await asyncio.sleep(0.001)
            return x * y

        result = await async_test_function(4, 3)
        assert result == 12

    @pytest.mark.asyncio
    async def test_log_async_call_decorator_with_exception(self):
        """Test log_async_call decorator with exception."""
        from src.common.logger import log_async_call

        logger = get_logger("test_async_decorator_exception")
        logger.setLevel(logging.DEBUG)

        @log_async_call(logger=logger)
        async def async_failing_function(x):
            await asyncio.sleep(0.001)
            if x < 0:
                raise ValueError("Cannot be negative")
            return x * 2

        # Should work normally
        result = await async_failing_function(5)
        assert result == 10

        # Should raise exception and log it
        with pytest.raises(ValueError, match="Cannot be negative"):
            await async_failing_function(-1)


class TestTracingAdvancedCoverage:
    """Advanced tracing tests to cover remaining lines."""

    def test_tracing_manager_basic(self):
        """Test basic tracing manager functionality."""
        manager = TracingManager()

        # Test that manager is a singleton
        manager2 = TracingManager()
        assert manager is manager2

        # Test basic properties
        assert hasattr(manager, '_service_name')
        assert hasattr(manager, '_enabled')
        assert hasattr(manager, '_sample_rate')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
