# Local imports
from config.settings import *
from utils.file_helpers import ensure_directories, setup_test_file
from utils.file_watcher import FileWatcher
from diffing.diff_tracker import DiffTracker
from ai.openai_client import OpenAIClient

class ObbyMonitor:
    """Main Obby monitoring class for API integration"""
    
    def __init__(self):
        self.diff_tracker = None
        self.ai_client = None
        self.file_watcher = None
        self.is_running = False
        self.watched_paths = [str(NOTES_FOLDER)]
        
    def start(self):
        """Start the monitoring system"""
        if self.is_running:
            return
            
        # Setup
        ensure_directories(DIFF_PATH, NOTES_FOLDER)
        setup_test_file(NOTES_FOLDER / "test.md")
        
        # Initialize components
        self.diff_tracker = DiffTracker(NOTES_FOLDER / "test.md", DIFF_PATH)
        self.ai_client = OpenAIClient()
        
        # Initialize file watcher
        utils_folder = NOTES_FOLDER.parent / "utils"
        self.file_watcher = FileWatcher(
            NOTES_FOLDER, 
            self.diff_tracker, 
            self.ai_client, 
            LIVING_NOTE_PATH, 
            utils_folder
        )
        
        self.file_watcher.start()
        self.is_running = True
        
    def stop(self):
        """Stop the monitoring system"""
        if self.file_watcher:
            self.file_watcher.stop()
        self.is_running = False

def main():
    print("🔍 Starting Obby - Note Change Tracker")
    print("=" * 40)
    print(f"📝 Watching: {NOTES_FOLDER}")
    print(f"⚡ Detection: Real-time file system events")
    print(f"📄 Diffs: {DIFF_PATH}")
    print(f"🤖 Living Note: {LIVING_NOTE_PATH}")
    print("\n🎯 Ready! Edit any markdown file in the notes folder to see changes...")
    print("Press Ctrl+C to stop\n")
    
    # Setup
    ensure_directories(DIFF_PATH, NOTES_FOLDER)
    setup_test_file(NOTES_FOLDER / "test.md")  # Create a sample file
    
    # Initialize components
    diff_tracker = DiffTracker(NOTES_FOLDER / "test.md", DIFF_PATH)  # Initial dummy file
    ai_client = OpenAIClient()
    
    # Initialize file watcher with the notes folder and utils folder
    utils_folder = NOTES_FOLDER.parent / "utils"  # Assuming utils is in the project root
    file_watcher = FileWatcher(NOTES_FOLDER, diff_tracker, ai_client, LIVING_NOTE_PATH, utils_folder)
    
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