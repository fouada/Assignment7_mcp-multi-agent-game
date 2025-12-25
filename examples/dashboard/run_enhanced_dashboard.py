"""
Run Enhanced Dashboard with Player Strategies Display
======================================================

This script runs a tournament with the enhanced dashboard that prominently displays:
1. Each player's strategy
2. Round-by-round progress
3. Detailed standings table
4. Winner celebration with strategy

Usage:
    python examples/dashboard/run_enhanced_dashboard.py
    
Then open your browser to: http://localhost:8050
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.agents.game_orchestrator import GameOrchestrator
from src.common.config_loader import get_config
from src.common.logger import get_logger

logger = get_logger(__name__)


async def run_enhanced_dashboard_demo(
    num_players: int = 6,
    num_rounds: int = 15,
    dashboard_port: int = 8050
):
    """
    Run a tournament with enhanced dashboard.
    
    Args:
        num_players: Number of players (each with different strategy)
        num_rounds: Number of rounds to play
        dashboard_port: Port for dashboard server
    """
    logger.info("=" * 70)
    logger.info("🎮 ENHANCED DASHBOARD DEMO - Player Strategies Display")
    logger.info("=" * 70)
    
    # Load configuration
    config = get_config()
    
    # Define players with different strategies
    player_strategies = [
        ("P01", "RandomStrategy"),
        ("P02", "BayesianOpponentModeling"),
        ("P03", "CounterfactualRegretMinimization"),
        ("P04", "CompositeStrategy"),
        ("P05", "AdaptiveStrategy"),
        ("P06", "MixedStrategy"),
    ]
    
    # Take only the requested number of players
    players = player_strategies[:num_players]
    
    logger.info(f"\n📋 Tournament Configuration:")
    logger.info(f"  • Players: {num_players}")
    logger.info(f"  • Rounds: {num_rounds}")
    logger.info(f"  • Dashboard: http://localhost:{dashboard_port}")
    logger.info(f"\n👥 Player Strategies:")
    for player_id, strategy in players:
        logger.info(f"  • {player_id}: {strategy}")
    
    # Create orchestrator with dashboard enabled
    logger.info(f"\n🚀 Starting tournament with enhanced dashboard...")
    orchestrator = GameOrchestrator(
        config,
        enable_dashboard=True,
        dashboard_port=dashboard_port
    )
    
    # Register players with their strategies
    player_configs = []
    for player_id, strategy_name in players:
        player_configs.append({
            "id": player_id,
            "name": f"Player {player_id}",
            "strategy": strategy_name,
            "endpoint": f"http://localhost:5000/player/{player_id}"  # Mock endpoint
        })
    
    # Start all components
    await orchestrator.start_all(
        player_configs=player_configs,
        num_rounds=num_rounds
    )
    
    logger.info(f"\n✅ Dashboard running at: http://localhost:{dashboard_port}")
    logger.info(f"   Open this URL in your browser to see:")
    logger.info(f"   • Each player's strategy (in standings table)")
    logger.info(f"   • Round-by-round progress bar")
    logger.info(f"   • Live standings with win rates")
    logger.info(f"   • Winner celebration with strategy highlight")
    
    # Run the league
    logger.info(f"\n▶️  Starting tournament...")
    await orchestrator.run_league()
    
    # Keep dashboard running to see final results
    logger.info(f"\n🏁 Tournament Complete!")
    logger.info(f"   • Dashboard still running at http://localhost:{dashboard_port}")
    logger.info(f"   • Check the winner celebration modal!")
    logger.info(f"   • Press Ctrl+C to exit")
    
    try:
        # Keep running to view results
        await asyncio.sleep(300)  # 5 minutes
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down dashboard...")
    
    # Cleanup
    await orchestrator.cleanup()


async def run_quick_demo():
    """Run a quick 4-player, 5-round demo."""
    logger.info("🎯 Running Quick Demo (4 players, 5 rounds)")
    await run_enhanced_dashboard_demo(
        num_players=4,
        num_rounds=5,
        dashboard_port=8050
    )


async def run_full_demo():
    """Run a full 6-player, 15-round demo."""
    logger.info("🎯 Running Full Demo (6 players, 15 rounds)")
    await run_enhanced_dashboard_demo(
        num_players=6,
        num_rounds=15,
        dashboard_port=8050
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run tournament with enhanced dashboard showing player strategies"
    )
    parser.add_argument(
        "--players",
        type=int,
        default=6,
        help="Number of players (2-6, default: 6)"
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=15,
        help="Number of rounds (default: 15)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8050,
        help="Dashboard port (default: 8050)"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick demo (4 players, 5 rounds)"
    )
    
    args = parser.parse_args()
    
    if args.quick:
        asyncio.run(run_quick_demo())
    else:
        asyncio.run(run_enhanced_dashboard_demo(
            num_players=args.players,
            num_rounds=args.rounds,
            dashboard_port=args.port
        ))

