#!/bin/bash
# Complete restart script

echo "🔄 Restarting MCP Game System..."
echo ""

# Step 1: Clean up all processes
echo "1️⃣ Cleaning up old processes..."
./full_cleanup.sh

# Wait a moment for ports to free up
sleep 2

# Step 2: Restart dashboard (if needed)
echo ""
echo "2️⃣ Checking dashboard..."
if ! lsof -ti:8050 > /dev/null 2>&1; then
    echo "   Starting dashboard..."
    nohup uv run uvicorn src.visualization.dashboard:app --host 0.0.0.0 --port 8050 > dashboard.log 2>&1 &
    sleep 3
else
    echo "   Dashboard already running ✓"
fi

# Step 3: Restart league manager
echo ""
echo "3️⃣ Starting league manager..."
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "   Killing old league manager..."
    kill -9 $(lsof -ti:8000) 2>/dev/null
    sleep 1
fi

# Start in background and show the command
echo "   League manager starting..."
echo ""
echo "================================================================"
echo "✅ Ready! Now in your terminal 171, run:"
echo ""
echo "   cd /Users/fouadaz/LearningFromUniversity/Learning/LLMSAndMultiAgentOrchestration/course-materials/assignments/Assignment7_mcp-multi-agent-game"
echo "   uv run python -m src.cli league --port 8000 --dashboard"
echo ""
echo "================================================================"

