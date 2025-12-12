#!/bin/bash
# Run the MCP Multi-Agent Game League
# Usage: ./scripts/run_league.sh [OPTIONS]
#
# Options:
#   --players N    Number of players (default: 4)
#   --debug        Enable debug logging
#   --help         Show this help message

set -e

# Default values
PLAYERS=4
DEBUG=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --players)
            PLAYERS="$2"
            shift 2
            ;;
        --debug)
            DEBUG="--debug"
            export LOG_LEVEL=DEBUG
            shift
            ;;
        --help)
            echo "Usage: ./scripts/run_league.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --players N    Number of players (default: 4)"
            echo "  --debug        Enable debug logging"
            echo "  --help         Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "🎮 MCP Multi-Agent Game League"
echo "==============================="
echo ""
echo "Configuration:"
echo "  Players: $PLAYERS"
echo "  Debug: ${DEBUG:-disabled}"
echo ""

# Check if UV is available
if command -v uv &> /dev/null; then
    echo "📦 Using UV package manager"
    CMD="uv run python"
else
    echo "📦 Using system Python"
    CMD="python"
fi

echo ""
echo "🚀 Starting League..."
echo ""

# Run the league
$CMD -m src.main --run --players "$PLAYERS" $DEBUG
