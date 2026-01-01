# 📸 Screenshot Guide for README Documentation

## 🎯 Recommended Screenshots

### 1. **Dashboard Overview** (`docs/screenshots/dashboard-overview.png`)
**When to capture:** After all 4 players have registered but before starting the league
**What to show:**
- All panels visible
- 4 players in standings (Alice, Bob, Carol, Dave)
- Player names (not P01, P02, etc.)
- Strategy names (random, pattern, nash, adaptive_bayesian)
- "Waiting for tournament" or Round 0/3 status

**How to get there:**
```bash
# Terminal 152: League Manager should be running
# Terminal 153-154: Both referees running
# Terminal 155-158: All 4 players registered
# Browser: http://localhost:8050
```

---

### 2. **Player Registration Live** (`docs/screenshots/player-registration.png`)
**When to capture:** The moment a player registers (shows real-time updates)
**What to show:**
- Dashboard with fewer players (1-3 players visible)
- Recent activity log showing registration
- WebSocket status: "Connected" (green)

**How to get there:**
```bash
# Start fresh:
# 1. Restart League Manager
# 2. Open browser at http://localhost:8050
# 3. Start players ONE BY ONE and capture after each registration
./launch_player.sh --name Alice --port 8101 --strategy random
# Wait 1 second, take screenshot showing Alice appeared
./launch_player.sh --name Bob --port 8102 --strategy pattern
# Wait 1 second, take screenshot showing both Alice and Bob
```

---

### 3. **Active Tournament - Round 1** (`docs/screenshots/round-1-active.png`)
**When to capture:** During Round 1 execution
**What to show:**
- Current Round: 1/3
- Active matches in "Live Game Arena"
- Player moves and scores
- Real-time standings updates

**How to get there:**
```bash
# After all players registered:
uv run python -m src.main --start-league
uv run python -m src.main --run-round
# Take screenshot while matches are playing
```

---

### 4. **Standings Table Detailed** (`docs/screenshots/standings-detail.png`)
**When to capture:** After Round 2 (mid-tournament)
**What to show:**
- Clear rankings (1st, 2nd, 3rd, 4th)
- Player names (Alice, Bob, Carol, Dave)
- Strategy badges
- Scores, wins, matches played
- Win rate percentages

**How to get there:**
```bash
uv run python -m src.main --run-round  # Round 2
# Take screenshot of standings table
```

---

### 5. **Winner Celebration** (`docs/screenshots/winner-celebration.png`)
**When to capture:** Immediately after Round 3 completes
**What to show:**
- Confetti animation
- Winner modal/banner
- Winner's name, strategy, final score
- Final standings

**How to get there:**
```bash
uv run python -m src.main --run-round  # Round 3
# Winner celebration should appear automatically (no F5!)
# Take screenshot quickly while confetti is visible
```

---

### 6. **Live Match Details** (`docs/screenshots/live-match.png`)
**When to capture:** During any round when matches are in progress
**What to show:**
- "Live Game Arena" panel
- Two players facing each other
- Player moves (numbers)
- Real-time scores
- Match progress

**How to get there:**
```bash
# During any round execution, quickly take screenshot
# Matches complete in ~2 seconds, so be ready!
```

---

## 🛠️ Screenshot Tools

### macOS (Recommended):
```bash
# Full dashboard screenshot
Cmd + Shift + 3  # Saves to Desktop

# Selected area (crop to dashboard only)
Cmd + Shift + 4  # Drag to select area

# Specific browser window
Cmd + Shift + 4 → Press Space → Click browser window
```

### Chrome DevTools (Best Quality):
1. Open dashboard: http://localhost:8050
2. Press F12 (open DevTools)
3. Press Cmd+Shift+P (Mac) or Ctrl+Shift+P (Windows)
4. Type: "screenshot"
5. Select: **"Capture full size screenshot"**
6. Saves high-quality PNG to Downloads

### Firefox DevTools:
1. Press F12
2. Click "..." (three dots) menu
3. Select "Take a screenshot"
4. Choose "Save full page" or "Save visible"

---

## 📐 Screenshot Best Practices

### Window Size
Set consistent browser window size for all screenshots:
```javascript
// Recommended dashboard size (paste in browser console)
window.resizeTo(1920, 1080);  // Full HD
// or
window.resizeTo(1440, 900);   // Laptop standard
```

### Clean Screenshots
- Close unnecessary browser tabs
- Hide browser bookmarks bar (Cmd+Shift+B)
- Use browser's "Responsive Design Mode" for consistent sizing
- Disable browser extensions that add UI elements

### File Naming
```
docs/screenshots/
  ├── dashboard-overview.png          # Main view
  ├── player-registration-live.png    # Real-time updates
  ├── standings-table.png             # Detailed standings
  ├── live-match-round-1.png         # Match in progress
  ├── round-2-active.png             # Mid-tournament
  ├── winner-celebration.png          # Tournament end
  ├── strategy-badges.png             # Close-up of strategies
  └── full-tournament-flow.gif        # (Optional) Animated GIF
```

---

## 🎬 Optional: Create Animated GIF

Use **LICEcap** (free, cross-platform) or **Kap** (Mac) to record:

1. Full tournament flow (30 seconds max):
   - Players registering one by one
   - Starting league
   - Round execution
   - Winner celebration

2. Save as: `docs/screenshots/tournament-flow.gif`
3. Keep file size < 5MB for README

Tools:
- **LICEcap**: https://www.cockos.com/licecap/
- **Kap**: https://getkap.co/ (Mac only)
- **ScreenToGif**: https://www.screentogif.com/ (Windows)

---

## 📝 Adding to README

After capturing screenshots, add them to your README:

```markdown
## 🎮 Dashboard Overview

![Dashboard Overview](docs/screenshots/dashboard-overview.png)
*Real-time tournament dashboard showing player standings and strategies*

## 🏃 Live Tournament

![Live Match](docs/screenshots/live-match.png)
*Players competing in real-time with visible moves and scores*

## 🏆 Winner Celebration

![Winner](docs/screenshots/winner-celebration.png)
*Tournament completion with winner announcement*
```

---

## ✅ Checklist

Before taking screenshots, ensure:
- [ ] League Manager restarted with latest fixes
- [ ] All 4 players registered successfully
- [ ] Player names showing correctly (Alice, Bob, Carol, Dave)
- [ ] Strategies displaying (random, pattern, nash, adaptive_bayesian)
- [ ] Dashboard updates WITHOUT refresh (F5)
- [ ] WebSocket status shows "Connected" (green)
- [ ] Browser at http://localhost:8050
- [ ] Browser window sized consistently

---

## 🐛 If Things Don't Look Right

**Player names showing as P01, P02, etc.:**
```bash
# Restart League Manager to load latest fixes
cd terminal-152
Ctrl+C
./launch_league.sh
```

**Dashboard not updating without refresh:**
```bash
# Check League Manager logs for datetime errors
# Should see NO errors when players register
# WebSocket should stay connected: "1 active connections"
```

**Strategies showing as "Unknown":**
```bash
# Restart players to load correct strategy names
./launch_player.sh --name Carol --port 8103 --strategy nash
./launch_player.sh --name Dave --port 8104 --strategy adaptive_bayesian
```

