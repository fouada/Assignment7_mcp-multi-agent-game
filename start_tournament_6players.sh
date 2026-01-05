#!/bin/bash
# Complete tournament setup with 6 players and 3 referees for maximum opponent model learning

cd /Users/fouadaz/LearningFromUniversity/Learning/LLMSAndMultiAgentOrchestration/course-materials/assignments/Assignment7_mcp-multi-agent-game

echo "🎮 Starting MCP Game Tournament with 6 Players & 3 Referees"
echo "=========================================================="
echo ""

# Clean up any existing processes
echo "1️⃣ Cleaning up old processes..."
./full_cleanup.sh
sleep 2

echo ""
echo "2️⃣ Starting Dashboard..."
# Check if dashboard is already running
if ! lsof -ti:8050 > /dev/null 2>&1; then
    nohup uv run uvicorn src.visualization.dashboard:app --host 0.0.0.0 --port 8050 > dashboard.log 2>&1 &
    echo "   Dashboard starting at http://localhost:8050"
    sleep 3
else
    echo "   Dashboard already running ✓"
fi

echo ""
echo "3️⃣ Starting League Manager with 5× round-robin (25 rounds total)..."
# Kill existing league manager
if lsof -ti:8000 > /dev/null 2>&1; then
    kill -9 $(lsof -ti:8000) 2>/dev/null
    sleep 1
fi

# Start league manager with 5 repeats for more learning data
# With 6 players: 5 rounds × 5 repeats = 25 total rounds
export TOURNAMENT_REPEAT=5
nohup uv run python -m src.cli league --port 8000 --dashboard > league.log 2>&1 &
echo "   League manager starting (wait 5 seconds)..."
sleep 5

echo ""
echo "4️⃣ Registering 3 Referees..."
# Referee 1
echo "   Registering REF01 (port 8001)..."
uv run python -m src.cli referee --id REF01 --port 8001 --register &
sleep 2

# Referee 2
echo "   Registering REF02 (port 8002)..."
uv run python -m src.cli referee --id REF02 --port 8002 --register &
sleep 2

# Referee 3
echo "   Registering REF03 (port 8003)..."
uv run python -m src.cli referee --id REF03 --port 8003 --register &
sleep 3

echo ""
echo "5️⃣ Registering 6 Players with diverse strategies..."

# Player 1 - Bob: Adaptive Bayesian (LEARNS OPPONENT MODELS!) ⭐
echo "   Registering Bob (adaptive_bayesian) - WILL GENERATE OPPONENT MODEL DATA ⭐"
uv run python -m src.cli player --name Bob --port 8101 --strategy adaptive_bayesian --register &
sleep 2

# Player 2 - Alice: Random
echo "   Registering Alice (random)"
uv run python -m src.cli player --name Alice --port 8102 --strategy random --register &
sleep 2

# Player 3 - Charlie: Regret Matching (GENERATES COUNTERFACTUAL DATA!) ⭐
echo "   Registering Charlie (regret_matching) - WILL GENERATE COUNTERFACTUAL DATA ⭐"
uv run python -m src.cli player --name Charlie --port 8103 --strategy regret_matching --register &
sleep 2

# Player 4 - Dave: Nash Equilibrium
echo "   Registering Dave (nash_equilibrium)"
uv run python -m src.cli player --name Dave --port 8104 --strategy nash_equilibrium --register &
sleep 2

# Player 5 - Emma: Adaptive Bayesian (MORE OPPONENT MODEL DATA!)
echo "   Registering Emma (adaptive_bayesian) - WILL ALSO GENERATE OPPONENT MODEL DATA ⭐"
uv run python -m src.cli player --name Emma --port 8105 --strategy adaptive_bayesian --register &
sleep 2

# Player 6 - Frank: Mixed Strategy
echo "   Registering Frank (mixed)"
uv run python -m src.cli player --name Frank --port 8106 --strategy mixed --register &
sleep 3

echo ""
echo "=========================================================="
echo "✅ Setup Complete!"
echo "=========================================================="
echo ""
echo "📊 Tournament Configuration:"
echo "   • Players: 6 (Bob & Emma will learn opponent models)"
echo "   • Referees: 3 (matches run in parallel)"
echo "   • Total Rounds: 25 (5 × 5 repeats)"
echo "   • Each player faces every opponent 5 times"
echo ""
echo "🌐 Dashboard: http://localhost:8050"
echo ""
echo "📋 Next Steps:"
echo "   1. Open dashboard in browser"
echo "   2. Click '🚀 Start Tournament'"
echo "   3. Click '▶️ Run Round' 25 times (or use the button repeatedly)"
echo "   4. Watch the Opponent Model Confidence chart populate!"
echo ""
echo "💡 Expected Charts:"
echo "   • Opponent Model: Bob will show 5 opponent bars"
echo "   • Opponent Model: Emma will show 5 opponent bars"
echo "   • Counterfactual: Charlie's regret analysis"
echo "   • Strategy Performance: All 6 strategies compared"
echo ""
echo "⏱️  Tip: Run rounds faster by clicking 'Run Round' rapidly"
echo "    (3 referees = up to 3 matches in parallel!)"
echo ""

