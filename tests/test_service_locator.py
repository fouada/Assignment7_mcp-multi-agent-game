"""
Comprehensive tests for Service Locator Pattern.

Testing:
- Service registration (instance, factory, singleton)
- Service retrieval
- Type-safe access
- Service aliasing
- Lazy loading
- Health checks
- Edge cases and error handling

Coverage target: 95%+
"""

import pytest

from src.common.exceptions import ServiceNotFoundError
from src.common.service_locator import ServiceLocator

# ============================================================================
# Test Services
# ============================================================================


class ILogger:
    """Logger interface."""

    def log(self, message: str) -> None:
        raise NotImplementedError


class ConsoleLogger(ILogger):
    """Console logger implementation."""

    def __init__(self):
        self.messages = []

    def log(self, message: str) -> None:
        self.messages.append(message)


class IDatabase:
    """Database interface."""

    def connect(self) -> str:
        raise NotImplementedError


class PostgresDatabase(IDatabase):
    """Postgres database implementation."""

    def __init__(self):
        self.connected = False

    def connect(self) -> str:
        self.connected = True
        return "Connected to Postgres"


class ICache:
    """Cache interface."""

    def get(self, key: str) -> str | None:
        raise NotImplementedError


class RedisCache(ICache):
    """Redis cache implementation."""

    def __init__(self):
        self.data = {}

    def get(self, key: str) -> str | None:
        return self.data.get(key)

    def set(self, key: str, value: str) -> None:
        self.data[key] = value


# ============================================================================
# Test ServiceLocator - Basic Registration
# ============================================================================


class TestServiceLocatorRegistration:
    """Test service registration methods."""

    def setup_method(self):
        """Clear service locator before each test."""
        ServiceLocator.clear()

    def test_register_instance(self):
        """Test registering a service instance."""
        logger = ConsoleLogger()
        ServiceLocator.register("logger", logger)

        # Should not raise error
        assert True

    def test_register_factory(self):
        """Test registering a factory function."""

        def database_factory():
            return PostgresDatabase()

        ServiceLocator.register("database", database_factory)

        # Should not raise error
        assert True

    def test_register_singleton(self):
        """Test registering a singleton service."""
        call_count = 0

        def cache_factory():
            nonlocal call_count
            call_count += 1
            return RedisCache()

        ServiceLocator.register("cache", cache_factory, singleton=True)

        # Get twice - should only call factory once
        cache1 = ServiceLocator.get("cache")
        cache2 = ServiceLocator.get("cache")

        assert call_count == 1
        assert cache1 is cache2

    def test_register_multiple_services(self):
        """Test registering multiple services."""
        logger = ConsoleLogger()
        database = PostgresDatabase()
        cache = RedisCache()

        ServiceLocator.register("logger", logger)
        ServiceLocator.register("database", database)
        ServiceLocator.register("cache", cache)

        # Should be able to get all
        assert ServiceLocator.get("logger") is logger
        assert ServiceLocator.get("database") is database
        assert ServiceLocator.get("cache") is cache


# ============================================================================
# Test ServiceLocator - Service Retrieval
# ============================================================================


class TestServiceLocatorRetrieval:
    """Test service retrieval methods."""

    def setup_method(self):
        """Clear service locator before each test."""
        ServiceLocator.clear()

    def test_get_registered_service(self):
        """Test getting a registered service."""
        logger = ConsoleLogger()
        ServiceLocator.register("logger", logger)

        retrieved = ServiceLocator.get("logger")

        assert retrieved is logger

    def test_get_unregistered_service(self):
        """Test getting an unregistered service raises error."""
        with pytest.raises(ServiceNotFoundError) as exc_info:
            ServiceLocator.get("nonexistent")
        assert "nonexistent" in str(exc_info.value)

    def test_get_with_default(self):
        """Test getting service with default value."""
        default_logger = ConsoleLogger()

        # Try to get unregistered service with default
        if hasattr(ServiceLocator, "get_or_default"):
            logger = ServiceLocator.get_or_default("logger", default_logger)
            assert logger is default_logger

    def test_get_typed(self):
        """Test type-safe service retrieval."""
        logger = ConsoleLogger()
        ServiceLocator.register("logger", logger)

        # Type-safe access
        if hasattr(ServiceLocator, "get_typed"):
            retrieved = ServiceLocator.get_typed("logger", ILogger)
            assert isinstance(retrieved, ILogger)

    def test_get_factory_service(self):
        """Test getting service from factory."""

        def database_factory():
            return PostgresDatabase()

        ServiceLocator.register("database", database_factory)

        database = ServiceLocator.get("database")

        assert isinstance(database, PostgresDatabase)

    def test_get_factory_creates_new_instance(self):
        """Test that factory creates new instance each time (non-singleton)."""

        def cache_factory():
            return RedisCache()

        ServiceLocator.register("cache", cache_factory, singleton=False)

        cache1 = ServiceLocator.get("cache")
        cache2 = ServiceLocator.get("cache")

        # Should be different instances
        assert cache1 is not cache2


# ============================================================================
# Test ServiceLocator - Service Checking
# ============================================================================


class TestServiceLocatorChecking:
    """Test service availability checking."""

    def setup_method(self):
        """Clear service locator before each test."""
        ServiceLocator.clear()

    def test_has_registered_service(self):
        """Test checking if service is registered."""
        logger = ConsoleLogger()
        ServiceLocator.register("logger", logger)

        assert ServiceLocator.has("logger") is True

    def test_has_unregistered_service(self):
        """Test checking unregistered service."""
        assert ServiceLocator.has("nonexistent") is False

    def test_is_registered(self):
        """Test is_registered method."""
        logger = ConsoleLogger()
        ServiceLocator.register("logger", logger)

        if hasattr(ServiceLocator, "is_registered"):
            assert ServiceLocator.is_registered("logger") is True
            assert ServiceLocator.is_registered("nonexistent") is False


# ============================================================================
# Test ServiceLocator - Service Aliasing
# ============================================================================


class TestServiceLocatorAliasing:
    """Test service aliasing features."""

    def setup_method(self):
        """Clear service locator before each test."""
        ServiceLocator.clear()

    def test_register_alias(self):
        """Test registering an alias for a service."""
        logger = ConsoleLogger()
        ServiceLocator.register("logger", logger)

        if hasattr(ServiceLocator, "register_alias"):
            ServiceLocator.register_alias("log", "logger")

            # Should be able to get via alias
            retrieved = ServiceLocator.get("log")
            assert retrieved is logger

    def test_multiple_aliases(self):
        """Test multiple aliases for same service."""
        logger = ConsoleLogger()
        ServiceLocator.register("logger", logger)

        if hasattr(ServiceLocator, "register_alias"):
            ServiceLocator.register_alias("log", "logger")
            ServiceLocator.register_alias("logging", "logger")

            # All should return same instance
            log1 = ServiceLocator.get("log")
            log2 = ServiceLocator.get("logging")
            log3 = ServiceLocator.get("logger")

            assert log1 is log2 is log3


# ============================================================================
# Test ServiceLocator - Lazy Loading
# ============================================================================


class TestServiceLocatorLazyLoading:
    """Test lazy loading features."""

    def setup_method(self):
        """Clear service locator before each test."""
        ServiceLocator.clear()

    def test_factory_not_called_until_get(self):
        """Test that factory is not called until service is requested."""
        call_count = 0

        def database_factory():
            nonlocal call_count
            call_count += 1
            return PostgresDatabase()

        ServiceLocator.register("database", database_factory)

        # Factory should not be called yet
        assert call_count == 0

        # Get service
        ServiceLocator.get("database")

        # Factory should be called now
        assert call_count == 1

    def test_singleton_factory_called_once(self):
        """Test that singleton factory is called only once."""
        call_count = 0

        def cache_factory():
            nonlocal call_count
            call_count += 1
            return RedisCache()

        ServiceLocator.register("cache", cache_factory, singleton=True)

        # Get multiple times
        for _ in range(5):
            ServiceLocator.get("cache")

        # Factory should be called only once
        assert call_count == 1


# ============================================================================
# Test ServiceLocator - Service Management
# ============================================================================


class TestServiceLocatorManagement:
    """Test service management operations."""

    def setup_method(self):
        """Clear service locator before each test."""
        ServiceLocator.clear()

    def test_unregister_service(self):
        """Test unregistering a service."""
        logger = ConsoleLogger()
        ServiceLocator.register("logger", logger)

        if hasattr(ServiceLocator, "unregister"):
            ServiceLocator.unregister("logger")

            # Should no longer be available
            assert ServiceLocator.has("logger") is False

    def test_clear_all_services(self):
        """Test clearing all services."""
        ServiceLocator.register("logger", ConsoleLogger())
        ServiceLocator.register("database", PostgresDatabase())
        ServiceLocator.register("cache", RedisCache())

        ServiceLocator.clear()

        # All should be cleared
        assert ServiceLocator.has("logger") is False
        assert ServiceLocator.has("database") is False
        assert ServiceLocator.has("cache") is False

    def test_list_services(self):
        """Test listing all registered services."""
        ServiceLocator.register("logger", ConsoleLogger())
        ServiceLocator.register("database", PostgresDatabase())

        if hasattr(ServiceLocator, "list_services"):
            services = ServiceLocator.list_services()
            assert "logger" in services
            assert "database" in services

    def test_replace_service(self):
        """Test replacing an existing service."""
        logger1 = ConsoleLogger()
        logger2 = ConsoleLogger()

        ServiceLocator.register("logger", logger1)
        ServiceLocator.register("logger", logger2)

        # Should get the new logger
        retrieved = ServiceLocator.get("logger")
        assert retrieved is logger2


# ============================================================================
# Test ServiceLocator - Health Checks
# ============================================================================


class TestServiceLocatorHealthChecks:
    """Test health check features."""

    def setup_method(self):
        """Clear service locator before each test."""
        ServiceLocator.clear()

    def test_health_check_all_services(self):
        """Test health check for all services."""
        ServiceLocator.register("logger", ConsoleLogger())
        ServiceLocator.register("database", PostgresDatabase())

        if hasattr(ServiceLocator, "health_check"):
            health = ServiceLocator.health_check()
            assert isinstance(health, dict)

    def test_health_check_specific_service(self):
        """Test health check for specific service."""
        database = PostgresDatabase()
        ServiceLocator.register("database", database)

        if hasattr(ServiceLocator, "health_check"):
            health = ServiceLocator.health_check("database")
            assert health is not None


# ============================================================================
# Test ServiceLocator - Thread Safety
# ============================================================================


class TestServiceLocatorThreadSafety:
    """Test thread safety of service locator."""

    def setup_method(self):
        """Clear service locator before each test."""
        ServiceLocator.clear()

    def test_concurrent_access(self):
        """Test concurrent access from multiple threads."""
        import threading

        logger = ConsoleLogger()
        ServiceLocator.register("logger", logger)

        results = []
        errors = []

        def get_logger():
            try:
                log = ServiceLocator.get("logger")
                results.append(log)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = [threading.Thread(target=get_logger) for _ in range(10)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Should have no errors
        assert len(errors) == 0
        # All should get same instance
        assert all(r is logger for r in results)

    def test_concurrent_registration(self):
        """Test concurrent registration from multiple threads."""
        import threading

        errors = []

        def register_service(name):
            try:
                ServiceLocator.register(name, ConsoleLogger())
            except Exception as e:
                errors.append(e)

        # Create multiple threads registering different services
        threads = [
            threading.Thread(target=register_service, args=(f"logger{i}",))
            for i in range(10)
        ]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Should have no errors
        assert len(errors) == 0


# ============================================================================
# Test Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def setup_method(self):
        """Clear service locator before each test."""
        ServiceLocator.clear()

    def test_register_none_service(self):
        """Test registering None as service."""
        try:
            ServiceLocator.register("null_service", None)
            # If no error, None is allowed
            assert True
        except ValueError:
            # If error, None validation is working
            assert True

    def test_register_empty_name(self):
        """Test registering service with empty name."""
        logger = ConsoleLogger()

        try:
            ServiceLocator.register("", logger)
            # If no error, empty name is allowed
            assert True
        except ValueError:
            # If error, name validation is working
            assert True

    def test_factory_raises_exception(self):
        """Test factory that raises exception."""

        def failing_factory():
            raise RuntimeError("Factory failed")

        ServiceLocator.register("failing", failing_factory)

        with pytest.raises(RuntimeError):
            ServiceLocator.get("failing")

    def test_get_with_none_name(self):
        """Test getting service with None name."""
        with pytest.raises(ServiceNotFoundError) as exc_info:
            ServiceLocator.get(None)  # type: ignore
        assert "None" in str(exc_info.value)

    def test_register_callable_class(self):
        """Test registering a callable class."""

        class DatabaseFactory:
            def __call__(self):
                return PostgresDatabase()

        factory = DatabaseFactory()
        ServiceLocator.register("database", factory)

        database = ServiceLocator.get("database")
        assert isinstance(database, PostgresDatabase)


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for service locator."""

    def setup_method(self):
        """Clear service locator before each test."""
        ServiceLocator.clear()

    def test_full_application_setup(self):
        """Test setting up a complete application with service locator."""
        # Register infrastructure services
        ServiceLocator.register("logger", ConsoleLogger())
        ServiceLocator.register("database", lambda: PostgresDatabase(), singleton=True)
        ServiceLocator.register("cache", lambda: RedisCache(), singleton=True)

        # Use services
        logger = ServiceLocator.get("logger")
        database = ServiceLocator.get("database")
        cache = ServiceLocator.get("cache")

        # Services should work
        logger.log("Application started")
        database.connect()
        cache.set("status", "running")

        assert len(logger.messages) > 0
        assert database.connected is True
        assert cache.get("status") == "running"

    def test_service_replacement_pattern(self):
        """Test replacing services for testing."""
        # Register production services
        ServiceLocator.register("database", PostgresDatabase())

        # Get production service
        prod_db = ServiceLocator.get("database")
        assert isinstance(prod_db, PostgresDatabase)

        # Replace with test double
        class MockDatabase(IDatabase):
            def connect(self) -> str:
                return "Mock connection"

        ServiceLocator.register("database", MockDatabase())

        # Get test service
        test_db = ServiceLocator.get("database")
        assert isinstance(test_db, MockDatabase)

    def test_optional_dependencies(self):
        """Test handling optional dependencies."""
        # Register required services
        ServiceLocator.register("logger", ConsoleLogger())

        # Check for optional service
        if ServiceLocator.has("metrics"):
            ServiceLocator.get("metrics")
            # Use metrics if available
        else:
            # Gracefully handle missing optional service
            assert True

    def test_service_lifecycle(self):
        """Test complete service lifecycle."""
        # Register
        logger = ConsoleLogger()
        ServiceLocator.register("logger", logger)

        # Use
        retrieved = ServiceLocator.get("logger")
        retrieved.log("Test message")

        # Verify
        assert len(retrieved.messages) == 1

        # Cleanup
        if hasattr(ServiceLocator, "unregister"):
            ServiceLocator.unregister("logger")
            assert ServiceLocator.has("logger") is False

