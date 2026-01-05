#!/bin/bash
#
# Cleanup Script - Reset All Game Ports
# =====================================
# Use this when processes crash or are interrupted
#

echo "🧹 MCP Game League - Port Cleanup"
echo "=================================="
echo ""

# Function to check if any processes are running on ports
check_ports() {
    local ports="8000,8001,8050,8101,8102,8103,8104,8105,8106,8107,8108"
    lsof -ti:$ports 2>/dev/null
}

# Show what's running before cleanup
echo "📊 Checking for processes on game ports..."
BEFORE=$(check_ports | wc -l | tr -d ' ')
if [ "$BEFORE" -gt 0 ]; then
    echo "   Found $BEFORE process(es) using game ports"
    echo ""
    echo "   Processes:"
    lsof -ti:8000,8001,8050,8101,8102,8103,8104,8105,8106,8107,8108 2>/dev/null | while read pid; do
        ps -p $pid -o pid,command | tail -1
    done
else
    echo "   ✅ No processes found on game ports"
    echo ""
    echo "All ports are already clean!"
    exit 0
fi

echo ""
read -p "🗑️  Kill all these processes? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🔨 Killing processes..."
    
    # Kill by port
    lsof -ti:8000,8001,8050,8101,8102,8103,8104,8105,8106,8107,8108 2>/dev/null | xargs kill -9 2>/dev/null
    
    # Also kill by process name (backup)
    pkill -9 -f "src.cli player" 2>/dev/null
    pkill -9 -f "src.cli referee" 2>/dev/null
    pkill -9 -f "launch_player" 2>/dev/null
    pkill -9 -f "launch_referee" 2>/dev/null
    
    sleep 1
    
    # Verify cleanup
    echo ""
    echo "📊 Verifying cleanup..."
    AFTER=$(check_ports | wc -l | tr -d ' ')
    
    if [ "$AFTER" -eq 0 ]; then
        echo "   ✅ All ports cleaned successfully!"
        echo ""
        echo "✨ Ready to start fresh!"
        echo ""
        echo "Next steps:"
        echo "  1. ./launch_league.sh"
        echo "  2. Open http://localhost:8050"
        echo "  3. Register referee & players"
    else
        echo "   ⚠️  Warning: $AFTER process(es) still running"
        echo ""
        echo "Remaining processes:"
        check_ports | while read pid; do
            ps -p $pid -o pid,command | tail -1
        done
        echo ""
        echo "You may need to manually kill these with:"
        echo "  sudo kill -9 <PID>"
    fi
else
    echo ""
    echo "❌ Cleanup cancelled"
fi

echo ""

