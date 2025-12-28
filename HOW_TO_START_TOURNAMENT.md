# 🎮 How to Start a Complete Tournament

## Overview
This guide shows you how to start a complete tournament with:
- 1 League Manager (with dashboard)
- Multiple Referees (in separate terminals)
- Multiple Players (in separate terminals)

---

## 🚀 Step-by-Step: Start Your First Tournament

### Step 1: Start League Manager (Terminal 1)

**Open Terminal 1:**
```bash
cd /Users/fouadaz/LearningFromUniversity/Learning/LLMSAndMultiAgentOrchestration/course-materials/assignments/Assignment7_mcp-multi-agent-game

./launch_league.sh
```

**What You'll See:**
```
============================================================
League Manager Running
============================================================
  Endpoint: http://localhost:8000
  Dashboard: http://localhost:8050
  League ID: league_2024_01

  Press Ctrl+C to stop
============================================================
```

**✅ League Manager is Ready!**
- Open browser to http://localhost:8050 to see dashboard

---

### Step 2: Start Referee #1 (Terminal 2)

**Open NEW Terminal 2:**
```bash
cd /Users/fouadaz/LearningFromUniversity/Learning/LLMSAndMultiAgentOrchestration/course-materials/assignments/Assignment7_mcp-multi-agent-game

./launch_referee.sh --id REF01 --port 8001
```

**What You'll See:**
```
========================================
  MCP Multi-Agent Game League
  Starting Referee: REF01
========================================

  Referee ID:      REF01
  Endpoint:        http://localhost:8001
  League Manager:  http://localhost:8000
  Auto-register:   Yes

  Press Ctrl+C to stop
========================================

✓ Referee REF01 registered with League Manager
✓ Ready to coordinate matches
```

---

### Step 3: Start Referee #2 (Terminal 3)

**Open NEW Terminal 3:**
```bash
cd /Users/fouadaz/LearningFromUniversity/Learning/LLMSAndMultiAgentOrchestration/course-materials/assignments/Assignment7_mcp-multi-agent-game

./launch_referee.sh --id REF02 --port 8002
```

**Note:** Each referee needs a **unique ID** and **unique port**!

---

### Step 4: Start Player #1 - Alice (Terminal 4)

**Open NEW Terminal 4:**
```bash
cd /Users/fouadaz/LearningFromUniversity/Learning/LLMSAndMultiAgentOrchestration/course-materials/assignments/Assignment7_mcp-multi-agent-game

./launch_player.sh --name Alice --port 8101 --strategy random
```

**What You'll See:**
```
========================================
  MCP Multi-Agent Game League
  Starting Player: Alice
========================================

  Player Name:     Alice
  Endpoint:        http://localhost:8101
  Strategy:        random
  League Manager:  http://localhost:8000
  Auto-register:   Yes

  Press Ctrl+C to stop
========================================

✓ Player Alice registered with League Manager
✓ Strategy: Random
✓ Waiting for matches...
```

---

### Step 5: Start Player #2 - Bob (Terminal 5)

**Open NEW Terminal 5:**
```bash
cd /Users/fouadaz/LearningFromUniversity/Learning/LLMSAndMultiAgentOrchestration/course-materials/assignments/Assignment7_mcp-multi-agent-game

./launch_player.sh --name Bob --port 8102 --strategy pattern
```

---

### Step 6: Start Player #3 - Carol (Terminal 6)

**Open NEW Terminal 6:**
```bash
cd /Users/fouadaz/LearningFromUniversity/Learning/LLMSAndMultiAgentOrchestration/course-materials/assignments/Assignment7_mcp-multi-agent-game

./launch_player.sh --name Carol --port 8103 --strategy nash
```

---

### Step 7: Start Player #4 - Dave (Terminal 7)

**Open NEW Terminal 7:**
```bash
cd /Users/fouadaz/LearningFromUniversity/Learning/LLMSAndMultiAgentOrchestration/course-materials/assignments/Assignment7_mcp-multi-agent-game

./launch_player.sh --name Dave --port 8104 --strategy bayesian
```

---

## 📊 Visual Terminal Layout

```
┌─────────────────┬─────────────────┬─────────────────┐
│   Terminal 1    │   Terminal 2    │   Terminal 3    │
│                 │                 │                 │
│ League Manager  │   Referee 1     │   Referee 2     │
│    :8000        │    REF01        │    REF02        │
│   Dashboard     │    :8001        │    :8002        │
│    :8050        │                 │                 │
└─────────────────┴─────────────────┴─────────────────┘

┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│   Terminal 4    │   Terminal 5    │   Terminal 6    │   Terminal 7    │
│                 │                 │                 │                 │
│  Player: Alice  │  Player: Bob    │  Player: Carol  │  Player: Dave   │
│  Strategy: Rand │  Strategy: Ptrn │  Strategy: Nash │  Strategy: Bayes│
│    :8101        │    :8102        │    :8103        │    :8104        │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

---

## 🎯 Quick Reference: Port Assignments

| Component | ID/Name | Port | Terminal |
|-----------|---------|------|----------|
| **League Manager** | league_2024_01 | 8000 | Terminal 1 |
| **Dashboard** | - | 8050 | Terminal 1 |
| **Referee 1** | REF01 | 8001 | Terminal 2 |
| **Referee 2** | REF02 | 8002 | Terminal 3 |
| **Referee 3** | REF03 | 8003 | Terminal 4 (optional) |
| **Player 1** | Alice | 8101 | Terminal 5 |
| **Player 2** | Bob | 8102 | Terminal 6 |
| **Player 3** | Carol | 8103 | Terminal 7 |
| **Player 4** | Dave | 8104 | Terminal 8 |
| **Player 5+** | ... | 8105+ | Terminal 9+ |

---

## 🔧 Command Templates

### Start Referee
```bash
./launch_referee.sh --id <REFEREE_ID> --port <PORT>
```

**Examples:**
```bash
./launch_referee.sh --id REF01 --port 8001
./launch_referee.sh --id REF02 --port 8002
./launch_referee.sh --id REF03 --port 8003
```

### Start Player
```bash
./launch_player.sh --name <NAME> --port <PORT> --strategy <STRATEGY>
```

**Examples:**
```bash
./launch_player.sh --name Alice --port 8101 --strategy random
./launch_player.sh --name Bob --port 8102 --strategy pattern
./launch_player.sh --name Carol --port 8103 --strategy nash
./launch_player.sh --name Dave --port 8104 --strategy bayesian
```

---

## 🎲 Available Player Strategies

| Strategy | Description | Best For |
|----------|-------------|----------|
| `random` | Random moves | Baseline testing |
| `pattern` | Pattern recognition | Learning opponent behavior |
| `nash` | Nash Equilibrium | Optimal mixed strategy |
| `bayesian` | Bayesian learning | Adaptive play |
| `cfr` | Counterfactual Regret Min | Advanced game theory |
| `ucb` | Upper Confidence Bound | Exploration/exploitation |
| `thompson` | Thompson Sampling | Bayesian bandits |
| `quantum` | Quantum-inspired | MIT innovation |
| `byzantine` | Byzantine tolerant | Secure multi-agent |
| `llm` | LLM-powered | Requires API key |

---

## 📋 Complete Example: 4-Player Tournament

Here's a complete script to start everything in order:

### Terminal 1: League Manager
```bash
./launch_league.sh
```

### Terminal 2: Referee 1
```bash
./launch_referee.sh --id REF01 --port 8001
```

### Terminal 3: Referee 2
```bash
./launch_referee.sh --id REF02 --port 8002
```

### Terminal 4: Player Alice (Random)
```bash
./launch_player.sh --name Alice --port 8101 --strategy random
```

### Terminal 5: Player Bob (Nash)
```bash
./launch_player.sh --name Bob --port 8102 --strategy nash
```

### Terminal 6: Player Carol (Bayesian)
```bash
./launch_player.sh --name Carol --port 8103 --strategy bayesian
```

### Terminal 7: Player Dave (CFR)
```bash
./launch_player.sh --name Dave --port 8104 --strategy cfr
```

---

## 🌐 View the Tournament

Once all components are running:

1. **Dashboard**: http://localhost:8050
   - Real-time tournament state
   - Live standings
   - Active matches
   - Round progression

2. **League Manager API**: http://localhost:8000/health
   - Check system health

3. **Metrics**: http://localhost:9090/metrics
   - Prometheus metrics (if enabled)

---

## 🎮 Using LLM Strategies

To use LLM-powered strategies:

### Step 1: Set API Key
```bash
export ANTHROPIC_API_KEY=your-api-key-here
# OR
export OPENAI_API_KEY=your-api-key-here
```

### Step 2: Launch LLM Player
```bash
./launch_player.sh --name Einstein --port 8105 --strategy llm
```

---

## 🛑 Stopping Everything

### Option 1: Stop Each Terminal Individually
Press `Ctrl+C` in each terminal to stop gracefully.

**Stop Order (Recommended):**
1. Stop all Players first (Terminals 4-7)
2. Stop all Referees (Terminals 2-3)
3. Stop League Manager (Terminal 1)

### Option 2: Kill All Processes
```bash
# Kill all league components
pkill -f "league_manager"
pkill -f "referee"
pkill -f "player"

# Or more aggressive
lsof -ti :8000-8200 | xargs kill -9
```

---

## 🔍 Troubleshooting

### Issue: "Port already in use"
```bash
# Check what's using the port
lsof -i :<PORT_NUMBER>

# Kill the process
kill -9 <PID>
```

### Issue: "Can't connect to League Manager"
Make sure League Manager is running first (Terminal 1):
```bash
curl http://localhost:8000/health
```

### Issue: Player/Referee not registering
Check League Manager terminal for registration messages.

---

## 📈 Monitoring Active Tournament

### Check Component Status
```bash
# Check League Manager
curl http://localhost:8000/health

# Check Referee
curl http://localhost:8001/health

# Check Player
curl http://localhost:8101/health
```

### View Logs
```bash
# League Manager logs
tail -f logs/system.log

# Referee logs
tail -f logs/agents/referee_REF01.log

# Player logs
tail -f logs/agents/player_Alice.log
```

---

## 🎯 Advanced Options

### Start Without Auto-Registration
```bash
# Referee without auto-registration
./launch_referee.sh --id REF01 --port 8001 --no-register

# Player without auto-registration
./launch_player.sh --name Alice --port 8101 --strategy random --no-register
```

### Enable Debug Mode
```bash
# Referee with debug logging
./launch_referee.sh --id REF01 --port 8001 --debug

# Player with debug logging
./launch_player.sh --name Alice --port 8101 --strategy random --debug
```

---

## 🎊 Success Indicators

You'll know everything is working when:

✅ **League Manager**: Shows "League Manager Running" with dashboard URL  
✅ **Each Referee**: Shows "✓ Referee registered with League Manager"  
✅ **Each Player**: Shows "✓ Player registered with League Manager"  
✅ **Dashboard**: Shows all players and referees in the web interface  
✅ **Matches Start**: You see match activity in the terminal logs  

---

## 📚 Next Steps

Once your tournament is running:

1. **Watch the Dashboard** - http://localhost:8050
2. **Add More Players** - Open more terminals and launch additional players
3. **Test Different Strategies** - Try all available strategies
4. **Run Research** - Use the research pipeline for analysis
5. **Monitor Performance** - Check metrics and logs

---

## 🆘 Need Help?

- **Full Guide**: `OPERATIONS_GUIDE.md`
- **Quick Fix**: `QUICK_FIX.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **Strategies**: `docs/GAME_THEORY_STRATEGIES.md`

---

<div align="center">

**🎮 Enjoy Your Tournament! 🎮**

**Made with ❤️ by the MCP Game Team**

</div>

