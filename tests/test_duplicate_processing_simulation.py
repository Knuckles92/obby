#!/usr/bin/env python3
"""
Test script to simulate the duplicate processing issue causing +0/-0 diffs.

This script demonstrates how the current file monitoring logic can create
duplicate content_diffs entries when:
1. File system events trigger multiple times for the same content
2. Same version IDs are used for both old and new content
3. Content hashes are identical but diff entry is still created
"""

import difflib
from datetime import datetime
from typing import Tuple, Dict, Any


def generate_diff(old_content: str, new_content: str) -> Tuple[str, int, int]:
    """Generate diff using ContentDiffModel logic."""
    old_lines = old_content.splitlines(keepends=True) if old_content else []
    new_lines = new_content.splitlines(keepends=True) if new_content else []
    
    diff_lines = list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile='old', tofile='new',
        lineterm=''
    ))
    diff_content = '\n'.join(diff_lines)
    
    lines_added = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
    lines_removed = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
    
    return diff_content, lines_added, lines_removed


def simulate_content_diff_creation(file_path: str, old_version_id: int, new_version_id: int, 
                                 old_content: str, new_content: str, change_type: str = 'modified') -> Dict[str, Any]:
    """Simulate creating a content_diffs entry."""
    diff_content, lines_added, lines_removed = generate_diff(old_content, new_content)
    
    return {
        'file_path': file_path,
        'old_version_id': old_version_id,
        'new_version_id': new_version_id,
        'change_type': change_type,
        'diff_content': diff_content,
        'lines_added': lines_added,
        'lines_removed': lines_removed,
        'timestamp': datetime.now(),
        'old_content': old_content,
        'new_content': new_content,
        'content_identical': old_content == new_content,
        'same_version_id': old_version_id == new_version_id
    }


def main():
    """Demonstrate the duplicate processing issue."""
    print("DUPLICATE PROCESSING SIMULATION")
    print("="*60)
    print("This simulates how +0/-0 diffs are created in the database.")
    
    # Test content
    file_content = "# Test File\n\nThis is test content.\nNo changes here."
    file_path = "test_file.md"
    
    print(f"\nFile: {file_path}")
    print(f"Content: {repr(file_content)}")
    
    # Scenario 1: Proper content change (should not be +0/-0)
    print(f"\n{'='*60}")
    print("SCENARIO 1: Actual content change (EXPECTED)")
    print(f"{'='*60}")
    
    old_content = "# Test File\n\nOld content."
    new_content = "# Test File\n\nNew content."
    
    diff_entry = simulate_content_diff_creation(
        file_path, old_version_id=1, new_version_id=2, 
        old_content=old_content, new_content=new_content
    )
    
    print(f"Old version ID: {diff_entry['old_version_id']}")
    print(f"New version ID: {diff_entry['new_version_id']}")
    print(f"Same version ID: {diff_entry['same_version_id']}")
    print(f"Content identical: {diff_entry['content_identical']}")
    print(f"Result: +{diff_entry['lines_added']}/-{diff_entry['lines_removed']}")
    print(f"Diff content: {repr(diff_entry['diff_content'][:100])}")
    
    # Scenario 2: Duplicate processing (BUG - causes +0/-0)
    print(f"\n{'='*60}")
    print("SCENARIO 2: Duplicate processing (BUG REPRODUCTION)")
    print(f"{'='*60}")
    
    # This simulates what happens in the database:
    # 1. File content hasn't actually changed
    # 2. Same version ID is used for both old and new
    # 3. File system event still triggers diff creation
    
    same_content = file_content
    
    diff_entry = simulate_content_diff_creation(
        file_path, old_version_id=5, new_version_id=5,  # SAME VERSION ID!
        old_content=same_content, new_content=same_content
    )
    
    print(f"Old version ID: {diff_entry['old_version_id']}")
    print(f"New version ID: {diff_entry['new_version_id']}")
    print(f"Same version ID: {diff_entry['same_version_id']} <-- BUG INDICATOR")
    print(f"Content identical: {diff_entry['content_identical']} <-- BUG INDICATOR")
    print(f"Result: +{diff_entry['lines_added']}/-{diff_entry['lines_removed']} <-- PROBLEMATIC")
    print(f"Diff content: '{diff_entry['diff_content']}' (empty)")
    
    # Scenario 3: Another duplicate processing case
    print(f"\n{'='*60}")
    print("SCENARIO 3: Content hash collision (ANOTHER BUG PATTERN)")
    print(f"{'='*60}")
    
    # This simulates when content hash is the same but different version IDs exist
    diff_entry = simulate_content_diff_creation(
        file_path, old_version_id=7, new_version_id=8,  # Different IDs
        old_content=same_content, new_content=same_content  # But same content
    )
    
    print(f"Old version ID: {diff_entry['old_version_id']}")
    print(f"New version ID: {diff_entry['new_version_id']}")
    print(f"Same version ID: {diff_entry['same_version_id']}")
    print(f"Content identical: {diff_entry['content_identical']} <-- BUG INDICATOR")
    print(f"Result: +{diff_entry['lines_added']}/-{diff_entry['lines_removed']} <-- STILL PROBLEMATIC")
    print(f"Diff content: '{diff_entry['diff_content']}' (empty)")
    
    # Root cause analysis
    print(f"\n{'='*60}")
    print("ROOT CAUSE ANALYSIS")
    print(f"{'='*60}")
    
    print("The +0/-0 diff entries are caused by:")
    print("1. File system events triggering without actual content changes")
    print("2. Processing logic that creates diffs even when content is identical")
    print("3. Same version IDs being used for old/new content")
    print("4. No pre-check to avoid creating diffs for identical content")
    
    print(f"\nFix recommendations:")
    print("1. Check content hashes before creating diff entries")
    print("2. Skip diff creation if old_version_id == new_version_id")
    print("3. Add validation to prevent identical content diffs")
    print("4. Implement deduplication in the monitoring logic")
    
    # Proposed fix logic
    print(f"\n{'='*60}")
    print("PROPOSED FIX LOGIC")
    print(f"{'='*60}")
    
    def should_create_diff(old_version_id: int, new_version_id: int, 
                          old_content: str, new_content: str) -> bool:
        """Determine if a diff should be created."""
        # Skip if same version ID
        if old_version_id == new_version_id:
            return False
        
        # Skip if content is identical
        if old_content == new_content:
            return False
        
        # Create diff for actual changes
        return True
    
    test_cases = [
        ("Actual change", 1, 2, "old", "new"),
        ("Same version ID", 5, 5, "content", "content"),
        ("Identical content", 7, 8, "same", "same"),
        ("Valid change", 9, 10, "before", "after"),
    ]
    
    print("Testing proposed fix logic:")
    for name, old_id, new_id, old_content, new_content in test_cases:
        should_create = should_create_diff(old_id, new_id, old_content, new_content)
        print(f"  {name}: {should_create}")


if __name__ == "__main__":
    main()