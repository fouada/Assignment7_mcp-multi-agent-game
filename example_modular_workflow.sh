#!/usr/bin/env bash
#
# Example Modular Workflow - MIT Level
# =====================================
#
# This script demonstrates how to start all components separately
# with real-time dashboard synchronization.
#
# Each component runs as a separate process, allowing for:
# - Independent scaling
# - Dynamic addition/removal of components
# - Real-time monitoring via dashboard
# - Production-grade deployment
#
# Usage:
#   ./example_modular_workflow.sh
#

set -e

echo "========================================"
echo "  MCP Multi-Agent Game League"
echo "  Modular Component Workflow Example"
echo "========================================"
echo ""
echo "This script will start all components"
echo "in separate background processes."
echo ""
echo "Components:"
echo "  - 1 League Manager + Dashboard"
echo "  - 2 Referees"
echo "  - 4 Players (mixed strategies)"
echo ""
echo "Press Enter to continue or Ctrl+C to cancel..."
read

# Create logs directory
mkdir -p logs

echo ""
echo "Step 1: Starting League Manager + Dashboard..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
./launch_league.sh > logs/league.log 2>&1 &
LEAGUE_PID=$!
echo "  ✓ League Manager started (PID: $LEAGUE_PID)"
echo "  → Log: logs/league.log"
echo "  → Endpoint: http://localhost:8000"
echo "  → Dashboard: http://localhost:8050"

# Wait for league manager to be ready
echo "  ⏳ Waiting for League Manager to initialize..."
sleep 3

echo ""
echo "Step 2: Starting Referees..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
./launch_referee.sh --id REF01 --port 8001 > logs/ref01.log 2>&1 &
REF01_PID=$!
echo "  ✓ Referee REF01 started (PID: $REF01_PID)"
echo "  → Log: logs/ref01.log"

./launch_referee.sh --id REF02 --port 8002 > logs/ref02.log 2>&1 &
REF02_PID=$!
echo "  ✓ Referee REF02 started (PID: $REF02_PID)"
echo "  → Log: logs/ref02.log"

# Wait for referees to register
echo "  ⏳ Waiting for referee registration..."
sleep 2

echo ""
echo "Step 3: Starting Players..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

./launch_player.sh --name Alice --port 8101 --strategy random > logs/alice.log 2>&1 &
ALICE_PID=$!
echo "  ✓ Player Alice (Random) started (PID: $ALICE_PID)"
echo "  → Log: logs/alice.log"

./launch_player.sh --name Bob --port 8102 --strategy pattern > logs/bob.log 2>&1 &
BOB_PID=$!
echo "  ✓ Player Bob (Pattern) started (PID: $BOB_PID)"
echo "  → Log: logs/bob.log"

./launch_player.sh --name Charlie --port 8103 --strategy random > logs/charlie.log 2>&1 &
CHARLIE_PID=$!
echo "  ✓ Player Charlie (Random) started (PID: $CHARLIE_PID)"
echo "  → Log: logs/charlie.log"

./launch_player.sh --name Diana --port 8104 --strategy pattern > logs/diana.log 2>&1 &
DIANA_PID=$!
echo "  ✓ Player Diana (Pattern) started (PID: $DIANA_PID)"
echo "  → Log: logs/diana.log"

# Wait for player registration
echo "  ⏳ Waiting for player registration..."
sleep 2

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ All components started successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Component Status:"
echo "  League Manager:  http://localhost:8000  (PID: $LEAGUE_PID)"
echo "  Dashboard:       http://localhost:8050"
echo "  Referee REF01:   http://localhost:8001  (PID: $REF01_PID)"
echo "  Referee REF02:   http://localhost:8002  (PID: $REF02_PID)"
echo "  Player Alice:    http://localhost:8101  (PID: $ALICE_PID)"
echo "  Player Bob:      http://localhost:8102  (PID: $BOB_PID)"
echo "  Player Charlie:  http://localhost:8103  (PID: $CHARLIE_PID)"
echo "  Player Diana:    http://localhost:8104  (PID: $DIANA_PID)"
echo ""
echo "Next Steps:"
echo "  1. Open dashboard: http://localhost:8050"
echo "  2. Start league:   uv run python -m src.main --start-league"
echo "  3. Run rounds:     uv run python -m src.main --run-all-rounds"
echo "  4. View logs:      tail -f logs/*.log"
echo ""
echo "To stop all components:"
echo "  kill $LEAGUE_PID $REF01_PID $REF02_PID $ALICE_PID $BOB_PID $CHARLIE_PID $DIANA_PID"
echo ""
echo "Or use: pkill -f 'launch_'"
echo ""

# Save PIDs to file for cleanup
cat > .component_pids <<EOF
LEAGUE_PID=$LEAGUE_PID
REF01_PID=$REF01_PID
REF02_PID=$REF02_PID
ALICE_PID=$ALICE_PID
BOB_PID=$BOB_PID
CHARLIE_PID=$CHARLIE_PID
DIANA_PID=$DIANA_PID
EOF

echo "PIDs saved to .component_pids"
echo ""
echo "Monitoring dashboard updates..."
echo "  ✓ Registrations will appear in real-time"
echo "  ✓ Round announcements will be instant"
echo "  ✓ Match results will update live"
echo "  ✓ Standings will refresh automatically"
echo ""
echo "Press Ctrl+C to stop monitoring (components will keep running)"
echo ""

# Monitor logs
trap 'echo ""; echo "Monitoring stopped. Components still running."; exit 0' INT

tail -f logs/league.log
