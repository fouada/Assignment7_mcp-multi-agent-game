#!/usr/bin/env python3
"""Auto-format Python code to fix common formatting issues."""

import re
from pathlib import Path


def format_file(filepath: Path) -> tuple[int, int]:
    """Format a Python file.
    
    Returns:
        Tuple of (changes_made, total_lines)
    """
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    changes = 0
    
    # Fix common formatting issues
    lines = content.split('\n')
    formatted_lines = []
    
    for i, line in enumerate(lines):
        original_line = line
        
        # Remove trailing whitespace
        line = line.rstrip()
        
        # Ensure proper spacing around operators (basic fixes)
        # This is a simplified formatter - real formatting would use AST
        
        if line != original_line:
            changes += 1
        
        formatted_lines.append(line)
    
    # Join lines back
    formatted_content = '\n'.join(formatted_lines)
    
    # Ensure file ends with newline
    if formatted_content and not formatted_content.endswith('\n'):
        formatted_content += '\n'
        changes += 1
    
    # Write back if changed
    if formatted_content != original_content:
        with open(filepath, 'w') as f:
            f.write(formatted_content)
    
    return changes, len(lines)


def main():
    """Format all Python files."""
    files_to_format = [
        "src/agents/league_manager.py",
        "src/agents/player.py",
        "src/agents/strategies/game_theory.py",
        "src/launcher/component_launcher.py",
        "src/visualization/analytics.py",
        "src/visualization/dashboard.py",
        "src/visualization/integration.py",
        "tests/test_analytics_engine_reset.py",
        "tests/test_coverage_validation.py",
        "tests/test_dashboard_api.py",
        "tests/test_functional_comprehensive.py",
        "tests/test_pattern_strategy.py",
        "tests/test_performance_comprehensive.py",
        "tests/test_random_strategy.py",
    ]
    
    total_changes = 0
    total_lines = 0
    
    for file_path in files_to_format:
        path = Path(file_path)
        if path.exists():
            changes, lines = format_file(path)
            total_changes += changes
            total_lines += lines
            if changes > 0:
                print(f"✓ {file_path}: {changes} changes")
            else:
                print(f"✓ {file_path}: no changes needed")
        else:
            print(f"✗ {file_path}: not found")
    
    print(f"\nTotal: {total_changes} changes across {len(files_to_format)} files ({total_lines} lines)")
    print("\nNote: For full formatting, the CI will use 'ruff format' or 'black'")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

