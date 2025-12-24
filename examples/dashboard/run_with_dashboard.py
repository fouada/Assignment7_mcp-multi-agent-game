"""
Dashboard Demo - Running Tournament with Real-Time Visualization
================================================================

This example demonstrates Innovation #4: Real-Time Interactive Dashboard

**What it shows:**
1. Starting a tournament with dashboard enabled
2. Real-time visualization of game state
3. Monitoring opponent modeling beliefs
4. Tracking counterfactual regrets
5. Observing strategy composition decisions
6. Interactive web-based interface

**How to run:**
```bash
# From project root:
python examples/dashboard/run_with_dashboard.py

# Then open browser to:
http://localhost:8050
```

**What you'll see:**
- Tournament overview with live standings
- Real-time game event stream
- Strategy performance charts over time
- Opponent modeling confidence graphs
- Counterfactual regret analysis
- Export data functionality

**Innovation Highlights:**
This is the first real-time dashboard for multi-agent game theory research that:
- Visualizes internal agent reasoning (beliefs, regrets)
- Enables interactive analysis during gameplay
- Provides publication-quality visualizations
- Supports time-travel debugging through replay
"""

import asyncio
import argparse
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.common.logger import setup_logging, get_logger
from src.common.config import get_config
from src.main import GameOrchestrator

logger = get_logger(__name__)


async def run_dashboard_demo(num_players: int = 4, num_rounds: int = 10):
    """
    Run a demo tournament with dashboard enabled.

    Args:
        num_players: Number of players (default: 4)
        num_rounds: Rounds per match (default: 10)
    """
    logger.info("="*70)
    logger.info("DASHBOARD DEMO - Multi-Agent Game League")
    logger.info("="*70)
    logger.info("")
    logger.info("This demo showcases Innovation #4: Real-Time Interactive Dashboard")
    logger.info("")
    logger.info("Features demonstrated:")
    logger.info("  ✓ Real-time WebSocket streaming")
    logger.info("  ✓ Interactive tournament visualization")
    logger.info("  ✓ Strategy performance tracking")
    logger.info("  ✓ Live standings and metrics")
    logger.info("")
    logger.info(f"Configuration:")
    logger.info(f"  Players: {num_players}")
    logger.info(f"  Rounds per match: {num_rounds}")
    logger.info("")
    logger.info("="*70)
    logger.info("")

    # Get config
    config = get_config()

    # Override rounds per match
    config.game.rounds_per_match = num_rounds

    # Create orchestrator with dashboard enabled
    orchestrator = GameOrchestrator(config, enable_dashboard=True)

    try:
        # Start all components
        logger.info("🚀 Starting league components...")
        await orchestrator.start_all(
            num_players=num_players,
            num_referees=2,
            strategy="mixed"  # Mix of random and pattern
        )

        logger.info("")
        logger.info("✅ League started!")
        logger.info("")
        logger.info("="*70)
        logger.info("📊 DASHBOARD IS NOW LIVE!")
        logger.info("="*70)
        logger.info("")
        logger.info("Open your browser to:")
        logger.info("  🌐 http://localhost:8050")
        logger.info("")
        logger.info("You will see:")
        logger.info("  • Real-time tournament overview")
        logger.info("  • Live standings table")
        logger.info("  • Strategy performance charts")
        logger.info("  • Game event log (streaming)")
        logger.info("")
        logger.info("Press Ctrl+C to stop the demo")
        logger.info("="*70)
        logger.info("")

        # Wait for players to register
        await asyncio.sleep(2)

        # Run the league
        await orchestrator.run_league()

        logger.info("")
        logger.info("="*70)
        logger.info("🏁 Tournament Complete!")
        logger.info("="*70)
        logger.info("")
        logger.info("The dashboard remains accessible for post-game analysis.")
        logger.info("Press Ctrl+C when done.")
        logger.info("")

        # Keep running to allow dashboard access
        await orchestrator.wait_for_shutdown()

    except KeyboardInterrupt:
        logger.info("\n\n🛑 Shutting down...")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        await orchestrator.stop()
        logger.info("✅ Demo complete!")


async def run_custom_strategies_demo():
    """
    Run demo with custom innovation strategies.

    This would demonstrate:
    - Opponent modeling engine integration
    - Counterfactual regret minimization
    - Hierarchical strategy composition

    Note: Requires implementing innovation strategies in PlayerAgent
    """
    logger.info("="*70)
    logger.info("INNOVATION STRATEGIES DEMO")
    logger.info("="*70)
    logger.info("")
    logger.info("⚠️  This demo requires innovation strategies to be")
    logger.info("   integrated into PlayerAgent.")
    logger.info("")
    logger.info("Innovations to integrate:")
    logger.info("  1. Opponent Modeling with Bayesian Inference")
    logger.info("  2. Counterfactual Regret Minimization (CFR)")
    logger.info("  3. Hierarchical Strategy Composition")
    logger.info("")
    logger.info("Once integrated, this demo will show:")
    logger.info("  • Real-time opponent belief updates")
    logger.info("  • Counterfactual regret accumulation")
    logger.info("  • Strategy composition decisions")
    logger.info("")
    logger.info("="*70)

    # For now, run standard demo
    await run_dashboard_demo(num_players=4, num_rounds=10)


def main():
    """Main entry point for dashboard demo."""
    parser = argparse.ArgumentParser(
        description="Dashboard Demo for Multi-Agent Game League",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic demo with 4 players
  python examples/dashboard/run_with_dashboard.py

  # Demo with 6 players
  python examples/dashboard/run_with_dashboard.py --players 6

  # Demo with custom rounds
  python examples/dashboard/run_with_dashboard.py --players 4 --rounds 20

  # Demo with innovation strategies (future)
  python examples/dashboard/run_with_dashboard.py --innovation

Quick Start:
  1. Run this script
  2. Open http://localhost:8050 in browser
  3. Watch the tournament live!
  4. Press Ctrl+C when done
        """
    )

    parser.add_argument(
        "--players",
        type=int,
        default=4,
        help="Number of players (default: 4)",
    )

    parser.add_argument(
        "--rounds",
        type=int,
        default=10,
        help="Rounds per match (default: 10)",
    )

    parser.add_argument(
        "--innovation",
        action="store_true",
        help="Use innovation strategies (opponent modeling, CFR, composition)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(level="DEBUG" if args.debug else "INFO")

    # Run demo
    if args.innovation:
        asyncio.run(run_custom_strategies_demo())
    else:
        asyncio.run(run_dashboard_demo(
            num_players=args.players,
            num_rounds=args.rounds
        ))


if __name__ == "__main__":
    main()
