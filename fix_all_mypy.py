#!/usr/bin/env python3
"""
Comprehensive script to fix remaining MyPy errors systematically.
"""

import re
from pathlib import Path
from typing import Tuple

def fix_any_none_attribute(filepath: Path) -> int:
    """Fix 'Item "None" of "Any | None" has no attribute' errors."""
    content = filepath.read_text()
    original = content
    
    # Add None checks before attribute access
    # Pattern: variable.attribute where variable could be None
    # This is complex, so we'll handle specific cases
    
    changes = 0
    if "base_server.py" in str(filepath):
        # Fix msg_type issues
        content = content.replace(
            'handler_name = f"_handle_{msg_type.lower()}"',
            'handler_name = f"_handle_{msg_type.lower()}" if msg_type else "_handle_unknown"'
        )
        if content != original:
            changes += 1
            
    if content != original:
        filepath.write_text(content)
        return changes
    return 0

def fix_optional_parameters_in_calls(filepath: Path) -> int:
    """Fix calls with None arguments that expect non-None."""
    content = filepath.read_text()
    original = content
    changes = 0
    
    if "mcp_server.py" in str(filepath):
        # Fix create_response call
        content = re.sub(
            r'create_response\(request_id\)',
            'create_response(request_id if request_id is not None else "")',
            content
        )
        if content != original:
            changes += 1
    
    if "base_server.py" in str(filepath):
        # Fix ProtocolError call
        content = re.sub(
            r'raise ProtocolError\(error\)',
            'raise ProtocolError(error or "Protocol error")',
            content
        )
        if content != original:
            changes += 1
    
    if content != original:
        filepath.write_text(content)
        return changes
    return 0

def fix_agent_errors(filepath: Path) -> int:
    """Fix agents module errors."""
    content = filepath.read_text()
    original = content
    changes = 0
    
    if "player.py" in str(filepath) or "referee.py" in str(filepath):
        # Add None checks for Any | None parameters
        lines = content.split('\n')
        new_lines = []
        
        for i, line in enumerate(lines):
            new_lines.append(line)
            
            # Look for function calls with parameters that might be None
            if '_respond_to_invitation' in line and '(' in line:
                # Check if there's validation
                if i > 0 and 'if' not in lines[i-1]:
                    # We might need to add validation
                    pass
        
        # For now, add type assertions where needed
        content = re.sub(
            r'await self\._respond_to_invitation\(([^)]+)\)',
            lambda m: f'await self._respond_to_invitation(str({m.group(1)}) if {m.group(1)} else "")',
            content
        )
        
    if content != original:
        filepath.write_text(content)
        return 1
    return 0

def add_type_ignore_comments(filepath: Path, patterns: list) -> int:
    """Add type: ignore comments for complex cases."""
    content = filepath.read_text()
    original = content
    changes = 0
    
    for pattern, ignore_type in patterns:
        # Add # type: ignore[error-type] to lines matching pattern
        lines = content.split('\n')
        new_lines = []
        
        for line in lines:
            if re.search(pattern, line) and '# type: ignore' not in line:
                # Add type ignore at end of line
                line = line.rstrip() + f'  # type: ignore[{ignore_type}]'
                changes += 1
            new_lines.append(line)
        
        content = '\n'.join(new_lines)
    
    if content != original:
        filepath.write_text(content)
        return changes
    return 0

def main():
    """Main entry point."""
    src_dir = Path("src")
    
    total_fixes = 0
    
    # Fix specific files
    files_to_fix = [
        src_dir / "server" / "base_server.py",
        src_dir / "server" / "mcp_server.py",
        src_dir / "agents" / "player.py",
        src_dir / "agents" / "referee.py",
        src_dir / "middleware" / "builtin.py",
        src_dir / "observability" / "tracing.py",
    ]
    
    for filepath in files_to_fix:
        if filepath.exists():
            print(f"Processing {filepath}...")
            total_fixes += fix_any_none_attribute(filepath)
            total_fixes += fix_optional_parameters_in_calls(filepath)
            total_fixes += fix_agent_errors(filepath)
    
    print(f"\nTotal fixes applied: {total_fixes}")

if __name__ == "__main__":
    main()

