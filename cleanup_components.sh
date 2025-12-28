#!/usr/bin/env bash
#
# Cleanup Script - Stop All Components
# =====================================
#
# Stops all running components gracefully.
#

set -e

echo "Stopping all MCP Game League components..."

if [ -f .component_pids ]; then
    echo "Found saved PIDs, stopping components gracefully..."
    source .component_pids

    for pid in $LEAGUE_PID $REF01_PID $REF02_PID $ALICE_PID $BOB_PID $CHARLIE_PID $DIANA_PID; do
        if ps -p $pid > /dev/null 2>&1; then
            echo "  Stopping PID $pid..."
            kill $pid 2>/dev/null || true
        fi
    done

    rm .component_pids
    echo "✓ All components stopped"
else
    echo "No saved PIDs found, killing by process name..."
    pkill -f "launch_league" || true
    pkill -f "launch_referee" || true
    pkill -f "launch_player" || true
    pkill -f "src.cli" || true
    echo "✓ All processes killed"
fi

echo ""
echo "Cleanup complete!"
