# Visualization System - Quick Start Guide
## Get Started in 5 Minutes

---

## 🚀 Quick Launch

### 1. Start Tournament with Dashboard

```bash
# From project root
python -m src.cli league start \
  --league-id my_tournament \
  --dashboard \
  --num-rounds 100
```

### 2. Open Dashboard

Navigate to: **http://localhost:8050**

That's it! The dashboard will start updating automatically as matches progress.

---

## 📊 Dashboard Sections

### **Tournament Overview**
Top cards showing:
- Game type (e.g., even_odd)
- Current round / total rounds
- Active players count

### **Player Standings**
Real-time leaderboard with:
- Rank (🥇🥈🥉)
- Player names & strategies
- Points, Wins, Draws, Losses
- Win percentage

### **Live Game Arena**
Watch matches in progress:
- Player moves displayed in real-time
- Current scores
- Match state (IN_PROGRESS, FINISHED)

### **Strategy Learning Evolution** (4 Tabs)

1. **Bayesian Beliefs**: Opponent model confidence over time
2. **Confidence**: Model accuracy evolution
3. **Regret Analysis**: Counterfactual regret minimization
4. **Learning Curve**: Win rate trends with improvement indicators

### **Tournament Flow** (3 Views)

1. **Matchup Matrix**: Head-to-head W-L-D grid
2. **Standings Race**: Animated progression
3. **Head-to-Head Stats**: Detailed matchup statistics

### **Tournament Replay**
Time-travel through tournament history:
- Play/Pause/Step controls
- Speed adjustment (0.25x - 10x)
- Timeline scrubber
- Snapshot capture & compare
- Export replay data

### **Analytics Charts**

- **Strategy Performance Over Time**: Win rates evolving
- **Opponent Model Confidence**: Prediction accuracy
- **Counterfactual Regret Analysis**: Decision quality

### **Live Event Log**
Scrolling log of all tournament events

---

## 🔌 API Quick Reference

### Get All Strategy Analytics
```bash
curl http://localhost:8050/api/analytics/strategies | jq
```

### Get Specific Strategy Details
```bash
curl http://localhost:8050/api/analytics/strategy/adaptive | jq
```

### Get Opponent Models for Player
```bash
curl http://localhost:8050/api/analytics/opponent_models/player_1 | jq
```

### Get Counterfactual Analysis
```bash
curl http://localhost:8050/api/analytics/counterfactual/player_1 | jq
```

### Get Matchup Matrix
```bash
curl http://localhost:8050/api/analytics/matchup_matrix | jq
```

### Export Research Data
```bash
curl http://localhost:8050/api/analytics/export > research_data.json
```

### Get Replay History
```bash
curl "http://localhost:8050/api/analytics/replay/history?start_round=0&end_round=50" | jq
```

---

## 💻 Programmatic Usage

### Python Example

```python
from src.visualization import (
    get_dashboard_integration,
    get_analytics_engine,
)

# Get instances
integration = get_dashboard_integration()
analytics = get_analytics_engine()

# Start tournament monitoring
await integration.start(
    tournament_id="my_tournament",
    total_rounds=100
)

# Register players (if using custom agents)
integration.register_player(
    player_id="player_1",
    strategy_name="adaptive_cfr",
    opponent_modeling_engine=my_om_engine,  # Optional
    cfr_engine=my_cfr_engine,  # Optional
    strategy_composition=my_composite  # Optional
)

# Query analytics anytime
strategy_data = analytics.get_strategy_analytics("adaptive_cfr")
print(f"Win Rate: {strategy_data.win_rate:.2%}")
print(f"Learning Rate: {strategy_data.learning_rate:.4f}")
print(f"Trend: {strategy_data.improvement_trend}")

# Get matchup data
matrix = analytics.get_matchup_matrix()
for (p1, p2), stats in matrix.matrix.items():
    print(f"{p1} vs {p2}: {stats['player_a_wins']}-{stats['player_b_wins']}")

# Export for research
research_data = analytics.export_for_research()
with open('tournament_analytics.json', 'w') as f:
    json.dump(research_data, f, indent=2)
```

---

## 🎮 Interactive Features

### Replay Controls

| Button | Action |
|--------|--------|
| ⏮️ | Jump to start |
| ⏪ | Step back one round |
| ▶️/⏸️ | Play/Pause |
| ⏩ | Step forward one round |
| ⏭️ | Jump to end |

**Speed Options**: 0.25x, 0.5x, 1x (default), 2x, 5x, 10x

**Additional Actions**:
- 📸 **Snapshot**: Capture current state
- 📊 **Compare**: Compare last 2 snapshots
- 💾 **Export**: Download replay JSON

### Tab Navigation

**Strategy Evolution Tabs**:
- Click tab names to switch views
- All tabs auto-update with live data
- Hover over data points for details

**Tournament Flow Views**:
- Toggle between Matrix/Standings/Stats
- Click matrix cells for match details
- Hover for tooltips

---

## 📥 Export Options

### Dashboard Export (Button in UI)

Click "**Export Data**" button:
- Downloads comprehensive JSON
- Includes all analytics
- Research-ready format
- Timestamped filename

### Replay Export

In replay section, click "💾 Export":
- Full tournament history
- All snapshots captured
- Playback-compatible format

### API Export

```bash
# Comprehensive export
curl http://localhost:8050/api/analytics/export > export.json

# Strategy-specific export
curl http://localhost:8050/api/analytics/strategy/adaptive | jq . > adaptive_analytics.json
```

---

## 🎯 Common Use Cases

### 1. Monitor Tournament Progress

Just open the dashboard - everything updates automatically!

### 2. Analyze Strategy Performance

1. Go to "Strategy Performance Over Time" chart
2. See which strategies are improving
3. Check "Strategy Learning Evolution" tabs for details

### 3. Debug Agent Behavior

1. Use "Opponent Model Confidence" chart
2. Check if agent is learning opponents correctly
3. Look at "Counterfactual Regret" for decision quality

### 4. Compare Head-to-Head

1. Go to "Tournament Flow" section
2. Click "Matchup Matrix" view
3. Click any cell for detailed match history

### 5. Time-Travel Debugging

1. Go to "Tournament Replay" section
2. Scrub timeline to problematic round
3. Capture snapshot
4. Step through rounds frame-by-frame
5. Compare with later snapshots

### 6. Export for Paper/Presentation

1. Run tournament
2. Click "Export Data" button
3. Use JSON data in analysis scripts
4. Take screenshots of visualizations

---

## 🐛 Troubleshooting

### Dashboard Not Loading

```bash
# Check if server is running
curl http://localhost:8050/health

# Should return: {"status": "healthy", ...}
```

### Charts Not Updating

1. Check WebSocket connection (green "Connected" badge)
2. Click "Connect" button if disconnected
3. Refresh page if needed

### No Data Showing

- Wait for tournament to start
- At least 1 round must complete for charts to populate
- Check that `--dashboard` flag was used when starting tournament

### Export Fails

- Ensure tournament has started (at least 1 round completed)
- Check browser console for errors
- Try API export as fallback:
  ```bash
  curl http://localhost:8050/api/analytics/export > data.json
  ```

---

## 📚 Advanced Topics

### Custom Strategies Visualization

Your custom strategies will automatically appear in all charts once registered.

### Multiple Tournaments

Each tournament gets its own state. Use different `tournament_id` values.

### Integration with Existing Code

No changes needed! The visualization system hooks into existing event bus automatically.

### Performance Tuning

If handling very long tournaments (>1000 rounds):

```python
# In your code
analytics = get_analytics_engine()

# Replay history kept to last 2000 rounds (default: 1000)
# Modify in analytics.py: _capture_replay_state method
```

---

## 🎓 Next Steps

1. ✅ **Quick Start**: Follow this guide to launch dashboard
2. 📖 **Deep Dive**: Read `EXCEPTIONAL_VISUALIZATION_ENHANCEMENTS.md`
3. 🔬 **Research Use**: Explore API endpoints for analysis pipelines
4. 🎨 **Customization**: Extend analytics engine with domain-specific metrics
5. 🤝 **Share**: Export data and visualizations for collaborations

---

## 📞 Support Resources

- **Main Docs**: `docs/EXCEPTIONAL_VISUALIZATION_ENHANCEMENTS.md`
- **API Reference**: `docs/API.md`
- **Architecture**: `docs/architecture/`
- **Examples**: `examples/dashboard/`

---

**Happy Analyzing! 🎉**

*The dashboard brings your multi-agent tournament to life with MIT-level analytics and visualizations.*

