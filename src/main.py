"""
Main Entry Point - League System Runner
===================================================

Orchestrates the MCP Multi-Agent Game League.

 Default Configuration:
    - 1 League Manager (port 8000)
    - 2 Referees (ports 8001, 8002)
    - 4 Players (ports 8101-8104)

Usage:
    # Start full league with  defaults (1 LM, 2 Refs, 4 Players)
    python -m src.main --run

    # Custom configuration
    python -m src.main --run --players 6 --referees 3

    # Start full league with LLM (Claude) strategies
    python -m src.main --run --strategy llm

    # Start only league manager
    python -m src.main --component league

    # Start only referee
    python -m src.main --component referee

    # Start a player with LLM strategy
    python -m src.main --component player --name "ClaudeBot" --port 8101 --strategy llm --register

LLM Configuration:
    Set ANTHROPIC_API_KEY environment variable for Claude
    Set OPENAI_API_KEY environment variable for OpenAI
"""

import argparse
import asyncio
import os
import signal
from typing import Any

from .agents.league_manager import LeagueManager
from .agents.player import PlayerAgent
from .agents.referee import RefereeAgent
from .agents.strategies import RandomStrategy
from .common.config import Config, get_config
from .common.events import get_event_bus
from .common.logger import get_logger, setup_logging

# Plugin System
from .common.plugins import PluginContext, auto_discover_and_register, get_plugin_registry

logger = get_logger(__name__)


class GameOrchestrator:
    """
    Orchestrates the full game league.

    Manages:
    - League Manager (1)
    - Multiple Referees (configurable, default 2)
    - Multiple Players (configurable, default 4)

    Example configuration:
        - 1 League Manager on port 8000
        - 2 Referees on ports 8001, 8002
        - 4 Players on ports 8101-8104
    """

    def __init__(self, config: Config, enable_dashboard: bool = False):
        self.config = config
        self.enable_dashboard = enable_dashboard

        # Components
        self.league_manager: LeagueManager | None = None
        self.referees: list[RefereeAgent] = []  # Support multiple referees
        self.players: list[PlayerAgent] = []

        # Plugin Registry
        self.plugin_registry = get_plugin_registry()
        self.event_bus = get_event_bus()

        # State
        self._running = False
        self._shutdown_event = asyncio.Event()

        # Referee round-robin assignment
        self._referee_index = 0

    async def _init_plugins(self) -> None:
        """Initialize the plugin system."""
        logger.info("Initializing plugin system...")

        # Load plugin configuration from config loader
        try:
            from .common.config_loader import get_config_loader

            plugin_config: dict[str, Any] = get_config_loader().load_plugins_config()
        except Exception as e:
            logger.warning(f"Could not load plugin config: {e}. Using defaults.")
            plugin_config = {}

        # Merge with main config for context
        full_config: dict[str, Any] = (
            self.config.__dict__ if hasattr(self.config, "__dict__") else {}
        )
        full_config["plugins"] = plugin_config

        # Create plugin context
        context = PluginContext(
            registry=self.plugin_registry,
            config=full_config,
            logger=logger,
            event_bus=self.event_bus,
        )
        self.plugin_registry.set_context(context)

        # Discovery configuration
        # Look for plugins in 'plugins' directory and default user path
        plugin_paths = ["plugins", os.path.expanduser("~/.mcp_game/plugins")]

        # Use config if available, otherwise defaults
        discovery_config = plugin_config.get(
            "plugin_discovery",
            {
                "entry_point_group": "mcp_game.plugins",
                "directory_scan": {
                    "enabled": True,
                    "paths": plugin_paths,
                    "pattern": "*_plugin.py",
                },
            },
        )

        # Auto-discover and register
        count = await auto_discover_and_register(discovery_config, auto_enable=True)
        logger.info(f"Plugin system initialized. Active plugins: {count}")

    async def start_league_manager(self) -> LeagueManager:
        """Start the league manager."""
        self.league_manager = LeagueManager(
            league_id=self.config.league.league_id,
            min_players=self.config.league.min_players,
            max_players=self.config.league.max_players,
            host=self.config.league_manager.host,
            port=self.config.league_manager.port,
        )

        await self.league_manager.start()
        logger.info(f"League Manager started at {self.league_manager.url}")

        return self.league_manager

    async def start_referee(
        self, referee_id: str = "REF01", port: int | None = None
    ) -> RefereeAgent:
        """Start a referee agent."""
        if port is None:
            port = self.config.referee.port + len(self.referees)

        referee = RefereeAgent(
            referee_id=referee_id,
            league_id=self.config.league.league_id,
            host=self.config.referee.host,
            port=port,
            move_timeout=self.config.game.move_timeout,
            league_manager_url=self.config.league_manager.url,
        )

        await referee.start()
        self.referees.append(referee)
        logger.info(f"Referee {referee_id} started at {referee.url}")

        return referee

    async def start_referees(self, num_referees: int = 2) -> list[RefereeAgent]:
        """Start multiple referees."""
        for i in range(num_referees):
            referee_id = f"REF{i + 1:02d}"
            port = self.config.referee.port + i
            await self.start_referee(referee_id=referee_id, port=port)

        return self.referees

    def get_next_referee(self) -> RefereeAgent:
        """Get the next referee in round-robin fashion."""
        if not self.referees:
            raise RuntimeError("No referees available")
        referee = self.referees[self._referee_index % len(self.referees)]
        self._referee_index += 1
        return referee

    async def start_player(
        self,
        name: str,
        port: int,
        strategy_type: str = "random",
    ) -> PlayerAgent:
        """Start a player agent."""
        # Create strategy
        from .agents.strategies import Strategy
        from .agents.strategies.base import StrategyConfig
        from .agents.strategies.classic import LLMStrategy, PatternStrategy

        strategy: Strategy
        if strategy_type == "random":
            strategy = RandomStrategy()
        elif strategy_type == "pattern":
            strategy = PatternStrategy()
        elif strategy_type == "llm":
            # Use default StrategyConfig for LLM
            llm_config = StrategyConfig()
            strategy = LLMStrategy(llm_config)
        else:
            # Try to load from strategy registry (plugins)
            from .agents.strategies.plugin_registry import get_strategy_plugin_registry

            strategy_registry = get_strategy_plugin_registry()

            if strategy_registry.is_registered(strategy_type):
                strategy = strategy_registry.create_strategy(strategy_type)
                logger.info(f"Using plugin strategy: {strategy_type}")
            else:
                logger.warning(f"Unknown strategy '{strategy_type}', using RandomStrategy")
                strategy = RandomStrategy()

        player = PlayerAgent(
            player_name=name,
            strategy=strategy,
            league_id=self.config.league.league_id,
            host="localhost",
            port=port,
            league_manager_url=self.config.league_manager.url,
        )

        await player.start()
        self.players.append(player)

        logger.info(f"Player {name} started at {player.url}")

        return player

    async def start_all(
        self,
        num_players: int = 4,
        num_referees: int = 2,
        strategy: str = "mixed",
    ) -> None:
        """
        Start all components.
        """
        logger.info("=" * 60)
        logger.info("Starting MCP Game League")
        logger.info("=" * 60)
        logger.info("  League Manager: 1")
        logger.info(f"  Referees: {num_referees}")
        logger.info(f"  Players: {num_players}")
        logger.info(f"  Strategy: {strategy}")
        if strategy == "llm":
            logger.info(f"  LLM: {self.config.llm.provider} / {self.config.llm.model}")
        logger.info("=" * 60)

        # Initialize Plugins
        await self._init_plugins()

        # Start dashboard if enabled
        dashboard = None
        integration = None
        if self.enable_dashboard:
            from .visualization import get_dashboard
            from .visualization.integration import get_dashboard_integration

            logger.info("Starting interactive dashboard...")
            dashboard = get_dashboard()
            integration = get_dashboard_integration()

            # Start dashboard server in background
            # Use localhost by default for security, can be configured via environment
            dashboard_host = os.getenv("DASHBOARD_HOST", "127.0.0.1")
            await dashboard.start_server_background(host=dashboard_host, port=8050)

            # Initialize dashboard integration with tournament info
            await integration.start(
                tournament_id=self.config.league.league_id,
                total_rounds=0,  # Will be updated after league starts
            )

            # Connect event bus to dashboard
            self.event_bus.on("game.round.start", integration.on_round_start)
            self.event_bus.on("game.move.decision", integration.on_move_decision)
            self.event_bus.on("game.round.complete", integration.on_round_complete)
            self.event_bus.on("match.completed", integration.on_match_completed)

            # Connect strategy learning events
            self.event_bus.on("opponent.model.update", integration.on_opponent_model_update)
            self.event_bus.on("counterfactual.analysis", integration.on_counterfactual_analysis)

            logger.info("✓ Dashboard enabled at http://localhost:8050")

        # Start league manager
        await self.start_league_manager()

        # Connect dashboard to league manager if enabled
        if self.enable_dashboard and dashboard and self.league_manager:
            self.league_manager.set_dashboard(dashboard)

        # Wait a bit for league manager to be ready
        await asyncio.sleep(0.5)

        # Start referees
        await self.start_referees(num_referees)

        # Wait a bit
        await asyncio.sleep(0.5)

        # Register all referees with league manager
        for referee in self.referees:
            await referee.register_with_league()
            logger.info(f"Referee {referee.referee_id} registered with league manager")

        # Determine strategies for each player
        if strategy == "llm":
            strategies = ["llm"] * num_players
            logger.info(f"🧠 Using LLM strategy (Anthropic Claude) for all {num_players} players")
        elif strategy == "random":
            strategies = ["random"] * num_players
        elif strategy == "pattern":
            strategies = ["pattern"] * num_players
        else:  # mixed
            strategies = ["random", "pattern", "random", "pattern"]

        # Start players
        for i in range(num_players):
            name = f"Player_{i + 1}"
            port = 8101 + i
            player_strategy = strategies[i % len(strategies)]

            player = await self.start_player(name, port, player_strategy)

            # Register with league
            await asyncio.sleep(0.2)
            await player.register_with_league()

            # Update strategy info in league manager if dashboard is enabled
            if self.enable_dashboard and self.league_manager and integration:
                # Get the player's actual strategy name
                strategy_display_name = player.strategy.__class__.__name__
                # Update the registered player's strategy name
                if player.player_id in self.league_manager._players:
                    self.league_manager._players[
                        player.player_id
                    ].strategy_name = strategy_display_name
                    logger.debug(
                        f"Updated strategy for {player.player_id}: {strategy_display_name}"
                    )

                # Register player with dashboard integration
                if player.player_id:
                    integration.register_player(player.player_id, strategy_display_name)

        self._running = True
        logger.info(f"League started with {num_players} players")

    async def run_league(self) -> None:
        """Run the complete league."""
        if not self._running:
            await self.start_all()

        # Wait for enough players
        if self.league_manager:
            while self.league_manager.player_count < self.config.league.min_players:
                logger.info(
                    f"Waiting for players... ({self.league_manager.player_count}/{self.config.league.min_players})"
                )
                await asyncio.sleep(1)

            # Start the league
            result = await self.league_manager._start_league()
            if not result.get("success"):
                logger.error(f"Failed to start league: {result.get('error')}")
                return

            # Stream initial tournament state to dashboard
            if self.enable_dashboard:
                await self.league_manager._stream_tournament_update()

        else:
            logger.error("League manager not initialized")
            return

        logger.info("League competition started!")

        # Run rounds
        if self.league_manager:
            total_rounds = result.get("rounds", 0)
            for round_num in range(total_rounds):
                logger.info(f"\n{'=' * 50}")
                logger.info(f"Starting Round {round_num + 1}/{total_rounds}")
                logger.info(f"{'=' * 50}\n")

                # Start round
                round_result = await self.league_manager.start_next_round()

                if not round_result.get("success"):
                    if round_result.get("league_complete"):
                        break
                    logger.error(f"Round failed: {round_result.get('error')}")
                    continue

                # Run matches
                matches = round_result.get("matches", [])
                for match_data in matches:
                    await self._run_match(match_data, round_num=round_num + 1)

                # Wait for matches to complete
                await asyncio.sleep(2)

                # Show standings
                standings = self.league_manager._get_standings()
                logger.info("\nCurrent Standings:")
                for entry in standings.get("standings", []):
                    logger.info(
                        f"  {entry['rank']}. {entry['display_name']}: {entry['points']} pts"
                    )

            # Final standings
            logger.info("\n" + "=" * 50)
            logger.info("LEAGUE COMPLETE - Final Standings")
            logger.info("=" * 50)

            standings = self.league_manager._get_standings()
            for entry in standings.get("standings", []):
                logger.info(
                    f"  {entry['rank']}. {entry['display_name']}: {entry['points']} pts ({entry['wins']}W-{entry['losses']}L)"
                )

            # Stream final tournament state and winner to dashboard
            if self.enable_dashboard:
                await self.league_manager._stream_tournament_update()

                # Get the winner
                if standings.get("standings"):
                    winner = standings["standings"][0]
                    from .visualization import get_dashboard

                    dashboard = get_dashboard()
                    await dashboard.broadcast_tournament_complete(
                        {
                            "player_id": winner["player_id"],
                            "display_name": winner["display_name"],
                            "points": winner["points"],
                            "wins": winner["wins"],
                            "losses": winner["losses"],
                        }
                    )

    async def _run_match(self, match_data: dict, round_num: int = 0) -> None:
        """Run a single match through a referee (round-robin assignment)."""
        try:
            # Get referee in round-robin fashion
            referee = self.get_next_referee()

            # Get player IDs from match data
            player_a_id = match_data.get("player_A_id")
            player_b_id = match_data.get("player_B_id")

            logger.info(
                f"Match {match_data.get('match_id')}: {player_a_id} vs {player_b_id} (Referee: {referee.referee_id})"
            )

            result = await referee._start_match(
                {
                    "match_id": match_data.get("match_id"),
                    "player1_id": player_a_id,
                    "player1_endpoint": match_data.get("_player_A_endpoint"),
                    "player2_id": player_b_id,
                    "player2_endpoint": match_data.get("_player_B_endpoint"),
                    "rounds": self.config.game.rounds_per_match,
                }
            )

            logger.debug(f"Match started: {result}")

        except Exception as e:
            logger.error(f"Match error: {e}")

    async def stop(self) -> None:
        """Stop all components."""
        logger.info("Stopping league...")

        # Shutdown plugins
        if self.plugin_registry:
            await self.plugin_registry.shutdown()

        # Stop players
        for player in self.players:
            await player.stop()
        self.players.clear()

        # Stop all referees
        for referee in self.referees:
            await referee.stop()
        self.referees.clear()

        # Stop league manager
        if self.league_manager:
            await self.league_manager.stop()
            self.league_manager = None

        self._running = False
        logger.info("League stopped")

    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal."""
        await self._shutdown_event.wait()

    def request_shutdown(self) -> None:
        """Request shutdown."""
        self._shutdown_event.set()


async def run_component(component: str, args: argparse.Namespace) -> None:
    """Run a single component."""
    setup_logging(level="DEBUG" if args.debug else "INFO")
    config = get_config()

    # Update LLM config if specified
    if args.llm_provider:
        config.llm.provider = args.llm_provider
    if args.llm_model:
        config.llm.model = args.llm_model

    from .agents.strategies import Strategy

    server: LeagueManager | RefereeAgent | PlayerAgent
    if component == "league":
        server = LeagueManager(
            league_id=config.league.league_id,
            port=args.port or config.league_manager.port,
        )
    elif component == "referee":
        server = RefereeAgent(
            referee_id=args.name or "REF01",
            league_id=config.league.league_id,
            port=args.port or config.referee.port,
        )
    elif component == "player":
        # Determine strategy
        strategy_type = getattr(args, "strategy", "random")
        strategy: Strategy
        if strategy_type == "llm":
            # LLM strategy not yet implemented, use random
            logger.warning("LLM strategy not yet implemented, using RandomStrategy")
            strategy = RandomStrategy()
        elif strategy_type == "pattern":
            # Pattern strategy not yet implemented, use random
            logger.warning("Pattern strategy not yet implemented, using RandomStrategy")
            strategy = RandomStrategy()
        else:
            strategy = RandomStrategy()

        server = PlayerAgent(
            player_name=args.name or "Player",
            strategy=strategy,
            port=args.port or 8101,
        )
    else:
        logger.error(f"Unknown component: {component}")
        return

    # Handle shutdown
    loop = asyncio.get_event_loop()
    shutdown_event = asyncio.Event()

    def signal_handler():
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await server.start()
        logger.info(f"{component} started at {server.url}")

        # Auto-register with league if requested
        if args.register:
            if component == "player" and isinstance(server, PlayerAgent):
                await server.register_with_league()
            elif component == "referee" and isinstance(server, RefereeAgent):
                await server.register_with_league()

        await shutdown_event.wait()

    finally:
        await server.stop()


async def send_league_command(command: str, arguments: dict | None = None) -> None:
    """Send a command to the running league manager."""
    import json

    import httpx

    setup_logging(level="INFO")
    config = get_config()

    url = config.league_manager.url

    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": command, "arguments": arguments or {}},
        "id": 1,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=request, timeout=30.0)
            result = response.json()

            if "result" in result:
                content = result["result"].get("content", [])
                if content and len(content) > 0:
                    text = content[0].get("text", "{}")
                    data = json.loads(text)
                    print(json.dumps(data, indent=2))
            elif "error" in result:
                print(f"Error: {result['error']}")
            else:
                print(json.dumps(result, indent=2))

    except httpx.ConnectError:
        print(f"Error: Could not connect to league manager at {url}")
        print("Make sure the league manager is running:")
        print("  uv run python -m src.main --component league")
    except Exception as e:
        print(f"Error: {e}")


async def run_full_league(args: argparse.Namespace) -> None:
    """Run the full league."""
    setup_logging(level="DEBUG" if args.debug else "INFO")
    config = get_config()

    # Update LLM config if specified via command line
    if args.llm_provider:
        config.llm.provider = args.llm_provider
        # Auto-update model if not explicitly set
        if not args.llm_model:
            from .common.config import DEFAULT_LLM_MODELS

            config.llm.model = DEFAULT_LLM_MODELS.get(args.llm_provider)
    if args.llm_model:
        config.llm.model = args.llm_model

    orchestrator = GameOrchestrator(config, enable_dashboard=getattr(args, "dashboard", False))

    # Handle shutdown
    loop = asyncio.get_event_loop()

    def signal_handler():
        orchestrator.request_shutdown()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        # Pass strategy and referee count from command line
        strategy = getattr(args, "strategy", "mixed")
        num_referees = getattr(args, "referees", 2)
        await orchestrator.start_all(
            num_players=args.players,
            num_referees=num_referees,
            strategy=strategy,
        )

        if args.run:
            await orchestrator.run_league()
        else:
            logger.info("League ready. Press Ctrl+C to stop.")
            await orchestrator.wait_for_shutdown()

    finally:
        await orchestrator.stop()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="MCP Multi-Agent Game League",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run league with random/pattern strategies (no LLM needed)
  python -m src.main --run --players 4

  # Run league with LLM (Claude) strategy
  export ANTHROPIC_API_KEY=your-key
  python -m src.main --run --players 4 --strategy llm

  # Run league with OpenAI GPT-4
  export OPENAI_API_KEY=your-key
  python -m src.main --run --players 4 --strategy llm --llm-provider openai

  # Start a single player with LLM strategy
  python -m src.main --component player --name "ClaudeBot" --port 8101 --strategy llm --register

  # Start league (after components are running)
  python -m src.main --start-league

  # Run next round
  python -m src.main --run-round

  # Run all rounds automatically
  python -m src.main --run-all-rounds

  # Get current standings
  python -m src.main --get-standings
        """,
    )

    parser.add_argument(
        "--component",
        choices=["league", "referee", "player", "all"],
        default="all",
        help="Component to start (default: all)",
    )

    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="Name/ID for player or referee (e.g., P01, REF02)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port number",
    )

    parser.add_argument(
        "--players",
        type=int,
        default=4,
        help="Number of players (default: 4, )",
    )

    parser.add_argument(
        "--referees",
        type=int,
        default=2,
        help="Number of referees (default: 2, )",
    )

    parser.add_argument(
        "--strategy",
        # choices=["mixed", "random", "pattern", "llm"], # allow custom plugin strategies
        default="mixed",
        help="Player strategy: mixed (default), random, pattern, llm, or custom plugin name",
    )

    parser.add_argument(
        "--llm-provider",
        choices=["anthropic", "openai"],
        default=None,
        help="LLM provider: anthropic (Claude) or openai (GPT). Default: anthropic",
    )

    parser.add_argument(
        "--llm-model",
        type=str,
        default=None,
        help="LLM model name (e.g., claude-sonnet-4-20250514, gpt-4)",
    )

    parser.add_argument(
        "--run",
        action="store_true",
        help="Run the league automatically",
    )

    parser.add_argument(
        "--register",
        action="store_true",
        help="Auto-register player with league",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Enable real-time interactive dashboard",
    )

    parser.add_argument(
        "--start-league",
        action="store_true",
        help="Send start_league command to running league manager",
    )

    parser.add_argument(
        "--reset-league",
        action="store_true",
        help="Reset the league to start a new tournament",
    )

    parser.add_argument(
        "--get-standings",
        action="store_true",
        help="Get current league standings",
    )

    parser.add_argument(
        "--run-round",
        action="store_true",
        help="Run the next round of matches",
    )

    parser.add_argument(
        "--run-all-rounds",
        action="store_true",
        help="Run all remaining rounds automatically",
    )

    args = parser.parse_args()

    # Handle utility commands first
    if args.start_league:
        asyncio.run(send_league_command("start_league"))
    elif args.reset_league:
        asyncio.run(send_league_command("reset_league"))
    elif args.get_standings:
        asyncio.run(send_league_command("get_standings"))
    elif args.run_round:
        asyncio.run(send_league_command("start_next_round"))
    elif args.run_all_rounds:
        asyncio.run(send_league_command("run_all_rounds"))
    elif args.component == "all":
        asyncio.run(run_full_league(args))
    else:
        asyncio.run(run_component(args.component, args))


if __name__ == "__main__":
    main()
