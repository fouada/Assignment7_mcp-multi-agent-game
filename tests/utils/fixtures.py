"""
Test Fixtures and Decorators
=============================

Provides reusable test fixtures and decorators for common testing patterns.
"""

import asyncio
import functools
import logging
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List
from unittest.mock import patch


def async_test(func: Callable) -> Callable:
    """
    Decorator to run async tests with asyncio.
    
    Usage:
        @async_test
        async def test_something():
            await some_async_function()
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(func(*args, **kwargs))
    return wrapper


@contextmanager
def temp_directory() -> Generator[Path, None, None]:
    """
    Context manager providing a temporary directory.
    
    Usage:
        with temp_directory() as temp_dir:
            # Use temp_dir for testing
            pass
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@contextmanager
def capture_logs(
    logger_name: str = None,
    level: int = logging.DEBUG
) -> Generator[List[logging.LogRecord], None, None]:
    """
    Context manager to capture log messages.
    
    Usage:
        with capture_logs("my_logger") as log_records:
            # Perform actions
            pass
        # Check log_records
    """
    records = []
    
    class ListHandler(logging.Handler):
        def emit(self, record):
            records.append(record)
    
    handler = ListHandler()
    handler.setLevel(level)
    
    if logger_name:
        logger = logging.getLogger(logger_name)
    else:
        logger = logging.getLogger()
    
    logger.addHandler(handler)
    original_level = logger.level
    logger.setLevel(level)
    
    try:
        yield records
    finally:
        logger.removeHandler(handler)
        logger.setLevel(original_level)


@contextmanager
def mock_time(frozen_time: float = None) -> Generator[Dict[str, Any], None, None]:
    """
    Context manager to mock time.time() for testing.
    
    Usage:
        with mock_time(1234567890.0) as time_control:
            # time.time() returns 1234567890.0
            time_control["advance"](10.0)  # Advance by 10 seconds
    """
    current_time = {"value": frozen_time or time.time()}
    
    def mock_time_func():
        return current_time["value"]
    
    def advance(seconds: float):
        current_time["value"] += seconds
    
    control = {
        "advance": advance,
        "set": lambda t: current_time.update({"value": t}),
        "get": lambda: current_time["value"]
    }
    
    with patch("time.time", side_effect=mock_time_func):
        yield control


@contextmanager
def mock_environment(**env_vars) -> Generator[None, None, None]:
    """
    Context manager to temporarily set environment variables.
    
    Usage:
        with mock_environment(API_KEY="test123"):
            # os.environ["API_KEY"] == "test123"
            pass
    """
    import os
    original = {}
    
    for key, value in env_vars.items():
        original[key] = os.environ.get(key)
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = str(value)
    
    try:
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class TimeoutContext:
    """Context manager for testing timeouts."""
    
    def __init__(self, timeout: float):
        self.timeout = timeout
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        if elapsed > self.timeout:
            raise TimeoutError(f"Operation took {elapsed:.2f}s, timeout was {self.timeout}s")
        return False


def timeout(seconds: float) -> Callable:
    """
    Decorator to add timeout to async functions.
    
    Usage:
        @timeout(5.0)
        async def test_something():
            await long_operation()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
        return wrapper
    return decorator


class PerformanceTimer:
    """Context manager for measuring performance."""
    
    def __init__(self, name: str = "operation"):
        self.name = name
        self.start_time = None
        self.end_time = None
        self.duration = None
        
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.duration = self.end_time - self.start_time
        print(f"{self.name} took {self.duration:.4f} seconds")
        return False


@contextmanager
def capture_output() -> Generator[Dict[str, List[str]], None, None]:
    """
    Context manager to capture stdout and stderr.
    
    Usage:
        with capture_output() as output:
            print("test")
        assert "test" in output["stdout"]
    """
    import sys
    from io import StringIO
    
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    stdout_capture = StringIO()
    stderr_capture = StringIO()
    
    sys.stdout = stdout_capture
    sys.stderr = stderr_capture
    
    output = {
        "stdout": [],
        "stderr": []
    }
    
    try:
        yield output
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        
        output["stdout"] = stdout_capture.getvalue().splitlines()
        output["stderr"] = stderr_capture.getvalue().splitlines()


class EventRecorder:
    """Record events for testing event-driven systems."""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.event_counts: Dict[str, int] = {}
        
    def record(self, event_type: str, **data):
        """Record an event."""
        event = {
            "type": event_type,
            "timestamp": time.time(),
            **data
        }
        self.events.append(event)
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
    
    def get_events(self, event_type: str = None) -> List[Dict[str, Any]]:
        """Get recorded events, optionally filtered by type."""
        if event_type:
            return [e for e in self.events if e["type"] == event_type]
        return self.events
    
    def count(self, event_type: str = None) -> int:
        """Get count of events."""
        if event_type:
            return self.event_counts.get(event_type, 0)
        return len(self.events)
    
    def clear(self):
        """Clear recorded events."""
        self.events.clear()
        self.event_counts.clear()


class AsyncContextManager:
    """Base class for async context managers in tests."""
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False


class MockAsyncIterator:
    """Mock async iterator for testing."""
    
    def __init__(self, items: List[Any]):
        self.items = items
        self.index = 0
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item


def retry_on_exception(
    max_attempts: int = 3,
    delay: float = 0.1,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Decorator to retry function on exception.
    
    Usage:
        @retry_on_exception(max_attempts=3, delay=0.5)
        def flaky_function():
            # Might fail
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(delay)
            return None
        return wrapper
    return decorator


def parametrize_async(argnames: str, argvalues: List[Any]) -> Callable:
    """
    Decorator to parametrize async test functions.
    
    Usage:
        @parametrize_async("input,expected", [(1, 2), (3, 4)])
        async def test_something(input, expected):
            result = await async_function(input)
            assert result == expected
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            results = []
            for values in argvalues:
                if isinstance(values, tuple):
                    test_kwargs = dict(zip(argnames.split(","), values))
                else:
                    test_kwargs = {argnames: values}
                
                result = asyncio.run(func(*args, **test_kwargs, **kwargs))
                results.append(result)
            return results
        return wrapper
    return decorator

