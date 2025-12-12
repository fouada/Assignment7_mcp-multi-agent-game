"""
Main Entry Point
================

Orchestrates the MCP Multi-Agent Game League.

Usage:
    # Start full league with all components
    python -m src.main
    
    # Start only league manager
    python -m src.main --component league
    
    # Start only referee
    python -m src.main --component referee
    
    # Start a player
    python -m src.main --component player --name "Player1" --port 8101
"""

import asyncio
import argparse
import signal
import sys
from typing import List, Optional

from .common.logger import setup_logging, get_logger
from .common.config import Config, get_config
from .agents.league_manager import LeagueManager
from .agents.referee import RefereeAgent
from .agents.player import PlayerAgent, RandomStrategy, PatternStrategy, LLMStrategy

logger = get_logger(__name__)


class GameOrchestrator:
    """
    Orchestrates the full game league.
    
    Manages:
    - League Manager
    - Referee
    - Multiple Players
    """
    
    def __init__(self, config: Config):
        self.config = config
        
        # Components
        self.league_manager: Optional[LeagueManager] = None
        self.referee: Optional[RefereeAgent] = None
        self.players: List[PlayerAgent] = []
        
        # State
        self._running = False
        self._shutdown_event = asyncio.Event()
    
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
    
    async def start_referee(self) -> RefereeAgent:
        """Start the referee."""
        self.referee = RefereeAgent(
            league_id=self.config.league.league_id,
            host=self.config.referee.host,
            port=self.config.referee.port,
            move_timeout=self.config.game.move_timeout,
            league_manager_url=self.config.league_manager.url,
        )
        
        await self.referee.start()
        logger.info(f"Referee started at {self.referee.url}")
        
        return self.referee
    
    async def start_player(
        self,
        name: str,
        port: int,
        strategy_type: str = "random",
    ) -> PlayerAgent:
        """Start a player agent."""
        # Create strategy
        if strategy_type == "random":
            strategy = RandomStrategy()
        elif strategy_type == "pattern":
            strategy = PatternStrategy()
        elif strategy_type == "llm":
            strategy = LLMStrategy(self.config.llm)
        else:
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
    
    async def start_all(self, num_players: int = 4) -> None:
        """Start all components."""
        logger.info("Starting MCP Game League...")
        
        # Start league manager
        await self.start_league_manager()
        
        # Wait a bit for league manager to be ready
        await asyncio.sleep(0.5)
        
        # Start referee
        await self.start_referee()
        
        # Wait a bit
        await asyncio.sleep(0.5)
        
        # Start players
        strategies = ["random", "pattern", "random", "pattern"]
        for i in range(num_players):
            name = f"Player_{i + 1}"
            port = 8101 + i
            strategy = strategies[i % len(strategies)]
            
            player = await self.start_player(name, port, strategy)
            
            # Register with league
            await asyncio.sleep(0.2)
            await player.register_with_league()
        
        self._running = True
        logger.info(f"League started with {num_players} players")
    
    async def run_league(self) -> None:
        """Run the complete league."""
        if not self._running:
            await self.start_all()
        
        # Wait for enough players
        while self.league_manager.player_count < self.config.league.min_players:
            logger.info(f"Waiting for players... ({self.league_manager.player_count}/{self.config.league.min_players})")
            await asyncio.sleep(1)
        
        # Start the league
        result = await self.league_manager._start_league()
        if not result.get("success"):
            logger.error(f"Failed to start league: {result.get('error')}")
            return
        
        logger.info("League competition started!")
        
        # Run rounds
        total_rounds = result.get("rounds", 0)
        for round_num in range(total_rounds):
            logger.info(f"\n{'='*50}")
            logger.info(f"Starting Round {round_num + 1}/{total_rounds}")
            logger.info(f"{'='*50}\n")
            
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
                await self._run_match(match_data)
            
            # Wait for matches to complete
            await asyncio.sleep(2)
            
            # Show standings
            standings = self.league_manager._get_standings()
            logger.info("\nCurrent Standings:")
            for entry in standings.get("standings", []):
                logger.info(f"  {entry['rank']}. {entry['display_name']}: {entry['points']} pts")
        
        # Final standings
        logger.info("\n" + "="*50)
        logger.info("LEAGUE COMPLETE - Final Standings")
        logger.info("="*50)
        
        standings = self.league_manager._get_standings()
        for entry in standings.get("standings", []):
            logger.info(f"  {entry['rank']}. {entry['display_name']}: {entry['points']} pts ({entry['wins']}W-{entry['losses']}L)")
    
    async def _run_match(self, match_data: Dict) -> None:
        """Run a single match through the referee."""
        try:
            result = await self.referee._start_match({
                "match_id": match_data.get("match_id"),
                "player1_id": match_data.get("player1", {}).get("player_id"),
                "player1_endpoint": match_data.get("player1", {}).get("endpoint"),
                "player2_id": match_data.get("player2", {}).get("player_id"),
                "player2_endpoint": match_data.get("player2", {}).get("endpoint"),
                "rounds": self.config.game.rounds_per_match,
            })
            
            logger.debug(f"Match started: {result}")
            
        except Exception as e:
            logger.error(f"Match error: {e}")
    
    async def stop(self) -> None:
        """Stop all components."""
        logger.info("Stopping league...")
        
        # Stop players
        for player in self.players:
            await player.stop()
        self.players.clear()
        
        # Stop referee
        if self.referee:
            await self.referee.stop()
            self.referee = None
        
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
    
    if component == "league":
        server = LeagueManager(
            league_id=config.league.league_id,
            port=args.port or config.league_manager.port,
        )
    elif component == "referee":
        server = RefereeAgent(
            league_id=config.league.league_id,
            port=args.port or config.referee.port,
        )
    elif component == "player":
        server = PlayerAgent(
            player_name=args.name or "Player",
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
        
        if component == "player" and args.register:
            await server.register_with_league()
        
        await shutdown_event.wait()
        
    finally:
        await server.stop()


async def run_full_league(args: argparse.Namespace) -> None:
    """Run the full league."""
    setup_logging(level="DEBUG" if args.debug else "INFO")
    config = get_config()
    
    orchestrator = GameOrchestrator(config)
    
    # Handle shutdown
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        orchestrator.request_shutdown()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    try:
        await orchestrator.start_all(num_players=args.players)
        
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
        description="MCP Multi-Agent Game League"
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
        help="Name (for player component)",
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
        help="Number of players (for full league)",
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
    
    args = parser.parse_args()
    
    if args.component == "all":
        asyncio.run(run_full_league(args))
    else:
        asyncio.run(run_component(args.component, args))


if __name__ == "__main__":
    main()

