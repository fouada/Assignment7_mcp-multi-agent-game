"""
Run Ultimate MIT-Level League with Dashboard
============================================

This script launches the complete game league system with the Ultimate
MIT-Level Dashboard, showcasing all innovations and real-time data.

Features:
---------
- Complete game league (League Manager, Referees, Players)
- Ultimate dashboard with 8 interactive tabs
- Real-time data integration via event bus
- All innovations visualized live
- BRQC performance monitoring
- Theorem 1 validation display
- Byzantine fault tolerance metrics
- Strategy comparison analytics

Usage:
------
Basic:
    python examples/dashboard/run_ultimate_league.py

Custom configuration:
    python examples/dashboard/run_ultimate_league.py --players 6 --rounds 20

With simulation:
    python examples/dashboard/run_ultimate_league.py --simulate

Options:
    --players N     Number of players (default: 6)
    --rounds N      Rounds per match (default: 15)
    --port N        Dashboard port (default: 8050)
    --simulate      Run with simulated data
    --quick         Quick 5-round demo

Then open: http://localhost:8050
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.visualization.ultimate_dashboard import UltimateDashboard
from src.visualization.ultimate_integration import (
    UltimateDashboardIntegration,
    set_ultimate_dashboard_integration
)
from src.common.config import get_config
from src.common.events import get_event_bus
from src.common.logger import get_logger, setup_logging
from src.main import GameOrchestrator

logger = get_logger(__name__)


async def run_ultimate_league(
    num_players: int = 6,
    num_rounds: int = 15,
    dashboard_port: int = 8050,
    simulate: bool = False
):
    """
    Run complete league with Ultimate Dashboard.

    Args:
        num_players: Number of players
        num_rounds: Rounds per match
        dashboard_port: Port for dashboard
        simulate: Use simulated data
    """
    logger.info("=" * 80)
    logger.info("🏆 ULTIMATE MIT-LEVEL GAME LEAGUE")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Starting complete system with:")
    logger.info(f"  🎮 Players: {num_players}")
    logger.info(f"  🔄 Rounds: {num_rounds}")
    logger.info(f"  📊 Dashboard: http://localhost:{dashboard_port}")
    logger.info("")
    logger.info("Dashboard Features:")
    logger.info("  📊 Overview - Real-time tournament metrics")
    logger.info("  🏆 Tournament - Live standings & performance")
    logger.info("  💡 Innovations - All 10+ MIT-level innovations")
    logger.info("  ⚛️  BRQC - Quantum consensus performance")
    logger.info("  📐 Theorem 1 - Convergence validation")
    logger.info("  🛡️  Byzantine - Fault tolerance monitoring")
    logger.info("  📈 Analytics - Strategy comparison")
    logger.info("  🔬 Research - Publication-ready results")
    logger.info("")
    logger.info("=" * 80)
    logger.info("")

    # Get configuration
    config = get_config()
    config.game.rounds_per_match = num_rounds

    # Get event bus
    event_bus = get_event_bus()

    # Create Ultimate Dashboard
    logger.info("🎨 Creating Ultimate Dashboard...")
    dashboard = UltimateDashboard(port=dashboard_port)
    await dashboard.start()
    logger.info(f"✅ Dashboard running at http://localhost:{dashboard_port}")

    # Create Dashboard Integration
    logger.info("🔗 Setting up dashboard integration...")
    integration = UltimateDashboardIntegration(dashboard, event_bus)
    await integration.initialize(
        tournament_id="ultimate_league_001",
        total_rounds=num_rounds
    )
    set_ultimate_dashboard_integration(integration)
    logger.info("✅ Integration ready - all events will flow to dashboard")

    # Create Game Orchestrator
    logger.info("🎮 Creating game orchestrator...")
    orchestrator = GameOrchestrator(config, enable_dashboard=False)  # We handle dashboard ourselves

    try:
        # Define player strategies (showcase all innovations)
        player_strategies = [
            ("P01", "QuantumInspiredStrategy"),
            ("P02", "BayesianOpponentModeling"),
            ("P03", "CounterfactualRegretMinimization"),
            ("P04", "CompositeStrategy"),
            ("P05", "AdaptiveStrategy"),
            ("P06", "MixedStrategy"),
            ("P07", "NeuralNetworkStrategy"),
            ("P08", "RandomStrategy"),
        ]

        # Use requested number of players
        players = player_strategies[:num_players]

        logger.info("")
        logger.info("👥 Player Lineup:")
        for player_id, strategy in players:
            logger.info(f"  {player_id}: {strategy}")
            # Register with integration
            integration.register_player(player_id, strategy)

        logger.info("")
        logger.info("🚀 Starting league components...")

        # Start all components
        await orchestrator.start_all(
            num_players=num_players,
            num_referees=2,
            strategy="mixed"
        )

        logger.info("✅ All components started")
        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 DASHBOARD IS LIVE!")
        logger.info("=" * 80)
        logger.info("")
        logger.info("🌐 Open your browser to:")
        logger.info(f"   http://localhost:{dashboard_port}")
        logger.info("")
        logger.info("What you'll see:")
        logger.info("  • Real-time tournament progress")
        logger.info("  • Live player standings with strategies")
        logger.info("  • All 10+ innovations showcased")
        logger.info("  • BRQC performance charts")
        logger.info("  • Theorem 1 validation graphs")
        logger.info("  • Byzantine tolerance metrics")
        logger.info("  • Strategy comparison analytics")
        logger.info("  • Research-grade visualizations")
        logger.info("")
        logger.info("=" * 80)
        logger.info("")

        # Emit tournament start event
        await event_bus.emit("tournament.start", {
            "tournament_id": "ultimate_league_001",
            "num_players": num_players,
            "total_rounds": num_rounds
        })

        # Run the league
        logger.info("▶️  Starting tournament...")
        await orchestrator.run_league()

        logger.info("")
        logger.info("=" * 80)
        logger.info("🏁 TOURNAMENT COMPLETE!")
        logger.info("=" * 80)
        logger.info("")
        logger.info("🏆 Check the dashboard for:")
        logger.info("  • Final standings")
        logger.info("  • Winner celebration modal")
        logger.info("  • Complete statistics")
        logger.info("  • Strategy performance analysis")
        logger.info("")
        logger.info("📊 Dashboard will remain accessible")
        logger.info("   Press Ctrl+C to exit when done")
        logger.info("")
        logger.info("=" * 80)

        # Emit tournament complete event
        standings = integration.aggregator.get_standings()
        if standings:
            winner = standings[0]
            await event_bus.emit("tournament.complete", {
                "winner": winner
            })

        # Keep running to allow dashboard access
        try:
            await asyncio.sleep(3600)  # 1 hour
        except KeyboardInterrupt:
            pass

    except KeyboardInterrupt:
        logger.info("\n\n🛑 Shutting down...")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
    finally:
        logger.info("🧹 Cleaning up...")
        await orchestrator.stop()
        await integration.cleanup()
        await dashboard.cleanup()
        logger.info("✅ Shutdown complete")


async def run_simulated_league(
    num_players: int = 6,
    num_rounds: int = 15,
    dashboard_port: int = 8050
):
    """
    Run league with simulated data (no actual game logic).

    Useful for testing dashboard without full league setup.
    """
    logger.info("=" * 80)
    logger.info("🎮 SIMULATED LEAGUE FOR DASHBOARD TESTING")
    logger.info("=" * 80)
    logger.info("")

    # Get event bus
    event_bus = get_event_bus()

    # Create Ultimate Dashboard
    logger.info("🎨 Creating Ultimate Dashboard...")
    dashboard = UltimateDashboard(port=dashboard_port)
    await dashboard.start()
    logger.info(f"✅ Dashboard running at http://localhost:{dashboard_port}")

    # Create Dashboard Integration
    logger.info("🔗 Setting up dashboard integration...")
    integration = UltimateDashboardIntegration(dashboard, event_bus)
    await integration.initialize(
        tournament_id="simulated_league",
        total_rounds=num_rounds
    )

    logger.info("")
    logger.info(f"✅ Open http://localhost:{dashboard_port} in your browser")
    logger.info("")
    logger.info("🎮 Simulating tournament...")

    try:
        # Define players
        player_strategies = [
            ("P01", "QuantumInspiredStrategy"),
            ("P02", "BayesianOpponentModeling"),
            ("P03", "CounterfactualRegretMinimization"),
            ("P04", "CompositeStrategy"),
            ("P05", "AdaptiveStrategy"),
            ("P06", "MixedStrategy"),
        ]

        players = player_strategies[:num_players]

        # Register players
        for player_id, strategy in players:
            integration.register_player(player_id, strategy)
            await event_bus.emit("player.registered", {
                "player_id": player_id,
                "strategy": strategy
            })
            await asyncio.sleep(0.5)

        # Emit tournament start
        await event_bus.emit("tournament.start", {
            "tournament_id": "simulated_league",
            "num_players": num_players,
            "total_rounds": num_rounds
        })

        # Simulate rounds
        for round_num in range(1, num_rounds + 1):
            logger.info(f"📊 Round {round_num}/{num_rounds}")

            # Emit round start
            await event_bus.emit("round.start", {
                "round": round_num
            })

            # Simulate matches
            import random
            for player_id, strategy in players:
                # Simulate match result
                win = random.random() > 0.5
                score_gain = random.uniform(1.0, 3.0) if win else random.uniform(0.0, 1.0)

                # Update player stats
                integration.aggregator.update_player_stats(player_id,
                    score=integration.aggregator.players[player_id]["score"] + score_gain,
                    wins=integration.aggregator.players[player_id]["wins"] + (1 if win else 0),
                    total_matches=integration.aggregator.players[player_id]["total_matches"] + 1
                )

            # Emit round complete
            await event_bus.emit("round.complete", {
                "round": round_num,
                "stats": {}
            })

            await asyncio.sleep(2)

        # Get winner
        standings = integration.aggregator.get_standings()
        winner = standings[0] if standings else None

        if winner:
            logger.info(f"\n🏆 Winner: {winner['player_id']} ({winner['strategy']})")
            logger.info(f"   Score: {winner['score']:.1f}")
            logger.info(f"   Wins: {winner['wins']}/{winner['total_matches']}")

            await event_bus.emit("tournament.complete", {
                "winner": winner
            })

        logger.info("\n✨ Simulation complete! Dashboard shows final results")
        logger.info("   Press Ctrl+C to exit")

        # Keep running
        await asyncio.sleep(3600)

    except KeyboardInterrupt:
        logger.info("\n\n🛑 Exiting...")
    finally:
        await integration.cleanup()
        await dashboard.cleanup()


async def run_quick_demo():
    """Run a quick 5-round demo."""
    await run_ultimate_league(
        num_players=4,
        num_rounds=5,
        dashboard_port=8050
    )


if __name__ == "__main__":
    import argparse

    # Setup logging
    setup_logging(level="INFO")

    parser = argparse.ArgumentParser(
        description="Run Ultimate MIT-Level Game League with Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--players",
        type=int,
        default=6,
        help="Number of players (default: 6)"
    )

    parser.add_argument(
        "--rounds",
        type=int,
        default=15,
        help="Rounds per match (default: 15)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8050,
        help="Dashboard port (default: 8050)"
    )

    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run with simulated data (fast testing)"
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick demo (4 players, 5 rounds)"
    )

    args = parser.parse_args()

    try:
        if args.quick:
            asyncio.run(run_quick_demo())
        elif args.simulate:
            asyncio.run(run_simulated_league(
                num_players=args.players,
                num_rounds=args.rounds,
                dashboard_port=args.port
            ))
        else:
            asyncio.run(run_ultimate_league(
                num_players=args.players,
                num_rounds=args.rounds,
                dashboard_port=args.port
            ))
    except KeyboardInterrupt:
        logger.info("\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
