# 🔧 Quick Fix Guide for Port 8050 Error

## The Problem
You encountered: `ERROR: [Errno 48] error while attempting to bind on address ('127.0.0.1', 8050): address already in use`

## Solution Steps

### Option 1: Kill Process on Port 8050 (Recommended)
```bash
# Find what's using port 8050
lsof -i :8050

# Kill the process (replace <PID> with the actual process ID)
kill -9 <PID>

# Or kill all Python processes on that port
lsof -ti :8050 | xargs kill -9
```

### Option 2: Use Different Port
```bash
# Edit the launch script to use a different port
# Or set environment variable
export DASHBOARD_PORT=8051

# Then run
./launch_league.sh
```

### Option 3: Manual Restart (Clean Method)
```bash
# 1. Make sure virtual environment is activated
source .venv/bin/activate  # If using .venv
# OR
source venv/bin/activate   # If using venv

# 2. Check if anything is running on the ports
lsof -i :8000 :8050

# 3. Kill any existing processes
pkill -f "league_manager"
pkill -f "dashboard"

# 4. Wait a moment for ports to be released
sleep 2

# 5. Restart the league
./launch_league.sh
```

### Option 4: Use Python Directly
```bash
# Activate virtual environment first
source .venv/bin/activate

# Run without dashboard (League Manager only)
python -m src.main --run --players 4 --strategy mixed

# Or with dashboard on different port
DASHBOARD_PORT=8051 python -m src.main --run --dashboard --players 4
```

## Alternative: Run Without Dashboard

If dashboard keeps having issues, run without it:

```bash
# Simple game without dashboard
python -m src.main --run --players 2 --strategy nash

# Tournament without dashboard
python -m src.main --run --players 4 --strategy mixed --rounds 5
```

## Verify Ports are Free

Before starting, check both ports:
```bash
# Check if ports are free
lsof -i :8000 :8050

# If nothing is returned, ports are free ✅
```

## Common Issues

### Issue: "python: command not found"
**Solution:** Activate virtual environment
```bash
source .venv/bin/activate
# OR
source venv/bin/activate
```

### Issue: "uv: Operation not permitted"
**Solution:** Use pip or clear UV cache
```bash
# Clear UV cache
rm -rf ~/.cache/uv/

# OR use pip instead
pip install -e ".[dev]"
```

### Issue: Dashboard starts then immediately fails
**Solution:** Port conflict - use different port
```bash
# Set custom port
export DASHBOARD_PORT=8051
./launch_league.sh
```

## Step-by-Step: Fresh Start

```bash
# 1. Stop everything
pkill -f "league_manager"
pkill -f "dashboard"
pkill -f "python.*src"

# 2. Verify ports are free
lsof -i :8000 :8050

# 3. Activate environment
source .venv/bin/activate

# 4. Test simple command first
python -c "import src; print('✅ Ready')"

# 5. Run simple game (no dashboard)
python -m src.main --run --players 2

# 6. If that works, try with dashboard
python -m src.main --run --dashboard --players 2
```

## Success Indicators

✅ **League Manager Started:**
```
[INFO] MCP Server started (server=league_manager | port=8000)
[INFO] League Manager running at http://localhost:8000/mcp
```

✅ **Dashboard Started:**
```
[INFO] ✓ Dashboard started at http://127.0.0.1:8050
[INFO] Dashboard enabled at http://localhost:8050
```

✅ **Both Running:**
```
============================================================
League Manager Running
============================================================
  Endpoint: http://localhost:8000
  Dashboard: http://localhost:8050
```

## Next Steps After Fix

Once it's running:
1. Open browser to http://localhost:8050 for dashboard
2. The league manager is ready to accept players
3. You can now run players/referees or test the system

## Need More Help?

- Check full guide: `OPERATIONS_GUIDE.md`
- Review logs: `tail -f logs/system.log`
- Check documentation: `docs/`

