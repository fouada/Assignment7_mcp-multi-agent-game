"""
Modular Component Launcher System
==================================

MIT-Level Architecture for separate component invocation with guaranteed
state synchronization and real-time dashboard updates.

Components can be started independently:
- League Manager + Dashboard (together)
- Referee (separate instances)
- Player (separate instances with different strategies)

All state changes are synchronized via event bus with dashboard subscription.
"""

from .component_launcher import ComponentLauncher, ComponentType
from .service_registry import ServiceRegistry, get_service_registry
from .state_sync import StateSyncService, get_state_sync

__all__ = [
    "ComponentLauncher",
    "ComponentType",
    "ServiceRegistry",
    "get_service_registry",
    "StateSyncService",
    "get_state_sync",
]
