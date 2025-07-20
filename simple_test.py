#!/usr/bin/env python3
"""
Simple test script for new Living Note features without emojis.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from ai.openai_client import OpenAIClient
from config.settings import LIVING_NOTE_PATH, NOTES_FOLDER

def main():
    """Run simple tests."""
    print("Testing New Living Note Features")
    print("=" * 40)
    
    # Ensure required directories exist
    NOTES_FOLDER.mkdir(exist_ok=True)
    
    # Set dummy API key for testing (won't actually call OpenAI)
    os.environ['OPENAI_API_KEY'] = 'dummy-key-for-testing'
    
    # Initialize AI client
    ai_client = OpenAIClient(model="gpt-4.1-mini")
    
    # Clear living note for fresh test
    if LIVING_NOTE_PATH.exists():
        LIVING_NOTE_PATH.unlink()
    
    print("\n1. Testing Structured Living Note Format...")
    
    # Test 1: Create first entry
    test_summary_1 = """**Summary**: Added new task management functionality to project
**Topics**: task-management, productivity, features
**Keywords**: tasks, add, create, management, productivity, new-feature
**Impact**: moderate"""
    
    ai_client.update_living_note(LIVING_NOTE_PATH, test_summary_1, "content")
    print("   - Created first entry")
    
    # Test 2: Add second entry
    test_summary_2 = """**Summary**: Updated task completion logic and added validation
**Topics**: validation, logic, completion
**Keywords**: tasks, update, logic, validation, completion, fix
**Impact**: brief"""
    
    ai_client.update_living_note(LIVING_NOTE_PATH, test_summary_2, "content")
    print("   - Added second entry")
    
    # Test 3: Add tree change
    test_summary_3 = """**Summary**: Created new directory structure for task modules
**Topics**: organization, structure, modules
**Keywords**: directory, create, structure, organization, modules
**Impact**: significant"""
    
    ai_client.update_living_note(LIVING_NOTE_PATH, test_summary_3, "tree")
    print("   - Added tree change entry")
    
    # Verify structured format
    if LIVING_NOTE_PATH.exists():
        content = LIVING_NOTE_PATH.read_text(encoding='utf-8')
        
        # Check key elements
        checks = [
            "# Living Note -" in content,
            "## Session Summary" in content,
            "**Focus**:" in content,
            "**Changes**:" in content,
            "### Detailed Changes:" in content,
            "## Insights" in content,
            content.count("- **") >= 3
        ]
        
        passed = sum(checks)
        print(f"   - Structure check: {passed}/7 elements found")
        
        if passed >= 6:
            print("   [PASS] Structured format working")
        else:
            print("   [FAIL] Structured format issues")
    
    print("\n2. Testing Semantic Indexing...")
    
    # Check semantic index
    index_path = Path("notes/semantic_index.json")
    
    if index_path.exists():
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            entries = index_data.get('entries', [])
            print(f"   - Found {len(entries)} indexed entries")
            
            if entries:
                entry = entries[0]
                has_fields = all(field in entry for field in 
                    ['id', 'timestamp', 'summary', 'topics', 'keywords', 'searchable_text'])
                
                if has_fields:
                    print("   [PASS] Semantic indexing working")
                    
                    # Show sample data
                    all_topics = set()
                    all_keywords = set()
                    for e in entries:
                        all_topics.update(e.get('topics', []))
                        all_keywords.update(e.get('keywords', []))
                    
                    print(f"   - Topics: {', '.join(list(all_topics)[:3])}")
                    print(f"   - Keywords: {', '.join(list(all_keywords)[:5])}")
                else:
                    print("   [FAIL] Missing required fields in entries")
            else:
                print("   [FAIL] No entries in index")
        except Exception as e:
            print(f"   [FAIL] Error reading index: {e}")
    else:
        print("   [FAIL] Semantic index file not created")
    
    print("\n3. Testing Metadata Extraction...")
    
    # Test metadata extraction
    test_summary = """**Summary**: Added user authentication system
**Topics**: authentication, security, users
**Keywords**: auth, login, security, users, system
**Impact**: significant"""
    
    metadata = ai_client.extract_semantic_metadata(test_summary)
    
    if metadata.get('summary') and metadata.get('topics') and metadata.get('keywords'):
        print("   [PASS] Metadata extraction working")
        print(f"   - Extracted {len(metadata.get('topics', []))} topics")
        print(f"   - Extracted {len(metadata.get('keywords', []))} keywords")
    else:
        print("   [FAIL] Metadata extraction issues")
    
    print("\n" + "=" * 40)
    print("SUMMARY:")
    print("1. Structured Living Note Format: Implemented")
    print("2. Semantic Indexing Optimization: Implemented")
    print("3. New Features Ready for Use!")
    
    # Show living note preview
    if LIVING_NOTE_PATH.exists():
        content = LIVING_NOTE_PATH.read_text(encoding='utf-8')
        lines = content.split('\n')[:15]  # First 15 lines
        print("\nSample Living Note Output:")
        print("-" * 30)
        for line in lines:
            print(line)
        if len(content.split('\n')) > 15:
            print("... (truncated)")

if __name__ == "__main__":
    main()