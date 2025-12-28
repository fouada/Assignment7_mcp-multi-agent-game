#!/usr/bin/env bash
#
# Launch Referee Agent
# ====================
#
# Starts a referee agent that connects to the league manager.
# Multiple referees can be started on different ports.
#
# Usage:
#   ./launch_referee.sh [--id REF_ID] [--port PORT] [--no-register]
#

set -e

# Default values
REFEREE_ID="REF01"
PORT=8001
REGISTER="--register"
DEBUG=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --id)
            REFEREE_ID="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
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
            echo "Usage: $0 [--id REF_ID] [--port PORT] [--no-register] [--debug]"
            exit 1
            ;;
    esac
done

echo "========================================"
echo "  MCP Multi-Agent Game League"
echo "  Starting Referee: ${REFEREE_ID}"
echo "========================================"
echo ""
echo "  Referee ID:      ${REFEREE_ID}"
echo "  Endpoint:        http://localhost:${PORT}"
echo "  League Manager:  http://localhost:8000"
if [[ -n "$REGISTER" ]]; then
    echo "  Auto-register:   Yes"
fi
echo ""
echo "  Press Ctrl+C to stop"
echo "========================================"
echo ""

# Launch using UV
uv run python -m src.cli referee --id ${REFEREE_ID} --port ${PORT} ${REGISTER} ${DEBUG}
