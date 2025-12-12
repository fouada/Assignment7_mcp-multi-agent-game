"""
Structured Logging System
=========================

Production-grade logging with structured output, context tracking,
and performance metrics.
"""

import logging
import sys
import json
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
import asyncio
from functools import wraps
import time
import traceback

try:
    import structlog
    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False


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
                "traceback": traceback.format_exception(*record.exc_info) if record.exc_info[0] else None,
            }
        
        return json.dumps(log_data)


class ColorFormatter(logging.Formatter):
    """Colored console formatter."""
    
    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
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
            message += f"\n{color}{self.format_exception(record.exc_info)}{self.RESET}"
        
        return message


class GameLogger(logging.Logger):
    """Enhanced logger with context tracking."""
    
    def __init__(self, name: str, level: int = logging.NOTSET):
        super().__init__(name, level)
        self._context: Dict[str, Any] = {}
    
    def bind(self, **kwargs) -> "GameLogger":
        """Bind context data to logger."""
        self._context.update(kwargs)
        return self
    
    def unbind(self, *keys) -> "GameLogger":
        """Remove context keys."""
        for key in keys:
            self._context.pop(key, None)
        return self
    
    def _log_with_context(
        self, 
        level: int, 
        msg: str, 
        args, 
        exc_info=None, 
        extra=None, 
        **kwargs
    ):
        """Log with context data."""
        if extra is None:
            extra = {}
        
        # Merge context with extra data
        extra_data = {**self._context, **kwargs}
        extra["extra_data"] = extra_data
        
        super()._log(level, msg, args, exc_info=exc_info, extra=extra)
    
    def debug(self, msg: str, *args, **kwargs):
        self._log_with_context(logging.DEBUG, msg, args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        self._log_with_context(logging.INFO, msg, args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        self._log_with_context(logging.WARNING, msg, args, **kwargs)
    
    def error(self, msg: str, *args, exc_info=False, **kwargs):
        self._log_with_context(logging.ERROR, msg, args, exc_info=exc_info, **kwargs)
    
    def critical(self, msg: str, *args, exc_info=True, **kwargs):
        self._log_with_context(logging.CRITICAL, msg, args, exc_info=exc_info, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs):
        kwargs["exc_info"] = True
        self.error(msg, *args, **kwargs)


# Register custom logger class
logging.setLoggerClass(GameLogger)

# Logger cache
_loggers: Dict[str, GameLogger] = {}


def setup_logging(
    level: str = "INFO",
    json_output: bool = False,
    log_file: Optional[str] = None,
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
        _loggers[name] = logging.getLogger(name)
    return _loggers[name]


# Decorators for logging

def log_call(logger: Optional[GameLogger] = None):
    """Decorator to log function calls."""
    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.debug(f"Calling {func.__name__}", args_count=len(args), kwargs_keys=list(kwargs.keys()))
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                logger.debug(f"Completed {func.__name__}", duration_ms=round(duration * 1000, 2))
                return result
            except Exception as e:
                duration = time.time() - start
                logger.error(f"Error in {func.__name__}: {e}", duration_ms=round(duration * 1000, 2), exc_info=True)
                raise
        
        return wrapper
    return decorator


def log_async_call(logger: Optional[GameLogger] = None):
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
                logger.error(f"Error in {func.__name__}: {e}", duration_ms=round(duration * 1000, 2), exc_info=True)
                raise
        
        return wrapper
    return decorator


class PerformanceTracker:
    """Context manager for tracking operation performance."""
    
    def __init__(self, operation: str, logger: Optional[GameLogger] = None):
        self.operation = operation
        self.logger = logger or get_logger()
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.debug(f"Starting {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = (self.end_time - self.start_time) * 1000
        
        if exc_type:
            self.logger.error(
                f"Failed {self.operation}",
                duration_ms=round(duration, 2),
                error=str(exc_val)
            )
        else:
            self.logger.info(
                f"Completed {self.operation}",
                duration_ms=round(duration, 2)
            )
        
        return False  # Don't suppress exceptions
    
    async def __aenter__(self):
        return self.__enter__()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self.__exit__(exc_type, exc_val, exc_tb)
    
    @property
    def duration_ms(self) -> Optional[float]:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return None

