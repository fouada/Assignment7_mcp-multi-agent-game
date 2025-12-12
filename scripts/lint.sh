#!/bin/bash
# Lint and format code for MCP Multi-Agent Game League
# Usage: ./scripts/lint.sh [OPTIONS]
#
# Options:
#   --fix          Auto-fix issues
#   --format       Format code only
#   --check        Check only (no changes)
#   --help         Show this help message

set -e

# Default values
FIX=""
FORMAT_ONLY=""
CHECK_ONLY=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            FIX="--fix"
            shift
            ;;
        --format)
            FORMAT_ONLY="true"
            shift
            ;;
        --check)
            CHECK_ONLY="true"
            shift
            ;;
        --help)
            echo "Usage: ./scripts/lint.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --fix          Auto-fix issues"
            echo "  --format       Format code only"
            echo "  --check        Check only (no changes)"
            echo "  --help         Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "🔍 MCP Multi-Agent Game League - Code Quality"
echo "=============================================="
echo ""

# Check if UV is available
if command -v uv &> /dev/null; then
    CMD="uv run"
else
    CMD=""
fi

if [ -n "$FORMAT_ONLY" ]; then
    echo "📝 Formatting code..."
    $CMD ruff format src/ tests/
    echo "✅ Formatting complete!"
    exit 0
fi

if [ -n "$CHECK_ONLY" ]; then
    echo "🔍 Checking code (no changes)..."
    echo ""
    echo "Ruff check:"
    $CMD ruff check src/ tests/
    echo ""
    echo "Ruff format check:"
    $CMD ruff format --check src/ tests/
    echo ""
    echo "MyPy type check:"
    $CMD mypy src/ || true
    echo ""
    echo "✅ Check complete!"
    exit 0
fi

echo "🔍 Running Ruff linter..."
$CMD ruff check src/ tests/ $FIX

echo ""
echo "📝 Running Ruff formatter..."
$CMD ruff format src/ tests/

echo ""
echo "🔍 Running MyPy type checker..."
$CMD mypy src/ || echo "⚠️  Type errors found (non-blocking)"

echo ""
echo "✅ Lint complete!"

