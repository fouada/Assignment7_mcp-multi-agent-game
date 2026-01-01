"""
Manual Control Dashboard with UV Command Support
================================================

This script provides the Ultimate Dashboard with full manual control
via UV commands, matching your original workflow:

Workflow:
---------
1. Launch league script
2. UV: Register referees
3. UV: Register players
4. UV: Start league
5. UV: Run each round manually
6. View: Winner + all statistics
7. View: Research results
8. View: Innovation showcase

Features:
---------
- Manual step-by-step control via CLI
- Real-time dashboard updates
- All current innovations displayed
- Future innovations roadmap (to 100 A+)
- Research results visualization
- Statistics and simulations
- Full UV command compatibility

Usage:
------
# Terminal 1: Start dashboard
python examples/dashboard/run_manual_control_dashboard.py

# Terminal 2: Manual UV commands
uv run python -m src.main --component league
uv run python -m src.main --component referee --register
uv run python -m src.main --component player --name "P01" --strategy quantum --register
# ... continue with UV commands

Dashboard updates automatically as you progress!
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.visualization.ultimate_dashboard import UltimateDashboard
from src.visualization.ultimate_integration import (
    UltimateDashboardIntegration,
    set_ultimate_dashboard_integration
)
from src.common.events import get_event_bus
from src.common.logger import get_logger, setup_logging

logger = get_logger(__name__)


class ManualControlServer:
    """
    Server that listens for UV commands and updates dashboard.

    This allows you to use your existing UV workflow while seeing
    everything in real-time on the dashboard.
    """

    def __init__(self, dashboard: UltimateDashboard, integration: UltimateDashboardIntegration):
        self.dashboard = dashboard
        self.integration = integration
        self.event_bus = get_event_bus()

        # State
        self.referees_registered = []
        self.players_registered = []
        self.league_started = False
        self.current_round = 0
        self.tournament_complete = False

    async def start_listening(self):
        """Start listening for manual commands."""
        logger.info("📡 Manual control server ready")
        logger.info("   Dashboard will update as you run UV commands")

        # Subscribe to events from manual UV commands
        self._subscribe_to_events()

    def _subscribe_to_events(self):
        """Subscribe to all manual command events."""
        self.event_bus.on("referee.registered", self._on_referee_registered)
        self.event_bus.on("player.registered", self._on_player_registered)
        self.event_bus.on("league.started", self._on_league_started)
        self.event_bus.on("round.started", self._on_round_started)
        self.event_bus.on("round.completed", self._on_round_completed)
        self.event_bus.on("tournament.completed", self._on_tournament_completed)

    async def _on_referee_registered(self, event):
        """Handle referee registration from UV command."""
        referee_id = event.get("referee_id", f"REF{len(self.referees_registered)+1:02d}")
        self.referees_registered.append(referee_id)

        logger.info(f"✅ Referee registered: {referee_id}")
        logger.info(f"   Total referees: {len(self.referees_registered)}")

        await self.dashboard.broadcast({
            "type": "system_update",
            "data": {
                "referees": len(self.referees_registered),
                "message": f"Referee {referee_id} registered"
            }
        })

    async def _on_player_registered(self, event):
        """Handle player registration from UV command."""
        player_id = event.get("player_id")
        strategy = event.get("strategy", "Unknown")

        self.players_registered.append({"player_id": player_id, "strategy": strategy})
        self.integration.register_player(player_id, strategy)

        logger.info(f"✅ Player registered: {player_id} ({strategy})")
        logger.info(f"   Total players: {len(self.players_registered)}")

        await self.integration._broadcast_tournament_update()

    async def _on_league_started(self, event):
        """Handle league start from UV command."""
        self.league_started = True
        total_rounds = event.get("total_rounds", 10)
        self.integration.total_rounds = total_rounds

        logger.info("✅ League started!")
        logger.info(f"   Players: {len(self.players_registered)}")
        logger.info(f"   Referees: {len(self.referees_registered)}")
        logger.info(f"   Total rounds: {total_rounds}")

        await self.event_bus.emit("tournament.start", {
            "num_players": len(self.players_registered),
            "total_rounds": total_rounds
        })

    async def _on_round_started(self, event):
        """Handle round start from UV command."""
        round_num = event.get("round", self.current_round + 1)
        self.current_round = round_num

        logger.info(f"▶️  Round {round_num} started")

        await self.integration._broadcast_tournament_update()

    async def _on_round_completed(self, event):
        """Handle round complete from UV command."""
        round_num = event.get("round", self.current_round)

        logger.info(f"✅ Round {round_num} completed")

        # Update player stats from event
        results = event.get("results", {})
        for player_id, stats in results.items():
            if player_id in self.integration.aggregator.players:
                self.integration.aggregator.update_player_stats(player_id, **stats)

        await self.integration._broadcast_tournament_update()

    async def _on_tournament_completed(self, event):
        """Handle tournament complete from UV command."""
        self.tournament_complete = True

        standings = self.integration.aggregator.get_standings()
        if standings:
            winner = standings[0]

            logger.info("🏆 Tournament Complete!")
            logger.info(f"   Winner: {winner['player_id']}")
            logger.info(f"   Strategy: {winner['strategy']}")
            logger.info(f"   Score: {winner['score']:.1f}")

            await self.dashboard.send_tournament_complete(winner)


async def run_manual_control_dashboard(port: int = 8050):
    """
    Run dashboard with manual control support.

    Dashboard runs continuously and updates as you execute
    UV commands in another terminal.
    """
    logger.info("=" * 80)
    logger.info("🎮 ULTIMATE DASHBOARD - MANUAL CONTROL MODE")
    logger.info("=" * 80)
    logger.info("")
    logger.info("This dashboard supports your manual UV workflow:")
    logger.info("")
    logger.info("📋 Your Workflow:")
    logger.info("  1. ✓ Launch league script (this)")
    logger.info("  2. → UV: Register referees")
    logger.info("  3. → UV: Register players")
    logger.info("  4. → UV: Start league")
    logger.info("  5. → UV: Run rounds (one by one)")
    logger.info("  6. ✓ View: Winner + statistics")
    logger.info("  7. ✓ View: Research results")
    logger.info("  8. ✓ View: Innovation showcase")
    logger.info("")
    logger.info("=" * 80)
    logger.info("")

    # Get event bus
    event_bus = get_event_bus()

    # Create Ultimate Dashboard
    logger.info("🎨 Starting Ultimate Dashboard...")
    dashboard = UltimateDashboard(port=port)
    await dashboard.start()
    logger.info(f"✅ Dashboard running at http://localhost:{port}")

    # Create Dashboard Integration
    logger.info("🔗 Setting up dashboard integration...")
    integration = UltimateDashboardIntegration(dashboard, event_bus)
    await integration.initialize(
        tournament_id="manual_control",
        total_rounds=10  # Will be updated when league starts
    )
    set_ultimate_dashboard_integration(integration)
    logger.info("✅ Integration ready")

    # Create Manual Control Server
    logger.info("📡 Starting manual control listener...")
    control_server = ManualControlServer(dashboard, integration)
    await control_server.start_listening()

    logger.info("")
    logger.info("=" * 80)
    logger.info("✅ DASHBOARD READY FOR MANUAL CONTROL")
    logger.info("=" * 80)
    logger.info("")
    logger.info("🌐 Open your browser:")
    logger.info(f"   http://localhost:{port}")
    logger.info("")
    logger.info("📊 Dashboard will show:")
    logger.info("  • Real-time updates as you run UV commands")
    logger.info("  • All current innovations (10+)")
    logger.info("  • Future innovation roadmap (to 100 A+)")
    logger.info("  • Research results & statistics")
    logger.info("  • BRQC experimental data")
    logger.info("  • Theorem 1 validation")
    logger.info("  • Byzantine tolerance metrics")
    logger.info("  • Complete analytics")
    logger.info("")
    logger.info("🔧 Now run UV commands in another terminal:")
    logger.info("")
    logger.info("# Step 1: Register referees")
    logger.info("uv run python -m src.main --component referee --referee-id REF01 --port 8001")
    logger.info("uv run python -m src.main --component referee --referee-id REF02 --port 8002")
    logger.info("")
    logger.info("# Step 2: Register players")
    logger.info("uv run python -m src.main --component player --name P01 --strategy quantum --register")
    logger.info("uv run python -m src.main --component player --name P02 --strategy bayesian --register")
    logger.info("uv run python -m src.main --component player --name P03 --strategy cfr --register")
    logger.info("uv run python -m src.main --component player --name P04 --strategy composite --register")
    logger.info("")
    logger.info("# Step 3: Start league")
    logger.info("uv run python -m src.main --start-league --rounds 10")
    logger.info("")
    logger.info("# Step 4: Run rounds (repeat for each round)")
    logger.info("uv run python -m src.main --run-round 1")
    logger.info("uv run python -m src.main --run-round 2")
    logger.info("# ... continue until all rounds complete")
    logger.info("")
    logger.info("=" * 80)
    logger.info("")
    logger.info("⏳ Waiting for your UV commands...")
    logger.info("   (Dashboard will update automatically)")
    logger.info("")
    logger.info("Press Ctrl+C to stop dashboard")
    logger.info("=" * 80)

    try:
        # Keep running indefinitely
        while True:
            await asyncio.sleep(1)

            # Periodically update dashboard with system status
            if control_server.league_started and not control_server.tournament_complete:
                await dashboard.broadcast({
                    "type": "heartbeat",
                    "data": {
                        "current_round": control_server.current_round,
                        "players": len(control_server.players_registered),
                        "referees": len(control_server.referees_registered)
                    }
                })

    except KeyboardInterrupt:
        logger.info("\n\n🛑 Shutting down...")
    finally:
        logger.info("🧹 Cleaning up...")
        await integration.cleanup()
        await dashboard.cleanup()
        logger.info("✅ Shutdown complete")


async def run_with_command_prompt():
    """
    Run with interactive command prompt for manual control.

    Alternative to UV commands - control everything from one terminal.
    """
    logger.info("=" * 80)
    logger.info("🎮 INTERACTIVE MANUAL CONTROL MODE")
    logger.info("=" * 80)
    logger.info("")

    # Start dashboard
    event_bus = get_event_bus()
    dashboard = UltimateDashboard(port=8050)
    await dashboard.start()

    integration = UltimateDashboardIntegration(dashboard, event_bus)
    await integration.initialize(tournament_id="interactive", total_rounds=10)

    control_server = ManualControlServer(dashboard, integration)
    await control_server.start_listening()

    logger.info("✅ Dashboard ready at http://localhost:8050")
    logger.info("")
    logger.info("🎮 Interactive Commands:")
    logger.info("  ref <id>              - Register referee")
    logger.info("  player <id> <strat>   - Register player")
    logger.info("  start <rounds>        - Start league")
    logger.info("  round <n>             - Run round N")
    logger.info("  complete              - End tournament")
    logger.info("  status                - Show current status")
    logger.info("  quit                  - Exit")
    logger.info("")

    try:
        while True:
            cmd = input("Command> ").strip().split()

            if not cmd:
                continue

            if cmd[0] == "quit":
                break

            elif cmd[0] == "ref":
                referee_id = cmd[1] if len(cmd) > 1 else f"REF{len(control_server.referees_registered)+1:02d}"
                await event_bus.emit("referee.registered", {"referee_id": referee_id})

            elif cmd[0] == "player":
                if len(cmd) < 3:
                    logger.error("Usage: player <id> <strategy>")
                    continue
                player_id, strategy = cmd[1], cmd[2]
                await event_bus.emit("player.registered", {
                    "player_id": player_id,
                    "strategy": strategy
                })

            elif cmd[0] == "start":
                rounds = int(cmd[1]) if len(cmd) > 1 else 10
                await event_bus.emit("league.started", {"total_rounds": rounds})

            elif cmd[0] == "round":
                round_num = int(cmd[1]) if len(cmd) > 1 else control_server.current_round + 1
                await event_bus.emit("round.started", {"round": round_num})

                # Simulate round completion with dummy results
                await asyncio.sleep(1)
                await event_bus.emit("round.completed", {"round": round_num})

            elif cmd[0] == "complete":
                await event_bus.emit("tournament.completed", {})

            elif cmd[0] == "status":
                logger.info(f"Referees: {len(control_server.referees_registered)}")
                logger.info(f"Players: {len(control_server.players_registered)}")
                logger.info(f"League started: {control_server.league_started}")
                logger.info(f"Current round: {control_server.current_round}")
                logger.info(f"Complete: {control_server.tournament_complete}")

            else:
                logger.warning(f"Unknown command: {cmd[0]}")

    except KeyboardInterrupt:
        logger.info("\n\n🛑 Exiting...")
    finally:
        await integration.cleanup()
        await dashboard.cleanup()


if __name__ == "__main__":
    import argparse

    setup_logging(level="INFO")

    parser = argparse.ArgumentParser(
        description="Manual Control Dashboard for UV Workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8050,
        help="Dashboard port (default: 8050)"
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Use interactive command prompt instead of UV commands"
    )

    args = parser.parse_args()

    try:
        if args.interactive:
            asyncio.run(run_with_command_prompt())
        else:
            asyncio.run(run_manual_control_dashboard(port=args.port))
    except KeyboardInterrupt:
        logger.info("\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
