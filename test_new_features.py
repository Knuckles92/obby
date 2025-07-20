#!/usr/bin/env python3
"""
Test script for new Living Note Structure Improvements and Semantic Indexing features.
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from ai.openai_client import OpenAIClient
from config.settings import LIVING_NOTE_PATH, NOTES_FOLDER

def test_structured_living_note():
    """Test the new structured living note format."""
    print("Testing Structured Living Note Format...")
    
    # Initialize AI client
    ai_client = OpenAIClient(model="gpt-4.1-mini")
    
    # Clear living note for fresh test
    if LIVING_NOTE_PATH.exists():
        LIVING_NOTE_PATH.unlink()
    
    # Test 1: Create first entry (new session)
    print("  Creating first entry (new session)...")
    test_summary_1 = """**Summary**: Added new task management functionality to project
**Topics**: task-management, productivity, features
**Keywords**: tasks, add, create, management, productivity, new-feature
**Impact**: moderate"""
    
    ai_client.update_living_note(LIVING_NOTE_PATH, test_summary_1, "content")
    
    # Test 2: Add second entry to existing session
    print("  Adding second entry to existing session...")
    test_summary_2 = """**Summary**: Updated task completion logic and added validation
**Topics**: validation, logic, completion
**Keywords**: tasks, update, logic, validation, completion, fix
**Impact**: brief"""
    
    ai_client.update_living_note(LIVING_NOTE_PATH, test_summary_2, "content")
    
    # Test 3: Add tree change
    print("  Adding tree change entry...")
    test_summary_3 = """**Summary**: Created new directory structure for task modules
**Topics**: organization, structure, modules
**Keywords**: directory, create, structure, organization, modules
**Impact**: significant"""
    
    ai_client.update_living_note(LIVING_NOTE_PATH, test_summary_3, "tree")
    
    # Read and verify the structured format
    if LIVING_NOTE_PATH.exists():
        content = LIVING_NOTE_PATH.read_text(encoding='utf-8')
        print("  [PASS] Living note created with structured format")
        
        # Check for key structural elements
        checks = [
            ("Session header", "# Living Note -" in content),
            ("Session summary", "## Session Summary" in content),
            ("Focus field", "**Focus**:" in content),
            ("Changes field", "**Changes**:" in content),
            ("Key progress", "**Key Progress**:" in content),
            ("Detailed changes", "### Detailed Changes:" in content),
            ("Insights section", "## Insights" in content),
            ("Multiple entries", content.count("- **") >= 3),
        ]
        
        for check_name, check_result in checks:
            status = "[PASS]" if check_result else "[FAIL]"
            print(f"    {status} {check_name}")
        
        return all(check[1] for check in checks)
    else:
        print("  [FAIL] Living note file not created")
        return False

def test_semantic_indexing():
    """Test the semantic indexing functionality."""
    print("\nTesting Semantic Indexing...")
    
    # Check if semantic index was created
    index_path = Path("notes/semantic_index.json")
    
    if not index_path.exists():
        print("  ❌ Semantic index file not created")
        return False
    
    # Load and examine index
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
        
        print("  ✅ Semantic index file exists and is valid JSON")
        
        # Check structure
        checks = [
            ("Has entries", 'entries' in index_data),
            ("Has metadata", 'metadata' in index_data),
            ("Has at least 3 entries", len(index_data.get('entries', [])) >= 3),
        ]
        
        for check_name, check_result in checks:
            status = "✅" if check_result else "❌"
            print(f"    {status} {check_name}")
        
        # Examine entries
        entries = index_data.get('entries', [])
        if entries:
            print(f"  📊 Found {len(entries)} indexed entries")
            
            # Check first entry structure
            first_entry = entries[0]
            entry_checks = [
                ("Has ID", 'id' in first_entry),
                ("Has timestamp", 'timestamp' in first_entry),
                ("Has type", 'type' in first_entry),
                ("Has summary", 'summary' in first_entry),
                ("Has topics", 'topics' in first_entry),
                ("Has keywords", 'keywords' in first_entry),
                ("Has searchable text", 'searchable_text' in first_entry),
            ]
            
            print("    Entry structure:")
            for check_name, check_result in entry_checks:
                status = "✅" if check_result else "❌"
                print(f"      {status} {check_name}")
            
            # Show sample topics and keywords
            all_topics = set()
            all_keywords = set()
            
            for entry in entries:
                all_topics.update(entry.get('topics', []))
                all_keywords.update(entry.get('keywords', []))
            
            print(f"    📋 Sample topics: {', '.join(list(all_topics)[:5])}")
            print(f"    🏷️  Sample keywords: {', '.join(list(all_keywords)[:7])}")
            
            return all(check[1] for check in checks + entry_checks)
        else:
            print("  ❌ No entries found in index")
            return False
            
    except json.JSONDecodeError:
        print("  ❌ Invalid JSON in semantic index")
        return False
    except Exception as e:
        print(f"  ❌ Error reading semantic index: {e}")
        return False

def test_search_functionality():
    """Test the semantic search functionality using the AI client methods."""
    print("\n🔎 Testing Search Functionality...")
    
    ai_client = OpenAIClient()
    
    # Test metadata extraction
    test_summary = """**Summary**: Added new user authentication system
**Topics**: authentication, security, users
**Keywords**: auth, login, security, users, system, new
**Impact**: significant"""
    
    metadata = ai_client.extract_semantic_metadata(test_summary)
    
    print("  📋 Testing metadata extraction:")
    checks = [
        ("Summary extracted", bool(metadata.get('summary'))),
        ("Topics extracted", len(metadata.get('topics', [])) > 0),
        ("Keywords extracted", len(metadata.get('keywords', [])) > 0),
        ("Impact extracted", bool(metadata.get('impact'))),
    ]
    
    for check_name, check_result in checks:
        status = "✅" if check_result else "❌"
        print(f"    {status} {check_name}")
    
    print(f"    🔍 Extracted: {metadata}")
    
    # Test searchable entry creation
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    searchable_entry = ai_client.create_searchable_entry(
        metadata, timestamp, "content", "test_file.md"
    )
    
    print("  📝 Testing searchable entry creation:")
    entry_checks = [
        ("Entry created", bool(searchable_entry)),
        ("Has searchable text", bool(searchable_entry.get('searchable_text'))),
        ("Proper timestamp format", 'T' in searchable_entry.get('date', '')),
    ]
    
    for check_name, check_result in entry_checks:
        status = "✅" if check_result else "❌"
        print(f"    {status} {check_name}")
    
    return all(check[1] for check in checks + entry_checks)

def main():
    """Run all tests."""
    print("🚀 Testing New Living Note Features\n")
    print("=" * 50)
    
    # Ensure required directories exist
    NOTES_FOLDER.mkdir(exist_ok=True)
    
    # Set dummy API key for testing (won't actually call OpenAI)
    os.environ['OPENAI_API_KEY'] = 'dummy-key-for-testing'
    
    results = []
    
    try:
        # Test 1: Structured Living Note Format
        result1 = test_structured_living_note()
        results.append(("Structured Living Note Format", result1))
        
        # Test 2: Semantic Indexing
        result2 = test_semantic_indexing()
        results.append(("Semantic Indexing", result2))
        
        # Test 3: Search Functionality
        result3 = test_search_functionality()
        results.append(("Search Functionality", result3))
        
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        return False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} {test_name}")
        if not result:
            all_passed = False
    
    print(f"\n🎯 Overall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    if all_passed:
        print("\n🎉 Both new featuresets are working correctly!")
        print("   1. ✅ Living Note Structure Improvements implemented")
        print("   2. ✅ Semantic Indexing Optimization implemented")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)