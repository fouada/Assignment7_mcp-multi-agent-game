# 🐛 Bug Fix: Dashboard Port Conflict (Port 8050)

## Problem
When running `./launch_league.sh`, the dashboard was trying to start **twice**, causing:
```
ERROR: [Errno 48] error while attempting to bind on address ('127.0.0.1', 8050): address already in use
```

## Root Cause
In `src/visualization/integration.py` line 150, the `start()` method was calling:
```python
asyncio.create_task(self.dashboard.start_server())
```

This tried to start the dashboard server a **second time**, even though it was already started by the launcher in `src/launcher/component_launcher.py`.

## Solution Applied
**File**: `src/visualization/integration.py`  
**Line**: 150

**Before:**
```python
async def start(self, tournament_id: str, total_rounds: int):
    """Start dashboard integration for a tournament."""
    self.enabled = True
    
    # Initialize tournament state
    self.tournament_state = TournamentDashboardState(...)
    
    # Start dashboard server (non-blocking)
    asyncio.create_task(self.dashboard.start_server())  # ❌ DUPLICATE START
    
    logger.info(f"Dashboard integration started for tournament {tournament_id}")
```

**After:**
```python
async def start(self, tournament_id: str, total_rounds: int):
    """Start dashboard integration for a tournament."""
    self.enabled = True
    
    # Initialize tournament state
    self.tournament_state = TournamentDashboardState(...)
    
    # Dashboard server is already started by the launcher
    # No need to start it again here to avoid port conflicts  # ✅ FIXED
    
    logger.info(f"Dashboard integration started for tournament {tournament_id}")
```

## Impact
- ✅ Removes duplicate dashboard server initialization
- ✅ Prevents port 8050 conflict
- ✅ Allows clean startup of League Manager with dashboard
- ✅ No functional changes - dashboard still works correctly

## Testing
After applying this fix, run:
```bash
./launch_league.sh
```

**Expected Result:**
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

No errors should appear, and both services should remain running.

## Verification
You can verify the fix by:

1. **Check the log output** - Should see only ONE dashboard start message:
   ```
   [INFO] Starting dashboard server in background on 127.0.0.1:8050
   [INFO] ✓ Dashboard started at http://127.0.0.1:8050
   ```

2. **Open the dashboard** in your browser:
   - Navigate to: http://localhost:8050
   - Should see the live tournament dashboard

3. **Check processes**:
   ```bash
   lsof -i :8050
   ```
   Should show exactly ONE process on port 8050

## Related Files
- `src/visualization/integration.py` - Fixed duplicate server start
- `src/launcher/component_launcher.py` - Primary dashboard starter (unchanged)
- `src/main.py` - Alternative dashboard starter for direct runs (unchanged)

## Status
✅ **FIXED** - Ready to use

---

**Date**: December 28, 2025  
**Fix Applied By**: AI Assistant  
**Tested**: Pending user verification

