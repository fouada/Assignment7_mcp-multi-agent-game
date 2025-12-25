"""
Real-Time Interactive Dashboard System for Multi-Agent Games
============================================================

**Innovation #4: Production-Grade Visualization**

This module provides a real-time interactive dashboard for monitoring
and analyzing multi-agent game tournaments with deep insights into:
- Opponent modeling (belief states, predictions)
- Counterfactual reasoning (regrets, alternative actions)
- Strategy composition (decision trees, component usage)
- Tournament progress (standings, performance metrics)

**Key Components:**
- `DashboardAPI`: FastAPI server with WebSocket streaming
- `DashboardIntegration`: Connects dashboard to innovation engines
- Real-time visualizations with Plotly.js
- Tournament replay system
- Export functionality

**Usage:**
```python
from src.visualization import get_dashboard_integration

# Start dashboard integration
integration = get_dashboard_integration()
await integration.start(tournament_id="tour_001", total_rounds=100)

# Register players with their innovation engines
integration.register_player(
    player_id="player_1",
    strategy_name="bayesian_cfr",
    opponent_modeling_engine=om_engine,
    cfr_engine=cfr_engine
)

# Dashboard automatically receives updates via event hooks
```

**Access Dashboard:**
Open http://localhost:8050 in browser to view live dashboard.
"""

from .dashboard import (
    CounterfactualVisualization,
    DashboardAPI,
    GameEvent,
    OpponentModelVisualization,
    StrategyPerformance,
    get_dashboard,
    reset_dashboard,
)
from .integration import (
    DashboardIntegration,
    PlayerDashboardState,
    TournamentDashboardState,
    get_dashboard_integration,
    reset_dashboard_integration,
)

__all__ = [
    # Dashboard API
    "DashboardAPI",
    "GameEvent",
    "StrategyPerformance",
    "OpponentModelVisualization",
    "CounterfactualVisualization",
    "get_dashboard",
    "reset_dashboard",
    # Integration
    "DashboardIntegration",
    "PlayerDashboardState",
    "TournamentDashboardState",
    "get_dashboard_integration",
    "reset_dashboard_integration",
]
