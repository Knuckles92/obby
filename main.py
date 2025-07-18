# Local imports
from config.settings import *
from utils.file_helpers import ensure_directories, setup_test_file
from utils.file_watcher import FileWatcher
from diffing.diff_tracker import DiffTracker
from ai.openai_client import OpenAIClient

def main():
    print("🔍 Starting Obby - Note Change Tracker")
    print("=" * 40)
    print(f"📝 Watching: {NOTES_FOLDER}")
    print(f"⚡ Detection: Real-time file system events")
    print(f"📁 Snapshots: {SNAPSHOT_PATH}")
    print(f"📄 Diffs: {DIFF_PATH}")
    print(f"🤖 Living Note: {LIVING_NOTE_PATH}")
    print("\n🎯 Ready! Edit any markdown file in the notes folder to see changes...")
    print("Press Ctrl+C to stop\n")
    
    # Setup
    ensure_directories(SNAPSHOT_PATH, DIFF_PATH, NOTES_FOLDER)
    setup_test_file(NOTES_FOLDER / "test.md")  # Create a sample file
    
    # Initialize components
    diff_tracker = DiffTracker(NOTES_FOLDER / "test.md", SNAPSHOT_PATH, DIFF_PATH)  # Initial dummy file
    ai_client = OpenAIClient()
    
    # Initialize file watcher with the notes folder
    file_watcher = FileWatcher(NOTES_FOLDER, diff_tracker, ai_client, LIVING_NOTE_PATH)
    
    try:
        # Start watching for file changes
        file_watcher.start()
        
        # Keep the main thread alive
        file_watcher.wait()
        
    except KeyboardInterrupt:
        print("\n\n👋 Stopping Obby. Thanks for using it!")
    finally:
        file_watcher.stop()

if __name__ == "__main__":
    main()