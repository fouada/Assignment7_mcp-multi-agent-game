#!/usr/bin/env python3
"""
Script to fix common MyPy type errors systematically.
"""

import re
from pathlib import Path

def fix_optional_defaults(content: str) -> str:
    """Fix 'None' defaults that should be 'Type | None'."""
    # Pattern: parameter_name: Type = None
    pattern = r'(\w+):\s+([A-Za-z_][\w\[\], ]+)\s*=\s*None'
    
    def replace_fn(match):
        param_name = match.group(1)
        type_hint = match.group(2).strip()
        # Don't modify if already has | None or Optional
        if '| None' in type_hint or 'Optional' in type_hint or 'None' in type_hint:
            return match.group(0)
        return f'{param_name}: {type_hint} | None = None'
    
    return re.sub(pattern, replace_fn, content)

def fix_callable_lowercase(content: str) -> str:
    """Fix lowercase 'callable' to 'Callable[..., Any]'."""
    # Add imports if needed
    if 'from collections.abc import Callable' not in content and ': callable' in content.lower():
        # Find import section
        import_match = re.search(r'(from typing import.*?\n)', content)
        if import_match:
            content = content.replace(
                import_match.group(1),
                import_match.group(1) + 'from collections.abc import Callable\n'
            )
    
    # Replace callable with Callable[..., Any]
    content = re.sub(r':\s*callable\b', ': Callable[..., Any]', content)
    return content

def add_type_annotations(content: str, filepath: str) -> str:
    """Add missing type annotations for common patterns."""
    
    # Fix: result = {} -> result: dict[str, Any] = {}
    if 'dict[str, Any]' not in content:
        content = re.sub(
            r'\n(\s+)(\w+)\s*=\s*\{\}',
            r'\n\1\2: dict[str, Any] = {}',
            content
        )
    
    # Fix: items = [] -> items: list[Type] = []
    # This is trickier, skip for now
    
    return content

def process_file(filepath: Path) -> bool:
    """Process a single file and return True if changes were made."""
    try:
        content = filepath.read_text()
        original = content
        
        # Apply fixes
        content = fix_optional_defaults(content)
        content = fix_callable_lowercase(content)
        content = add_type_annotations(content, str(filepath))
        
        if content != original:
            filepath.write_text(content)
            print(f"Fixed: {filepath}")
            return True
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def main():
    """Main entry point."""
    src_dir = Path("src")
    
    # Process all Python files
    python_files = list(src_dir.rglob("*.py"))
    
    fixed_count = 0
    for filepath in python_files:
        if process_file(filepath):
            fixed_count += 1
    
    print(f"\nFixed {fixed_count} files")

if __name__ == "__main__":
    main()

