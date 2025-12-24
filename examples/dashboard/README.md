# Dashboard Examples - Real-Time Interactive Visualization

This directory contains examples demonstrating **Innovation #4: Real-Time Interactive Dashboard System**.

## Overview

The dashboard provides real-time visualization of multi-agent game tournaments with deep insights into:
- Tournament state and standings
- Strategy performance over time
- Opponent modeling beliefs
- Counterfactual regret analysis
- Game event streaming

## Quick Start

### Basic Usage

```bash
# Run tournament with dashboard
python -m src.main --run --players 4 --dashboard

# Open browser to:
# http://localhost:8050
```

### Using the Demo Script

```bash
# Run the demo
python examples/dashboard/run_with_dashboard.py

# With custom configuration
python examples/dashboard/run_with_dashboard.py --players 6 --rounds 20
```

## Dashboard Features

### 1. Real-Time Tournament Overview
- **Live Standings Table**: Updated after each match
  - Player rankings
  - Win/loss records
  - Total scores
  - Real-time updates via WebSocket

- **Tournament Metrics**:
  - Current round progress
  - Total matches played
  - Tournament start time
  - Active players count

### 2. Strategy Performance Visualization
- **Line Charts** showing win rates over time
- **Score Trends** for each strategy type
- **Comparative Analysis** between strategies
- Interactive Plotly charts (zoom, pan, export)

### 3. Opponent Modeling Dashboard
- **Confidence Levels**: How certain agents are about opponent strategies
- **Predicted Strategies**: What agents believe opponents will do
- **Belief Updates**: Real-time changes in opponent models
- **Accuracy Metrics**: Prediction accuracy over time

### 4. Counterfactual Regret Analysis
- **Regret Charts**: Showing alternative action values
- **What-If Analysis**: "Should have chosen X instead of Y"
- **Cumulative Regret**: Learning progress visualization
- **Decision Tree**: Visual representation of alternative paths

### 5. Live Event Log
- **Streaming Events**: Real-time game actions
- **Timestamped Log**: Complete event history
- **Filterable**: By event type, player, round
- **Color-Coded**: Easy visual scanning

## Innovation Highlights

### First-of-Its-Kind Features

1. **Internal Reasoning Visualization**
   - See what agents *think* about opponents
   - Watch beliefs update in real-time
   - Understand decision-making process

2. **Counterfactual What-If Analysis**
   - Learn from actions NOT taken
   - Visualize alternative timelines
   - Understand regret accumulation

3. **Strategy Composition Trees**
   - See how complex strategies are built
   - Understand component interactions
   - Track which primitives are used

4. **Publication-Quality Exports**
   - Export data as JSON
   - Interactive Plotly charts
   - Ready for research papers

## Architecture

### Backend (FastAPI + WebSocket)
```
DashboardAPI (FastAPI)
├── REST Endpoints
│   ├── GET /                          # Dashboard UI
│   ├── GET /api/tournament/{id}       # Tournament state
│   ├── GET /api/strategy/{name}/...   # Strategy metrics
│   ├── GET /api/opponent_model/...    # Opponent beliefs
│   └── GET /api/counterfactual/...    # Regret analysis
└── WebSocket
    └── WS /ws                          # Real-time event stream
```

### Frontend (HTML + Plotly.js)
```
Dashboard UI
├── Header with connection status
├── Tournament Overview Cards
├── Live Standings Table
├── Strategy Performance Chart (Plotly)
├── Opponent Model Chart (Plotly)
├── Counterfactual Regret Chart (Plotly)
└── Live Event Log (streaming)
```

### Integration Layer
```
DashboardIntegration
├── Connects to game engines
├── Aggregates player states
├── Streams events via WebSocket
└── Provides API data
```

## Usage Examples

### Example 1: Basic Tournament Monitoring

```bash
# Start tournament with dashboard
python -m src.main --run --players 4 --dashboard
```

Open browser to `http://localhost:8050` and watch:
- Matches progress in real-time
- Standings update after each round
- Event log showing all actions

### Example 2: Custom Number of Players

```bash
# 6-player tournament
python examples/dashboard/run_with_dashboard.py --players 6
```

See how standings and matchups change with more players.

### Example 3: Extended Analysis

```bash
# More rounds for deeper analysis
python examples/dashboard/run_with_dashboard.py --rounds 50
```

Watch strategy performance trends emerge over many rounds.

### Example 4: Debug Mode

```bash
# Enable debug logging
python examples/dashboard/run_with_dashboard.py --debug
```

See detailed event processing in console while watching dashboard.

## Data Export

The dashboard provides a **Export Data** button to save all visualization data as JSON:

```json
{
  "tournament": {
    "tournament_id": "tournament_league_001",
    "current_round": 15,
    "total_rounds": 20
  },
  "standings": [
    {"player_id": "P01", "wins": 8, "losses": 2, ...},
    ...
  ],
  "strategy_performance": {
    "random": {"win_rate": 0.45, ...},
    "pattern": {"win_rate": 0.55, ...}
  },
  "events": [
    {"timestamp": "...", "type": "round_start", ...},
    ...
  ]
}
```

This data can be used for:
- Post-game analysis
- Statistical testing
- Research publications
- Custom visualizations

## Integration with Innovation Systems

### Opponent Modeling Integration

When players use opponent modeling strategies, the dashboard shows:
- **Predicted opponent type**: "tit_for_tat", "random", "grudger", etc.
- **Confidence level**: 0-100%
- **Move distribution**: Probability of each move
- **Concept drift detection**: When opponent changes strategy

### Counterfactual Regret Integration

When players use CFR strategies, the dashboard shows:
- **Actual move**: What was chosen
- **Actual reward**: Result received
- **Counterfactual moves**: Alternatives that could have been chosen
- **Regret values**: How much better/worse alternatives would have been
- **Cumulative regret**: Learning progress over time

### Strategy Composition Integration

When players use composite strategies, the dashboard shows:
- **Composition tree**: Visual hierarchy of strategy components
- **Active component**: Which primitive is currently deciding
- **Component usage**: How often each primitive is used
- **Performance breakdown**: Win rate per component

## Technical Details

### WebSocket Protocol

Events are streamed as JSON:

```json
{
  "type": "round_end",
  "round": 5,
  "players": ["P01", "P02"],
  "moves": {"P01": "cooperate", "P02": "defect"},
  "scores": {"P01": 0, "P02": 5}
}
```

### Event Types

- `round_start`: New round beginning
- `move`: Player decision made
- `round_end`: Round complete with scores
- `opponent_model_update`: Belief update
- `counterfactual_update`: Regret analysis
- `strategy_performance_update`: Metrics update

### REST API Endpoints

#### GET /api/tournament/{tournament_id}
Returns tournament state:
```json
{
  "tournament_id": "tour_001",
  "current_round": 10,
  "total_rounds": 20,
  "num_players": 4
}
```

#### GET /api/strategy/{strategy_name}/performance
Returns strategy performance:
```json
{
  "strategy_name": "random",
  "win_rate": 0.45,
  "avg_score": 3.2,
  "rounds": [1, 2, 3, ...],
  "scores": [3, 5, 1, ...]
}
```

#### GET /api/opponent_model/{player_id}/{opponent_id}
Returns opponent model:
```json
{
  "opponent_id": "P02",
  "predicted_strategy": "tit_for_tat",
  "confidence": 0.85,
  "move_distribution": {
    "cooperate": 0.6,
    "defect": 0.4
  }
}
```

## Troubleshooting

### Dashboard Not Loading

**Problem**: Browser shows "Connection failed"

**Solution**:
1. Check that dashboard is enabled with `--dashboard` flag
2. Verify port 8050 is not in use: `lsof -i :8050`
3. Check logs for dashboard startup message

### WebSocket Connection Issues

**Problem**: Events not streaming in real-time

**Solution**:
1. Check browser console for WebSocket errors
2. Verify firewall allows WebSocket connections
3. Try refreshing the page
4. Check that matches are actually running

### Charts Not Updating

**Problem**: Plotly charts are static

**Solution**:
1. Ensure WebSocket connection is active (green indicator)
2. Check that game events are being generated
3. Verify JavaScript console for errors
4. Try exporting data to verify data is available

### Performance Issues

**Problem**: Dashboard is slow with many players

**Solution**:
1. Reduce number of players
2. Reduce rounds per match
3. Clear event history (refresh page)
4. Use Chrome/Firefox for better performance

## Research Applications

### Publication Use Cases

1. **Algorithm Comparison Papers**
   - Export performance charts
   - Include strategy comparison graphs
   - Show learning curves over time

2. **Multi-Agent Learning Papers**
   - Visualize opponent modeling accuracy
   - Show belief convergence
   - Demonstrate adaptive behavior

3. **Game Theory Papers**
   - Visualize Nash equilibrium convergence
   - Show regret minimization
   - Demonstrate strategy evolution

4. **Explainable AI Papers**
   - Show internal reasoning visualization
   - Demonstrate counterfactual analysis
   - Provide interpretable decision trees

### Educational Use Cases

1. **Course Demonstrations**
   - Live demo of game theory concepts
   - Interactive exploration of strategies
   - Real-time learning visualization

2. **Student Projects**
   - Platform for developing new strategies
   - Visual feedback for testing
   - Data export for analysis

3. **Research Training**
   - Learn to use multi-agent tools
   - Understand research visualization
   - Practice experiment design

## Future Enhancements

Potential extensions to the dashboard:

1. **Tournament Replay**: Time-travel through past tournaments
2. **Strategy Comparison Mode**: Side-by-side strategy analysis
3. **Interactive Strategy Builder**: Visual strategy composition
4. **Live Collaboration**: Multiple users viewing same tournament
5. **Advanced Analytics**: Statistical tests, confidence intervals
6. **3D Visualizations**: Strategy space exploration
7. **Mobile Support**: Responsive design for tablets/phones

## Related Documentation

- [MIT_LEVEL_INNOVATIONS.md](../../docs/MIT_LEVEL_INNOVATIONS.md) - Overview of all innovations
- [INNOVATION.md](../../docs/INNOVATION.md) - Innovation feature details
- [README.md](../../README.md) - Project overview

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review logs with `--debug` flag
3. Check WebSocket connection in browser console
4. Verify game events are being generated

## Citation

If you use this dashboard in your research, please cite:

```bibtex
@software{mcp_game_dashboard,
  title = {Real-Time Interactive Dashboard for Multi-Agent Game Theory Research},
  author = {[Your Name]},
  year = {2025},
  url = {https://github.com/yourusername/mcp-game-league}
}
```

---

**Innovation #4** - First real-time dashboard for multi-agent game theory research with internal reasoning visualization.
