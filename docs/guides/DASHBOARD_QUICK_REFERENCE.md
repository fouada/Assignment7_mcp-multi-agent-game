# 🎮 Comprehensive Dashboard - Quick Reference Card

## 🚀 Quick Start

```bash
# Method 1: Shell script (easiest)
./run_comprehensive_dashboard.sh

# Method 2: Python directly
python examples/dashboard/run_enhanced_dashboard.py

# Method 3: Quick demo (4 players, 5 rounds)
python examples/dashboard/run_enhanced_dashboard.py --quick
```

**Then open**: http://localhost:8050

---

## 📊 What You'll See

### 1. Round Progress Banner (Top)
```
Current: 5  |  Total: 15  |  Played: 5  |  Remaining: 10
[█████░░░░░░░░░░] 33.3% Complete
```

### 2. Player Standings Table
```
Rank | Player & Strategy              | Score | Wins | Matches | Win Rate
🥇   | P01 - BAYESIAN MODELING        | 45.0  | 15   | 20      | 75.0%
🥈   | P02 - CFR MINIMIZATION         | 38.5  | 12   | 20      | 60.0%
🥉   | P03 - COMPOSITE STRATEGY       | 32.0  | 10   | 20      | 50.0%
```

### 3. Live Matches with Player Moves
```
┌──────────────────────────────┐
│ Match-R5-M1    Round 5/15    │
│                              │
│ P01 - BAYESIAN MODELING      │
│ Move: 7                      │
│                              │
│          VS                  │
│                              │
│ P02 - RANDOM STRATEGY        │
│ Move: 5                      │
│                              │
│ P01: 15 pts | P02: 12 pts    │
└──────────────────────────────┘
```

### 4. Match History
```
Round 4 - Match-R4-M2
P03 (COMPOSITE) Move: 8  →  WIN
P04 (ADAPTIVE)  Move: 3  →  LOSS
```

### 5. Winner Modal
```
🏆 Tournament Champion!
     [PLAYER NAME]
  Winning Strategy:
 BAYESIAN OPPONENT MODELING
 
Score: 45.0 | Wins: 15 | Matches: 20 | Win Rate: 75%
```

---

## 🎯 All Features Checklist

✅ Each player's strategy  
✅ Current round  
✅ Total rounds  
✅ Rounds played  
✅ Rounds remaining  
✅ Live standings  
✅ Player moves in each match  
✅ Match history  
✅ Winner display  
✅ Real-time updates  

---

## ⚙️ Command Options

```bash
# Default (6 players, 15 rounds)
python examples/dashboard/run_enhanced_dashboard.py

# Quick demo (4 players, 5 rounds)
python examples/dashboard/run_enhanced_dashboard.py --quick

# Custom players
python examples/dashboard/run_enhanced_dashboard.py --players 8

# Custom rounds
python examples/dashboard/run_enhanced_dashboard.py --rounds 30

# Custom port
python examples/dashboard/run_enhanced_dashboard.py --port 9000

# Combine options
python examples/dashboard/run_enhanced_dashboard.py --players 4 --rounds 10 --port 8080
```

---

## 🔄 Real-Time Updates

**Dashboard automatically updates when:**
- New round starts
- Player makes a move
- Match completes
- Standings change
- Tournament ends

**No refresh needed!** All via WebSocket streaming.

---

## 💾 Export Data

Click **"Export Data"** button to save complete tournament data as JSON:

```json
{
  "currentRound": 5,
  "totalRounds": 15,
  "standings": [...],
  "matchHistory": [...]
}
```

---

## 🌐 API Endpoints

```
GET  /               Dashboard UI
GET  /health         Health check
GET  /api/tournament Tournament state
GET  /api/standings  Current standings
WS   /ws             Real-time updates
```

---

## 🎨 Strategy Badges

Your dashboard will show these strategies:
- `RANDOM STRATEGY`
- `BAYESIAN OPPONENT MODELING`
- `COUNTERFACTUAL REGRET MINIMIZATION`
- `COMPOSITE STRATEGY`
- `ADAPTIVE STRATEGY`
- `MIXED STRATEGY`

---

## 🐛 Troubleshooting

**Dashboard won't load?**
```bash
# Check if server is running
curl http://localhost:8050/health
```

**Not seeing updates?**
- Check browser console (F12)
- Ensure WebSocket connects
- Try refreshing page

**Port already in use?**
```bash
python examples/dashboard/run_enhanced_dashboard.py --port 9000
```

---

## 📚 More Info

- **Full Guide**: `docs/COMPREHENSIVE_DASHBOARD_GUIDE.md`
- **Implementation Summary**: `COMPREHENSIVE_DASHBOARD_SUMMARY.md`
- **Code**: `src/visualization/comprehensive_dashboard.py`

---

## 🎉 Features Summary

| Feature | Location | Real-Time |
|---------|----------|-----------|
| Player Strategies | Everywhere | ✅ |
| Current Round | Top banner | ✅ |
| Rounds Played | Top banner | ✅ |
| Rounds Remaining | Top banner | ✅ |
| Standings Table | Main section | ✅ |
| Live Matches | Match cards | ✅ |
| Player Moves | Match cards | ✅ |
| Match History | History section | ✅ |
| Winner Display | Modal popup | ✅ |

---

## 💡 Pro Tips

1. **Full screen**: Press F11 for immersive view
2. **Record**: Use browser screen recording
3. **Share**: Export data button → JSON file
4. **Compare**: Watch multiple strategies compete
5. **Learn**: See how strategies make decisions

---

## 🎯 What Makes This Special?

✨ **Real data** - Not mocked or simulated  
✨ **Complete visibility** - See everything  
✨ **Real-time** - Updates as games happen  
✨ **Player moves** - Actual choices displayed  
✨ **Strategies shown** - Know who uses what  
✨ **Round tracking** - Complete progress info  

---

## 🚀 Ready to Go!

```bash
# Start now:
./run_comprehensive_dashboard.sh

# Or:
python examples/dashboard/run_enhanced_dashboard.py

# Then visit:
http://localhost:8050
```

**Enjoy your comprehensive, real-time game league dashboard!** 🎮

