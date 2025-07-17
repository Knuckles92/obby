"""
OpenAI integration for AI-managed living notes.
This module will handle communication with OpenAI API for summarizing diffs.
"""

import os
from pathlib import Path

class OpenAIClient:
    """Handles OpenAI API calls for diff summarization."""
    
    def __init__(self, api_key=None, model="gpt-4"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
    
    def summarize_diff(self, diff_content):
        """
        Summarize a diff for the living note.
        
        Args:
            diff_content: The diff content to summarize
            
        Returns:
            str: AI-generated summary
        """
        # TODO: Implement OpenAI API call
        # For now, return a placeholder
        return f"[AI Summary Placeholder] Changes detected in diff: {len(diff_content.splitlines())} lines modified"
    
    def update_living_note(self, living_note_path, summary):
        """
        Update the living note with the AI summary.
        
        Args:
            living_note_path: Path to the living note file
            summary: AI-generated summary to append
        """
        living_note_path = Path(living_note_path)
        
        # Create living note if it doesn't exist
        if not living_note_path.exists():
            living_note_path.parent.mkdir(exist_ok=True)
            living_note_path.write_text("# Living Note\n\nThis file contains AI-generated summaries of changes to your notes.\n\n---\n\n")
        
        # Append summary with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(living_note_path, "a") as f:
            f.write(f"## {timestamp}\n\n{summary}\n\n---\n\n")
        
        print(f"    ↪ Living note updated: {living_note_path}")
