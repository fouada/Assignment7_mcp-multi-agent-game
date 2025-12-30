"""
Tests for CLI entry points
===========================

Tests the CLI command-line interface for launching individual components.
"""

import argparse
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cli import (
    launch_all,
    launch_league_manager,
    launch_player,
    launch_referee,
    main,
)


@pytest.fixture
def mock_launcher():
    """Create a mock ComponentLauncher."""
    launcher = MagicMock()
    launcher.start = AsyncMock()
    launcher.stop = AsyncMock()
    launcher.wait_for_shutdown = AsyncMock()
    launcher.config = MagicMock()
    launcher.config.league.league_id = "test-league-123"
    launcher.config.league_manager.url = "http://localhost:8000"
    return launcher


class TestLaunchLeagueManager:
    """Tests for launch_league_manager function."""

    @pytest.mark.asyncio
    async def test_launch_league_manager_with_dashboard(self, mock_launcher, capsys):
        """Test launching league manager with dashboard enabled."""
        args = argparse.Namespace(dashboard=True, port=8000, debug=False)

        with patch("src.cli.ComponentLauncher", return_value=mock_launcher):
            await launch_league_manager(args)

        # Verify ComponentLauncher was initialized correctly
        mock_launcher.start.assert_called_once_with(
            enable_dashboard=True,
            port=8000,
        )
        mock_launcher.wait_for_shutdown.assert_called_once()
        mock_launcher.stop.assert_called_once()

        # Check output
        captured = capsys.readouterr()
        assert "League Manager Running" in captured.out
        assert "http://localhost:8000" in captured.out
        assert "Dashboard: http://localhost:8050" in captured.out
        assert "test-league-123" in captured.out

    @pytest.mark.asyncio
    async def test_launch_league_manager_without_dashboard(self, mock_launcher, capsys):
        """Test launching league manager without dashboard."""
        args = argparse.Namespace(dashboard=False, port=8000, debug=False)

        with patch("src.cli.ComponentLauncher", return_value=mock_launcher):
            await launch_league_manager(args)

        mock_launcher.start.assert_called_once_with(
            enable_dashboard=False,
            port=8000,
        )

        # Check output doesn't include dashboard line
        captured = capsys.readouterr()
        assert "League Manager Running" in captured.out
        assert "Dashboard: http://localhost:8050" not in captured.out

    @pytest.mark.asyncio
    async def test_launch_league_manager_custom_port(self, mock_launcher, capsys):
        """Test launching league manager with custom port."""
        args = argparse.Namespace(dashboard=True, port=9000, debug=False)

        with patch("src.cli.ComponentLauncher", return_value=mock_launcher):
            await launch_league_manager(args)

        mock_launcher.start.assert_called_once_with(
            enable_dashboard=True,
            port=9000,
        )

        captured = capsys.readouterr()
        assert "http://localhost:9000" in captured.out

    @pytest.mark.asyncio
    async def test_launch_league_manager_no_port(self, mock_launcher):
        """Test launching league manager without specifying port."""
        args = argparse.Namespace(dashboard=True, port=None, debug=False)

        with patch("src.cli.ComponentLauncher", return_value=mock_launcher):
            await launch_league_manager(args)

        mock_launcher.start.assert_called_once_with(
            enable_dashboard=True,
            port=None,
        )

    @pytest.mark.asyncio
    async def test_launch_league_manager_cleanup_on_error(self, mock_launcher):
        """Test that launcher is stopped even if wait_for_shutdown raises error."""
        args = argparse.Namespace(dashboard=True, port=8000, debug=False)
        mock_launcher.wait_for_shutdown.side_effect = KeyboardInterrupt()

        with patch("src.cli.ComponentLauncher", return_value=mock_launcher):
            with pytest.raises(KeyboardInterrupt):
                await launch_league_manager(args)

        # Verify cleanup was called
        mock_launcher.stop.assert_called_once()


class TestLaunchReferee:
    """Tests for launch_referee function."""

    @pytest.mark.asyncio
    async def test_launch_referee_with_registration(self, mock_launcher, capsys):
        """Test launching referee with auto-registration."""
        args = argparse.Namespace(id="REF01", port=8001, register=True, debug=False)

        with patch("src.cli.ComponentLauncher", return_value=mock_launcher):
            await launch_referee(args)

        mock_launcher.start.assert_called_once_with(
            referee_id="REF01",
            port=8001,
            auto_register=True,
        )
        mock_launcher.wait_for_shutdown.assert_called_once()
        mock_launcher.stop.assert_called_once()

        captured = capsys.readouterr()
        assert "Referee REF01 Running" in captured.out
        assert "http://localhost:8001" in captured.out
        assert "Status: Registered with league" in captured.out

    @pytest.mark.asyncio
    async def test_launch_referee_without_registration(self, mock_launcher, capsys):
        """Test launching referee without auto-registration."""
        args = argparse.Namespace(id="REF02", port=8002, register=False, debug=False)

        with patch("src.cli.ComponentLauncher", return_value=mock_launcher):
            await launch_referee(args)

        mock_launcher.start.assert_called_once_with(
            referee_id="REF02",
            port=8002,
            auto_register=False,
        )

        captured = capsys.readouterr()
        assert "Referee REF02 Running" in captured.out
        assert "Status: Registered with league" not in captured.out

    @pytest.mark.asyncio
    async def test_launch_referee_custom_id(self, mock_launcher, capsys):
        """Test launching referee with custom ID."""
        args = argparse.Namespace(id="CUSTOM_REF", port=8003, register=True, debug=False)

        with patch("src.cli.ComponentLauncher", return_value=mock_launcher):
            await launch_referee(args)

        captured = capsys.readouterr()
        assert "Referee CUSTOM_REF Running" in captured.out

    @pytest.mark.asyncio
    async def test_launch_referee_cleanup_on_error(self, mock_launcher):
        """Test that launcher is stopped even if wait_for_shutdown raises error."""
        args = argparse.Namespace(id="REF01", port=8001, register=True, debug=False)
        mock_launcher.wait_for_shutdown.side_effect = KeyboardInterrupt()

        with patch("src.cli.ComponentLauncher", return_value=mock_launcher):
            with pytest.raises(KeyboardInterrupt):
                await launch_referee(args)

        mock_launcher.stop.assert_called_once()


class TestLaunchPlayer:
    """Tests for launch_player function."""

    @pytest.mark.asyncio
    async def test_launch_player_with_registration(self, mock_launcher, capsys):
        """Test launching player with auto-registration."""
        args = argparse.Namespace(
            name="Alice",
            port=8101,
            strategy="random",
            register=True,
            debug=False,
        )

        with patch("src.cli.ComponentLauncher", return_value=mock_launcher):
            await launch_player(args)

        mock_launcher.start.assert_called_once_with(
            name="Alice",
            port=8101,
            strategy="random",
            auto_register=True,
        )
        mock_launcher.wait_for_shutdown.assert_called_once()
        mock_launcher.stop.assert_called_once()

        captured = capsys.readouterr()
        assert "Player Alice Running" in captured.out
        assert "http://localhost:8101" in captured.out
        assert "Strategy: random" in captured.out
        assert "Status: Registered with league" in captured.out

    @pytest.mark.asyncio
    async def test_launch_player_without_registration(self, mock_launcher, capsys):
        """Test launching player without auto-registration."""
        args = argparse.Namespace(
            name="Bob",
            port=8102,
            strategy="pattern",
            register=False,
            debug=False,
        )

        with patch("src.cli.ComponentLauncher", return_value=mock_launcher):
            await launch_player(args)

        mock_launcher.start.assert_called_once_with(
            name="Bob",
            port=8102,
            strategy="pattern",
            auto_register=False,
        )

        captured = capsys.readouterr()
        assert "Player Bob Running" in captured.out
        assert "Strategy: pattern" in captured.out
        assert "Status: Registered with league" not in captured.out

    @pytest.mark.asyncio
    async def test_launch_player_llm_strategy(self, mock_launcher, capsys):
        """Test launching player with LLM strategy."""
        args = argparse.Namespace(
            name="Charlie",
            port=8103,
            strategy="llm",
            register=True,
            debug=False,
        )

        with patch("src.cli.ComponentLauncher", return_value=mock_launcher):
            await launch_player(args)

        captured = capsys.readouterr()
        assert "Strategy: llm" in captured.out

    @pytest.mark.asyncio
    async def test_launch_player_cleanup_on_error(self, mock_launcher):
        """Test that launcher is stopped even if wait_for_shutdown raises error."""
        args = argparse.Namespace(
            name="Alice",
            port=8101,
            strategy="random",
            register=True,
            debug=False,
        )
        mock_launcher.wait_for_shutdown.side_effect = KeyboardInterrupt()

        with patch("src.cli.ComponentLauncher", return_value=mock_launcher):
            with pytest.raises(KeyboardInterrupt):
                await launch_player(args)

        mock_launcher.stop.assert_called_once()


class TestLaunchAll:
    """Tests for launch_all function."""

    @pytest.mark.asyncio
    async def test_launch_all(self):
        """Test launching all components (legacy mode)."""
        args = argparse.Namespace(
            players=4,
            referees=2,
            strategy="mixed",
            dashboard=True,
            run=True,
            debug=False,
        )

        mock_run_full_league = AsyncMock()
        with patch("src.main.run_full_league", mock_run_full_league):
            await launch_all(args)

        mock_run_full_league.assert_called_once_with(args)


class TestMain:
    """Tests for main CLI entry point."""

    def test_main_no_command(self, capsys):
        """Test main with no command shows help and exits."""
        with patch.object(sys, "argv", ["cli"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "usage:" in captured.out

    def test_main_league_command(self):
        """Test main routes to league manager."""
        with patch.object(sys, "argv", ["cli", "league", "--port", "8000"]):
            with patch("src.cli.asyncio.run") as mock_run:
                with patch("src.cli.setup_logging"):
                    main()

        # Verify asyncio.run was called with launch_league_manager
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        # Check it's a coroutine for launch_league_manager
        assert args.__name__ == "launch_league_manager"

    def test_main_referee_command(self):
        """Test main routes to referee."""
        with patch.object(sys, "argv", ["cli", "referee", "--id", "REF01"]):
            with patch("src.cli.asyncio.run") as mock_run:
                with patch("src.cli.setup_logging"):
                    main()

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args.__name__ == "launch_referee"

    def test_main_player_command(self):
        """Test main routes to player."""
        with patch.object(sys, "argv", ["cli", "player", "--name", "Alice"]):
            with patch("src.cli.asyncio.run") as mock_run:
                with patch("src.cli.setup_logging"):
                    main()

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args.__name__ == "launch_player"

    def test_main_all_command(self):
        """Test main routes to all components."""
        with patch.object(sys, "argv", ["cli", "all", "--players", "4"]):
            with patch("src.cli.asyncio.run") as mock_run:
                with patch("src.cli.setup_logging"):
                    main()

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args.__name__ == "launch_all"

    def test_main_debug_logging(self):
        """Test main sets up debug logging when --debug flag is used."""
        with patch.object(sys, "argv", ["cli", "league", "--debug"]):
            with patch("src.cli.asyncio.run"):
                with patch("src.cli.setup_logging") as mock_setup_logging:
                    main()

        mock_setup_logging.assert_called_once_with(level="DEBUG")

    def test_main_info_logging(self):
        """Test main sets up info logging by default."""
        with patch.object(sys, "argv", ["cli", "league"]):
            with patch("src.cli.asyncio.run"):
                with patch("src.cli.setup_logging") as mock_setup_logging:
                    main()

        mock_setup_logging.assert_called_once_with(level="INFO")

    def test_main_league_with_dashboard(self):
        """Test parsing league command with dashboard flag."""
        with patch.object(sys, "argv", ["cli", "league", "--dashboard"]):
            with patch("src.cli.asyncio.run"):
                with patch("src.cli.setup_logging"):
                    main()

    def test_main_league_without_dashboard(self):
        """Test parsing league command with no-dashboard flag."""
        with patch.object(sys, "argv", ["cli", "league", "--no-dashboard"]):
            with patch("src.cli.asyncio.run"):
                with patch("src.cli.setup_logging"):
                    main()

    def test_main_referee_with_custom_port(self):
        """Test parsing referee command with custom port."""
        with patch.object(sys, "argv", ["cli", "referee", "--port", "9001"]):
            with patch("src.cli.asyncio.run"):
                with patch("src.cli.setup_logging"):
                    main()

    def test_main_player_with_strategy(self):
        """Test parsing player command with strategy."""
        with patch.object(sys, "argv", ["cli", "player", "--strategy", "llm"]):
            with patch("src.cli.asyncio.run"):
                with patch("src.cli.setup_logging"):
                    main()

    def test_main_all_with_options(self):
        """Test parsing all command with various options."""
        with patch.object(
            sys,
            "argv",
            [
                "cli",
                "all",
                "--players",
                "6",
                "--referees",
                "3",
                "--strategy",
                "mixed",
                "--dashboard",
                "--run",
            ],
        ):
            with patch("src.cli.asyncio.run"):
                with patch("src.cli.setup_logging"):
                    main()

    def test_main_invalid_command(self, capsys):
        """Test main with invalid command shows help and exits."""
        with patch.object(sys, "argv", ["cli", "invalid"]):
            with pytest.raises(SystemExit):
                main()


class TestArgumentParsing:
    """Tests for argument parsing."""

    def test_league_parser_defaults(self):
        """Test league parser with default arguments."""
        with patch.object(sys, "argv", ["cli", "league"]):
            with patch("src.cli.asyncio.run"):
                with patch("src.cli.setup_logging"):
                    main()

    def test_referee_parser_defaults(self):
        """Test referee parser with default arguments."""
        with patch.object(sys, "argv", ["cli", "referee"]):
            with patch("src.cli.asyncio.run"):
                with patch("src.cli.setup_logging"):
                    main()

    def test_player_parser_defaults(self):
        """Test player parser with default arguments."""
        with patch.object(sys, "argv", ["cli", "player"]):
            with patch("src.cli.asyncio.run"):
                with patch("src.cli.setup_logging"):
                    main()

    def test_all_parser_defaults(self):
        """Test all parser with default arguments."""
        with patch.object(sys, "argv", ["cli", "all"]):
            with patch("src.cli.asyncio.run"):
                with patch("src.cli.setup_logging"):
                    main()


class TestCLIEdgeCases:
    """Tests for CLI edge cases."""

    @pytest.mark.asyncio
    async def test_launch_functions_with_keyboard_interrupt(self, mock_launcher):
        """Test all launch functions handle KeyboardInterrupt gracefully."""
        mock_launcher.wait_for_shutdown.side_effect = KeyboardInterrupt()

        # Test league manager
        args_league = argparse.Namespace(dashboard=True, port=8000, debug=False)
        with patch("src.cli.ComponentLauncher", return_value=mock_launcher):
            with pytest.raises(KeyboardInterrupt):
                await launch_league_manager(args_league)
        mock_launcher.stop.assert_called()

        # Test referee
        mock_launcher.stop.reset_mock()
        args_referee = argparse.Namespace(id="REF01", port=8001, register=True, debug=False)
        with patch("src.cli.ComponentLauncher", return_value=mock_launcher):
            with pytest.raises(KeyboardInterrupt):
                await launch_referee(args_referee)
        mock_launcher.stop.assert_called()

        # Test player
        mock_launcher.stop.reset_mock()
        args_player = argparse.Namespace(
            name="Alice", port=8101, strategy="random", register=True, debug=False
        )
        with patch("src.cli.ComponentLauncher", return_value=mock_launcher):
            with pytest.raises(KeyboardInterrupt):
                await launch_player(args_player)
        mock_launcher.stop.assert_called()

    def test_main_entry_point(self):
        """Test __main__ entry point."""
        with patch.object(sys, "argv", ["cli", "league"]):
            with patch("src.cli.asyncio.run"):
                with patch("src.cli.setup_logging"):
                    # This would be called when running: python -m src.cli
                    main()
