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
        self.dashboard = None

        # Infrastructure
        self.event_bus = get_event_bus()
        self.service_registry: ServiceRegistry = get_service_registry()
        self.state_sync: StateSyncService = get_state_sync()

        # State
        self._running = False
        self._shutdown_event = asyncio.Event()

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

        # Setup signal handlers
        loop = asyncio.get_event_loop()

        def signal_handler():
            self._shutdown_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)

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
        await self.service_registry.register_service(
            service_id=self.component.name,
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
        self.event_bus.on("game.round.start", integration.on_round_start)
        self.event_bus.on("game.move.decision", integration.on_move_decision)
        self.event_bus.on("game.round.complete", integration.on_round_complete)

        logger.info("Dashboard started and connected to event bus")

    async def _start_referee(self, **kwargs: Any) -> None:
        """Start a referee agent."""
        referee_id = kwargs.get("referee_id", "REF01")
        port = kwargs.get("port", self.config.referee.port)
        league_manager_url = kwargs.get(
            "league_manager_url", self.config.league_manager.url
        )

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
        await self.service_registry.register_service(
            service_id=referee_id,
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
        league_manager_url = kwargs.get(
            "league_manager_url", self.config.league_manager.url
        )

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
        await self.service_registry.register_service(
            service_id=name,
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
            # Unregister from service registry
            if hasattr(self.component, "name"):
                await self.service_registry.unregister_service(
                    str(getattr(self.component, "name", "unknown"))
                )

            await self.component.stop()
            self.component = None

        # Stop state sync
        await self.state_sync.stop()

        self._running = False
        logger.info(f"✓ {self.component_type.value} stopped")

    def request_shutdown(self) -> None:
        """Request shutdown."""
        self._shutdown_event.set()
