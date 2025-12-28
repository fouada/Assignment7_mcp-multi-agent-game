# Quick Start: Modular Component Invocation

## 🚀 Start Components Separately with Real-Time Dashboard

This guide shows you how to start the MCP Multi-Agent Game League with **modular component invocation** and **real-time dashboard synchronization**.

---

## Prerequisites

1. **UV installed** (Python package manager)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **(Optional) LLM API Key** for AI-powered strategies
   ```bash
   export ANTHROPIC_API_KEY=your-key-here
   # or
   export OPENAI_API_KEY=your-key-here
   ```

---

## 🎯 Fastest Start (4 Players, 2 Referees)

Open **8 terminal windows** and run these commands:

### Terminal 1: League Manager + Dashboard
```bash
./launch_league.sh
```
✓ League Manager: `http://localhost:8000`
✓ Dashboard: `http://localhost:8050`

**Wait for:** `"League Manager Running"` message

---

### Terminal 2: Referee 1
```bash
./launch_referee.sh --id REF01 --port 8001
```
✓ Automatically registers with league

---

### Terminal 3: Referee 2
```bash
./launch_referee.sh --id REF02 --port 8002
```
✓ Enables parallel match execution

---

### Terminal 4: Player 1 (Random Strategy)
```bash
./launch_player.sh --name Alice --port 8101 --strategy random
```
✓ Fast, simple random moves

---

### Terminal 5: Player 2 (Pattern Strategy)
```bash
./launch_player.sh --name Bob --port 8102 --strategy pattern
```
✓ Alternating pattern moves

---

### Terminal 6: Player 3 (LLM Strategy - Claude)
```bash
export ANTHROPIC_API_KEY=your-key
./launch_player.sh --name Charlie --port 8103 --strategy llm
```
✓ AI-powered strategic gameplay

---

### Terminal 7: Player 4 (Random Strategy)
```bash
./launch_player.sh --name Diana --port 8104 --strategy random
```
✓ Balanced competition

---

### Terminal 8: Control the League
```bash
# Start the league (after all components registered)
uv run python -m src.main --start-league

# Run next round
uv run python -m src.main --run-round

# Or auto-run all rounds
uv run python -m src.main --run-all-rounds

# Check standings anytime
uv run python -m src.main --get-standings
```

---

### Browser: Monitor Dashboard
Open: **http://localhost:8050**

You'll see:
- ✅ Real-time player registration
- ✅ Live round announcements
- ✅ Match assignments to referees
- ✅ Player moves and decisions
- ✅ Match results (instant)
- ✅ Updated standings (live)
- ✅ Tournament progress

---

## 📊 What You'll See

### 1. Component Registration (Instant)
```
Dashboard updates as each component registers:
  → REF01 registered
  → REF02 registered
  → Alice registered (Random)
  → Bob registered (Pattern)
  → Charlie registered (LLM)
  → Diana registered (Random)
```

### 2. League Start
```
Terminal 8:
  $ uv run python -m src.main --start-league
  ✓ League started with 4 players
  ✓ 6 rounds scheduled (round-robin)
```

Dashboard shows:
```
  Tournament: league_2024_01
  Round: 0 / 6
  Players: 4
  Status: Ready
```

### 3. Round Execution (Real-Time)
```
Terminal 8:
  $ uv run python -m src.main --run-round

  ========================================
  Round 1/6
  ========================================
  Match 1: Alice vs Bob (REF01)
  Match 2: Charlie vs Diana (REF02)
```

Dashboard displays:
```
  ⚡ Round 1 Started

  Match 1: Alice (Random) vs Bob (Pattern)
    Referee: REF01
    Status: In Progress

  Match 2: Charlie (LLM) vs Diana (Random)
    Referee: REF02
    Status: In Progress
```

### 4. Match Progress (Live Updates)
```
Dashboard shows move-by-move:

  Round 1, Game 1:
    Alice chose: EVEN
    Bob chose: ODD
    Winner: Bob

  Round 2, Game 1:
    Alice chose: ODD
    Bob chose: EVEN
    Winner: Alice
```

### 5. Standings Update (Instant)
```
After each round, standings update immediately:

  Rank  Player   Strategy  Wins  Points
  ───────────────────────────────────────
   1    Charlie  LLM       2     6
   2    Bob      Pattern   2     6
   3    Alice    Random    1     3
   4    Diana    Random    0     0
```

---

## 🎮 Advanced Usage

### Add More Players Dynamically

You can add players BEFORE the league starts:

```bash
# Terminal 9: Add 5th player
./launch_player.sh --name Eve --port 8105 --strategy pattern

# Terminal 10: Add 6th player
./launch_player.sh --name Frank --port 8106 --strategy llm
```

Dashboard instantly shows new registrations!

---

### Mix Different Strategies

```bash
# Tournament of strategies
./launch_player.sh --name "Random_1" --port 8101 --strategy random
./launch_player.sh --name "Random_2" --port 8102 --strategy random
./launch_player.sh --name "Pattern_1" --port 8103 --strategy pattern
./launch_player.sh --name "Pattern_2" --port 8104 --strategy pattern
./launch_player.sh --name "LLM_1" --port 8105 --strategy llm
./launch_player.sh --name "LLM_2" --port 8106 --strategy llm
```

See which strategy performs best!

---

### Scale to More Referees

More referees = faster parallel execution:

```bash
./launch_referee.sh --id REF01 --port 8001
./launch_referee.sh --id REF02 --port 8002
./launch_referee.sh --id REF03 --port 8003
./launch_referee.sh --id REF04 --port 8004
```

Now 4 matches can run simultaneously!

---

## 🔍 Monitoring & Debugging

### Check Component Status

```bash
# League Manager health
curl http://localhost:8000/health

# Referee status
curl http://localhost:8001/health

# Player status
curl http://localhost:8101/health
```

### View Logs

Enable debug logging:
```bash
./launch_league.sh --debug
./launch_referee.sh --id REF01 --port 8001 --debug
./launch_player.sh --name Alice --port 8101 --debug
```

### Dashboard WebSocket

Open browser console at `http://localhost:8050` to see live events:
```javascript
// WebSocket messages show all state changes
{
  type: "state_update",
  event_type: "agent.registered",
  data: { player_id: "P01", name: "Alice" }
}

{
  type: "tournament_update",
  data: { current_round: 2, standings: [...] }
}
```

---

## 🛑 Stopping Components

### Graceful Shutdown

Press `Ctrl+C` in each terminal to stop gracefully:
1. Players stop accepting matches
2. Referees finish current matches
3. League Manager saves final state
4. Dashboard closes WebSocket connections

### Kill All (Emergency)

```bash
pkill -f "src.cli"
pkill -f "launch_"
```

---

## 📚 Next Steps

- Read [MODULAR_ARCHITECTURE.md](MODULAR_ARCHITECTURE.md) for detailed architecture
- See [README.md](README.md) for full documentation
- Check `src/launcher/` for implementation details
- View `src/cli.py` for all CLI options

---

## 🎉 Summary

You now have:
- ✅ **Modular component invocation** (each component runs independently)
- ✅ **Real-time dashboard** (instant state synchronization)
- ✅ **Guaranteed state updates** (every action reflected immediately)
- ✅ **Service discovery** (components find each other automatically)
- ✅ **MIT-level architecture** (production-grade design)

The dashboard updates in **real-time** for:
- Player/referee registration
- Round announcements
- Match assignments
- Player moves
- Match results
- Standings changes

**Enjoy your MIT-level multi-agent game league!** 🚀
