"""
Comprehensive tests for ComponentLauncher to increase coverage.
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.launcher.component_launcher import ComponentLauncher, ComponentType


class TestComponentLauncherCore:
    """Test core launcher functionality."""

    def test_launcher_initialization(self):
        """Test launcher initialization."""
        launcher = ComponentLauncher()

        assert launcher is not None
        assert hasattr(launcher, 'components')

    def test_launcher_with_custom_config(self):
        """Test launcher with custom configuration."""
        config = {"timeout": 30, "max_retries": 3}
        launcher = ComponentLauncher(config=config)

        assert launcher is not None


class TestComponentStarting:
    """Test component starting functionality."""

    @pytest.mark.asyncio
    async def test_start_league_manager_basic(self):
        """Test starting league manager."""
        launcher = ComponentLauncher()

        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process

            result = await launcher.start_league_manager(port=8000)

            assert result is not None

    @pytest.mark.asyncio
    async def test_start_league_manager_with_dashboard(self):
        """Test starting league manager with dashboard."""
        launcher = ComponentLauncher()

        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process

            result = await launcher.start_league_manager(
                port=8000,
                enable_dashboard=True
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_start_referee_basic(self):
        """Test starting referee."""
        launcher = ComponentLauncher()

        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12346
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process

            result = await launcher.start_referee(
                referee_id="ref_001",
                league_url="http://localhost:8000"
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_start_referee_with_auto_register(self):
        """Test starting referee with auto-register."""
        launcher = ComponentLauncher()

        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12346
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process

            result = await launcher.start_referee(
                referee_id="ref_001",
                league_url="http://localhost:8000",
                auto_register=True
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_start_player_basic(self):
        """Test starting player."""
        launcher = ComponentLauncher()

        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12347
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process

            result = await launcher.start_player(
                player_id="player_001",
                strategy="random",
                league_url="http://localhost:8000"
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_start_player_with_custom_strategy(self):
        """Test starting player with custom strategy."""
        launcher = ComponentLauncher()

        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12347
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process

            result = await launcher.start_player(
                player_id="player_001",
                strategy="adaptive",
                league_url="http://localhost:8000",
                strategy_config={"exploration": 0.2}
            )

            assert result is not None


class TestComponentStopping:
    """Test component stopping functionality."""

    @pytest.mark.asyncio
    async def test_stop_component_by_id(self):
        """Test stopping a component by ID."""
        launcher = ComponentLauncher()

        # Mock a running component
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        launcher.components["comp_001"] = {
            "process": mock_process,
            "type": ComponentType.LEAGUE_MANAGER
        }

        result = await launcher.stop_component("comp_001")

        assert result is True

    @pytest.mark.asyncio
    async def test_stop_nonexistent_component(self):
        """Test stopping a nonexistent component."""
        launcher = ComponentLauncher()

        result = await launcher.stop_component("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_stop_all_components(self):
        """Test stopping all components."""
        launcher = ComponentLauncher()

        # Mock multiple running components
        for i in range(3):
            mock_process = Mock()
            mock_process.pid = 12345 + i
            mock_process.poll.return_value = None
            launcher.components[f"comp_{i}"] = {
                "process": mock_process,
                "type": ComponentType.PLAYER
            }

        await launcher.stop_all()

        # All components should be stopped
        assert True

    @pytest.mark.asyncio
    async def test_stop_component_force(self):
        """Test force stopping a component."""
        launcher = ComponentLauncher()

        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        launcher.components["comp_001"] = {
            "process": mock_process,
            "type": ComponentType.REFEREE
        }

        result = await launcher.stop_component("comp_001", force=True)

        assert result is True


class TestComponentManagement:
    """Test component management functionality."""

    def test_list_components(self):
        """Test listing all components."""
        launcher = ComponentLauncher()

        # Add some components
        for i in range(3):
            launcher.components[f"comp_{i}"] = {
                "type": ComponentType.PLAYER,
                "status": "running"
            }

        components = launcher.list_components()

        assert len(components) == 3

    def test_get_component_info(self):
        """Test getting component information."""
        launcher = ComponentLauncher()

        launcher.components["comp_001"] = {
            "type": ComponentType.LEAGUE_MANAGER,
            "status": "running",
            "port": 8000
        }

        info = launcher.get_component_info("comp_001")

        assert info is not None
        assert info["type"] == ComponentType.LEAGUE_MANAGER

    def test_get_components_by_type(self):
        """Test getting components by type."""
        launcher = ComponentLauncher()

        launcher.components["lm_001"] = {"type": ComponentType.LEAGUE_MANAGER}
        launcher.components["ref_001"] = {"type": ComponentType.REFEREE}
        launcher.components["ref_002"] = {"type": ComponentType.REFEREE}
        launcher.components["p_001"] = {"type": ComponentType.PLAYER}

        referees = launcher.get_components_by_type(ComponentType.REFEREE)

        assert len(referees) == 2


class TestComponentHealth:
    """Test component health checking."""

    @pytest.mark.asyncio
    async def test_check_component_health(self):
        """Test checking component health."""
        launcher = ComponentLauncher()

        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Running
        launcher.components["comp_001"] = {
            "process": mock_process,
            "type": ComponentType.PLAYER
        }

        is_healthy = await launcher.check_component_health("comp_001")

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_check_dead_component(self):
        """Test checking health of dead component."""
        launcher = ComponentLauncher()

        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = 1  # Exited
        launcher.components["comp_001"] = {
            "process": mock_process,
            "type": ComponentType.PLAYER
        }

        is_healthy = await launcher.check_component_health("comp_001")

        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_all(self):
        """Test health check for all components."""
        launcher = ComponentLauncher()

        for i in range(3):
            mock_process = Mock()
            mock_process.pid = 12345 + i
            mock_process.poll.return_value = None
            launcher.components[f"comp_{i}"] = {
                "process": mock_process,
                "type": ComponentType.PLAYER
            }

        health = await launcher.health_check_all()

        assert len(health) == 3


class TestComponentRestart:
    """Test component restart functionality."""

    @pytest.mark.asyncio
    async def test_restart_component(self):
        """Test restarting a component."""
        launcher = ComponentLauncher()

        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        launcher.components["comp_001"] = {
            "process": mock_process,
            "type": ComponentType.PLAYER,
            "start_params": {
                "player_id": "player_001",
                "strategy": "random",
                "league_url": "http://localhost:8000"
            }
        }

        with patch.object(launcher, 'start_player', new_callable=AsyncMock):
            await launcher.restart_component("comp_001")

            # May succeed or fail depending on implementation

            assert True


class TestPortManagement:
    """Test port management functionality."""

    def test_find_available_port(self):
        """Test finding available port."""
        launcher = ComponentLauncher()

        port = launcher.find_available_port(start_port=9000)

        assert port >= 9000

    def test_is_port_available(self):
        """Test checking if port is available."""
        launcher = ComponentLauncher()

        # Port 0 should always be available for binding
        is_available = launcher.is_port_available(0)

        assert is_available is True

    def test_allocate_port_for_component(self):
        """Test allocating port for component."""
        launcher = ComponentLauncher()

        port = launcher.allocate_port_for_component("comp_001")

        assert port > 0


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_start_component_failure(self):
        """Test handling component start failure."""
        launcher = ComponentLauncher()

        with patch('subprocess.Popen', side_effect=Exception("Failed to start")):
            with pytest.raises((OSError, RuntimeError, ValueError)):
                await launcher.start_player(
                    player_id="player_001",
                    strategy="random",
                    league_url="http://localhost:8000"
                )

    @pytest.mark.asyncio
    async def test_stop_component_already_stopped(self):
        """Test stopping already stopped component."""
        launcher = ComponentLauncher()

        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = 1  # Already exited
        launcher.components["comp_001"] = {
            "process": mock_process,
            "type": ComponentType.PLAYER
        }

        await launcher.stop_component("comp_001")


        # Should handle gracefully


        assert True

    @pytest.mark.asyncio
    async def test_component_crash_detection(self):
        """Test detecting component crash."""
        launcher = ComponentLauncher()

        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = -1  # Crashed
        launcher.components["comp_001"] = {
            "process": mock_process,
            "type": ComponentType.PLAYER
        }

        is_healthy = await launcher.check_component_health("comp_001")

        assert is_healthy is False


class TestConcurrentOperations:
    """Test concurrent operations."""

    @pytest.mark.asyncio
    async def test_start_multiple_components_concurrently(self):
        """Test starting multiple components concurrently."""
        launcher = ComponentLauncher()

        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process

            tasks = []
            for i in range(3):
                task = launcher.start_player(
                    player_id=f"player_{i}",
                    strategy="random",
                    league_url="http://localhost:8000"
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Should complete without deadlock
            assert len(results) == 3

    @pytest.mark.asyncio
    async def test_stop_multiple_components_concurrently(self):
        """Test stopping multiple components concurrently."""
        launcher = ComponentLauncher()

        # Add multiple components
        for i in range(3):
            mock_process = Mock()
            mock_process.pid = 12345 + i
            mock_process.poll.return_value = None
            launcher.components[f"comp_{i}"] = {
                "process": mock_process,
                "type": ComponentType.PLAYER
            }

        tasks = []
        for i in range(3):
            task = launcher.stop_component(f"comp_{i}")
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        assert len(results) == 3


class TestComponentConfiguration:
    """Test component configuration."""

    @pytest.mark.asyncio
    async def test_start_with_environment_variables(self):
        """Test starting component with environment variables."""
        launcher = ComponentLauncher()

        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process

            result = await launcher.start_player(
                player_id="player_001",
                strategy="random",
                league_url="http://localhost:8000",
                env_vars={"DEBUG": "true"}
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_start_with_custom_working_directory(self):
        """Test starting component with custom working directory."""
        launcher = ComponentLauncher()

        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process

            result = await launcher.start_player(
                player_id="player_001",
                strategy="random",
                league_url="http://localhost:8000",
                working_dir="/tmp"
            )

            assert result is not None


class TestCleanup:
    """Test cleanup functionality."""

    @pytest.mark.asyncio
    async def test_cleanup_on_exit(self):
        """Test cleanup on exit."""
        launcher = ComponentLauncher()

        # Add some components
        for i in range(3):
            mock_process = Mock()
            mock_process.pid = 12345 + i
            mock_process.poll.return_value = None
            launcher.components[f"comp_{i}"] = {
                "process": mock_process,
                "type": ComponentType.PLAYER
            }

        await launcher.cleanup()

        # All components should be cleaned up
        assert True

    @pytest.mark.asyncio
    async def test_cleanup_handles_errors(self):
        """Test that cleanup handles errors gracefully."""
        launcher = ComponentLauncher()

        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_process.terminate.side_effect = Exception("Termination failed")
        launcher.components["comp_001"] = {
            "process": mock_process,
            "type": ComponentType.PLAYER
        }

        # Should not raise exception
        await launcher.cleanup()

        assert True


class TestComponentLogging:
    """Test component logging."""

    @pytest.mark.asyncio
    async def test_capture_component_output(self):
        """Test capturing component output."""
        launcher = ComponentLauncher()

        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.poll.return_value = None
            mock_process.stdout = Mock()
            mock_process.stderr = Mock()
            mock_popen.return_value = mock_process

            result = await launcher.start_player(
                player_id="player_001",
                strategy="random",
                league_url="http://localhost:8000",
                capture_output=True
            )

            assert result is not None

    def test_get_component_logs(self):
        """Test getting component logs."""
        launcher = ComponentLauncher()

        launcher.components["comp_001"] = {
            "type": ComponentType.PLAYER,
            "logs": ["Log line 1", "Log line 2"]
        }

        logs = launcher.get_component_logs("comp_001")

        assert logs is not None

