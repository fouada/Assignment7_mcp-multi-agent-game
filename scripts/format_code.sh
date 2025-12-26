#!/bin/bash
#
# Code Formatting Script
# ======================
#
# Formats code using Ruff formatter to match CI/CD requirements
#

set -e

echo "========================================"
echo "Code Formatting with Ruff"
echo "========================================"
echo ""

# Check if ruff is available
if command -v ruff &> /dev/null; then
    echo "✓ Ruff found"
elif python3 -m ruff --version &> /dev/null 2>&1; then
    echo "✓ Ruff found (via python module)"
    alias ruff="python3 -m ruff"
elif uv run ruff --version &> /dev/null 2>&1; then
    echo "✓ Ruff found (via uv)"
    alias ruff="uv run ruff"
else
    echo "❌ Ruff not found. Installing..."
    pip install ruff || uv pip install ruff || {
        echo "Failed to install ruff. Please install manually:"
        echo "  pip install ruff"
        exit 1
    }
fi

echo ""
echo "Formatting files..."
echo ""

# Format all Python files
ruff format src/ tests/

echo ""
echo "✅ Formatting complete!"
echo ""
echo "Files formatted and ready for commit."

