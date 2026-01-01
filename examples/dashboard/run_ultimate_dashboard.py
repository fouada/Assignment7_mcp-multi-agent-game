"""
Run Ultimate MIT-Level Dashboard
=================================

This script demonstrates the ultimate dashboard showcasing:
- All 10+ MIT-level innovations
- Real-time tournament visualization
- BRQC performance monitoring
- Theorem 1 convergence validation
- Byzantine fault tolerance metrics
- Strategy comparison and analytics
- Research-grade visualizations

Usage:
    python examples/dashboard/run_ultimate_dashboard.py

Then open your browser to: http://localhost:8050
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.visualization.ultimate_dashboard import UltimateDashboard
from src.common.logger import get_logger

logger = get_logger(__name__)


async def run_ultimate_dashboard_demo(
    port: int = 8050,
    duration: int = 600  # 10 minutes
):
    """
    Run the ultimate dashboard demo.

    Args:
        port: Port for dashboard server
        duration: How long to keep the dashboard running (seconds)
    """
    logger.info("=" * 80)
    logger.info("🏆 ULTIMATE MIT-LEVEL DASHBOARD")
    logger.info("=" * 80)
    logger.info("")
    logger.info("This dashboard showcases:")
    logger.info("  ⚛️  Byzantine-Resistant Quantum Consensus (BRQC)")
    logger.info("  📐 Theorem 1: Quantum Convergence Validation")
    logger.info("  🛡️  Byzantine Fault Tolerance Monitoring")
    logger.info("  🎯 Strategy Comparison & Analytics")
    logger.info("  💡 10+ World-First Innovations")
    logger.info("  🔬 Research Validation Dashboard")
    logger.info("")
    logger.info("=" * 80)

    # Create and start dashboard
    dashboard = UltimateDashboard(port=port)
    await dashboard.start()

    logger.info("")
    logger.info(f"✅ Dashboard is now running!")
    logger.info(f"   🌐 URL: http://localhost:{port}")
    logger.info("")
    logger.info("📊 Available Tabs:")
    logger.info("   1. Overview - Key metrics and system status")
    logger.info("   2. Tournament - Real-time standings and match data")
    logger.info("   3. Innovations - Showcase of all 10+ innovations")
    logger.info("   4. BRQC Performance - Convergence and speedup charts")
    logger.info("   5. Theorem 1 - Quantum vs classical validation")
    logger.info("   6. Byzantine - Fault tolerance monitoring")
    logger.info("   7. Analytics - Advanced strategy comparison")
    logger.info("   8. Research - Publication-ready results")
    logger.info("")
    logger.info("🎮 Features:")
    logger.info("   • Real-time WebSocket updates")
    logger.info("   • Interactive Plotly charts")
    logger.info("   • Innovation showcase with live metrics")
    logger.info("   • BRQC experimental data visualization")
    logger.info("   • Theorem 1 convergence proof validation")
    logger.info("   • Byzantine fault tolerance metrics")
    logger.info("   • Strategy effectiveness heatmaps")
    logger.info("   • Research validation dashboard")
    logger.info("")
    logger.info("=" * 80)
    logger.info(f"⏱️  Dashboard will run for {duration} seconds")
    logger.info("   Press Ctrl+C to exit earlier")
    logger.info("=" * 80)

    try:
        # Keep dashboard running
        await asyncio.sleep(duration)

        logger.info("\n⏰ Time limit reached. Shutting down...")

    except KeyboardInterrupt:
        logger.info("\n\n👋 Shutting down dashboard...")

    finally:
        await dashboard.cleanup()
        logger.info("✅ Dashboard stopped successfully")


async def run_with_tournament_simulation():
    """Run dashboard with simulated tournament data."""
    logger.info("🎮 Running Ultimate Dashboard with Tournament Simulation")
    logger.info("=" * 80)

    # Create dashboard
    dashboard = UltimateDashboard(port=8050)
    await dashboard.start()

    logger.info("\n✅ Dashboard running with live tournament simulation")
    logger.info("   Open http://localhost:8050 in your browser")
    logger.info("")

    # Simulate tournament progress
    try:
        total_rounds = 10
        num_players = 6

        # Initial players
        players = [
            {
                "player_id": f"P{i+1:02d}",
                "strategy": strategy,
                "score": 0,
                "wins": 0,
                "total_matches": 0
            }
            for i, strategy in enumerate([
                "RandomStrategy",
                "BayesianOpponentModeling",
                "QuantumInspiredStrategy",
                "ByzantineResistantStrategy",
                "CounterfactualRegretMinimization",
                "CompositeStrategy"
            ][:num_players])
        ]

        # Simulate rounds
        for round_num in range(1, total_rounds + 1):
            logger.info(f"📊 Round {round_num}/{total_rounds}")

            # Update player stats (simulated)
            for player in players:
                import random
                # Simulate match results
                player["total_matches"] += 2
                win = random.random() > 0.5
                if win:
                    player["wins"] += 1
                    player["score"] += random.uniform(1.0, 3.0)
                else:
                    player["score"] += random.uniform(0.0, 1.0)

            # Sort by score
            standings = sorted(players, key=lambda p: p["score"], reverse=True)

            # Send update to dashboard
            await dashboard.send_tournament_update(
                current_round=round_num,
                total_rounds=total_rounds,
                standings=standings
            )

            # Wait before next round
            await asyncio.sleep(3)

        # Tournament complete - send winner
        winner = standings[0]
        logger.info(f"\n🏆 Tournament Complete! Winner: {winner['player_id']}")
        logger.info(f"   Strategy: {winner['strategy']}")
        logger.info(f"   Score: {winner['score']:.1f}")
        logger.info(f"   Wins: {winner['wins']}/{winner['total_matches']}")

        await dashboard.send_tournament_complete(winner)

        logger.info("\n✨ Dashboard will continue running to display results")
        logger.info("   Press Ctrl+C to exit")

        # Keep running to show results
        await asyncio.sleep(300)

    except KeyboardInterrupt:
        logger.info("\n\n👋 Shutting down...")

    finally:
        await dashboard.cleanup()


async def run_quick_demo():
    """Run a quick 2-minute demo."""
    logger.info("🎯 Running Quick Demo (2 minutes)")
    await run_ultimate_dashboard_demo(port=8050, duration=120)


async def run_full_demo():
    """Run a full 10-minute demo."""
    logger.info("🎯 Running Full Demo (10 minutes)")
    await run_ultimate_dashboard_demo(port=8050, duration=600)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run Ultimate MIT-Level Dashboard"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8050,
        help="Dashboard port (default: 8050)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=600,
        help="How long to run dashboard in seconds (default: 600)"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick 2-minute demo"
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run with simulated tournament data"
    )

    args = parser.parse_args()

    if args.simulate:
        asyncio.run(run_with_tournament_simulation())
    elif args.quick:
        asyncio.run(run_quick_demo())
    else:
        asyncio.run(run_ultimate_dashboard_demo(
            port=args.port,
            duration=args.duration
        ))
