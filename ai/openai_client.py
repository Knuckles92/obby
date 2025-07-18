"""
OpenAI integration for AI-managed living notes.
This module will handle communication with OpenAI API for summarizing diffs.
"""

import os
from pathlib import Path
from openai import OpenAI

class OpenAIClient:
    """Handles OpenAI API calls for diff summarization."""
    
    def __init__(self, api_key=None, model="gpt-4"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.client = OpenAI(api_key=self.api_key)
    
    def summarize_diff(self, diff_content):
        """
        Summarize a diff for the living note.
        
        Args:
            diff_content: The diff content to summarize
            
        Returns:
            str: AI-generated summary
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI assistant for Obby, a comprehensive note monitoring system that tracks both file content changes and file tree structure changes. When summarizing diffs, provide a concise, human-readable summary focusing on what was changed, added, or removed at a high level. Consider the context that this is part of a living note system that also monitors file creation, deletion, and movement events."
                    },
                    {
                        "role": "user",
                        "content": f"Please summarize the following diff:\n\n{diff_content}"
                    }
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Error generating AI summary: {str(e)}"
    
    def summarize_tree_change(self, tree_change_description):
        """
        Summarize a file tree change for the living note.
        
        Args:
            tree_change_description: Description of the tree change (creation, deletion, move)
            
        Returns:
            str: AI-generated summary
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI assistant for Obby, a comprehensive note monitoring system that tracks both file content changes and file tree structure changes. When summarizing file tree changes (creation, deletion, or movement of files/directories), provide a concise, human-readable summary focusing on the organizational impact and what it means for the project structure. Consider that this works alongside content change monitoring to provide a complete picture of how the knowledge base is evolving."
                    },
                    {
                        "role": "user",
                        "content": f"Please summarize the following file tree change:\n\n{tree_change_description}"
                    }
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Error generating tree change summary: {str(e)}"
    
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
        
        print(f"    Living note updated: {living_note_path}")
