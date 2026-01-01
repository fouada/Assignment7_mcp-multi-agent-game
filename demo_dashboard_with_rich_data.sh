#!/bin/bash
# Demo Script: Launch Tournament with Rich Visualization Data
# This script sets up a tournament optimized for showcasing MIT-level dashboard features

set -e

echo "🎓 MIT-Level Dashboard Demo Setup"
echo "=================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Cleanup
echo -e "${YELLOW}Step 1: Cleaning up previous components...${NC}"
./cleanup_components.sh
sleep 2

# Step 2: Start League Manager
echo -e "${BLUE}Step 2: Starting League Manager...${NC}"
echo "  📊 Dashboard will be available at: http://localhost:8050"
osascript -e 'tell app "Terminal" to do script "cd '$(pwd)' && uv run python -m src.cli league --port 8000"'
sleep 3

# Step 3: Start Referee
echo -e "${BLUE}Step 3: Starting Referee...${NC}"
osascript -e 'tell app "Terminal" to do script "cd '$(pwd)' && uv run python -m src.cli referee --id ref1 --port 8001 --register"'
sleep 3

# Step 4: Start Players with DIVERSE strategies for rich visualizations
echo -e "${BLUE}Step 4: Starting Players with Advanced Strategies...${NC}"

echo -e "${GREEN}  🤖 Alice - Adaptive Bayesian (Opponent Modeling)${NC}"
osascript -e 'tell app "Terminal" to do script "cd '$(pwd)' && ./launch_player.sh --name Alice --port 8101 --strategy adaptive_bayesian"'
sleep 1.5

echo -e "${GREEN}  🎯 Bob - Regret Matching (CFR/Counterfactual)${NC}"
osascript -e 'tell app "Terminal" to do script "cd '$(pwd)' && ./launch_player.sh --name Bob --port 8102 --strategy regret_matching"'
sleep 1.5

echo -e "${GREEN}  ⚖️  Charlie - Nash Equilibrium${NC}"
osascript -e 'tell app "Terminal" to do script "cd '$(pwd)' && ./launch_player.sh --name Charlie --port 8103 --strategy nash"'
sleep 1.5

echo -e "${GREEN}  🎲 Dave - Random Baseline${NC}"
osascript -e 'tell app "Terminal" to do script "cd '$(pwd)' && ./launch_player.sh --name Dave --port 8104 --strategy random"'
sleep 2

# Step 5: Wait for all components to be ready
echo -e "${YELLOW}Step 5: Waiting for all components to initialize...${NC}"
sleep 5

# Step 6: Start the league
echo -e "${BLUE}Step 6: Starting the league...${NC}"
uv run python -m src.main --start-league
sleep 3

# Step 7: Run multiple rounds for rich data
echo -e "${BLUE}Step 7: Running tournament rounds for rich visualization data...${NC}"
echo ""

for i in {1..5}; do
    echo -e "${GREEN}  Round $i/5...${NC}"
    uv run python -m src.main --run-round
    sleep 2
done

echo ""
echo -e "${GREEN}✅ Tournament Setup Complete!${NC}"
echo ""
echo "=================================="
echo "🎓 MIT-Level Dashboard is LIVE!"
echo "=================================="
echo ""
echo "📊 Dashboard URL: http://localhost:8050"
echo ""
echo "🎯 What to Explore:"
echo "  1. Tournament Overview - See live standings"
echo "  2. Strategy Learning Evolution:"
echo "     - Bayesian Beliefs (Alice's opponent models)"
echo "     - Regret Analysis (Bob's CFR learning)"
echo "  3. Tournament Flow & Standings:"
echo "     - Matchup Matrix (Head-to-head records)"
echo "     - Standings Race (Animated rankings)"
echo "  4. Tournament Replay (Time-travel debugging)"
echo ""
echo "🔄 Continue Tournament:"
echo "  Run: uv run python -m src.main --run-round"
echo ""
echo "🎬 To run more rounds automatically:"
for i in {6..10}; do
    echo "  Round $i..."
done
echo ""

