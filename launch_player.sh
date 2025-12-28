#!/usr/bin/env bash
#
# Launch Player Agent
# ===================
#
# Starts a player agent with a specific strategy.
# Multiple players can be started on different ports.
#
# Usage:
#   ./launch_player.sh [--name NAME] [--port PORT] [--strategy STRATEGY] [--no-register]
#
# Strategies:
#   Classic:
#   - random: Uniform random (Nash-like)
#   - pattern: Pattern detection
#   - llm: LLM-powered (requires ANTHROPIC_API_KEY/OPENAI_API_KEY)
#
#   Game Theory:
#   - nash: Nash equilibrium (50/50 parity)
#   - best_response: Exploits opponent bias
#   - adaptive_bayesian: Learns and adapts (RECOMMENDED)
#   - fictitious_play: Classic game theory learning
#   - regret_matching: CFR-inspired regret minimization
#   - ucb: Multi-armed bandit (UCB1)
#   - thompson_sampling: Bayesian bandit sampling
#

set -e

# Default values
PLAYER_NAME="Player_1"
PORT=8101
STRATEGY="random"
REGISTER="--register"
DEBUG=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --name)
            PLAYER_NAME="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --strategy)
            STRATEGY="$2"
            shift 2
            ;;
        --no-register)
            REGISTER=""
            shift
            ;;
        --debug)
            DEBUG="--debug"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--name NAME] [--port PORT] [--strategy STRATEGY] [--no-register] [--debug]"
            echo ""
            echo "Classic Strategies: random, pattern, llm"
            echo "Game Theory Strategies: nash, best_response, adaptive_bayesian, fictitious_play,"
            echo "                        regret_matching, ucb, thompson_sampling"
            exit 1
            ;;
    esac
done

echo "========================================"
echo "  MCP Multi-Agent Game League"
echo "  Starting Player: ${PLAYER_NAME}"
echo "========================================"
echo ""
echo "  Player Name:     ${PLAYER_NAME}"
echo "  Endpoint:        http://localhost:${PORT}"
echo "  Strategy:        ${STRATEGY}"
echo "  League Manager:  http://localhost:8000"
if [[ -n "$REGISTER" ]]; then
    echo "  Auto-register:   Yes"
fi
echo ""
echo "  Press Ctrl+C to stop"
echo "========================================"
echo ""

# Check for LLM API key if using LLM strategy
if [[ "$STRATEGY" == "llm" ]] && [[ -z "$ANTHROPIC_API_KEY" ]] && [[ -z "$OPENAI_API_KEY" ]]; then
    echo "WARNING: LLM strategy requires ANTHROPIC_API_KEY or OPENAI_API_KEY"
    echo "         Set environment variable before running."
    echo ""
fi

# Launch using UV
uv run python -m src.cli player --name ${PLAYER_NAME} --port ${PORT} --strategy ${STRATEGY} ${REGISTER} ${DEBUG}
