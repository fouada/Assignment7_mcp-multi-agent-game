"""
System Monitor Plugin
=====================

A production-grade plugin that monitors system events and logs metrics.
Demonstrates the power of the event bus and plugin architecture.
"""

from typing import Dict, Any, List
import time
from collections import Counter

from src.common.plugins import PluginInterface, PluginMetadata, PluginContext
from src.common.logger import get_logger
from src.common.events import BaseEvent

logger = get_logger(__name__)


class SystemMonitorPlugin(PluginInterface):
    """
    Monitors system health and activity.
    
    Tracks:
    - Registered agents
    - Matches played
    - Error rates
    - Event bus throughput
    """

    def __init__(self):
        super().__init__()
        self.stats = {
            "agents_registered": 0,
            "matches_started": 0,
            "matches_completed": 0,
            "errors_detected": 0,
            "start_time": 0.0
        }
        self.error_counts = Counter()

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="system_monitor",
            version="1.0.0",
            author="System",
            description="Monitors system events and health metrics",
            dependencies=[]
        )

    async def on_load(self, context: PluginContext) -> None:
        """Called when plugin is loaded."""
        logger.info("System Monitor loaded")

    async def on_enable(self, context: PluginContext) -> None:
        """Register event handlers."""
        self.stats["start_time"] = time.time()
        
        if context.event_bus:
            # Register for key lifecycle events
            context.event_bus.on("agent.registered", self.on_agent_registered, priority=100)
            context.event_bus.on("match.started", self.on_match_started)
            context.event_bus.on("match.completed", self.on_match_completed)
            context.event_bus.on("*.error", self.on_error)
            
            logger.info("System Monitor enabled and listening to events")

    async def on_disable(self, context: PluginContext) -> None:
        """Cleanup."""
        # Note: Event bus handles unregistration if we stored handler IDs, 
        # but for simplicity we rely on the bus shutdown or weak refs here.
        # In a strict implementation, we would store return values of .on() and call .off()
        logger.info("System Monitor disabled")
        self._log_summary()

    async def on_unload(self, context: PluginContext) -> None:
        logger.info("System Monitor unloaded")

    async def on_agent_registered(self, event: BaseEvent) -> None:
        self.stats["agents_registered"] += 1
        agent_id = getattr(event, "agent_id", "unknown")
        agent_type = getattr(event, "agent_type", "unknown")
        logger.info(f"[Monitor] New Agent: {agent_id} ({agent_type})")

    async def on_match_started(self, event: BaseEvent) -> None:
        self.stats["matches_started"] += 1
        match_id = getattr(event, "match_id", "unknown")
        logger.debug(f"[Monitor] Match started: {match_id}")

    async def on_match_completed(self, event: BaseEvent) -> None:
        self.stats["matches_completed"] += 1
        winner = getattr(event, "winner", "draw")
        logger.info(f"[Monitor] Match completed. Winner: {winner}")

    async def on_error(self, event: BaseEvent) -> None:
        self.stats["errors_detected"] += 1
        error_msg = getattr(event, "error_message", "Unknown error")
        self.error_counts[error_msg] += 1
        logger.warning(f"[Monitor] Error detected: {error_msg}")

    def _log_summary(self) -> None:
        """Log a summary of session stats."""
        uptime = time.time() - self.stats["start_time"]
        logger.info("=" * 40)
        logger.info("System Monitor Summary")
        logger.info("=" * 40)
        logger.info(f"Uptime: {uptime:.2f}s")
        logger.info(f"Agents: {self.stats['agents_registered']}")
        logger.info(f"Matches: {self.stats['matches_completed']}/{self.stats['matches_started']}")
        logger.info(f"Errors: {self.stats['errors_detected']}")
        if self.error_counts:
            logger.info("Top Errors:")
            for err, count in self.error_counts.most_common(3):
                logger.info(f"  - {err}: {count}")
        logger.info("=" * 40)

