"""
Monitoring Plugin Example
==========================

Production-grade example of a monitoring plugin that demonstrates:
- Complete lifecycle management
- Hook registration
- Extension points
- Dependency injection
- Configuration management
- Health checks
- Metrics collection

This plugin monitors system health and collects metrics.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.common.plugins.base import (
    PluginInterface,
    PluginMetadata,
    PluginContext,
    PluginCapability,
)
from src.common.hooks.hook_manager import get_hook_manager
from src.common.hooks.types import HookContext, HookPriority
from src.common.extension_points import extension_provider
from src.common.logger import get_logger

logger = get_logger(__name__)


@dataclass
class HealthMetrics:
    """Health metrics data structure."""

    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    active_matches: int = 0
    active_players: int = 0
    total_moves: int = 0
    errors: int = 0
    last_update: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""

    avg_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    requests_per_second: float = 0.0
    error_rate: float = 0.0


class MonitoringPlugin(PluginInterface):
    """
    Monitoring plugin for system health and performance tracking.
    
    Features:
    - Real-time health monitoring
    - Performance metrics collection
    - Automatic alerting on thresholds
    - Historical data tracking
    - Dashboard integration ready
    
    Configuration:
        {
            "collection_interval": 5,  # seconds
            "alert_thresholds": {
                "cpu_usage": 80.0,
                "memory_usage": 85.0,
                "error_rate": 5.0
            },
            "retention_period": 3600  # seconds
        }
    """

    def __init__(self):
        super().__init__()
        
        # Metrics storage
        self.health_metrics = HealthMetrics()
        self.performance_metrics = PerformanceMetrics()
        self.history: list[dict[str, Any]] = []
        
        # Event counters
        self.event_counters = defaultdict(int)
        self.response_times: list[float] = []
        
        # Hook IDs for cleanup
        self.hook_ids: list[str] = []
        
        # Configuration
        self.config: dict[str, Any] = {}

    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="monitoring_plugin",
            version="1.0.0",
            author="MCP Team",
            description="System health and performance monitoring",
            capabilities=[
                PluginCapability.HOT_RELOAD,
                PluginCapability.PROVIDES_HOOKS,
                PluginCapability.TELEMETRY,
            ],
            tags=["monitoring", "metrics", "health", "performance"],
            homepage="https://github.com/your-org/mcp-game-league",
            license="MIT",
        )

    async def on_validate(self, context: PluginContext) -> bool:
        """Validate plugin can run in this environment."""
        # Check if hook manager is available
        if not context.hook_manager:
            logger.error("Hook manager not available")
            return False
        
        # Check if running in production mode
        if context.is_production():
            logger.info("Monitoring plugin validated for production")
        
        return True

    async def on_configure(self, context: PluginContext, config: dict[str, Any]) -> None:
        """Configure plugin with custom settings."""
        self.config = {
            "collection_interval": config.get("collection_interval", 5),
            "alert_thresholds": config.get("alert_thresholds", {
                "cpu_usage": 80.0,
                "memory_usage": 85.0,
                "error_rate": 5.0
            }),
            "retention_period": config.get("retention_period", 3600)
        }
        
        context.logger.info(f"Monitoring plugin configured: {self.config}")

    async def on_enable(self, context: PluginContext) -> None:
        """Enable plugin and register hooks."""
        hook_manager = context.hook_manager
        plugin_name = self.get_metadata().name
        
        # Register hooks for various events
        hooks = [
            ("system.startup", self._on_system_startup, HookPriority.NORMAL.value),
            ("system.shutdown", self._on_system_shutdown, HookPriority.NORMAL.value),
            ("match.started", self._on_match_started, HookPriority.LOW.value),
            ("match.ended", self._on_match_ended, HookPriority.LOW.value),
            ("round.completed", self._on_round_completed, HookPriority.LOW.value),
            ("player.registered", self._on_player_registered, HookPriority.LOW.value),
            ("error.occurred", self._on_error, HookPriority.HIGH.value),
        ]
        
        for hook_name, handler, priority in hooks:
            hook_id = hook_manager.register(
                hook_name=hook_name,
                handler=handler,
                priority=priority,
                plugin_name=plugin_name
            )
            self.hook_ids.append(hook_id)
        
        context.logger.info(f"Monitoring plugin enabled with {len(self.hook_ids)} hooks")

    async def on_disable(self, context: PluginContext) -> None:
        """Disable plugin and cleanup."""
        hook_manager = context.hook_manager
        
        # Unregister all hooks
        for hook_id in self.hook_ids:
            hook_manager.unregister(hook_id)
        
        self.hook_ids.clear()
        
        # Save final metrics
        self._save_metrics()
        
        context.logger.info("Monitoring plugin disabled")

    async def on_reload(self, context: PluginContext) -> None:
        """Hot reload plugin while preserving state."""
        # Save current state
        saved_health = self.health_metrics
        saved_performance = self.performance_metrics
        saved_history = self.history.copy()
        
        # Reload
        await self.on_disable(context)
        await self.on_enable(context)
        
        # Restore state
        self.health_metrics = saved_health
        self.performance_metrics = saved_performance
        self.history = saved_history
        
        context.logger.info("Monitoring plugin reloaded with state preserved")

    # Hook Handlers
    
    async def _on_system_startup(self, context: HookContext) -> None:
        """Track system startup."""
        self.event_counters["system.startup"] += 1
        context.set("monitoring_enabled", True)
        logger.info("System monitoring started")

    async def _on_system_shutdown(self, context: HookContext) -> None:
        """Track system shutdown."""
        uptime = context.get("uptime", 0)
        logger.info(f"System shutting down after {uptime}s uptime")
        self._save_metrics()

    async def _on_match_started(self, context: HookContext) -> None:
        """Track match start."""
        self.health_metrics.active_matches += 1
        self.event_counters["match.started"] += 1
        context.set("match_start_time", time.time())

    async def _on_match_ended(self, context: HookContext) -> None:
        """Track match end and performance."""
        self.health_metrics.active_matches = max(0, self.health_metrics.active_matches - 1)
        self.event_counters["match.ended"] += 1
        
        # Calculate match duration
        start_time = context.get("match_start_time")
        if start_time:
            duration = time.time() - start_time
            self.response_times.append(duration)
            
            # Keep only last 1000 measurements
            if len(self.response_times) > 1000:
                self.response_times = self.response_times[-1000:]
            
            # Update performance metrics
            self._update_performance_metrics()

    async def _on_round_completed(self, context: HookContext) -> None:
        """Track round completion."""
        self.health_metrics.total_moves += context.get("move_count", 2)
        self.event_counters["round.completed"] += 1

    async def _on_player_registered(self, context: HookContext) -> None:
        """Track player registration."""
        self.health_metrics.active_players += 1
        self.event_counters["player.registered"] += 1

    async def _on_error(self, context: HookContext) -> None:
        """Track errors."""
        self.health_metrics.errors += 1
        self.event_counters["error.occurred"] += 1
        
        error = context.get("error")
        logger.warning(f"Error tracked: {error}")
        
        # Check if error rate threshold exceeded
        self._check_alert_thresholds()

    # Metrics Management
    
    def _update_performance_metrics(self) -> None:
        """Update performance metrics from collected data."""
        if not self.response_times:
            return
        
        sorted_times = sorted(self.response_times)
        n = len(sorted_times)
        
        self.performance_metrics.avg_response_time = sum(sorted_times) / n
        self.performance_metrics.p95_response_time = sorted_times[int(n * 0.95)]
        self.performance_metrics.p99_response_time = sorted_times[int(n * 0.99)]
        
        # Calculate requests per second (approximate)
        if n > 1:
            time_span = sorted_times[-1] - sorted_times[0]
            if time_span > 0:
                self.performance_metrics.requests_per_second = n / time_span

    def _check_alert_thresholds(self) -> None:
        """Check if any metrics exceed alert thresholds."""
        thresholds = self.config.get("alert_thresholds", {})
        
        alerts = []
        
        if self.health_metrics.cpu_usage > thresholds.get("cpu_usage", 80):
            alerts.append(f"CPU usage high: {self.health_metrics.cpu_usage:.1f}%")
        
        if self.health_metrics.memory_usage > thresholds.get("memory_usage", 85):
            alerts.append(f"Memory usage high: {self.health_metrics.memory_usage:.1f}%")
        
        # Calculate error rate
        total_events = sum(self.event_counters.values())
        if total_events > 0:
            error_rate = (self.health_metrics.errors / total_events) * 100
            if error_rate > thresholds.get("error_rate", 5):
                alerts.append(f"Error rate high: {error_rate:.2f}%")
        
        if alerts:
            for alert in alerts:
                logger.warning(f"ALERT: {alert}")

    def _save_metrics(self) -> None:
        """Save current metrics to history."""
        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "health": {
                "cpu_usage": self.health_metrics.cpu_usage,
                "memory_usage": self.health_metrics.memory_usage,
                "active_matches": self.health_metrics.active_matches,
                "active_players": self.health_metrics.active_players,
                "total_moves": self.health_metrics.total_moves,
                "errors": self.health_metrics.errors,
            },
            "performance": {
                "avg_response_time": self.performance_metrics.avg_response_time,
                "p95_response_time": self.performance_metrics.p95_response_time,
                "p99_response_time": self.performance_metrics.p99_response_time,
                "requests_per_second": self.performance_metrics.requests_per_second,
            },
            "events": dict(self.event_counters),
        }
        
        self.history.append(snapshot)
        
        # Trim old history based on retention period
        retention = self.config.get("retention_period", 3600)
        cutoff = datetime.utcnow().timestamp() - retention
        self.history = [
            h for h in self.history
            if datetime.fromisoformat(h["timestamp"]).timestamp() > cutoff
        ]

    # Public API
    
    def get_health_metrics(self) -> dict[str, Any]:
        """Get current health metrics."""
        self.health_metrics.last_update = datetime.utcnow()
        return {
            "cpu_usage": self.health_metrics.cpu_usage,
            "memory_usage": self.health_metrics.memory_usage,
            "active_matches": self.health_metrics.active_matches,
            "active_players": self.health_metrics.active_players,
            "total_moves": self.health_metrics.total_moves,
            "errors": self.health_metrics.errors,
            "last_update": self.health_metrics.last_update.isoformat(),
        }

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get current performance metrics."""
        return {
            "avg_response_time": self.performance_metrics.avg_response_time,
            "p95_response_time": self.performance_metrics.p95_response_time,
            "p99_response_time": self.performance_metrics.p99_response_time,
            "requests_per_second": self.performance_metrics.requests_per_second,
            "error_rate": self.performance_metrics.error_rate,
        }

    def get_event_counters(self) -> dict[str, int]:
        """Get event counters."""
        return dict(self.event_counters)

    def get_history(self, last_n: int = 100) -> list[dict[str, Any]]:
        """Get historical metrics."""
        return self.history[-last_n:]

    def reset_metrics(self) -> None:
        """Reset all metrics (for testing)."""
        self.health_metrics = HealthMetrics()
        self.performance_metrics = PerformanceMetrics()
        self.event_counters.clear()
        self.response_times.clear()
        self.history.clear()


# Extension Point Provider Example
# This makes the monitoring data available as an extension point

@extension_provider("monitoring.health", priority=100)
class HealthMonitorExtension:
    """Provides health monitoring data as an extension."""
    
    def __init__(self):
        self.plugin: MonitoringPlugin | None = None
    
    def set_plugin(self, plugin: MonitoringPlugin) -> None:
        """Set the monitoring plugin reference."""
        self.plugin = plugin
    
    def get_health(self) -> dict[str, Any]:
        """Get health metrics."""
        if self.plugin:
            return self.plugin.get_health_metrics()
        return {}
    
    def get_performance(self) -> dict[str, Any]:
        """Get performance metrics."""
        if self.plugin:
            return self.plugin.get_performance_metrics()
        return {}
    
    def is_healthy(self) -> bool:
        """Check if system is healthy."""
        if not self.plugin:
            return False
        
        metrics = self.plugin.get_health_metrics()
        return (
            metrics["cpu_usage"] < 80 and
            metrics["memory_usage"] < 85 and
            metrics["errors"] < 10
        )


# Convenience function to get the monitoring plugin instance
def get_monitoring_plugin() -> MonitoringPlugin | None:
    """Get the monitoring plugin instance if registered."""
    from src.common.plugins.registry import get_plugin_registry
    
    registry = get_plugin_registry()
    plugin = registry.get_plugin("monitoring_plugin")
    
    if isinstance(plugin, MonitoringPlugin):
        return plugin
    
    return None

