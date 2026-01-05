#!/bin/bash
# Full cleanup script - kills all player and referee processes

echo "🧹 Cleaning up all game processes..."

# Kill all player processes (ports 8101-8199)
for port in {8101..8110}; do
    pid=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$pid" ]; then
        echo "  Killing process on port $port (PID: $pid)"
        kill -9 $pid 2>/dev/null
    fi
done

# Kill all referee processes (ports 8001-8010)
for port in {8001..8010}; do
    pid=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$pid" ]; then
        echo "  Killing process on port $port (PID: $pid)"
        kill -9 $pid 2>/dev/null
    fi
done

echo "✅ Cleanup complete!"
echo ""
echo "Now you can register fresh players from the dashboard."

