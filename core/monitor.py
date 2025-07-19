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