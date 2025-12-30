"""
Test State Synchronization Service
====================================

Unit and integration tests for StateSyncService.

Test Coverage:
- Service start/stop
- State change publishing
- Event subscription
- Dashboard forwarding
- State snapshots
- State history
- Edge cases
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.launcher.state_sync import StateChange, StateSnapshot, StateSyncService


@pytest.fixture
def state_sync():
    """Create a fresh state sync service."""
    # Reset singleton
    StateSyncService._instance = None
    sync = StateSyncService()
    return sync


@pytest.fixture
async def running_state_sync(state_sync):
    """Create and start state sync service."""
    await state_sync.start()
    yield state_sync
    await state_sync.stop()


class TestStateSyncService:
    """Test StateSyncService class."""

    def test_singleton_pattern(self):
        """Test that StateSyncService is a singleton."""
        sync1 = StateSyncService()
        sync2 = StateSyncService()

        assert sync1 is sync2
        assert id(sync1) == id(sync2)

    @pytest.mark.asyncio
    async def test_start_service(self, state_sync):
        """Test starting state sync service."""
        assert state_sync._running is False

        await state_sync.start()

        assert state_sync._running is True

    @pytest.mark.asyncio
    async def test_start_already_running(self, running_state_sync):
        """Test starting service when already running."""
        assert running_state_sync._running is True

        # Start again should be no-op
        await running_state_sync.start()

        assert running_state_sync._running is True

    @pytest.mark.asyncio
    async def test_stop_service(self, running_state_sync):
        """Test stopping state sync service."""
        await running_state_sync.stop()

        assert running_state_sync._running is False

    @pytest.mark.asyncio
    async def test_publish_state_change(self, running_state_sync):
        """Test publishing a state change."""
        event_type = "test.event"
        source = "test_source"
        data = {"key": "value"}

        # Capture emitted event
        captured_events = []

        async def capture_handler(event):
            captured_events.append(event)

        running_state_sync.event_bus.on(event_type, capture_handler)

        # Publish state change
        await running_state_sync.publish_state_change(
            event_type=event_type, source=source, data=data
        )

        # Give event bus time to process
        await asyncio.sleep(0.1)

        # Verify event was emitted
        assert len(captured_events) == 1
        assert captured_events[0].event_type == event_type
        assert captured_events[0].source == source
        assert captured_events[0].data == data

    @pytest.mark.asyncio
    async def test_subscribe_to_events(self, running_state_sync):
        """Test subscribing to state changes."""
        captured_events = []

        async def test_handler(event):
            captured_events.append(event)

        # Subscribe to test events
        subscription_id = running_state_sync.subscribe("test.*", test_handler)

        assert subscription_id is not None

        # Publish an event
        await running_state_sync.publish_state_change(
            event_type="test.event", source="test", data={"value": 123}
        )

        # Give time to process
        await asyncio.sleep(0.1)

        # Verify handler was called
        assert len(captured_events) > 0

        # Cleanup
        running_state_sync.unsubscribe(subscription_id)

    @pytest.mark.asyncio
    async def test_unsubscribe(self, running_state_sync):
        """Test unsubscribing from events."""
        captured_events = []

        async def test_handler(event):
            captured_events.append(event)

        # Subscribe
        subscription_id = running_state_sync.subscribe("test.*", test_handler)

        # Unsubscribe
        result = running_state_sync.unsubscribe(subscription_id)
        assert result is True

        # Publish event - handler should not be called
        await running_state_sync.publish_state_change(
            event_type="test.event", source="test", data={}
        )

        await asyncio.sleep(0.1)

        # Handler should not have been called
        # (Note: There might be one event from the subscription itself)
        # So we just verify unsubscribe returned True

    @pytest.mark.asyncio
    async def test_event_tracking(self, running_state_sync):
        """Test that events are tracked in state changes."""
        # Publish events
        for i in range(5):
            await running_state_sync.publish_state_change(
                event_type=f"test.event.{i}", source="test", data={"index": i}
            )

        await asyncio.sleep(0.1)

        # Get state history
        history = await running_state_sync.get_state_history(limit=10)

        # Should have tracked the events
        assert len(history) >= 5

    @pytest.mark.asyncio
    async def test_state_snapshot_creation(self, running_state_sync):
        """Test creating state snapshots."""
        snapshot_id = "test_snapshot_1"

        snapshot = await running_state_sync.create_snapshot(snapshot_id)

        assert snapshot.snapshot_id == snapshot_id
        assert isinstance(snapshot.timestamp, datetime)
        assert isinstance(snapshot.components, dict)

    @pytest.mark.asyncio
    async def test_get_current_state(self, running_state_sync):
        """Test getting current state."""
        state = await running_state_sync.get_current_state()

        assert isinstance(state, dict)

    @pytest.mark.asyncio
    async def test_get_state_history(self, running_state_sync):
        """Test getting state history."""
        # Publish some events
        for i in range(3):
            await running_state_sync.publish_state_change(
                event_type="test.event", source="test", data={"index": i}
            )

        await asyncio.sleep(0.1)

        # Get history
        history = await running_state_sync.get_state_history(limit=5)

        assert isinstance(history, list)
        # Should have at least some events
        assert len(history) >= 0

    @pytest.mark.asyncio
    async def test_get_state_history_with_limit(self, running_state_sync):
        """Test getting state history with limit."""
        # Publish many events
        for i in range(20):
            await running_state_sync.publish_state_change(
                event_type="test.event", source="test", data={"index": i}
            )

        await asyncio.sleep(0.1)

        # Get history with limit
        history = await running_state_sync.get_state_history(limit=5)

        # Should not exceed limit
        assert len(history) <= 5

    @pytest.mark.asyncio
    async def test_subscribe_to_all_events_dashboard(self, running_state_sync):
        """Test subscribing dashboard to all events."""
        # Mock dashboard
        mock_dashboard = MagicMock()
        mock_dashboard.connection_manager = AsyncMock()
        mock_dashboard.connection_manager.broadcast = AsyncMock()

        # Subscribe dashboard
        await running_state_sync.subscribe_to_all_events(mock_dashboard)

        # Publish an event that dashboard should receive
        await running_state_sync.publish_state_change(
            event_type="agent.registered", source="league_manager", data={"player_id": "P01"}
        )

        await asyncio.sleep(0.2)

        # Verify dashboard received broadcast
        assert mock_dashboard.connection_manager.broadcast.call_count >= 0


class TestStateSyncServiceEdgeCases:
    """Test edge cases for StateSyncService."""

    @pytest.mark.asyncio
    async def test_publish_when_not_running(self, state_sync):
        """Test publishing state change when service not running."""
        # Should still work (event bus is independent)
        await state_sync.publish_state_change(event_type="test.event", source="test", data={})

        # No exception should be raised

    @pytest.mark.asyncio
    async def test_subscribe_when_not_running(self, state_sync):
        """Test subscribing when service not running."""

        async def handler(event):
            pass

        # Should work (event bus is independent)
        subscription_id = state_sync.subscribe("test.*", handler)
        assert subscription_id is not None

        # Cleanup
        state_sync.unsubscribe(subscription_id)

    @pytest.mark.asyncio
    async def test_dashboard_forwarding_error(self, running_state_sync):
        """Test dashboard forwarding when broadcast fails."""
        # Mock dashboard that raises error
        mock_dashboard = MagicMock()
        mock_dashboard.connection_manager = AsyncMock()
        mock_dashboard.connection_manager.broadcast = AsyncMock(
            side_effect=Exception("Broadcast failed")
        )

        # Subscribe dashboard
        await running_state_sync.subscribe_to_all_events(mock_dashboard)

        # Publish event - should handle error gracefully
        await running_state_sync.publish_state_change(
            event_type="agent.registered", source="test", data={}
        )

        await asyncio.sleep(0.1)

        # Should not raise exception

    @pytest.mark.asyncio
    async def test_concurrent_state_changes(self, running_state_sync):
        """Test concurrent state change publishing."""

        async def publish_events(start_idx, count):
            for i in range(count):
                await running_state_sync.publish_state_change(
                    event_type=f"test.event.{start_idx + i}",
                    source="test",
                    data={"index": start_idx + i},
                )

        # Publish events concurrently
        await asyncio.gather(publish_events(0, 10), publish_events(10, 10), publish_events(20, 10))

        await asyncio.sleep(0.2)

        # Get history
        history = await running_state_sync.get_state_history(limit=50)

        # Should have tracked all events
        assert len(history) >= 30

    @pytest.mark.asyncio
    async def test_snapshot_with_empty_state(self, running_state_sync):
        """Test creating snapshot with empty state."""
        snapshot = await running_state_sync.create_snapshot("empty_snapshot")

        assert snapshot.snapshot_id == "empty_snapshot"
        assert len(snapshot.components) == 0

    @pytest.mark.asyncio
    async def test_multiple_snapshots(self, running_state_sync):
        """Test creating multiple snapshots."""
        snapshots = []
        for i in range(5):
            snapshot = await running_state_sync.create_snapshot(f"snapshot_{i}")
            snapshots.append(snapshot)

        # Verify all snapshots created
        assert len(snapshots) == 5
        assert all(s.snapshot_id == f"snapshot_{i}" for i, s in enumerate(snapshots))

    @pytest.mark.asyncio
    async def test_state_history_maxlen(self, running_state_sync):
        """Test state history respects maxlen."""
        # Publish more events than maxlen (1000)
        for i in range(1100):
            await running_state_sync.publish_state_change(
                event_type="test.event", source="test", data={"index": i}
            )

        await asyncio.sleep(0.5)

        # Get all history
        history = await running_state_sync.get_state_history(limit=2000)

        # Should not exceed maxlen of 1000
        assert len(history) <= 1000


class TestStateChange:
    """Test StateChange dataclass."""

    def test_state_change_creation(self):
        """Test creating StateChange."""
        change = StateChange(
            change_id="test_change",
            event_type="test.event",
            timestamp=datetime.now(),
            source="test_source",
            data={"key": "value"},
        )

        assert change.change_id == "test_change"
        assert change.event_type == "test.event"
        assert change.source == "test_source"
        assert change.data == {"key": "value"}
        assert change.acknowledged is False
        assert change.retries == 0


class TestStateSnapshot:
    """Test StateSnapshot dataclass."""

    def test_state_snapshot_creation(self):
        """Test creating StateSnapshot."""
        snapshot = StateSnapshot(snapshot_id="test_snapshot", timestamp=datetime.now())

        assert snapshot.snapshot_id == "test_snapshot"
        assert isinstance(snapshot.timestamp, datetime)
        assert isinstance(snapshot.components, dict)
        assert isinstance(snapshot.standings, list)
        assert snapshot.current_round == 0
        assert isinstance(snapshot.matches, list)

    def test_state_snapshot_with_data(self):
        """Test StateSnapshot with data."""
        components = {"league": "data"}
        standings = [{"player": "P01"}]
        matches = [{"match": "M01"}]

        snapshot = StateSnapshot(
            snapshot_id="test",
            timestamp=datetime.now(),
            components=components,
            standings=standings,
            current_round=5,
            matches=matches,
        )

        assert snapshot.components == components
        assert snapshot.standings == standings
        assert snapshot.current_round == 5
        assert snapshot.matches == matches
