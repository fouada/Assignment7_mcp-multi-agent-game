# MCP Multi-Agent Game League 🎮

A sophisticated multi-agent tournament system showcasing Model Context Protocol (MCP) for agent communication, featuring real-time dashboard visualization and advanced game theory strategies.

## 📸 Dashboard Features

### Real-Time Tournament Dashboard
![Dashboard Overview](screenshots/dashboard-overview.png)
*Live tournament dashboard showing player standings, strategies, and match results*

### Player Registration
![Player Registration](screenshots/player-registration-live.png)
*Players appear on the dashboard in real-time as they register - no refresh needed!*

### Live Match Visualization
![Live Match](screenshots/live-match.png)
*Watch matches unfold in real-time with player moves, scores, and outcomes*

### Tournament Progress
![Mid-Tournament](screenshots/round-2-active.png)
*Tournament standings update automatically as rounds progress*

### Winner Celebration
![Winner](screenshots/winner-celebration.png)
*Tournament completion with winner announcement and confetti celebration*

## 🎯 Key Features

✨ **Real-Time Updates**
- Dashboard updates automatically without page refresh
- WebSocket-based live communication
- Instant player registration visibility

🤖 **Advanced AI Strategies**
- Random (baseline)
- Pattern Detection
- Nash Equilibrium
- Adaptive Bayesian Learning
- Best Response
- Fictitious Play
- Regret Matching
- UCB (Upper Confidence Bound)
- Thompson Sampling

🏆 **Tournament Management**
- Automated round-robin scheduling
- Concurrent match execution
- Real-time standings calculation
- Winner determination

📊 **Analytics & Visualization**
- Live game arena showing active matches
- Strategy performance tracking
- Player statistics (wins, losses, win rate)
- Round-by-round progress

## 🚀 Quick Start

### 1. Start the League Manager
```bash
./launch_league.sh
```

Access dashboard at: http://localhost:8050

### 2. Start Referees
```bash
./launch_referee.sh --id REF01 --port 8001
./launch_referee.sh --id REF02 --port 8002
```

### 3. Register Players
```bash
./launch_player.sh --name Alice --port 8101 --strategy random
./launch_player.sh --name Bob --port 8102 --strategy pattern
./launch_player.sh --name Carol --port 8103 --strategy nash
./launch_player.sh --name Dave --port 8104 --strategy adaptive_bayesian
```

Watch players appear on the dashboard in real-time! ✨

### 4. Run the Tournament
```bash
# Option 1: Run all rounds automatically
uv run python -m src.main --run-all-rounds

# Option 2: Run rounds manually (step-by-step)
uv run python -m src.main --start-league
uv run python -m src.main --run-round  # Round 1
uv run python -m src.main --run-round  # Round 2
uv run python -m src.main --run-round  # Round 3
```

## 🎮 Game Rules

**Even-Odd Game:**
- Each player selects a number (0-10)
- Sum of both numbers determines winner
- **EVEN** player wins if sum is even (2 points)
- **ODD** player wins if sum is odd (2 points)
- Best of 5 rounds per match

**Tournament Scoring:**
- **Win:** 3 points
- **Draw:** 1 point
- **Loss:** 0 points

## 📊 Dashboard Panels

### 1. Tournament Status
- Current round / total rounds
- Active players count
- WebSocket connection status

### 2. Standings Table
- Player rankings
- Strategies used
- Points, wins, matches played
- Win rate percentages

### 3. Live Game Arena
- Active matches in progress
- Player moves and roles (ODD/EVEN)
- Real-time scores

### 4. Recent Activity
- Event log showing registrations, matches, results
- Timestamps for all actions

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ League Manager  │────▶│   Referees      │────▶│   Players       │
│   (Scheduler)   │     │  (Game Logic)   │     │ (AI Strategies) │
└────────┬────────┘     └─────────────────┘     └─────────────────┘
         │
         │ WebSocket
         ▼
┌─────────────────┐
│   Dashboard     │
│ (Real-time UI)  │
└─────────────────┘
```

**Communication:** MCP (Model Context Protocol)
**Updates:** WebSocket for real-time dashboard
**Event Bus:** Pub/sub for component coordination

## 🔧 Technologies

- **Python 3.11+**: Core language
- **FastAPI**: Dashboard backend & WebSocket
- **MCP**: Agent-to-agent communication
- **asyncio**: Asynchronous operations
- **OpenTelemetry**: Distributed tracing
- **Pydantic**: Data validation

## 📖 Documentation

- [Complete Setup Guide](HOW_TO_START_TOURNAMENT.md)
- [Operations Guide](docs/OPERATIONS_GUIDE.md)
- [Game Theory Strategies](docs/GAME_THEORY_STRATEGIES.md)
- [Architecture Details](docs/ARCHITECTURE.md)

## 🐛 Troubleshooting

**Dashboard not updating?**
- Check WebSocket status (should be green "Connected")
- Verify League Manager is running
- Check browser console for errors

**Players showing as P01, P02?**
- Ensure latest code is running (restart League Manager)
- Player names should display as "Alice", "Bob", etc.

**Strategies showing as "Unknown"?**
- Restart players with correct strategy names
- Valid strategies: random, pattern, nash, adaptive_bayesian, etc.

## 🎓 Educational Value

This project demonstrates:
- **Multi-agent systems** coordination
- **Event-driven architecture** patterns
- **Real-time communication** via WebSocket
- **Game theory** strategy implementation
- **Distributed tracing** and observability
- **Clean architecture** principles

## 📜 License

[Your License Here]

## 👥 Contributors

[Your Name/Team]

---

*Built with ❤️ for learning multi-agent orchestration and MCP*
