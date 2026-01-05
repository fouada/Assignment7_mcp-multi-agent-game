# 🔧 Troubleshooting & Fixes

## Overview

This folder contains documentation for fixes, workarounds, and troubleshooting guides for common issues in the MCP Multi-Agent Game League System.

---

## 📚 Documents

| Document | Issue | Status | Read Time |
|----------|-------|--------|-----------|
| [CHARTS_FIX.md](CHARTS_FIX.md) | Chart display issues | ✅ Fixed | 5 min |
| [REGISTRATION_FIX.md](REGISTRATION_FIX.md) | Player registration problems | ✅ Fixed | 10 min |
| [TOURNAMENT_START_FIX.md](TOURNAMENT_START_FIX.md) | Tournament startup issues | ✅ Fixed | 10 min |

---

## 🎯 Common Issues

### Issue #1: Charts Not Displaying

**Solution:** See [CHARTS_FIX.md](CHARTS_FIX.md)

**Quick Fix:**
```bash
# Verify chart dependencies
pip install matplotlib plotly

# Restart dashboard
python -m src.visualization.dashboard
```

### Issue #2: Player Registration Fails

**Solution:** See [REGISTRATION_FIX.md](REGISTRATION_FIX.md)

**Quick Fix:**
```bash
# Check port availability
netstat -an | grep LISTEN | grep 810

# Clear registration state
rm -rf .cache/registrations
```

### Issue #3: Tournament Won't Start

**Solution:** See [TOURNAMENT_START_FIX.md](TOURNAMENT_START_FIX.md)

**Quick Fix:**
```bash
# Verify minimum players
# Need at least 2 players registered

# Restart league manager
./restart_all.sh
```

---

## 🆘 Getting Help

If these fixes don't resolve your issue:

1. **Check Logs:** `tail -f league.log`
2. **Verify Setup:** `./scripts/verify_compliance.sh`
3. **Run Tests:** `make test`
4. **Full Cleanup:** `./full_cleanup.sh && ./restart_all.sh`

---

## 🔗 Related Documentation

- **[Main Guides](../README.md)** - All user guides
- **[Dashboard Guide](../DASHBOARD_COMPLETE_TESTING.md)** - Complete dashboard docs
- **[Getting Started](../../getting-started/README.md)** - Setup guides
- **[Testing](../../testing/README.md)** - Testing documentation

---

## 📝 Reporting New Issues

Found a bug? Please report it:

1. Check if already documented here
2. Check GitHub issues
3. Create detailed bug report
4. Include logs and steps to reproduce

---

*Last Updated: January 5, 2026*

