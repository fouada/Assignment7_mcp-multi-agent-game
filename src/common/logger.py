"""
Structured Logging System
=========================

Production-grade logging with structured output, context tracking,
and performance metrics.
"""

import json
import logging
import sys
import time
import traceback
from datetime import datetime
from functools import wraps
from importlib.util import find_spec
from pathlib import Path
from typing import Any

HAS_STRUCTLOG = find_spec("structlog") is not None


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
                if record.exc_info[0]
                else None,
            }

        return json.dumps(log_data)


class ColorFormatter(logging.Formatter):
    """Colored console formatter."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)

        # Format timestamp
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # Build message
        parts = [
            f"{color}{self.BOLD}[{timestamp}]{self.RESET}",
            f"{color}[{record.levelname:^8}]{self.RESET}",
            f"[{record.name}]",
            record.getMessage(),
        ]

        # Add extra context if present
        if hasattr(record, "extra_data") and record.extra_data:
            extra_str = " | ".join(f"{k}={v}" for k, v in record.extra_data.items())
            parts.append(f"\033[90m({extra_str})\033[0m")

        message = " ".join(parts)

        # Add exception if present
        if record.exc_info:
            exc_text = "".join(traceback.format_exception(*record.exc_info))
            message += f"\n{color}{exc_text}{self.RESET}"

        return message


class GameLogger(logging.Logger):
    """Enhanced logger with context tracking."""

    def __init__(self, name: str, level: int = logging.NOTSET):
        super().__init__(name, level)
        self._context: dict[str, Any] = {}

    def bind(self, **kwargs) -> "GameLogger":
        """Bind context data to logger."""
        self._context.update(kwargs)
        return self

    def unbind(self, *keys) -> "GameLogger":
        """Remove context keys."""
        for key in keys:
            self._context.pop(key, None)
        return self

    def _log_with_context(self, level: int, msg: object, args, exc_info=None, extra=None, **kwargs):
        """Log with context data."""
        if extra is None:
            extra = {}

        # Merge context with extra data
        # Extract context-specific kwargs (not standard logging kwargs)
        standard_kwargs = {'stack_info', 'stacklevel'}
        context_kwargs = {k: v for k, v in kwargs.items() if k not in standard_kwargs}
        logging_kwargs = {k: v for k, v in kwargs.items() if k in standard_kwargs}
        
        extra_data = {**self._context, **context_kwargs}
        extra["extra_data"] = extra_data

        super()._log(level, msg, args, exc_info=exc_info, extra=extra, **logging_kwargs)

    def debug(self, msg: object, *args: object, exc_info=None, stack_info: bool = False, 
              stacklevel: int = 1, extra=None, **kwargs) -> None:
        self._log_with_context(logging.DEBUG, msg, args, exc_info=exc_info, extra=extra, 
                               stack_info=stack_info, stacklevel=stacklevel, **kwargs)

    def info(self, msg: object, *args: object, exc_info=None, stack_info: bool = False, 
             stacklevel: int = 1, extra=None, **kwargs) -> None:
        self._log_with_context(logging.INFO, msg, args, exc_info=exc_info, extra=extra, 
                               stack_info=stack_info, stacklevel=stacklevel, **kwargs)

    def warning(self, msg: object, *args: object, exc_info=None, stack_info: bool = False, 
                stacklevel: int = 1, extra=None, **kwargs) -> None:
        self._log_with_context(logging.WARNING, msg, args, exc_info=exc_info, extra=extra, 
                               stack_info=stack_info, stacklevel=stacklevel, **kwargs)

    def error(self, msg: object, *args: object, exc_info=None, stack_info: bool = False, 
              stacklevel: int = 1, extra=None, **kwargs) -> None:
        self._log_with_context(logging.ERROR, msg, args, exc_info=exc_info, extra=extra, 
                               stack_info=stack_info, stacklevel=stacklevel, **kwargs)

    def critical(self, msg: object, *args: object, exc_info=None, stack_info: bool = False, 
                 stacklevel: int = 1, extra=None, **kwargs) -> None:
        self._log_with_context(logging.CRITICAL, msg, args, exc_info=exc_info, extra=extra, 
                               stack_info=stack_info, stacklevel=stacklevel, **kwargs)

    def exception(self, msg: object, *args: object, exc_info=True, stack_info: bool = False, 
                  stacklevel: int = 1, extra=None, **kwargs) -> None:
        self._log_with_context(logging.ERROR, msg, args, exc_info=exc_info, extra=extra, 
                               stack_info=stack_info, stacklevel=stacklevel, **kwargs)


# Register custom logger class
logging.setLoggerClass(GameLogger)

# Logger cache
_loggers: dict[str, GameLogger] = {}


def setup_logging(
    level: str = "INFO",
    json_output: bool = False,
    log_file: str | None = None,
) -> None:
    """Setup logging configuration."""

    log_level = getattr(logging, level.upper(), logging.INFO)

    # Root logger
    root = logging.getLogger()
    root.setLevel(log_level)

    # Remove existing handlers
    root.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    if json_output:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(ColorFormatter())

    root.addHandler(console_handler)

    # File handler (always JSON)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(JSONFormatter())
        root.addHandler(file_handler)


def get_logger(name: str = "mcp_game") -> GameLogger:
    """Get a logger instance."""
    if name not in _loggers:
        logger = logging.getLogger(name)
        # Ensure it's a GameLogger instance
        if not isinstance(logger, GameLogger):
            # This should not happen if setLoggerClass was called correctly
            logger = GameLogger(name)
        _loggers[name] = logger
    return _loggers[name]


# Decorators for logging


def log_call(logger: GameLogger | None = None):
    """Decorator to log function calls."""

    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)

        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.debug(
                f"Calling {func.__name__}", args_count=len(args), kwargs_keys=list(kwargs.keys())
            )
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                logger.debug(f"Completed {func.__name__}", duration_ms=round(duration * 1000, 2))
                return result
            except Exception as e:
                duration = time.time() - start
                logger.error(
                    f"Error in {func.__name__}: {e}",
                    duration_ms=round(duration * 1000, 2),
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator


def log_async_call(logger: GameLogger | None = None):
    """Decorator to log async function calls."""

    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            logger.debug(f"Calling async {func.__name__}", args_count=len(args))
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start
                logger.debug(f"Completed {func.__name__}", duration_ms=round(duration * 1000, 2))
                return result
            except Exception as e:
                duration = time.time() - start
                logger.error(
                    f"Error in {func.__name__}: {e}",
                    duration_ms=round(duration * 1000, 2),
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator


class PerformanceTracker:
    """Context manager for tracking operation performance."""

    def __init__(self, operation: str, logger: GameLogger | None = None):
        self.operation = operation
        self.logger = logger or get_logger()
        self.start_time: float | None = None
        self.end_time: float | None = None

    def __enter__(self):
        self.start_time = time.time()
        self.logger.debug(f"Starting {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = (self.end_time - self.start_time) * 1000

        if exc_type:
            self.logger.error(
                f"Failed {self.operation}", duration_ms=round(duration, 2), error=str(exc_val)
            )
        else:
            self.logger.info(f"Completed {self.operation}", duration_ms=round(duration, 2))

        return False  # Don't suppress exceptions

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self.__exit__(exc_type, exc_val, exc_tb)

    @property
    def duration_ms(self) -> float | None:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return None


# ============================================================================
# JSONL File Logging
# ============================================================================


class JSONLWriter:
    """
    JSONL file writer for structured event logging.

    Writes one JSON object per line to .log.jsonl files.
    Used for audit logs, event history, and debugging.

    File structure per document:
    - logs/league/<league_id>/*.log.jsonl - League events
    - logs/agents/*.log.jsonl - Agent events
    - logs/system/*.log.jsonl - System events
    """

    def __init__(self, base_path: str = "logs"):
        self.base_path = Path(base_path)
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create log directory structure."""
        (self.base_path / "league").mkdir(parents=True, exist_ok=True)
        (self.base_path / "agents").mkdir(parents=True, exist_ok=True)
        (self.base_path / "system").mkdir(parents=True, exist_ok=True)

    def _write_entry(self, path: Path, entry: dict[str, Any]) -> None:
        """Write a single JSONL entry."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str, ensure_ascii=False) + "\n")

    def log_league_event(
        self,
        league_id: str,
        event_type: str,
        data: dict[str, Any],
        log_file: str = "events",
    ) -> None:
        """
        Log a league event.

        File: logs/league/<league_id>/<log_file>.log.jsonl
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "league_id": league_id,
            "event_type": event_type,
            **data,
        }
        path = self.base_path / "league" / league_id / f"{log_file}.log.jsonl"
        self._write_entry(path, entry)

    def log_agent_event(
        self,
        agent_id: str,
        agent_type: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """
        Log an agent event.

        File: logs/agents/<agent_id>.log.jsonl
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "agent_id": agent_id,
            "agent_type": agent_type,
            "event_type": event_type,
            **data,
        }
        path = self.base_path / "agents" / f"{agent_id}.log.jsonl"
        self._write_entry(path, entry)

    def log_system_event(
        self,
        event_type: str,
        data: dict[str, Any],
        log_file: str = "system",
    ) -> None:
        """
        Log a system event.

        File: logs/system/<log_file>.log.jsonl
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,
            **data,
        }
        path = self.base_path / "system" / f"{log_file}.log.jsonl"
        self._write_entry(path, entry)

    def log_match_event(
        self,
        league_id: str,
        match_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """
        Log a match event.

        File: logs/league/<league_id>/matches/<match_id>.log.jsonl
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "match_id": match_id,
            "event_type": event_type,
            **data,
        }
        path = self.base_path / "league" / league_id / "matches" / f"{match_id}.log.jsonl"
        self._write_entry(path, entry)

    def read_events(
        self,
        path: Path,
        limit: int | None = None,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Read events from a JSONL file."""
        if not path.exists():
            return []

        events = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    if event_type is None or entry.get("event_type") == event_type:
                        events.append(entry)
                        if limit and len(events) >= limit:
                            break
        return events


class LeagueEventLogger:
    """
    High-level logger for league events.

    Provides structured methods for logging common league events.
    """

    def __init__(self, league_id: str, base_path: str = "logs"):
        self.league_id = league_id
        self.writer = JSONLWriter(base_path)

    def player_registered(
        self,
        player_id: str,
        display_name: str,
        endpoint: str,
    ) -> None:
        """Log player registration event."""
        self.writer.log_league_event(
            self.league_id,
            "PLAYER_REGISTERED",
            {
                "player_id": player_id,
                "display_name": display_name,
                "endpoint": endpoint,
            },
        )

    def referee_registered(
        self,
        referee_id: str,
        endpoint: str,
    ) -> None:
        """Log referee registration event."""
        self.writer.log_league_event(
            self.league_id,
            "REFEREE_REGISTERED",
            {
                "referee_id": referee_id,
                "endpoint": endpoint,
            },
        )

    def round_started(
        self,
        round_id: int,
        match_count: int,
    ) -> None:
        """Log round start event."""
        self.writer.log_league_event(
            self.league_id,
            "ROUND_STARTED",
            {
                "round_id": round_id,
                "match_count": match_count,
            },
        )

    def round_completed(
        self,
        round_id: int,
        results: list[dict[str, Any]],
    ) -> None:
        """Log round completion event."""
        self.writer.log_league_event(
            self.league_id,
            "ROUND_COMPLETED",
            {
                "round_id": round_id,
                "results": results,
            },
        )

    def match_started(
        self,
        match_id: str,
        player_A_id: str,
        player_B_id: str,
        referee_id: str,
    ) -> None:
        """Log match start event."""
        self.writer.log_match_event(
            self.league_id,
            match_id,
            "MATCH_STARTED",
            {
                "player_A_id": player_A_id,
                "player_B_id": player_B_id,
                "referee_id": referee_id,
            },
        )

    def match_completed(
        self,
        match_id: str,
        winner_id: str | None,
        player_A_score: int,
        player_B_score: int,
    ) -> None:
        """Log match completion event."""
        self.writer.log_match_event(
            self.league_id,
            match_id,
            "MATCH_COMPLETED",
            {
                "winner_id": winner_id,
                "player_A_score": player_A_score,
                "player_B_score": player_B_score,
            },
        )

    def move_submitted(
        self,
        match_id: str,
        player_id: str,
        round_number: int,
        move_value: int,
    ) -> None:
        """Log move submission event."""
        self.writer.log_match_event(
            self.league_id,
            match_id,
            "MOVE_SUBMITTED",
            {
                "player_id": player_id,
                "round_number": round_number,
                "move_value": move_value,
            },
        )

    def round_result(
        self,
        match_id: str,
        round_number: int,
        player_A_move: int,
        player_B_move: int,
        sum_value: int,
        winner_id: str | None,
    ) -> None:
        """Log round result event."""
        self.writer.log_match_event(
            self.league_id,
            match_id,
            "ROUND_RESULT",
            {
                "round_number": round_number,
                "player_A_move": player_A_move,
                "player_B_move": player_B_move,
                "sum_value": sum_value,
                "is_odd": sum_value % 2 == 1,
                "winner_id": winner_id,
            },
        )

    def standings_updated(
        self,
        round_id: int,
        standings: list[dict[str, Any]],
    ) -> None:
        """Log standings update event."""
        self.writer.log_league_event(
            self.league_id,
            "STANDINGS_UPDATED",
            {
                "round_id": round_id,
                "standings": standings,
            },
        )

    def error_occurred(
        self,
        error_code: str,
        error_message: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Log error event."""
        self.writer.log_league_event(
            self.league_id,
            "ERROR",
            {
                "error_code": error_code,
                "error_message": error_message,
                "context": context or {},
            },
            log_file="errors",
        )


class AgentEventLogger:
    """
    High-level logger for agent events.

    Each agent logs its own events to its own file.
    """

    def __init__(self, agent_id: str, agent_type: str, base_path: str = "logs"):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.writer = JSONLWriter(base_path)

    def started(self) -> None:
        """Log agent start event."""
        self.writer.log_agent_event(
            self.agent_id,
            self.agent_type,
            "AGENT_STARTED",
            {},
        )

    def stopped(self) -> None:
        """Log agent stop event."""
        self.writer.log_agent_event(
            self.agent_id,
            self.agent_type,
            "AGENT_STOPPED",
            {},
        )

    def registered(self, league_id: str) -> None:
        """Log registration event."""
        self.writer.log_agent_event(
            self.agent_id,
            self.agent_type,
            "REGISTERED",
            {"league_id": league_id},
        )

    def message_sent(self, message_type: str, recipient: str) -> None:
        """Log outgoing message."""
        self.writer.log_agent_event(
            self.agent_id,
            self.agent_type,
            "MESSAGE_SENT",
            {"message_type": message_type, "recipient": recipient},
        )

    def message_received(self, message_type: str, sender: str) -> None:
        """Log incoming message."""
        self.writer.log_agent_event(
            self.agent_id,
            self.agent_type,
            "MESSAGE_RECEIVED",
            {"message_type": message_type, "sender": sender},
        )

    def error(self, error_code: str, error_message: str) -> None:
        """Log error event."""
        self.writer.log_agent_event(
            self.agent_id,
            self.agent_type,
            "ERROR",
            {"error_code": error_code, "error_message": error_message},
        )


# Global JSONL writer instance
_jsonl_writer: JSONLWriter | None = None


def get_jsonl_writer(base_path: str = "logs") -> JSONLWriter:
    """Get global JSONL writer instance."""
    global _jsonl_writer
    if _jsonl_writer is None:
        _jsonl_writer = JSONLWriter(base_path)
    return _jsonl_writer
