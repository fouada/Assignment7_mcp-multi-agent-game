"""
CLI Entry Points for Modular Component Launching
=================================================

Provides separate commands for launching individual components.

Usage:
    # Start League Manager + Dashboard
    uv run python -m src.cli league

    # Start Referee
    uv run python -m src.cli referee --id REF01 --port 8001

    # Start Player
    uv run python -m src.cli player --name Player_1 --strategy llm --port 8101

    # Start All Components (legacy mode)
    uv run python -m src.cli all --players 4 --referees 2
"""

import argparse
import asyncio
import sys

from .common.logger import setup_logging
from .launcher import ComponentLauncher, ComponentType


async def launch_league_manager(args: argparse.Namespace) -> None:
    """Launch League Manager with optional dashboard."""
    launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER)

    try:
        await launcher.start(
            enable_dashboard=args.dashboard,
            port=args.port if args.port else None,
        )

        print(f"\n{'=' * 60}")
        print("League Manager Running")
        print(f"{'=' * 60}")
        print(f"  Endpoint: http://localhost:{args.port or 8000}")
        if args.dashboard:
            print("  Dashboard: http://localhost:8050")
        print(f"  League ID: {launcher.config.league.league_id}")
        print("\n  Press Ctrl+C to stop")
        print(f"{'=' * 60}\n")

        await launcher.wait_for_shutdown()

    finally:
        await launcher.stop()


async def launch_referee(args: argparse.Namespace) -> None:
    """Launch Referee agent."""
    launcher = ComponentLauncher(ComponentType.REFEREE)

    try:
        await launcher.start(
            referee_id=args.id,
            port=args.port,
            auto_register=args.register,
        )

        print(f"\n{'=' * 60}")
        print(f"Referee {args.id} Running")
        print(f"{'=' * 60}")
        print(f"  Endpoint: http://localhost:{args.port}")
        print(f"  League Manager: {launcher.config.league_manager.url}")
        if args.register:
            print("  Status: Registered with league")
        print("\n  Press Ctrl+C to stop")
        print(f"{'=' * 60}\n")

        await launcher.wait_for_shutdown()

    finally:
        await launcher.stop()


async def launch_player(args: argparse.Namespace) -> None:
    """Launch Player agent."""
    launcher = ComponentLauncher(ComponentType.PLAYER)

    try:
        await launcher.start(
            name=args.name,
            port=args.port,
            strategy=args.strategy,
            auto_register=args.register,
        )

        print(f"\n{'=' * 60}")
        print(f"Player {args.name} Running")
        print(f"{'=' * 60}")
        print(f"  Endpoint: http://localhost:{args.port}")
        print(f"  Strategy: {args.strategy}")
        print(f"  League Manager: {launcher.config.league_manager.url}")
        if args.register:
            print("  Status: Registered with league")
        print("\n  Press Ctrl+C to stop")
        print(f"{'=' * 60}\n")

        await launcher.wait_for_shutdown()

    finally:
        await launcher.stop()


async def launch_all(args: argparse.Namespace) -> None:
    """Launch all components (legacy mode)."""
    from .main import run_full_league

    await run_full_league(args)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="MCP Multi-Agent Game - Modular Component Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start League Manager with Dashboard
  uv run python -m src.cli league --dashboard

  # Start Referee
  uv run python -m src.cli referee --id REF01 --port 8001 --register

  # Start Player with LLM strategy
  uv run python -m src.cli player --name "Alice" --strategy llm --port 8101 --register

  # Start all components (legacy mode)
  uv run python -m src.cli all --players 4 --referees 2 --dashboard --run
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Component to launch")

    # League Manager command
    league_parser = subparsers.add_parser(
        "league", help="Start League Manager with optional dashboard"
    )
    league_parser.add_argument(
        "--port", type=int, default=8000, help="League Manager port (default: 8000)"
    )
    league_parser.add_argument(
        "--dashboard",
        action="store_true",
        default=True,
        help="Enable dashboard (default: True)",
    )
    league_parser.add_argument(
        "--no-dashboard", action="store_false", dest="dashboard", help="Disable dashboard"
    )
    league_parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    # Referee command
    referee_parser = subparsers.add_parser("referee", help="Start Referee agent")
    referee_parser.add_argument(
        "--id", type=str, default="REF01", help="Referee ID (default: REF01)"
    )
    referee_parser.add_argument(
        "--port", type=int, default=8001, help="Referee port (default: 8001)"
    )
    referee_parser.add_argument(
        "--register",
        action="store_true",
        default=True,
        help="Auto-register with league (default: True)",
    )
    referee_parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    # Player command
    player_parser = subparsers.add_parser("player", help="Start Player agent")
    player_parser.add_argument(
        "--name", type=str, default="Player_1", help="Player name (default: Player_1)"
    )
    player_parser.add_argument("--port", type=int, default=8101, help="Player port (default: 8101)")
    player_parser.add_argument(
        "--strategy",
        type=str,
        default="random",
        help="Strategy: random, pattern, llm, or plugin name (default: random)",
    )
    player_parser.add_argument(
        "--register",
        action="store_true",
        default=True,
        help="Auto-register with league (default: True)",
    )
    player_parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    # All components command (legacy)
    all_parser = subparsers.add_parser("all", help="Start all components (legacy mode)")
    all_parser.add_argument("--players", type=int, default=4, help="Number of players (default: 4)")
    all_parser.add_argument(
        "--referees", type=int, default=2, help="Number of referees (default: 2)"
    )
    all_parser.add_argument(
        "--strategy",
        type=str,
        default="mixed",
        help="Player strategy: mixed, random, pattern, llm (default: mixed)",
    )
    all_parser.add_argument("--dashboard", action="store_true", help="Enable dashboard")
    all_parser.add_argument("--run", action="store_true", help="Auto-run the league")
    all_parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Setup logging
    setup_logging(level="DEBUG" if getattr(args, "debug", False) else "INFO")

    # Route to appropriate launcher
    if args.command == "league":
        asyncio.run(launch_league_manager(args))
    elif args.command == "referee":
        asyncio.run(launch_referee(args))
    elif args.command == "player":
        asyncio.run(launch_player(args))
    elif args.command == "all":
        asyncio.run(launch_all(args))
    else:
        parser.print_help()
        sys.exit(1)


def main_league() -> None:
    """Entry point for mcp-league command."""
    import sys
    sys.argv = ["mcp-league", "league"] + sys.argv[1:]
    main()


def main_referee() -> None:
    """Entry point for mcp-referee command."""
    import sys
    sys.argv = ["mcp-referee", "referee"] + sys.argv[1:]
    main()


def main_player() -> None:
    """Entry point for mcp-player command."""
    import sys
    sys.argv = ["mcp-player", "player"] + sys.argv[1:]
    main()


if __name__ == "__main__":
    main()
