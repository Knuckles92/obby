import time

# Local imports
from config.settings import *
from utils.file_helpers import ensure_directories, setup_test_file
from diffing.diff_tracker import DiffTracker
from ai.openai_client import OpenAIClient

def main():
    print("🔍 Starting Obby - Note Change Tracker")
    print("=" * 40)
    print(f"📝 Watching: {NOTE_PATH}")
    print(f"⏰ Check interval: {CHECK_INTERVAL} seconds")
    print(f"📁 Snapshots: {SNAPSHOT_PATH}")
    print(f"📄 Diffs: {DIFF_PATH}")
    print(f"🤖 Living Note: {LIVING_NOTE_PATH}")
    print("\n🎯 Ready! Edit the note file to see changes...")
    print("Press Ctrl+C to stop\n")
    
    # Setup
    ensure_directories(SNAPSHOT_PATH, DIFF_PATH, NOTE_PATH.parent)
    setup_test_file(NOTE_PATH)
    
    # Initialize components
    diff_tracker = DiffTracker(NOTE_PATH, SNAPSHOT_PATH, DIFF_PATH)
    ai_client = OpenAIClient()
    
    try:
        while True:
            changed, diff_content = diff_tracker.check_for_changes()
            
            if changed:
                # Generate AI summary and update living note
                summary = ai_client.summarize_diff(diff_content)
                ai_client.update_living_note(LIVING_NOTE_PATH, summary)
            else:
                print("[✓] No change.")
            
            time.sleep(CHECK_INTERVAL)
    
    except KeyboardInterrupt:
        print("\n\n👋 Stopping Obby. Thanks for using it!")

if __name__ == "__main__":
    main()