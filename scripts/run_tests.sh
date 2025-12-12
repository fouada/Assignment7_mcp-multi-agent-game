#!/bin/bash
# Run tests for MCP Multi-Agent Game League
# Usage: ./scripts/run_tests.sh [OPTIONS]
#
# Options:
#   --coverage     Run with coverage report
#   --verbose      Verbose output
#   --file FILE    Run specific test file
#   --help         Show this help message

set -e

# Default values
COVERAGE=""
VERBOSE="-v"
FILE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage)
            COVERAGE="--cov=src --cov-report=term-missing --cov-report=html"
            shift
            ;;
        --verbose)
            VERBOSE="-vv"
            shift
            ;;
        --file)
            FILE="$2"
            shift 2
            ;;
        --help)
            echo "Usage: ./scripts/run_tests.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --coverage     Run with coverage report"
            echo "  --verbose      Verbose output"
            echo "  --file FILE    Run specific test file"
            echo "  --help         Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "🧪 MCP Multi-Agent Game League - Test Suite"
echo "============================================"
echo ""

# Check if UV is available
if command -v uv &> /dev/null; then
    echo "📦 Using UV package manager"
    CMD="uv run pytest"
else
    echo "📦 Using system pytest"
    CMD="pytest"
fi

# Build test command
if [ -n "$FILE" ]; then
    TEST_PATH="$FILE"
else
    TEST_PATH="tests/"
fi

echo ""
echo "🚀 Running tests..."
echo ""

# Run tests
$CMD $TEST_PATH $VERBOSE $COVERAGE

echo ""
echo "✅ Tests completed!"

# If coverage was run, show where to find the report
if [ -n "$COVERAGE" ]; then
    echo ""
    echo "📊 Coverage report generated:"
    echo "   - Terminal: above"
    echo "   - HTML: htmlcov/index.html"
fi
