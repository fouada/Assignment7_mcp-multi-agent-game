#!/usr/bin/env python3
"""Fix common linting issues in Python files."""

import re
import sys
from pathlib import Path


def fix_file(filepath: Path) -> tuple[int, int]:
    """Fix whitespace issues in a file.
    
    Returns:
        Tuple of (lines_fixed, total_lines)
    """
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    fixed_count = 0
    new_lines = []
    
    for line in lines:
        # Remove trailing whitespace
        new_line = line.rstrip() + '\n' if line.endswith('\n') else line.rstrip()
        if new_line != line:
            fixed_count += 1
        new_lines.append(new_line)
    
    # Write back
    with open(filepath, 'w') as f:
        f.writelines(new_lines)
    
    return fixed_count, len(lines)


def main():
    # Files to fix
    files = [
        "tests/test_dashboard_api.py",
        "tests/test_analytics_engine_reset.py",
        "tests/test_performance_comprehensive.py",
        "tests/test_functional_comprehensive.py",
        "tests/test_coverage_validation.py",
    ]
    
    total_fixed = 0
    total_lines = 0
    
    for file_path in files:
        path = Path(file_path)
        if path.exists():
            fixed, lines = fix_file(path)
            total_fixed += fixed
            total_lines += lines
            print(f"✓ {file_path}: fixed {fixed} lines")
        else:
            print(f"✗ {file_path}: not found")
    
    print(f"\nTotal: {total_fixed} lines fixed across {total_lines} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())

