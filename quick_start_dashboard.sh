#!/bin/bash
# Quick Start Dashboard Demo
# ==========================
# Launches everything needed for the dashboard

echo "🎮 MCP Game League - Quick Start"
echo "=================================="
echo ""
echo "This will open 6 terminals:"
echo "  1. League Manager (port 8000)"
echo "  2. Referee (port 8001)"  
echo "  3-6. Four Players (ports 8101-8104)"
echo ""
echo "Then open: http://localhost:8050"
echo ""
read -p "Press Enter to continue..."

# Check if on macOS (for osascript)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "✅ Detected macOS - using Terminal.app"
    
    # Terminal 1: League Manager
    echo "📊 Starting League Manager..."
    osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"' && ./launch_league.sh"'
    sleep 3
    
    # Terminal 2: Referee
    echo "🏁 Starting Referee..."
    osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"' && ./launch_referee.sh --id REF01 --port 8001"'
    sleep 2
    
    # Terminal 3: Player 1
    echo "👤 Starting Alice (Adaptive Bayesian)..."
    osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"' && ./launch_player.sh --name Alice --port 8101 --strategy adaptive_bayesian"'
    sleep 1.5
    
    # Terminal 4: Player 2
    echo "👤 Starting Bob (Regret Matching)..."
    osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"' && ./launch_player.sh --name Bob --port 8102 --strategy regret_matching"'
    sleep 1.5
    
    # Terminal 5: Player 3
    echo "👤 Starting Charlie (Nash Equilibrium)..."
    osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"' && ./launch_player.sh --name Charlie --port 8103 --strategy nash"'
    sleep 1.5
    
    # Terminal 6: Player 4
    echo "👤 Starting Dave (Random)..."
    osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"' && ./launch_player.sh --name Dave --port 8104 --strategy random"'
    sleep 2
    
    echo ""
    echo "✅ All components launched!"
    echo ""
    echo "🌐 Opening dashboard..."
    open http://localhost:8050
    
    echo ""
    echo "=================================="
    echo "🎯 NEXT STEPS:"
    echo "=================================="
    echo ""
    echo "In the dashboard:"
    echo "  1. Click 'Connect' button"
    echo "  2. Verify 4 players registered"
    echo "  3. Click '🚀 Start Tournament'"
    echo "  4. Click '▶️ Run Round' (repeat 3 times)"
    echo "  5. View results and export data!"
    echo ""
    echo "To stop everything:"
    echo "  Close all Terminal windows or Ctrl+C in each"
    echo ""
    
else
    echo "❌ This script requires macOS Terminal.app"
    echo ""
    echo "Manual steps for Linux/Windows:"
    echo ""
    echo "Terminal 1: ./launch_league.sh"
    echo "Terminal 2: ./launch_referee.sh --id REF01 --port 8001"
    echo "Terminal 3: ./launch_player.sh --name Alice --port 8101 --strategy adaptive_bayesian"
    echo "Terminal 4: ./launch_player.sh --name Bob --port 8102 --strategy regret_matching"
    echo "Terminal 5: ./launch_player.sh --name Charlie --port 8103 --strategy nash"
    echo "Terminal 6: ./launch_player.sh --name Dave --port 8104 --strategy random"
    echo ""
    echo "Then open: http://localhost:8050"
fi

