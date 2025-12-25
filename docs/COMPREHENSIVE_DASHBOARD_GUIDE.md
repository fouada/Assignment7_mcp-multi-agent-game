# Comprehensive Real-Time Dashboard Guide

## 🎯 Overview

The **Comprehensive Dashboard** displays **ALL real-time game league data** including:

✅ **Each player's strategy** - See every player's unique strategy  
✅ **Rounds progress** - Current round, total rounds, rounds played, rounds remaining  
✅ **Live standings** - Real-time rankings with strategies  
✅ **Player moves** - See each player's move/choice in every match  
✅ **Match history** - Complete history of all moves and results  
✅ **Winner celebration** - Tournament winner with strategy breakdown  
✅ **Real-time updates** - WebSocket streaming of live game data  

---

## 🚀 Quick Start

### 1. Run Tournament with Dashboard

```bash
# From project root
python examples/dashboard/run_enhanced_dashboard.py
```

### 2. Open Browser

Navigate to: **http://localhost:8050**

### 3. Watch Real-Time Data

The dashboard will automatically connect and stream all game data!

---

## 📊 Dashboard Sections

### 1. Round Progress Banner

**Top of page - Shows:**
- ⏱️ Current Round
- 📊 Total Rounds
- ✅ Rounds Played
- ⏳ Rounds Remaining
- Progress bar showing completion percentage

**Example:**
```
Current Round: 5
Total Rounds: 15  
Rounds Played: 5
Rounds Remaining: 10
[███████░░░░░░░░] 33.3% Complete
```

---

### 2. Player Standings & Strategies Table

**Shows for each player:**
- 🏅 **Rank** - Position (1st, 2nd, 3rd with special badges)
- 👤 **Player ID & Strategy** - Name with strategy badge
- 💯 **Score** - Total points
- 🏆 **Wins** - Number of victories
- 🎮 **Matches** - Total matches played
- 📈 **Win Rate** - Win percentage

**Real Data Example:**
```
┌──────┬──────────────────────────────────────┬───────┬──────┬─────────┬──────────┐
│ Rank │ Player & Strategy                    │ Score │ Wins │ Matches │ Win Rate │
├──────┼──────────────────────────────────────┼───────┼──────┼─────────┼──────────┤
│  🥇  │ P01                                  │ 45.0  │  15  │   20    │  75.0%   │
│      │ 🔷 BAYESIAN OPPONENT MODELING        │       │      │         │          │
├──────┼──────────────────────────────────────┼───────┼──────┼─────────┼──────────┤
│  🥈  │ P02                                  │ 38.5  │  12  │   20    │  60.0%   │
│      │ 🔷 COUNTERFACTUAL REGRET MINIMIZATION│       │      │         │          │
├──────┼──────────────────────────────────────┼───────┼──────┼─────────┼──────────┤
│  🥉  │ P03                                  │ 32.0  │  10  │   20    │  50.0%   │
│      │ 🔷 COMPOSITE STRATEGY                │       │      │         │          │
└──────┴──────────────────────────────────────┴───────┴──────┴─────────┴──────────┘
```

---

### 3. Live Matches - Player Moves in Real-Time

**Shows active matches with:**
- 🎮 Match ID and round number
- 👥 Both players with their strategies
- 🎯 **Each player's move/choice** in large display
- 📊 Current scores for both players

**Example:**
```
┌─────────────────────────────────────────────────────┐
│ Match-R5-M1                      Round 5/15         │
├─────────────────────────────────────────────────────┤
│  👤 P01 - Player 1                                  │
│  🔷 BAYESIAN OPPONENT MODELING                      │
│                                                     │
│           MOVE                                      │
│            ⃝7⃝                                      │
│                                                     │
├─────────────────────────────────────────────────────┤
│                    VS                               │
├─────────────────────────────────────────────────────┤
│  👤 P02 - Player 2                                  │
│  🔷 RANDOM STRATEGY                                 │
│                                                     │
│           MOVE                                      │
│            ⃝5⃝                                      │
│                                                     │
├─────────────────────────────────────────────────────┤
│  P01 Score: 15      P02 Score: 12                  │
└─────────────────────────────────────────────────────┘
```

---

### 4. Match History - All Moves & Results

**Complete history showing:**
- 📅 Round number and match ID
- 👥 Both players with strategies
- 🎯 **Each player's move** (the actual number they chose)
- 🏆 Match result (WIN/LOSS)
- ⏰ Timestamp

**Example:**
```
┌─────────────────────────────────────────────────────┐
│ Round 4 - Match-R4-M2              3:45:23 PM       │
├─────────────────────────────────────────────────────┤
│                                                     │
│  👤 P03                        WIN              P04 │
│  🔷 COMPOSITE STRATEGY                   ADAPTIVE   │
│  Move: 8                                    Move: 3 │
│                                                     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Round 3 - Match-R3-M1              3:42:15 PM       │
├─────────────────────────────────────────────────────┤
│                                                     │
│  👤 P01                      LOSS              P02  │
│  🔷 BAYESIAN                              RANDOM    │
│  Move: 2                                    Move: 7 │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

### 5. Winner Celebration Modal

**When tournament completes, displays:**
- 🏆 Trophy animation
- 👑 Champion name
- 🔷 **Winning strategy** (highlighted)
- 📊 Statistics:
  - Total Score
  - Total Wins
  - Total Matches
  - Win Rate

---

## 🎮 How to Use

### Basic Usage

```python
from src.visualization.dashboard import DashboardAPI

# Create dashboard
dashboard = DashboardAPI()

# Start server
await dashboard.start_server(host="0.0.0.0", port=8050)
```

### With Game Orchestrator

```python
from src.agents.game_orchestrator import GameOrchestrator
from src.common.config_loader import get_config

config = get_config()
orchestrator = GameOrchestrator(
    config,
    enable_dashboard=True,  # Enable dashboard
    dashboard_port=8050
)

await orchestrator.start_all(...)
await orchestrator.run_league()
```

---

## 📡 Real-Time Data Flow

### 1. Game Events → Dashboard
```
Match Start → WebSocket → Live Matches Display
Player Move → WebSocket → Move Display (real number)
Match End → WebSocket → Match History
Round End → WebSocket → Round Progress Update
Standings Update → WebSocket → Standings Table
```

### 2. Data Structure

**Tournament Update:**
```json
{
  "type": "tournament_update",
  "data": {
    "current_round": 5,
    "total_rounds": 15,
    "standings": [
      {
        "player_id": "P01",
        "strategy": "BayesianOpponentModeling",
        "score": 45.0,
        "wins": 15,
        "total_matches": 20,
        "win_rate": 0.75
      }
    ]
  }
}
```

**Match Update:**
```json
{
  "type": "match_update",
  "data": {
    "match_id": "Match-R5-M1",
    "round": 5,
    "total_rounds": 15,
    "player_a": {
      "id": "P01",
      "name": "Player 1",
      "strategy": "BayesianOpponentModeling",
      "move": 7,
      "score": 15
    },
    "player_b": {
      "id": "P02",
      "name": "Player 2",
      "strategy": "RandomStrategy",
      "move": 5,
      "score": 12
    },
    "state": "IN_PROGRESS"
  }
}
```

---

## 🎨 Customization

### Change Port

```bash
python examples/dashboard/run_enhanced_dashboard.py --port 9000
```

### Quick Demo (4 players, 5 rounds)

```bash
python examples/dashboard/run_enhanced_dashboard.py --quick
```

### Custom Tournament

```bash
python examples/dashboard/run_enhanced_dashboard.py --players 6 --rounds 20
```

---

## 🔍 What You See

### Player Strategies Displayed

Each player's strategy is shown everywhere:
- ✅ In the standings table
- ✅ In live match displays
- ✅ In match history
- ✅ In winner celebration

**Example strategies shown:**
- `RANDOM STRATEGY`
- `BAYESIAN OPPONENT MODELING`
- `COUNTERFACTUAL REGRET MINIMIZATION`
- `COMPOSITE STRATEGY`
- `ADAPTIVE STRATEGY`
- `MIXED STRATEGY`

### Player Moves Displayed

Every move is shown:
- ✅ **Live matches** - See moves as they happen (e.g., "7", "3", "10")
- ✅ **Match history** - See all past moves
- ✅ **Real numbers** - Not mocked, actual game choices (1-10 in Odd/Even game)

### Round Information

Always visible:
- ✅ Current round number
- ✅ Total rounds
- ✅ Rounds played so far
- ✅ Rounds remaining
- ✅ Progress percentage

---

## 🌟 Features Summary

| Feature | Status | Details |
|---------|--------|---------|
| Player Strategies | ✅ | Shown in all views |
| Current Round | ✅ | Large display at top |
| Total Rounds | ✅ | Large display at top |
| Rounds Played | ✅ | Large display at top |
| Rounds Remaining | ✅ | Large display at top |
| Live Standings | ✅ | Real-time table with strategies |
| Player Moves | ✅ | Actual moves displayed (1-10) |
| Match History | ✅ | All past moves and results |
| Winner Display | ✅ | With strategy highlight |
| Real-Time Updates | ✅ | WebSocket streaming |

---

## 🔧 Troubleshooting

### Dashboard not connecting?

```bash
# Check if server is running
curl http://localhost:8050/health

# Should return: {"status": "healthy", ...}
```

### Not seeing real-time updates?

1. Check browser console for WebSocket errors
2. Ensure port 8050 is not blocked
3. Try refreshing the page

### Want to see test data?

The dashboard is designed for **real game data**. To see it in action:

```bash
# Run a quick tournament
python examples/dashboard/run_enhanced_dashboard.py --quick
```

---

## 📚 API Endpoints

The dashboard also provides REST API endpoints:

```
GET  /                    - Dashboard UI
GET  /health              - Health check
GET  /api/tournament      - Tournament state
GET  /api/standings       - Current standings
GET  /api/player/{id}     - Player details
WS   /ws                  - WebSocket connection
```

---

## 🎯 What Makes This Dashboard Comprehensive?

**Unlike other dashboards, this shows:**

1. ✅ **Real player moves** - See actual choices (7, 3, 10, etc.)
2. ✅ **Every player's strategy** - Visible everywhere
3. ✅ **Complete round info** - Played + Remaining
4. ✅ **Match-by-match history** - Every move recorded
5. ✅ **Real-time streaming** - Updates as games happen
6. ✅ **No mocked data** - All data from real game league

---

## 🚀 Next Steps

1. **Run the dashboard**: `python examples/dashboard/run_enhanced_dashboard.py`
2. **Open browser**: http://localhost:8050
3. **Watch real-time gameplay**: See all moves, strategies, and results
4. **Export data**: Click "Export Data" button to save JSON

---

## 💡 Tips

- **Full screen**: Press F11 for immersive view
- **Multiple monitors**: Open dashboard on second screen
- **Record gameplay**: Use browser screen recording
- **Share results**: Use "Export Data" button
- **Compare strategies**: Watch how different strategies perform

---

## 🎉 Enjoy!

You now have a **comprehensive, real-time dashboard** that shows **every detail** of your game league, including player strategies, moves, rounds, and standings - all with **real data**!

**Questions?** Check the code in:
- `src/visualization/comprehensive_dashboard.py` - Dashboard HTML
- `src/visualization/dashboard.py` - Dashboard API
- `src/visualization/integration.py` - Data integration
- `examples/dashboard/run_enhanced_dashboard.py` - Usage example

