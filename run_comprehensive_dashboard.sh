#!/bin/bash

##############################################################################
# Comprehensive Dashboard Quick Start Script
##############################################################################
#
# This script launches the comprehensive real-time dashboard that shows:
#  - Each player's strategy
#  - Every player's move in every match
#  - Round progress (current, total, played, remaining)
#  - Live standings
#  - Match history
#  - Winner celebration
#
# Usage:
#   ./run_comprehensive_dashboard.sh              # Default: 6 players, 15 rounds
#   ./run_comprehensive_dashboard.sh --quick      # Quick: 4 players, 5 rounds
#   ./run_comprehensive_dashboard.sh --players 8  # Custom player count
#
##############################################################################

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "═══════════════════════════════════════════════════════════"
echo "  🎮 MCP GAME LEAGUE - COMPREHENSIVE DASHBOARD"
echo "═══════════════════════════════════════════════════════════"
echo -e "${NC}"

# Check if uv is available (preferred)
if command -v uv &> /dev/null; then
    PYTHON_CMD="uv run python"
    echo -e "${GREEN}✓ Using uv for faster execution${NC}"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    echo -e "${YELLOW}ℹ Using python3${NC}"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    echo -e "${YELLOW}ℹ Using python${NC}"
else
    echo -e "${YELLOW}⚠️  Python not found. Please install Python 3.11+${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}📋 Dashboard Features:${NC}"
echo "  ✓ Player strategies displayed everywhere"
echo "  ✓ Every player's move shown in real-time"
echo "  ✓ Round progress (played/remaining)"
echo "  ✓ Live standings table"
echo "  ✓ Complete match history"
echo "  ✓ Winner celebration"
echo ""

echo -e "${BLUE}🚀 Starting tournament...${NC}"
echo ""

# Run the dashboard
$PYTHON_CMD examples/dashboard/run_enhanced_dashboard.py "$@"

echo ""
echo -e "${GREEN}✅ Dashboard session ended${NC}"

