#!/usr/bin/env python3
"""
Investigation script to examine +0/-0 diff entries in the actual database.

This script connects to the database and analyzes existing content_diffs
entries to understand why some have +0/-0 results.
"""

import sqlite3
import os
from pathlib import Path
import difflib
from typing import List, Dict, Any


def get_database_path() -> str:
    """Get the database path."""
    return "obby.db"


def analyze_zero_zero_diffs() -> List[Dict[str, Any]]:
    """Find and analyze all +0/-0 diff entries in the database."""
    db_path = get_database_path()
    
    if not Path(db_path).exists():
        print(f"Database not found at: {db_path}")
        return []
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Find all +0/-0 diffs
    query = """
        SELECT cd.*, 
               fv_old.content as old_content, fv_old.content_hash as old_hash,
               fv_new.content as new_content, fv_new.content_hash as new_hash
        FROM content_diffs cd
        LEFT JOIN file_versions fv_old ON cd.old_version_id = fv_old.id
        LEFT JOIN file_versions fv_new ON cd.new_version_id = fv_new.id
        WHERE cd.lines_added = 0 AND cd.lines_removed = 0
        ORDER BY cd.timestamp DESC
        LIMIT 20
    """
    
    cursor = conn.execute(query)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return results


def regenerate_diff(old_content: str, new_content: str) -> tuple:
    """Regenerate diff using the same logic as ContentDiffModel."""
    old_lines = old_content.splitlines(keepends=True) if old_content else []
    new_lines = new_content.splitlines(keepends=True) if new_content else []
    
    # Generate unified diff
    diff_lines = list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile='old', tofile='new',
        lineterm=''
    ))
    diff_content = '\n'.join(diff_lines)
    
    # Count added/removed lines
    lines_added = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
    lines_removed = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
    
    return diff_content, lines_added, lines_removed


def get_database_stats() -> Dict[str, Any]:
    """Get statistics about the database content."""
    db_path = get_database_path()
    
    if not Path(db_path).exists():
        return {}
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    stats = {}
    
    # Total diffs
    result = conn.execute("SELECT COUNT(*) as count FROM content_diffs").fetchone()
    stats['total_diffs'] = result['count']
    
    # Zero-zero diffs
    result = conn.execute(
        "SELECT COUNT(*) as count FROM content_diffs WHERE lines_added = 0 AND lines_removed = 0"
    ).fetchone()
    stats['zero_zero_diffs'] = result['count']
    
    # Change types
    change_types = conn.execute(
        "SELECT change_type, COUNT(*) as count FROM content_diffs GROUP BY change_type"
    ).fetchall()
    stats['change_types'] = {row['change_type']: row['count'] for row in change_types}
    
    # Recent activity
    recent = conn.execute(
        "SELECT DATE(timestamp) as date, COUNT(*) as count FROM content_diffs "
        "WHERE timestamp > datetime('now', '-7 days') GROUP BY DATE(timestamp) ORDER BY date"
    ).fetchall()
    stats['recent_activity'] = {row['date']: row['count'] for row in recent}
    
    conn.close()
    return stats


def main():
    """Run the database investigation."""
    print("DATABASE DIFF INVESTIGATION")
    print("="*60)
    
    # Get database stats
    print("\n1. DATABASE STATISTICS")
    print("-" * 30)
    stats = get_database_stats()
    
    if not stats:
        print("No database found. Run the application first to generate data.")
        return
    
    print(f"Total content_diffs entries: {stats['total_diffs']}")
    print(f"Zero-zero diffs (+0/-0): {stats['zero_zero_diffs']}")
    
    if stats['total_diffs'] > 0:
        percentage = (stats['zero_zero_diffs'] / stats['total_diffs']) * 100
        print(f"Percentage of zero-zero diffs: {percentage:.1f}%")
    
    print("\nChange types:")
    for change_type, count in stats.get('change_types', {}).items():
        print(f"  {change_type}: {count}")
    
    print("\nRecent activity (last 7 days):")
    for date, count in stats.get('recent_activity', {}).items():
        print(f"  {date}: {count} diffs")
    
    # Analyze zero-zero diffs
    print("\n2. ZERO-ZERO DIFF ANALYSIS")
    print("-" * 40)
    
    zero_diffs = analyze_zero_zero_diffs()
    
    if not zero_diffs:
        print("No +0/-0 diff entries found in database.")
        return
    
    print(f"Found {len(zero_diffs)} recent +0/-0 diff entries")
    
    # Analyze each zero-zero diff
    for i, diff_entry in enumerate(zero_diffs):
        print(f"\n--- ANALYSIS {i+1} ---")
        print(f"File: {diff_entry['file_path']}")
        print(f"Change type: {diff_entry['change_type']}")
        print(f"Timestamp: {diff_entry['timestamp']}")
        print(f"Old version ID: {diff_entry['old_version_id']}")
        print(f"New version ID: {diff_entry['new_version_id']}")
        
        old_content = diff_entry['old_content'] or ""
        new_content = diff_entry['new_content'] or ""
        
        print(f"Old content hash: {diff_entry['old_hash']}")
        print(f"New content hash: {diff_entry['new_hash']}")
        print(f"Content hashes match: {diff_entry['old_hash'] == diff_entry['new_hash']}")
        
        print(f"Old content length: {len(old_content)}")
        print(f"New content length: {len(new_content)}")
        print(f"Contents are identical: {old_content == new_content}")
        
        # Regenerate diff to verify
        regenerated_diff, reg_added, reg_removed = regenerate_diff(old_content, new_content)
        stored_diff = diff_entry['diff_content'] or ""
        
        print(f"Stored diff length: {len(stored_diff)}")
        print(f"Regenerated +{reg_added}/-{reg_removed}")
        print(f"Regenerated diff length: {len(regenerated_diff)}")
        
        if regenerated_diff != stored_diff:
            print("WARNING: Regenerated diff differs from stored diff!")
        
        # Show content samples for analysis
        if old_content or new_content:
            print(f"Old content sample: {repr(old_content[:100])}")
            print(f"New content sample: {repr(new_content[:100])}")
        else:
            print("Both contents are empty")
        
        if i >= 4:  # Limit detailed output
            print(f"\n... and {len(zero_diffs) - 5} more entries")
            break
    
    # Summary conclusions
    print("\n3. CONCLUSIONS")
    print("-" * 20)
    
    if zero_diffs:
        identical_count = sum(1 for d in zero_diffs 
                            if (d['old_content'] or "") == (d['new_content'] or ""))
        same_hash_count = sum(1 for d in zero_diffs 
                            if d['old_hash'] == d['new_hash'])
        
        print(f"Entries with identical content: {identical_count}/{len(zero_diffs)}")
        print(f"Entries with same content hash: {same_hash_count}/{len(zero_diffs)}")
        
        if identical_count == len(zero_diffs):
            print("\nAll +0/-0 entries have identical old/new content.")
            print("This suggests:")
            print("- File system events triggered without actual content changes")
            print("- Duplicate processing of the same content")
            print("- Timestamp-only file updates")
            print("- Race conditions in file monitoring")
        else:
            print(f"\n{len(zero_diffs) - identical_count} entries have different content but +0/-0 diff!")
            print("This could indicate a bug in diff generation logic.")


if __name__ == "__main__":
    main()