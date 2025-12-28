#!/usr/bin/env bash
#
# Launch League Manager + Dashboard
# ==================================
#
# Starts the League Manager with real-time dashboard enabled.
# All other components will connect to this central hub.
#
# Usage:
#   ./launch_league.sh [--port PORT] [--no-dashboard]
#

set -e

# Default values
PORT=8000
DASHBOARD="--dashboard"
DEBUG=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --no-dashboard)
            DASHBOARD="--no-dashboard"
            shift
            ;;
        --debug)
            DEBUG="--debug"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--port PORT] [--no-dashboard] [--debug]"
            exit 1
            ;;
    esac
done

echo "========================================"
echo "  MCP Multi-Agent Game League"
echo "  Starting League Manager + Dashboard"
echo "========================================"
echo ""
echo "  League Manager: http://localhost:${PORT}"
if [[ "$DASHBOARD" == "--dashboard" ]]; then
    echo "  Dashboard:      http://localhost:8050"
fi
echo ""
echo "  Press Ctrl+C to stop"
echo "========================================"
echo ""

# Launch using UV
uv run python -m src.cli league --port ${PORT} ${DASHBOARD} ${DEBUG}
