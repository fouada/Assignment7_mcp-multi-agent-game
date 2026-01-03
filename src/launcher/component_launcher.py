"""
Component Launcher - MIT Level
===============================

Launches individual components with proper initialization, registration,
and state synchronization.

Features:
- Independent component startup
- Automatic service discovery and registration
- State synchronization with dashboard
- Health monitoring
- Graceful shutdown
"""

import asyncio
import signal
from enum import Enum
from typing import Any

from ..agents.league_manager import LeagueManager
from ..agents.player import PlayerAgent
from ..agents.referee import RefereeAgent
from ..agents.strategies import RandomStrategy, Strategy
from ..common.config import Config, get_config
from ..common.events import get_event_bus
from ..common.logger import get_logger
from .service_registry import ServiceRegistry, get_service_registry
from .state_sync import StateSyncService, get_state_sync

logger = get_logger(__name__)


class ComponentType(Enum):
    """Component types that can be launched."""

    LEAGUE_MANAGER = "league_manager"
    REFEREE = "referee"
    PLAYER = "player"
    DASHBOARD = "dashboard"


class ComponentLauncher:
    """
    Launches and manages individual components with state synchronization.

    Usage:
        # Launch League Manager + Dashboard
        launcher = ComponentLauncher(ComponentType.LEAGUE_MANAGER)
        await launcher.start(enable_dashboard=True)

        # Launch Referee
        launcher = ComponentLauncher(ComponentType.REFEREE)
        await launcher.start(referee_id="REF01", port=8001)

        # Launch Player
        launcher = ComponentLauncher(ComponentType.PLAYER)
        await launcher.start(name="Player_1", strategy="llm", port=8101)
    """

    def __init__(self, component_type: ComponentType, config: Config | None = None):
        self.component_type = component_type
        self.config = config or get_config()

        # Components
        self.component: LeagueManager | RefereeAgent | PlayerAgent | None = None
        self.dashboard: Any = None
        self._integration: Any = None  # Dashboard integration instance

        # Infrastructure
        self.event_bus = get_event_bus()
        self.service_registry: ServiceRegistry = get_service_registry()
        self.state_sync: StateSyncService = get_state_sync()

        # State
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._service_id: str | None = None  # Track service ID for unregistration

        logger.info(f"ComponentLauncher initialized for {component_type.value}")

    async def start(self, **kwargs: Any) -> None:
        """
        Start the component with given configuration.

        Args:
            **kwargs: Component-specific configuration
        """
        logger.info(f"Starting {self.component_type.value}...")

        # Initialize state sync
        await self.state_sync.start()

        if self.component_type == ComponentType.LEAGUE_MANAGER:
            await self._start_league_manager(**kwargs)
        elif self.component_type == ComponentType.REFEREE:
            await self._start_referee(**kwargs)
        elif self.component_type == ComponentType.PLAYER:
            await self._start_player(**kwargs)
        else:
            raise ValueError(f"Unknown component type: {self.component_type}")

        self._running = True
        logger.info(f"✓ {self.component_type.value} started successfully")

        # Setup signal handlers (not supported on Windows)
        loop = asyncio.get_event_loop()

        def signal_handler():
            self._shutdown_event.set()

        try:
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Signal handlers are not supported on Windows
            pass

    async def _start_league_manager(self, **kwargs: Any) -> None:
        """Start League Manager with optional dashboard."""
        enable_dashboard = kwargs.get("enable_dashboard", True)
        port = kwargs.get("port", self.config.league_manager.port)

        # Create League Manager
        self.component = LeagueManager(
            league_id=self.config.league.league_id,
            min_players=self.config.league.min_players,
            max_players=self.config.league.max_players,
            host=self.config.league_manager.host,
            port=port,
        )

        await self.component.start()

        # Register with service registry
        self._service_id = self.component.name
        await self.service_registry.register_service(
            service_id=self._service_id,
            service_type="league_manager",
            endpoint=self.component.url,
            metadata={
                "league_id": self.config.league.league_id,
                "min_players": self.config.league.min_players,
                "max_players": self.config.league.max_players,
            },
        )

        # Start dashboard if enabled
        if enable_dashboard:
            await self._start_dashboard()

            # Connect dashboard to league manager
            if self.dashboard:
                self.component.set_dashboard(self.dashboard)

                # Subscribe dashboard to all state changes
                await self.state_sync.subscribe_to_all_events(self.dashboard)

        logger.info(f"League Manager running at {self.component.url}")
        if enable_dashboard:
            logger.info("Dashboard enabled at http://localhost:8050")

    async def _start_dashboard(self) -> None:
        """Start the dashboard server."""
        from ..visualization import get_dashboard
        from ..visualization.integration import get_dashboard_integration

        self.dashboard = get_dashboard()
        integration = get_dashboard_integration()

        # Start dashboard server
        import os

        dashboard_host = os.getenv("DASHBOARD_HOST", "127.0.0.1")
        await self.dashboard.start_server_background(host=dashboard_host, port=8050)

        # Initialize integration
        await integration.start(
            tournament_id=self.config.league.league_id,
            total_rounds=0,
        )

        # Connect event bus to dashboard
        # Connect to actual events being emitted by the system
        self.event_bus.on("round.started", self._on_round_started)
        self.event_bus.on("player.move.after", self._on_player_move)
        self.event_bus.on("round.completed", self._on_round_completed)

        # Connect strategy learning events for dashboard visualization
        self.event_bus.on("opponent.model.update", self._on_opponent_model_update)
        self.event_bus.on("counterfactual.analysis", self._on_counterfactual_analysis)
        self.event_bus.on("match.completed", self._on_match_completed)
        self.event_bus.on("standings.updated", self._on_standings_updated)

        # Store integration for event handlers
        self._integration = integration

        logger.info("✓ Dashboard started and connected to event bus (including strategy learning events)")

    async def _on_round_started(self, event: Any) -> None:
        """Forward round started event to integration."""
        try:
            await self._integration.on_round_start(round_num=event.round_number, matches=[])
        except Exception as e:
            logger.error(f"Error forwarding round started event: {e}")

    async def _on_player_move(self, event: Any) -> None:
        """Forward player move event to integration."""
        try:
            # We need to get the opponent ID from the game
            # For now, just pass empty string for opponent_id
            await self._integration.on_move_decision(
                player_id=event.player_id,
                opponent_id="",  # Will be filled in by integration
                round_num=event.round_number,
                move=str(event.move),
                game_state={"game_id": event.game_id},
            )
        except Exception as e:
            logger.error(f"Error forwarding player move event: {e}")

    async def _on_round_completed(self, event: Any) -> None:
        """Forward round completed event to integration."""
        try:
            # Extract player IDs from moves dict
            player_ids = list(event.moves.keys())
            if len(player_ids) >= 2:
                await self._integration.on_round_complete(
                    round_num=event.round_number,
                    player1_id=player_ids[0],
                    player2_id=player_ids[1],
                    moves={k: str(v) for k, v in event.moves.items()},
                    scores={k: float(v) for k, v in event.cumulative_scores.items()},
                )
        except Exception as e:
            logger.error(f"Error forwarding round completed event: {e}")

    async def _on_opponent_model_update(self, event: Any) -> None:
        """Forward opponent model update event to integration."""
        logger.info(f"[Launcher] 🔍 DEBUG: Received opponent_model_update event from {event.player_id if hasattr(event, 'player_id') else 'unknown'}")
        try:
            if self._integration:
                await self._integration.on_opponent_model_update(event)
                logger.info(f"[Launcher] ✅ Successfully forwarded opponent_model_update to integration")
            else:
                logger.warning(f"[Launcher] ⚠️ No integration available to forward opponent_model_update")
        except Exception as e:
            logger.error(f"[Launcher] ❌ Error forwarding opponent model update event: {e}", exc_info=True)

    async def _on_counterfactual_analysis(self, event: Any) -> None:
        """Forward counterfactual analysis event to integration."""
        logger.info(f"[Launcher] 🔍 DEBUG: Received counterfactual_analysis event from {event.player_id if hasattr(event, 'player_id') else 'unknown'}")
        try:
            if self._integration:
                await self._integration.on_counterfactual_analysis(event)
                logger.info(f"[Launcher] ✅ Successfully forwarded counterfactual_analysis to integration")
            else:
                logger.warning(f"[Launcher] ⚠️ No integration available to forward counterfactual_analysis")
        except Exception as e:
            logger.error(f"[Launcher] ❌ Error forwarding counterfactual analysis event: {e}", exc_info=True)

    async def _on_match_completed(self, event: Any) -> None:
        """Forward match completed event to integration."""
        logger.info(f"[Launcher] 🔍 DEBUG: Received match_completed event")
        try:
            if self._integration:
                # Extract match data and forward to integration
                match_id = getattr(event, 'match_id', 'unknown')
                player1_id = getattr(event, 'player1_id', 'unknown')
                player2_id = getattr(event, 'player2_id', 'unknown')
                winner_id = getattr(event, 'winner', None)

                logger.info(f"[Launcher] Match completed: {match_id} ({player1_id} vs {player2_id}), winner: {winner_id}")

                # Forward to integration
                await self._integration.on_match_completed(event)
                logger.info(f"[Launcher] ✅ Successfully forwarded match_completed to integration")
            else:
                logger.warning(f"[Launcher] ⚠️ No integration available to forward match_completed")
        except Exception as e:
            logger.error(f"[Launcher] ❌ Error forwarding match completed event: {e}", exc_info=True)

    async def _on_standings_updated(self, event: Any) -> None:
        """Forward standings updated event to integration and broadcast tournament state."""
        logger.info(f"[Launcher] 🔍 DEBUG: Received standings_updated event for round {getattr(event, 'round_number', 'unknown')}")
        try:
            if self._integration:
                # Get the dashboard instance
                dashboard = self._integration.dashboard

                # Get current tournament state from dashboard's stored states
                if dashboard.tournament_states:
                    # Broadcast the updated tournament state to all connected clients
                    for tournament_id, state in dashboard.tournament_states.items():
                        from dataclasses import asdict
                        state_dict = asdict(state)

                        # Convert datetimes
                        def convert_datetimes(obj):
                            if isinstance(obj, dict):
                                return {k: convert_datetimes(v) for k, v in obj.items()}
                            elif isinstance(obj, list):
                                return [convert_datetimes(item) for item in obj]
                            elif hasattr(obj, 'isoformat'):
                                return obj.isoformat()
                            return obj

                        serializable_state = convert_datetimes(state_dict)

                        await dashboard.connection_manager.broadcast({
                            "type": "tournament_state",
                            "tournament_id": tournament_id,
                            "data": serializable_state
                        })

                        logger.info(f"[Launcher] ✅ Broadcasted updated tournament state for {tournament_id}")
                else:
                    logger.warning(f"[Launcher] ⚠️ No tournament states available to broadcast")
            else:
                logger.warning(f"[Launcher] ⚠️ No integration available to forward standings_updated")
        except Exception as e:
            logger.error(f"[Launcher] ❌ Error handling standings updated event: {e}", exc_info=True)

    async def _start_referee(self, **kwargs: Any) -> None:
        """Start a referee agent."""
        referee_id = kwargs.get("referee_id", "REF01")
        port = kwargs.get("port", self.config.referee.port)
        league_manager_url = kwargs.get("league_manager_url", self.config.league_manager.url)

        # Create Referee
        self.component = RefereeAgent(
            referee_id=referee_id,
            league_id=self.config.league.league_id,
            host=self.config.referee.host,
            port=port,
            move_timeout=self.config.game.move_timeout,
            league_manager_url=league_manager_url,
        )

        await self.component.start()

        # Register with service registry
        self._service_id = referee_id
        await self.service_registry.register_service(
            service_id=self._service_id,
            service_type="referee",
            endpoint=self.component.url,
            metadata={"league_id": self.config.league.league_id},
        )

        # Auto-register with league manager if requested
        if kwargs.get("auto_register", True):
            await self.component.register_with_league()
            logger.info(f"Referee {referee_id} registered with league manager")

        logger.info(f"Referee {referee_id} running at {self.component.url}")

    async def _start_player(self, **kwargs: Any) -> None:
        """Start a player agent."""
        name = kwargs.get("name", "Player")
        port = kwargs.get("port", 8101)
        strategy_type = kwargs.get("strategy", "random")
        league_manager_url = kwargs.get("league_manager_url", self.config.league_manager.url)

        # Create strategy
        strategy = await self._create_strategy(strategy_type)

        # Create Player
        self.component = PlayerAgent(
            player_name=name,
            strategy=strategy,
            league_id=self.config.league.league_id,
            host="localhost",
            port=port,
            league_manager_url=league_manager_url,
        )

        await self.component.start()

        # Register with service registry
        self._service_id = name
        await self.service_registry.register_service(
            service_id=self._service_id,
            service_type="player",
            endpoint=self.component.url,
            metadata={
                "league_id": self.config.league.league_id,
                "strategy": strategy_type,
            },
        )

        # Auto-register with league manager if requested
        if kwargs.get("auto_register", True):
            await asyncio.sleep(0.5)  # Wait for league manager to be ready
            await self.component.register_with_league()
            logger.info(f"Player {name} registered with league manager")

        logger.info(f"Player {name} ({strategy_type}) running at {self.component.url}")

    async def _create_strategy(self, strategy_type: str) -> Strategy:
        """Create a strategy instance."""
        from ..agents.strategies.factory import StrategyFactory, StrategyType
        from ..agents.strategies.plugin_registry import get_strategy_plugin_registry

        try:
            # First try built-in strategies (classic + game theory)
            strategy_enum = StrategyType.from_string(strategy_type)
            return StrategyFactory.create(strategy_enum)
        except ValueError:
            # Not a built-in strategy, try plugin registry
            strategy_registry = get_strategy_plugin_registry()
            if strategy_registry.is_registered(strategy_type):
                return strategy_registry.create_strategy(strategy_type)
            else:
                logger.warning(f"Unknown strategy '{strategy_type}', using RandomStrategy")
                return RandomStrategy()

    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal."""
        await self._shutdown_event.wait()

    async def stop(self) -> None:
        """Stop the component."""
        logger.info(f"Stopping {self.component_type.value}...")

        if self.component:
            # Unregister from service registry using tracked service_id
            if self._service_id:
                await self.service_registry.unregister_service(self._service_id)

            await self.component.stop()
            self.component = None

        # Stop state sync
        await self.state_sync.stop()

        self._running = False
        self._service_id = None
        logger.info(f"✓ {self.component_type.value} stopped")

    def request_shutdown(self) -> None:
        """Request shutdown."""
        self._shutdown_event.set()
