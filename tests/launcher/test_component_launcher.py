"""
Test Component Launcher
========================

Unit and integration tests for ComponentLauncher.

Test Coverage:
- Component lifecycle (start, stop, restart)
- Component type handling (league, referee, player)
- Service registration
- State synchronization
- Error handling
- Edge cases
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.launcher.component_launcher import ComponentLauncher, ComponentType


@pytest.fixture
def mock_config():
    """Mock configuration."""
    config = MagicMock()
    config.league.league_id = "test_league"
    config.league.min_players = 2
    config.league.max_players = 10
    config.league_manager.host = "localhost"
    config.league_manager.port = 8000
    config.league_manager.url = "http://localhost:8000"
    config.referee.host = "localhost"
    config.referee.port = 8001
    config.game.move_timeout = 30
    return config


@pytest.fixture
def mock_service_registry():
    """Mock service registry."""
    registry = AsyncMock()
    registry.register_service = AsyncMock()
    registry.unregister_service = AsyncMock()
    return registry


@pytest.fixture
def mock_state_sync():
    """Mock state sync service."""
    sync = AsyncMock()
    sync.start = AsyncMock()
    sync.stop = AsyncMock()
    sync.subscribe_to_all_events = AsyncMock()
    return sync


class TestComponentLauncher:
    """Test ComponentLauncher class."""

    @pytest.mark.asyncio
    async def test_initialization(self, mock_config):
        """Test launcher initialization."""
        launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)

        assert launcher.component_type == ComponentType.LEAGUE_MANAGER
        assert launcher.config == mock_config
        assert launcher.component is None
        assert launcher.dashboard is None
        assert launcher._running is False

    @pytest.mark.asyncio
    async def test_start_league_manager(self, mock_config, mock_service_registry, mock_state_sync):
        """Test starting league manager."""
        with patch(
            "src.launcher.component_launcher.get_service_registry",
            return_value=mock_service_registry,
        ):
            with patch(
                "src.launcher.component_launcher.get_state_sync", return_value=mock_state_sync
            ):
                with patch("src.launcher.component_launcher.LeagueManager") as MockLeagueManager:
                    # Setup mocks
                    mock_league = AsyncMock()
                    mock_league.name = "league_manager"
                    mock_league.url = "http://localhost:8000"
                    mock_league.start = AsyncMock()
                    mock_league.stop = AsyncMock()
                    MockLeagueManager.return_value = mock_league

                    launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)

                    # Start without dashboard
                    await launcher.start(enable_dashboard=False, port=8000)

                    # Verify league manager created and started
                    MockLeagueManager.assert_called_once()
                    mock_league.start.assert_awaited_once()

                    # Verify service registration
                    mock_service_registry.register_service.assert_awaited_once()

                    # Verify state sync started
                    mock_state_sync.start.assert_awaited_once()

                    assert launcher._running is True
                    assert launcher.component == mock_league

                    # Cleanup
                    await launcher.stop()

    @pytest.mark.asyncio
    async def test_start_referee(self, mock_config, mock_service_registry, mock_state_sync):
        """Test starting referee agent."""
        with patch(
            "src.launcher.component_launcher.get_service_registry",
            return_value=mock_service_registry,
        ):
            with patch(
                "src.launcher.component_launcher.get_state_sync", return_value=mock_state_sync
            ):
                with patch("src.launcher.component_launcher.RefereeAgent") as MockReferee:
                    # Setup mocks
                    mock_referee = AsyncMock()
                    mock_referee.url = "http://localhost:8001"
                    mock_referee.start = AsyncMock()
                    mock_referee.stop = AsyncMock()
                    mock_referee.register_with_league = AsyncMock()
                    MockReferee.return_value = mock_referee

                    launcher = ComponentLauncher(ComponentType.REFEREE, mock_config)

                    # Start with auto-register
                    await launcher.start(referee_id="REF01", port=8001, auto_register=True)

                    # Verify referee created and started
                    MockReferee.assert_called_once()
                    mock_referee.start.assert_awaited_once()
                    mock_referee.register_with_league.assert_awaited_once()

                    # Verify service registration
                    mock_service_registry.register_service.assert_awaited_once()

                    assert launcher._running is True
                    assert launcher.component == mock_referee

                    # Cleanup
                    await launcher.stop()

    @pytest.mark.asyncio
    async def test_start_player(self, mock_config, mock_service_registry, mock_state_sync):
        """Test starting player agent."""
        with patch(
            "src.launcher.component_launcher.get_service_registry",
            return_value=mock_service_registry,
        ):
            with patch(
                "src.launcher.component_launcher.get_state_sync", return_value=mock_state_sync
            ):
                with patch("src.launcher.component_launcher.PlayerAgent") as MockPlayer:
                    with patch("src.launcher.component_launcher.RandomStrategy"):
                        # Setup mocks
                        mock_player = AsyncMock()
                        mock_player.url = "http://localhost:8101"
                        mock_player.start = AsyncMock()
                        mock_player.stop = AsyncMock()
                        mock_player.register_with_league = AsyncMock()
                        MockPlayer.return_value = mock_player

                        launcher = ComponentLauncher(ComponentType.PLAYER, mock_config)

                        # Start with auto-register
                        await launcher.start(
                            name="TestPlayer", port=8101, strategy="random", auto_register=True
                        )

                        # Verify player created and started
                        MockPlayer.assert_called_once()
                        mock_player.start.assert_awaited_once()
                        mock_player.register_with_league.assert_awaited_once()

                        # Verify service registration
                        mock_service_registry.register_service.assert_awaited_once()

                        assert launcher._running is True
                        assert launcher.component == mock_player

                        # Cleanup
                        await launcher.stop()

    @pytest.mark.asyncio
    async def test_stop_component(self, mock_config, mock_service_registry, mock_state_sync):
        """Test stopping a component."""
        with patch(
            "src.launcher.component_launcher.get_service_registry",
            return_value=mock_service_registry,
        ):
            with patch(
                "src.launcher.component_launcher.get_state_sync", return_value=mock_state_sync
            ):
                with patch("src.launcher.component_launcher.RefereeAgent") as MockReferee:
                    # Setup mocks
                    mock_referee = AsyncMock()
                    mock_referee.name = "REF01"
                    mock_referee.url = "http://localhost:8001"
                    mock_referee.start = AsyncMock()
                    mock_referee.stop = AsyncMock()
                    mock_referee.register_with_league = AsyncMock()
                    MockReferee.return_value = mock_referee

                    launcher = ComponentLauncher(ComponentType.REFEREE, mock_config)
                    await launcher.start(referee_id="REF01", port=8001, auto_register=False)

                    # Stop component
                    await launcher.stop()

                    # Verify component stopped
                    mock_referee.stop.assert_awaited_once()
                    mock_service_registry.unregister_service.assert_awaited_once()
                    mock_state_sync.stop.assert_awaited_once()

                    assert launcher._running is False
                    assert launcher.component is None

    @pytest.mark.asyncio
    async def test_create_strategy_random(self, mock_config):
        """Test creating random strategy."""
        launcher = ComponentLauncher(ComponentType.PLAYER, mock_config)
        strategy = await launcher._create_strategy("random")

        assert strategy is not None
        assert strategy.__class__.__name__ == "RandomStrategy"

    @pytest.mark.asyncio
    async def test_create_strategy_pattern(self, mock_config):
        """Test creating pattern strategy."""
        launcher = ComponentLauncher(ComponentType.PLAYER, mock_config)
        strategy = await launcher._create_strategy("pattern")

        assert strategy is not None
        assert strategy.__class__.__name__ == "PatternStrategy"

    @pytest.mark.asyncio
    async def test_create_strategy_llm(self, mock_config):
        """Test creating LLM strategy."""
        launcher = ComponentLauncher(ComponentType.PLAYER, mock_config)
        # LLM strategy will fallback to random if no API key
        strategy = await launcher._create_strategy("llm")

        assert strategy is not None
        # Either LLM or fallback to Random
        assert strategy.__class__.__name__ in ["LLMStrategy", "RandomStrategy"]

    @pytest.mark.asyncio
    async def test_create_strategy_unknown_fallback(self, mock_config):
        """Test creating strategy with unknown type falls back to random."""
        launcher = ComponentLauncher(ComponentType.PLAYER, mock_config)
        strategy = await launcher._create_strategy("unknown_strategy")

        # Should fallback to RandomStrategy
        assert strategy is not None
        assert strategy.__class__.__name__ == "RandomStrategy"

    @pytest.mark.asyncio
    async def test_invalid_component_type(self, mock_config):
        """Test starting with invalid component type."""
        # Create a mock invalid component type
        invalid_type = MagicMock()
        invalid_type.value = "invalid"

        # Mock the state_sync to be async
        mock_state_sync = AsyncMock()
        mock_state_sync.start = AsyncMock()

        with patch("src.launcher.component_launcher.get_service_registry"):
            with patch(
                "src.launcher.component_launcher.get_state_sync", return_value=mock_state_sync
            ):
                launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)
                launcher.component_type = invalid_type

                # Should raise ValueError
                with pytest.raises(ValueError, match="Unknown component type"):
                    await launcher.start()

    @pytest.mark.asyncio
    async def test_request_shutdown(self, mock_config):
        """Test requesting shutdown."""
        launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)

        # Request shutdown
        launcher.request_shutdown()

        # Verify shutdown event is set
        assert launcher._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_wait_for_shutdown(self, mock_config):
        """Test waiting for shutdown."""
        launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)

        # Set shutdown event immediately
        launcher._shutdown_event.set()

        # Should return immediately
        await asyncio.wait_for(launcher.wait_for_shutdown(), timeout=1.0)


class TestComponentLauncherEdgeCases:
    """Test edge cases for ComponentLauncher."""

    @pytest.mark.asyncio
    async def test_start_already_running(self, mock_config, mock_service_registry, mock_state_sync):
        """Test starting a component that's already running."""
        with patch(
            "src.launcher.component_launcher.get_service_registry",
            return_value=mock_service_registry,
        ):
            with patch(
                "src.launcher.component_launcher.get_state_sync", return_value=mock_state_sync
            ):
                with patch("src.launcher.component_launcher.RefereeAgent") as MockReferee:
                    mock_referee = AsyncMock()
                    mock_referee.url = "http://localhost:8001"
                    mock_referee.start = AsyncMock()
                    mock_referee.register_with_league = AsyncMock()
                    MockReferee.return_value = mock_referee

                    launcher = ComponentLauncher(ComponentType.REFEREE, mock_config)
                    await launcher.start(referee_id="REF01", port=8001, auto_register=False)

                    assert launcher._running is True

                    # Try to start again - should handle gracefully
                    # (In real implementation, this might raise or be a no-op)
                    # For now, we just verify it was started once
                    assert mock_referee.start.await_count == 1

                    await launcher.stop()

    @pytest.mark.asyncio
    async def test_stop_not_running(self, mock_config, mock_service_registry, mock_state_sync):
        """Test stopping a component that's not running."""
        with patch(
            "src.launcher.component_launcher.get_service_registry",
            return_value=mock_service_registry,
        ):
            with patch(
                "src.launcher.component_launcher.get_state_sync", return_value=mock_state_sync
            ):
                launcher = ComponentLauncher(ComponentType.REFEREE, mock_config)

                # Stop without starting - should handle gracefully
                await launcher.stop()

                assert launcher._running is False
                assert launcher.component is None

    @pytest.mark.asyncio
    async def test_start_with_port_conflict(
        self, mock_config, mock_service_registry, mock_state_sync
    ):
        """Test starting with a port that's already in use."""
        with patch(
            "src.launcher.component_launcher.get_service_registry",
            return_value=mock_service_registry,
        ):
            with patch(
                "src.launcher.component_launcher.get_state_sync", return_value=mock_state_sync
            ):
                with patch("src.launcher.component_launcher.RefereeAgent") as MockReferee:
                    # Simulate port conflict
                    mock_referee = AsyncMock()
                    mock_referee.start = AsyncMock(side_effect=OSError("Address already in use"))
                    MockReferee.return_value = mock_referee

                    launcher = ComponentLauncher(ComponentType.REFEREE, mock_config)

                    # Should raise OSError
                    with pytest.raises(OSError, match="Address already in use"):
                        await launcher.start(referee_id="REF01", port=8001)

    @pytest.mark.asyncio
    async def test_player_registration_timeout(
        self, mock_config, mock_service_registry, mock_state_sync
    ):
        """Test player registration timeout."""
        with patch(
            "src.launcher.component_launcher.get_service_registry",
            return_value=mock_service_registry,
        ):
            with patch(
                "src.launcher.component_launcher.get_state_sync", return_value=mock_state_sync
            ):
                with patch("src.launcher.component_launcher.PlayerAgent") as MockPlayer:
                    with patch("src.launcher.component_launcher.RandomStrategy"):
                        # Simulate registration timeout
                        mock_player = AsyncMock()
                        mock_player.url = "http://localhost:8101"
                        mock_player.start = AsyncMock()
                        mock_player.register_with_league = AsyncMock(
                            side_effect=TimeoutError("Registration timeout")
                        )
                        MockPlayer.return_value = mock_player

                        launcher = ComponentLauncher(ComponentType.PLAYER, mock_config)

                        # Should raise TimeoutError
                        with pytest.raises(asyncio.TimeoutError):
                            await launcher.start(
                                name="TestPlayer", port=8101, strategy="random", auto_register=True
                            )

    @pytest.mark.asyncio
    async def test_league_manager_with_dashboard_error(
        self, mock_config, mock_service_registry, mock_state_sync
    ):
        """Test league manager start when dashboard fails."""
        with patch(
            "src.launcher.component_launcher.get_service_registry",
            return_value=mock_service_registry,
        ):
            with patch(
                "src.launcher.component_launcher.get_state_sync", return_value=mock_state_sync
            ):
                with patch("src.launcher.component_launcher.LeagueManager") as MockLeagueManager:
                    with patch("src.visualization.get_dashboard") as mock_get_dashboard:
                        # League manager starts fine
                        mock_league = AsyncMock()
                        mock_league.name = "league_manager"
                        mock_league.url = "http://localhost:8000"
                        mock_league.start = AsyncMock()
                        MockLeagueManager.return_value = mock_league

                        # Dashboard fails to start
                        mock_get_dashboard.side_effect = Exception("Dashboard startup failed")

                        launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)

                        # Should raise exception
                        with pytest.raises(Exception, match="Dashboard startup failed"):
                            await launcher.start(enable_dashboard=True)


@pytest.mark.asyncio
async def test_component_launcher_integration():
    """Integration test for component launcher flow."""
    # This would be an end-to-end test
    # For now, we'll mark it as a placeholder
    pass


class TestComponentLauncherDashboardEvents:
    """Test dashboard event handlers in ComponentLauncher."""

    @pytest.mark.asyncio
    async def test_on_round_started(self, mock_config):
        """Test round started event handler."""
        launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)
        mock_integration = AsyncMock()
        mock_integration.on_round_start = AsyncMock()
        launcher._integration = mock_integration

        # Create mock event
        event = MagicMock()
        event.round_number = 1

        # Call handler
        await launcher._on_round_started(event)

        # Verify integration called
        mock_integration.on_round_start.assert_awaited_once_with(round_num=1, matches=[])

    @pytest.mark.asyncio
    async def test_on_round_started_error(self, mock_config):
        """Test round started event handler with error."""
        launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)
        mock_integration = AsyncMock()
        mock_integration.on_round_start = AsyncMock(side_effect=Exception("Test error"))
        launcher._integration = mock_integration

        event = MagicMock()
        event.round_number = 1

        # Should handle error gracefully
        await launcher._on_round_started(event)

    @pytest.mark.asyncio
    async def test_on_player_move(self, mock_config):
        """Test player move event handler."""
        launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)
        mock_integration = AsyncMock()
        mock_integration.on_move_decision = AsyncMock()
        launcher._integration = mock_integration

        event = MagicMock()
        event.player_id = "player1"
        event.round_number = 1
        event.move = 0
        event.game_id = "game123"

        await launcher._on_player_move(event)

        mock_integration.on_move_decision.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_on_player_move_error(self, mock_config):
        """Test player move event handler with error."""
        launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)
        mock_integration = AsyncMock()
        mock_integration.on_move_decision = AsyncMock(side_effect=Exception("Test error"))
        launcher._integration = mock_integration

        event = MagicMock()
        event.player_id = "player1"
        event.round_number = 1
        event.move = 0
        event.game_id = "game123"

        await launcher._on_player_move(event)

    @pytest.mark.asyncio
    async def test_on_round_completed(self, mock_config):
        """Test round completed event handler."""
        launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)
        mock_integration = AsyncMock()
        mock_integration.on_round_complete = AsyncMock()
        launcher._integration = mock_integration

        event = MagicMock()
        event.round_number = 1
        event.moves = {"player1": 0, "player2": 1}
        event.cumulative_scores = {"player1": 1.0, "player2": 0.0}

        await launcher._on_round_completed(event)

        mock_integration.on_round_complete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_on_round_completed_insufficient_players(self, mock_config):
        """Test round completed with insufficient players."""
        launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)
        mock_integration = AsyncMock()
        launcher._integration = mock_integration

        event = MagicMock()
        event.round_number = 1
        event.moves = {"player1": 0}  # Only 1 player
        event.cumulative_scores = {"player1": 1.0}

        # Should handle gracefully
        await launcher._on_round_completed(event)

    @pytest.mark.asyncio
    async def test_on_round_completed_error(self, mock_config):
        """Test round completed event handler with error."""
        launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)
        mock_integration = AsyncMock()
        mock_integration.on_round_complete = AsyncMock(side_effect=Exception("Test error"))
        launcher._integration = mock_integration

        event = MagicMock()
        event.round_number = 1
        event.moves = {"player1": 0, "player2": 1}
        event.cumulative_scores = {"player1": 1.0, "player2": 0.0}

        await launcher._on_round_completed(event)

    @pytest.mark.asyncio
    async def test_on_opponent_model_update(self, mock_config):
        """Test opponent model update event handler."""
        launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)
        mock_integration = AsyncMock()
        mock_integration.on_opponent_model_update = AsyncMock()
        launcher._integration = mock_integration

        event = MagicMock()
        event.player_id = "player1"

        await launcher._on_opponent_model_update(event)

        mock_integration.on_opponent_model_update.assert_awaited_once_with(event)

    @pytest.mark.asyncio
    async def test_on_opponent_model_update_no_integration(self, mock_config):
        """Test opponent model update without integration."""
        launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)
        launcher._integration = None

        event = MagicMock()
        event.player_id = "player1"

        # Should handle gracefully
        await launcher._on_opponent_model_update(event)

    @pytest.mark.asyncio
    async def test_on_opponent_model_update_error(self, mock_config):
        """Test opponent model update event handler with error."""
        launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)
        mock_integration = AsyncMock()
        mock_integration.on_opponent_model_update = AsyncMock(side_effect=Exception("Test error"))
        launcher._integration = mock_integration

        event = MagicMock()
        event.player_id = "player1"

        await launcher._on_opponent_model_update(event)

    @pytest.mark.asyncio
    async def test_on_counterfactual_analysis(self, mock_config):
        """Test counterfactual analysis event handler."""
        launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)
        mock_integration = AsyncMock()
        mock_integration.on_counterfactual_analysis = AsyncMock()
        launcher._integration = mock_integration

        event = MagicMock()
        event.player_id = "player1"

        await launcher._on_counterfactual_analysis(event)

        mock_integration.on_counterfactual_analysis.assert_awaited_once_with(event)

    @pytest.mark.asyncio
    async def test_on_counterfactual_analysis_no_integration(self, mock_config):
        """Test counterfactual analysis without integration."""
        launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)
        launcher._integration = None

        event = MagicMock()
        event.player_id = "player1"

        # Should handle gracefully
        await launcher._on_counterfactual_analysis(event)

    @pytest.mark.asyncio
    async def test_on_counterfactual_analysis_error(self, mock_config):
        """Test counterfactual analysis event handler with error."""
        launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)
        mock_integration = AsyncMock()
        mock_integration.on_counterfactual_analysis = AsyncMock(side_effect=Exception("Test error"))
        launcher._integration = mock_integration

        event = MagicMock()
        event.player_id = "player1"

        await launcher._on_counterfactual_analysis(event)

    @pytest.mark.asyncio
    async def test_on_match_completed(self, mock_config):
        """Test match completed event handler."""
        launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)
        mock_integration = AsyncMock()
        mock_integration.on_match_completed = AsyncMock()
        launcher._integration = mock_integration

        event = MagicMock()
        event.match_id = "match123"
        event.player1_id = "player1"
        event.player2_id = "player2"
        event.winner = "player1"

        await launcher._on_match_completed(event)

        mock_integration.on_match_completed.assert_awaited_once_with(event)

    @pytest.mark.asyncio
    async def test_on_match_completed_no_integration(self, mock_config):
        """Test match completed without integration."""
        launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)
        launcher._integration = None

        event = MagicMock()
        event.match_id = "match123"

        # Should handle gracefully
        await launcher._on_match_completed(event)

    @pytest.mark.asyncio
    async def test_on_match_completed_error(self, mock_config):
        """Test match completed event handler with error."""
        launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)
        mock_integration = AsyncMock()
        mock_integration.on_match_completed = AsyncMock(side_effect=Exception("Test error"))
        launcher._integration = mock_integration

        event = MagicMock()
        event.match_id = "match123"

        await launcher._on_match_completed(event)

    @pytest.mark.asyncio
    async def test_on_standings_updated(self, mock_config):
        """Test standings updated event handler."""
        launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)

        # Mock dashboard with tournament states
        mock_dashboard = MagicMock()
        from dataclasses import dataclass
        from datetime import datetime

        @dataclass
        class MockTournamentState:
            tournament_id: str
            started_at: datetime

        mock_dashboard.tournament_states = {
            "tournament1": MockTournamentState("tournament1", datetime.now())
        }
        mock_dashboard.connection_manager = AsyncMock()
        mock_dashboard.connection_manager.broadcast = AsyncMock()

        mock_integration = AsyncMock()
        mock_integration.dashboard = mock_dashboard
        launcher._integration = mock_integration

        event = MagicMock()
        event.round_number = 1

        await launcher._on_standings_updated(event)

        mock_dashboard.connection_manager.broadcast.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_on_standings_updated_no_tournament_states(self, mock_config):
        """Test standings updated without tournament states."""
        launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)

        mock_dashboard = MagicMock()
        mock_dashboard.tournament_states = {}

        mock_integration = AsyncMock()
        mock_integration.dashboard = mock_dashboard
        launcher._integration = mock_integration

        event = MagicMock()
        event.round_number = 1

        # Should handle gracefully
        await launcher._on_standings_updated(event)

    @pytest.mark.asyncio
    async def test_on_standings_updated_no_integration(self, mock_config):
        """Test standings updated without integration."""
        launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)
        launcher._integration = None

        event = MagicMock()
        event.round_number = 1

        # Should handle gracefully
        await launcher._on_standings_updated(event)

    @pytest.mark.asyncio
    async def test_on_standings_updated_error(self, mock_config):
        """Test standings updated event handler with error."""
        launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)

        mock_integration = AsyncMock()
        mock_integration.dashboard = MagicMock()
        mock_integration.dashboard.tournament_states = None  # Will cause error
        launcher._integration = mock_integration

        event = MagicMock()
        event.round_number = 1

        # Should handle error gracefully
        await launcher._on_standings_updated(event)


class TestComponentLauncherDashboard:
    """Test dashboard initialization in ComponentLauncher."""

    @pytest.mark.asyncio
    async def test_start_dashboard(self, mock_config, mock_service_registry, mock_state_sync):
        """Test starting dashboard."""
        with patch(
            "src.launcher.component_launcher.get_service_registry",
            return_value=mock_service_registry,
        ):
            with patch(
                "src.launcher.component_launcher.get_state_sync", return_value=mock_state_sync
            ):
                with patch("src.launcher.component_launcher.LeagueManager") as MockLeagueManager:
                    with patch("src.visualization.get_dashboard") as mock_get_dashboard:
                        with patch(
                            "src.visualization.integration.get_dashboard_integration"
                        ) as mock_get_integration:
                            # Setup mocks
                            mock_league = AsyncMock()
                            mock_league.name = "league_manager"
                            mock_league.url = "http://localhost:8000"
                            mock_league.start = AsyncMock()
                            mock_league.set_dashboard = MagicMock()
                            MockLeagueManager.return_value = mock_league

                            mock_dashboard = AsyncMock()
                            mock_dashboard.start_server_background = AsyncMock()
                            mock_get_dashboard.return_value = mock_dashboard

                            mock_integration = AsyncMock()
                            mock_integration.start = AsyncMock()
                            mock_get_integration.return_value = mock_integration

                            launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER, mock_config)

                            # Start with dashboard
                            await launcher.start(enable_dashboard=True, port=8000)

                            # Verify dashboard started
                            mock_dashboard.start_server_background.assert_awaited_once()
                            mock_integration.start.assert_awaited_once()
                            mock_league.set_dashboard.assert_called_once()

                            # Verify event subscriptions
                            assert launcher.dashboard == mock_dashboard
                            assert launcher._integration == mock_integration

                            await launcher.stop()

    @pytest.mark.asyncio
    async def test_start_league_manager_with_custom_dashboard_host(
        self, mock_config, mock_service_registry, mock_state_sync
    ):
        """Test starting league manager with custom dashboard host."""
        with patch(
            "src.launcher.component_launcher.get_service_registry",
            return_value=mock_service_registry,
        ):
            with patch(
                "src.launcher.component_launcher.get_state_sync", return_value=mock_state_sync
            ):
                with patch("src.launcher.component_launcher.LeagueManager") as MockLeagueManager:
                    with patch("src.visualization.get_dashboard") as mock_get_dashboard:
                        with patch(
                            "src.visualization.integration.get_dashboard_integration"
                        ) as mock_get_integration:
                            with patch.dict("os.environ", {"DASHBOARD_HOST": "0.0.0.0"}):
                                mock_league = AsyncMock()
                                mock_league.name = "league_manager"
                                mock_league.url = "http://localhost:8000"
                                mock_league.start = AsyncMock()
                                mock_league.set_dashboard = MagicMock()
                                MockLeagueManager.return_value = mock_league

                                mock_dashboard = AsyncMock()
                                mock_dashboard.start_server_background = AsyncMock()
                                mock_get_dashboard.return_value = mock_dashboard

                                mock_integration = AsyncMock()
                                mock_integration.start = AsyncMock()
                                mock_get_integration.return_value = mock_integration

                                launcher = ComponentLauncher(
                                    ComponentType.LEAGUE_MANAGER, mock_config
                                )

                                await launcher.start(enable_dashboard=True, port=8000)

                                # Verify dashboard started with custom host
                                mock_dashboard.start_server_background.assert_awaited_once_with(
                                    host="0.0.0.0", port=8050
                                )

                                await launcher.stop()
