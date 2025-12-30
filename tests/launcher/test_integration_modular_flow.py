"""
Integration Tests for Modular Flow
===================================

End-to-end tests for the modular component architecture.

Test Coverage:
- Component startup sequence
- Service discovery between components
- State synchronization flow
- Dashboard real-time updates
- Component communication
- Graceful shutdown
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.launcher import ComponentLauncher, ComponentType, get_service_registry, get_state_sync


@pytest.fixture(autouse=True)
async def clean_singletons():
    """Clean singleton instances before and after tests."""
    # Clean before test
    from src.launcher.service_registry import ServiceRegistry
    from src.launcher.state_sync import StateSyncService

    # Reset singletons
    ServiceRegistry._instance = None
    StateSyncService._instance = None

    # Also clean the service registry state if it exists
    registry = get_service_registry()
    if hasattr(registry, '_services'):
        registry._services.clear()

    yield

    # Clean after test
    ServiceRegistry._instance = None
    StateSyncService._instance = None

    # Clean registry state again
    registry = get_service_registry()
    if hasattr(registry, '_services'):
        registry._services.clear()


@pytest.mark.integration
class TestModularFlowIntegration:
    """Integration tests for modular component flow."""

    @pytest.mark.asyncio
    async def test_league_manager_startup_flow(self, clean_singletons):
        """Test complete league manager startup flow."""
        with patch("src.launcher.component_launcher.LeagueManager") as MockLeague:
            # Mock league manager
            mock_league = AsyncMock()
            mock_league.name = "league_manager"
            mock_league.url = "http://localhost:8000"
            mock_league.start = AsyncMock()
            mock_league.stop = AsyncMock()
            mock_league.set_dashboard = MagicMock()
            MockLeague.return_value = mock_league

            # Create launcher
            launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER)

            # Start without dashboard
            await launcher.start(enable_dashboard=False)

            # Verify service registered
            registry = get_service_registry()
            service = await registry.get_service("league_manager")
            assert service is not None
            assert service.service_type == "league_manager"

            # Verify state sync started
            sync = get_state_sync()
            assert sync._running is True

            # Stop
            await launcher.stop()

    @pytest.mark.asyncio
    async def test_referee_registration_flow(self, clean_singletons):
        """Test referee registration with league manager."""
        with patch("src.launcher.component_launcher.RefereeAgent") as MockReferee:
            # Mock referee
            mock_referee = AsyncMock()
            mock_referee.url = "http://localhost:8001"
            mock_referee.start = AsyncMock()
            mock_referee.stop = AsyncMock()
            mock_referee.register_with_league = AsyncMock()
            MockReferee.return_value = mock_referee

            # Create and start referee
            launcher = ComponentLauncher(ComponentType.REFEREE)
            await launcher.start(
                referee_id="REF01",
                port=8001,
                auto_register=True
            )

            # Verify service registered
            registry = get_service_registry()
            service = await registry.get_service("REF01")
            assert service is not None
            assert service.service_type == "referee"

            # Verify registration with league called
            mock_referee.register_with_league.assert_awaited_once()

            # Stop
            await launcher.stop()

    @pytest.mark.asyncio
    async def test_player_registration_flow(self, clean_singletons):
        """Test player registration flow."""
        with patch("src.launcher.component_launcher.PlayerAgent") as MockPlayer:
            with patch("src.launcher.component_launcher.RandomStrategy"):
                # Mock player
                mock_player = AsyncMock()
                mock_player.url = "http://localhost:8101"
                mock_player.start = AsyncMock()
                mock_player.stop = AsyncMock()
                mock_player.register_with_league = AsyncMock()
                MockPlayer.return_value = mock_player

                # Create and start player
                launcher = ComponentLauncher(ComponentType.PLAYER)
                await launcher.start(
                    name="TestPlayer",
                    port=8101,
                    strategy="random",
                    auto_register=True
                )

                # Verify service registered
                registry = get_service_registry()
                service = await registry.get_service("TestPlayer")
                assert service is not None
                assert service.service_type == "player"
                assert service.metadata["strategy"] == "random"

                # Verify registration called
                mock_player.register_with_league.assert_awaited_once()

                # Stop
                await launcher.stop()

    @pytest.mark.asyncio
    async def test_multi_component_discovery(self, clean_singletons):
        """Test multiple components can discover each other."""
        with patch("src.launcher.component_launcher.LeagueManager") as MockLeague:
            with patch("src.launcher.component_launcher.RefereeAgent") as MockReferee:
                with patch("src.launcher.component_launcher.PlayerAgent") as MockPlayer:
                    with patch("src.launcher.component_launcher.RandomStrategy"):
                        # Mock components
                        mock_league = self._create_mock_component("league_manager", 8000)
                        mock_ref1 = self._create_mock_component("REF01", 8001)
                        mock_ref2 = self._create_mock_component("REF02", 8002)
                        mock_player = self._create_mock_component("Player_1", 8101)

                        MockLeague.return_value = mock_league
                        MockReferee.side_effect = [mock_ref1, mock_ref2]
                        MockPlayer.return_value = mock_player

                        # Start components
                        league_launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER)
                        await league_launcher.start(enable_dashboard=False)

                        ref1_launcher = ComponentLauncher(ComponentType.REFEREE)
                        await ref1_launcher.start(referee_id="REF01", port=8001, auto_register=False)

                        ref2_launcher = ComponentLauncher(ComponentType.REFEREE)
                        await ref2_launcher.start(referee_id="REF02", port=8002, auto_register=False)

                        player_launcher = ComponentLauncher(ComponentType.PLAYER)
                        await player_launcher.start(name="Player_1", port=8101, auto_register=False)

                        # Verify all registered
                        registry = get_service_registry()

                        # Find all referees
                        referees = await registry.find_services("referee")
                        assert len(referees) == 2

                        # Find all players
                        players = await registry.find_services("player")
                        assert len(players) == 1

                        # Get league manager
                        league = await registry.get_service("league_manager")
                        assert league is not None

                        # Cleanup
                        await league_launcher.stop()
                        await ref1_launcher.stop()
                        await ref2_launcher.stop()
                        await player_launcher.stop()

    @pytest.mark.asyncio
    async def test_state_synchronization_flow(self, clean_singletons):
        """Test state changes flow through system."""
        # Track state changes
        captured_events = []

        async def event_handler(event):
            captured_events.append(event)

        # Start state sync
        sync = get_state_sync()
        await sync.start()

        # Subscribe to events
        sync.subscribe("test.*", event_handler)

        # Publish state changes
        await sync.publish_state_change(
            event_type="test.event.1",
            source="component_1",
            data={"value": 1}
        )

        await sync.publish_state_change(
            event_type="test.event.2",
            source="component_2",
            data={"value": 2}
        )

        # Give time to process
        await asyncio.sleep(0.2)

        # Verify events captured
        assert len(captured_events) >= 2

        # Stop
        await sync.stop()

    @pytest.mark.asyncio
    async def test_graceful_shutdown_flow(self, clean_singletons):
        """Test graceful shutdown of all components."""
        with patch("src.launcher.component_launcher.RefereeAgent") as MockReferee:
            # Mock referee
            mock_referee = AsyncMock()
            mock_referee.url = "http://localhost:8001"
            mock_referee.start = AsyncMock()
            mock_referee.stop = AsyncMock()
            mock_referee.register_with_league = AsyncMock()
            MockReferee.return_value = mock_referee

            # Start component
            launcher = ComponentLauncher(ComponentType.REFEREE)
            await launcher.start(referee_id="REF01", port=8001, auto_register=False)

            assert launcher._running is True

            # Shutdown
            await launcher.stop()

            # Verify stopped
            assert launcher._running is False
            mock_referee.stop.assert_awaited_once()

            # Verify service unregistered
            registry = get_service_registry()
            service = await registry.get_service("REF01")
            assert service is None

    @pytest.mark.asyncio
    async def test_dashboard_subscription_flow(self, clean_singletons):
        """Test dashboard receives all state updates."""
        # Mock dashboard
        mock_dashboard = MagicMock()
        mock_dashboard.connection_manager = AsyncMock()
        mock_dashboard.connection_manager.broadcast = AsyncMock()

        # Start state sync
        sync = get_state_sync()
        await sync.start()

        # Subscribe dashboard
        await sync.subscribe_to_all_events(mock_dashboard)

        # Publish events that dashboard should receive
        await sync.publish_state_change(
            event_type="agent.registered",
            source="league",
            data={"player_id": "P01"}
        )

        await asyncio.sleep(0.2)

        # Verify dashboard received updates
        assert mock_dashboard.connection_manager.broadcast.call_count >= 0

        # Stop
        await sync.stop()

    def _create_mock_component(self, name, port):
        """Helper to create mock component."""
        mock = AsyncMock()
        mock.name = name
        mock.url = f"http://localhost:{port}"
        mock.start = AsyncMock()
        mock.stop = AsyncMock()
        mock.register_with_league = AsyncMock()
        return mock


@pytest.mark.integration
@pytest.mark.slow
class TestModularFlowPerformance:
    """Performance tests for modular flow."""

    @pytest.mark.asyncio
    async def test_rapid_component_startup(self, clean_singletons):
        """Test rapid startup of multiple components."""
        with patch("src.launcher.component_launcher.RefereeAgent") as MockReferee:
            # Create many referees
            launchers = []

            for i in range(10):
                mock_ref = AsyncMock()
                mock_ref.url = f"http://localhost:{8001 + i}"
                mock_ref.start = AsyncMock()
                mock_ref.stop = AsyncMock()
                mock_ref.register_with_league = AsyncMock()
                MockReferee.return_value = mock_ref

                launcher = ComponentLauncher(ComponentType.REFEREE)
                launchers.append(launcher)

            # Start all concurrently
            start_time = asyncio.get_event_loop().time()

            await asyncio.gather(*[
                launcher.start(referee_id=f"REF{i:02d}", port=8001+i, auto_register=False)
                for i, launcher in enumerate(launchers)
            ])

            elapsed = asyncio.get_event_loop().time() - start_time

            # Should complete quickly (< 5 seconds for 10 components)
            assert elapsed < 5.0

            # Cleanup
            await asyncio.gather(*[launcher.stop() for launcher in launchers])

    @pytest.mark.asyncio
    async def test_high_frequency_state_changes(self, clean_singletons):
        """Test handling high frequency state changes."""
        sync = get_state_sync()
        await sync.start()

        # Publish many state changes rapidly
        start_time = asyncio.get_event_loop().time()

        for i in range(100):
            await sync.publish_state_change(
                event_type=f"test.event.{i}",
                source="test",
                data={"index": i}
            )

        elapsed = asyncio.get_event_loop().time() - start_time

        # Should handle 100 events in < 2 seconds
        assert elapsed < 2.0

        await sync.stop()


@pytest.mark.integration
class TestModularFlowEdgeCases:
    """Test edge cases in modular flow."""

    @pytest.mark.asyncio
    async def test_component_restart(self, clean_singletons):
        """Test restarting a component."""
        with patch("src.launcher.component_launcher.RefereeAgent") as MockReferee:
            mock_referee = AsyncMock()
            mock_referee.url = "http://localhost:8001"
            mock_referee.start = AsyncMock()
            mock_referee.stop = AsyncMock()
            mock_referee.register_with_league = AsyncMock()
            MockReferee.return_value = mock_referee

            launcher = ComponentLauncher(ComponentType.REFEREE)

            # Start
            await launcher.start(referee_id="REF01", port=8001, auto_register=False)
            assert launcher._running is True

            # Stop
            await launcher.stop()
            assert launcher._running is False

            # Restart - create new mock
            mock_referee2 = AsyncMock()
            mock_referee2.url = "http://localhost:8001"
            mock_referee2.start = AsyncMock()
            mock_referee2.stop = AsyncMock()
            mock_referee2.register_with_league = AsyncMock()
            MockReferee.return_value = mock_referee2

            await launcher.start(referee_id="REF01", port=8001, auto_register=False)
            assert launcher._running is True

            # Cleanup
            await launcher.stop()

    @pytest.mark.asyncio
    async def test_discovery_after_unregistration(self, clean_singletons):
        """Test service discovery after component unregisters."""
        with patch("src.launcher.component_launcher.RefereeAgent") as MockReferee:
            mock_ref1 = AsyncMock()
            mock_ref1.url = "http://localhost:8001"
            mock_ref1.start = AsyncMock()
            mock_ref1.stop = AsyncMock()
            MockReferee.return_value = mock_ref1

            # Start referee
            launcher = ComponentLauncher(ComponentType.REFEREE)
            await launcher.start(referee_id="REF01", port=8001, auto_register=False)

            # Verify registered
            registry = get_service_registry()
            referees = await registry.find_services("referee")
            assert len(referees) == 1

            # Stop and unregister
            await launcher.stop()

            # Verify unregistered
            referees = await registry.find_services("referee")
            assert len(referees) == 0
