#!/bin/bash
# Setup script for MCP Multi-Agent Game League
# Usage: ./scripts/setup.sh

set -e

echo "🚀 Setting up MCP Multi-Agent Game League"
echo "=========================================="

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo ""
    echo "📦 Installing UV package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Source the shell to get UV in PATH
    export PATH="$HOME/.cargo/bin:$PATH"
    
    echo "✅ UV installed successfully!"
fi

echo ""
echo "📦 UV version: $(uv --version)"

# Create virtual environment and install dependencies
echo ""
echo "📦 Creating virtual environment and installing dependencies..."
uv sync --all-extras

echo ""
echo "✅ Setup complete!"
echo ""
echo "To activate the environment, run:"
echo "  source .venv/bin/activate"
echo ""
echo "Or use UV directly:"
echo "  uv run python -m src.main --help"
echo ""
echo "Quick start:"
echo "  uv run python -m src.main --run --players 4"

