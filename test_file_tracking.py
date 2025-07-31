#!/usr/bin/env python3
"""
Test Script: File-Based Monitoring System
=========================================

Tests the file tracking system without git dependencies to validate
that diff generation, content hashing, and file monitoring work correctly.
"""

import os
import sys
import tempfile
import time
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_file_tracker():
    """Test the file tracking system."""
    print("Testing File-Based Tracking System")
    print("=" * 50)
    
    try:
        # Import our file tracking components
        from core.file_tracker import FileContentTracker
        from database.models import FileVersionModel, ContentDiffModel, FileChangeModel, FileStateModel
        
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir)
            test_file = test_dir / "test_note.md"
            
            print(f"Testing in: {test_dir}")
            
            # Initialize file tracker
            tracker = FileContentTracker([str(test_dir)])
            
            # Test 1: File Creation
            print("\n1. Testing file creation...")
            initial_content = "# Test Note\n\nThis is a test note for validating file tracking."
            test_file.write_text(initial_content)
            
            version_id = tracker.track_file_change(str(test_file), 'created')
            if version_id:
                print(f"PASS File creation tracked: version_id={version_id}")
            else:
                print("FAIL File creation tracking failed")
                return False
            
            # Test 2: File Modification
            print("\n2. Testing file modification...")
            modified_content = initial_content + "\n\n## Update\n\nAdded some new content to test modification tracking."
            test_file.write_text(modified_content)
            
            version_id_2 = tracker.track_file_change(str(test_file), 'modified')
            if version_id_2 and version_id_2 != version_id:
                print(f"PASS File modification tracked: version_id={version_id_2}")
            else:
                print("FAIL File modification tracking failed")
                return False
            
            # Test 3: Diff Generation
            print("\n3. Testing diff generation...")
            history = tracker.get_file_history(str(test_file))
            
            if history and history.get('diffs'):
                diff_content = history['diffs'][0].get('diff_content', '')
                if '+## Update' in diff_content and '+Added some new content' in diff_content:
                    print("PASS Diff generation successful")
                    print(f"   Lines added: {history['diffs'][0].get('lines_added', 0)}")
                    print(f"   Lines removed: {history['diffs'][0].get('lines_removed', 0)}")
                else:
                    print("FAIL Diff content incorrect")
                    return False
            else:
                print("FAIL Diff generation failed")
                return False
            
            # Test 4: Content Hashing
            print("\n4. Testing content hashing...")
            file_state = tracker.get_current_file_state(str(test_file))
            
            if file_state and file_state.get('content_hash'):
                expected_hash = FileStateModel.calculate_content_hash(modified_content)
                if file_state['content_hash'] == expected_hash:
                    print("PASS Content hashing working correctly")
                else:
                    print(f"FAIL Content hash mismatch: {file_state['content_hash'][:8]}... != {expected_hash[:8]}...")
                    return False
            else:
                print("FAIL Content hashing failed")
                return False
            
            # Test 5: Version History
            print("\n5. Testing version history...")
            versions = history.get('versions', [])
            if len(versions) >= 2:
                print(f"PASS Version history maintained: {len(versions)} versions")
                
                first_version = versions[-1]  # Oldest first
                latest_version = versions[0]   # Newest first
                
                print(f"   First version: {first_version['change_description']} ({first_version['line_count']} lines)")
                print(f"   Latest version: {latest_version['change_description']} ({latest_version['line_count']} lines)")
            else:
                print("FAIL Version history incomplete")
                return False
            
            # Test 6: File Deletion
            print("\n6. Testing file deletion...")
            test_file.unlink()  # Delete the file
            
            deletion_id = tracker.track_file_change(str(test_file), 'deleted')
            if deletion_id:
                print(f"PASS File deletion tracked: change_id={deletion_id}")
            else:
                print("FAIL File deletion tracking failed")
                return False
            
            print("\nAll tests passed! File tracking system working correctly.")
            return True
            
    except ImportError as e:
        print(f"Import error: {e}")
        print("   Make sure all dependencies are installed and the database schema is up to date.")
        return False
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_diff_generation():
    """Test diff generation specifically."""
    print("\nTesting Diff Generation")
    print("=" * 30)
    
    try:
        from database.models import ContentDiffModel
        
        # Test diff generation with sample content
        old_content = """# Sample Document

This is the original content.
It has multiple lines.
Some will be changed.
Others will remain.
"""

        new_content = """# Sample Document

This is the modified content.
It has multiple lines.
Some will be changed significantly.
Others will remain.
New line added here.
"""
        
        diff_content, lines_added, lines_removed = ContentDiffModel.generate_diff(old_content, new_content)
        
        print(f"PASS Diff generated successfully")
        print(f"   Lines added: {lines_added}")
        print(f"   Lines removed: {lines_removed}")
        print(f"   Diff preview: {len(diff_content)} characters")
        
        # Verify diff contains expected changes
        if '+modified content' in diff_content and '+significantly' in diff_content and '+New line added' in diff_content:
            print("PASS Diff content verification passed")
            return True
        else:
            print("FAIL Diff content verification failed")
            return False
            
    except Exception as e:
        print(f"FAIL Diff generation test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Starting File-Based Monitoring System Tests")
    print("=" * 60)
    
    # Test basic diff generation first
    diff_test_passed = test_diff_generation()
    
    # Test full file tracking system
    file_tracking_passed = test_file_tracker()
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    print(f"Diff Generation: {'PASSED' if diff_test_passed else 'FAILED'}")
    print(f"File Tracking: {'PASSED' if file_tracking_passed else 'FAILED'}")
    
    if diff_test_passed and file_tracking_passed:
        print("\nAll tests passed! The file-based monitoring system is working correctly.")
        print("Your Obby installation has successfully migrated away from git dependencies.")
        return True
    else:
        print("\nSome tests failed. Please check the error messages above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)