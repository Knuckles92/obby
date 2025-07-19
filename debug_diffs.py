#!/usr/bin/env python3

import os
import sys
from pathlib import Path
from datetime import datetime

print("=== DEBUG DIFFS API ===")
print(f"Current working directory: {os.getcwd()}")
print(f"Script location: {__file__}")
print(f"Script parent: {Path(__file__).parent}")

# Simulate the API logic
diffs_dir = Path(__file__).parent / 'diffs'
print(f"Computed diffs_dir: {diffs_dir}")
print(f"Diffs dir resolved: {diffs_dir.resolve()}")
print(f"Diffs dir exists: {diffs_dir.exists()}")

if diffs_dir.exists():
    # List files
    all_files = list(diffs_dir.iterdir())
    print(f"All files in diffs dir: {[f.name for f in all_files]}")
    
    txt_files = list(diffs_dir.glob('*.txt'))
    print(f"Found {len(txt_files)} .txt files: {[f.name for f in txt_files]}")
    
    # Process files like the API does
    diff_files = []
    sorted_files = sorted(txt_files, key=lambda f: f.stat().st_mtime, reverse=True)[:20]
    
    for diff_file in sorted_files:
        try:
            content = diff_file.read_text(encoding='utf-8')
            file_parts = diff_file.stem.split('.')
            base_name = file_parts[0] if file_parts else diff_file.stem
            
            diff_entry = {
                'id': diff_file.stem,
                'filePath': base_name,
                'timestamp': datetime.fromtimestamp(diff_file.stat().st_mtime).isoformat(),
                'content': content[:100] + '...' if len(content) > 100 else content,
                'size': len(content),
                'fullPath': str(diff_file)
            }
            diff_files.append(diff_entry)
            print(f"Processed: {diff_file.name} -> base_name: {base_name}")
        except Exception as e:
            print(f"Error processing {diff_file}: {e}")
    
    print(f"\nTotal diff entries created: {len(diff_files)}")
    if diff_files:
        print("First entry:")
        print(diff_files[0])
else:
    print("ERROR: Diffs directory does not exist!")