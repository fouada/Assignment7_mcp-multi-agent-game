# 🔧 Fix "Registration Rejected" Error

## Problem
You're seeing: `error: "Registration rejected"`

## Why This Happens
The league manager only accepts player registration when in **REGISTRATION** state. If a tournament has been started, the state changes to **IN_PROGRESS** and new registrations are blocked.

## ✅ Solution 1: Reset from Dashboard (Easiest)

1. **Click "🔄 Reset Tournament" button**
   - This resets the league back to REGISTRATION state
   - Keeps your existing players/referees registered
   - Clears match history and scores

2. **Try registering again**
   - Click "👤 Register Player"
   - Fill in the form
   - Should work now!

## ✅ Solution 2: Restart League Manager (Clean Slate)

If reset doesn't work, do a complete restart:

### Step 1: Stop Current League Manager
In Terminal 166 (or wherever it's running), press **Ctrl+C** to stop it

### Step 2: Start Fresh League Manager
```bash
cd /Users/fouadaz/LearningFromUniversity/Learning/LLMSAndMultiAgentOrchestration/course-materials/assignments/Assignment7_mcp-multi-agent-game
uv run python -m src.cli league --port 8000
```

### Step 3: Refresh Dashboard
1. In browser at `localhost:8050`
2. Press **Ctrl+Shift+R** (hard refresh)
3. Click "Connect"

### Step 4: Register Everything
Now you can register in this order:
1. **Register Referee first**: Click "🏁 Register Referee"
   - ID: `REF01`
   - Port: `8001`
   
2. **Register Players**: Click "👤 Register Player" (multiple times)
   - Alice, 8101, Adaptive Bayesian
   - Bob, 8102, Regret Matching
   - Charlie, 8103, Nash Equilibrium
   - Dave, 8104, Random

3. **Start Tournament**: Click "🚀 Start Tournament"

4. **Run Rounds**: Click "▶️ Run Round"

## ✅ Solution 3: Use Terminal Registration (Alternative)

If dashboard registration keeps failing, use terminal:

```bash
# Terminal 1: League Manager
uv run python -m src.cli league --port 8000

# Terminal 2: Register Referee
uv run python -m src.cli referee --id REF01 --port 8001 --register

# Terminal 3-6: Register Players
uv run python -m src.cli player --name Alice --port 8101 --strategy adaptive_bayesian --register
uv run python -m src.cli player --name Bob --port 8102 --strategy regret_matching --register
uv run python -m src.cli player --name Charlie --port 8103 --strategy nash --register
uv run python -m src.cli player --name Dave --port 8104 --strategy random --register
```

Then use dashboard for:
- ✅ Start Tournament
- ✅ Run Rounds
- ✅ View Results
- ✅ Export Data

## 🔍 How to Check League State

Open browser console (F12) and check the console logs. You should see league state information.

## 📋 Registration Order (Important!)

**Always follow this order:**
1. ✅ Start League Manager
2. ✅ Register Referee (at least 1)
3. ✅ Register Players (at least 2)
4. ✅ Start Tournament
5. ✅ Run Rounds

**Don't:**
- ❌ Try to register players after tournament started
- ❌ Register without a referee
- ❌ Start tournament with < 2 players

## 🎯 Expected Flow

```
League Manager Starts
    ↓
State = REGISTRATION (accepts registrations)
    ↓
Register Referee + Players
    ↓
Click "Start Tournament"
    ↓
State = IN_PROGRESS (rejects new registrations)
    ↓
Run Rounds
    ↓
Click "Reset Tournament"
    ↓
State = REGISTRATION (accepts registrations again!)
```

## ✅ Verify It's Working

When registration succeeds, you should see:
- ✅ Success popup: "Player 'Alice' registered successfully!"
- ✅ Event log: "✅ Player registered: Alice (adaptive_bayesian)"
- ✅ Console log: "success: true"

When registration fails:
- ❌ Error popup: "Failed to register player: Registration rejected"
- ❌ Event log: "❌ Failed to register player: Registration rejected"
- ❌ Console log: "success: false"

## 🆘 Still Not Working?

If you still see "Registration rejected" after reset:

1. **Check league manager terminal** - Look for error messages
2. **Check browser console (F12)** - Look for network errors
3. **Verify port 8000** - League manager must be on port 8000
4. **Try the terminal registration method** instead of dashboard

---

**Quick Command Reference:**
```bash
# Restart everything cleanly
pkill -f "src.cli league"  # Stop league manager
uv run python -m src.cli league --port 8000  # Start fresh

# Then in dashboard:
1. Hard refresh (Ctrl+Shift+R)
2. Click Connect
3. Register referee
4. Register players
5. Start tournament
```

