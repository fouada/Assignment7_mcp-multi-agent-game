#!/bin/bash
#
# Install Git Hooks
# =================
#
# This script installs the git hooks from .githooks/ directory
# Usage: ./install-hooks.sh
#

echo "🔧 Installing Git Hooks..."
echo ""

# Get the root directory of the git repository
GIT_ROOT=$(git rev-parse --show-toplevel)
HOOKS_DIR="$GIT_ROOT/.githooks"
GIT_HOOKS_DIR="$GIT_ROOT/.git/hooks"

# Check if we're in a git repository
if [ ! -d "$GIT_ROOT/.git" ]; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

# Check if hooks directory exists
if [ ! -d "$HOOKS_DIR" ]; then
    echo "❌ Error: $HOOKS_DIR directory not found"
    exit 1
fi

# Make hooks executable
echo "Making hooks executable..."
chmod +x "$HOOKS_DIR"/*

# Install hooks
echo "Installing hooks..."
for hook in "$HOOKS_DIR"/*; do
    hook_name=$(basename "$hook")
    
    # Skip this installation script and README
    if [ "$hook_name" = "install-hooks.sh" ] || [ "$hook_name" = "README.md" ]; then
        continue
    fi
    
    target="$GIT_HOOKS_DIR/$hook_name"
    
    # Backup existing hook if it exists
    if [ -f "$target" ] && [ ! -L "$target" ]; then
        echo "  Backing up existing $hook_name to $hook_name.backup"
        mv "$target" "$target.backup"
    fi
    
    # Create symlink
    ln -sf "../../.githooks/$hook_name" "$target"
    echo "  ✓ Installed $hook_name"
done

echo ""
echo "✅ Git hooks installed successfully!"
echo ""
echo "Installed hooks:"
ls -la "$GIT_HOOKS_DIR" | grep -E "pre-commit|pre-push" | awk '{print "  -", $9}'
echo ""
echo "To uninstall, run: rm $GIT_HOOKS_DIR/pre-commit $GIT_HOOKS_DIR/pre-push"
echo "To skip hooks temporarily, use: git commit --no-verify"

