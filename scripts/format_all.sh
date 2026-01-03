#!/bin/bash
# Format all Python files with ruff
# Run this before committing to ensure code is properly formatted

echo "================================================"
echo "  Formatting Python Code with Ruff"
echo "================================================"
echo ""

# Check if ruff is available
if ! command -v ruff &> /dev/null; then
    echo "⚠️  Ruff is not installed"
    echo ""
    echo "Install ruff using one of:"
    echo "  pip install ruff"
    echo "  uv pip install ruff"
    echo "  brew install ruff"
    echo ""
    exit 1
fi

echo "Running ruff format..."
echo ""

# Format all Python files
ruff format src/ tests/

echo ""
echo "✅ Formatting complete!"
echo ""
echo "Files formatted:"
echo "  • src/ (all Python files)"
echo "  • tests/ (all Python files)"
echo ""
echo "================================================"

