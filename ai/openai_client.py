"""
OpenAI integration for AI-managed living notes.
This module will handle communication with OpenAI API for summarizing diffs.
"""

import os
import logging
from pathlib import Path
from openai import OpenAI

class OpenAIClient:
    """Handles OpenAI API calls for diff summarization."""
    
    # Latest OpenAI models as of July 2025
    MODELS = {
        'gpt-4o': 'gpt-4o',           # Latest GPT-4 model with improved capabilities
        'gpt-4.1': 'gpt-4.1',         # GPT-4.1 model
        'gpt-4.1-mini': 'gpt-4.1-mini',  # GPT-4.1 mini model
        'o4-mini': 'o4-mini',         # O4 mini model
        'gpt-4.1-nano': 'gpt-4.1-nano'  # GPT-4.1 nano model
    }
    
    def __init__(self, api_key=None, model="gpt-4.1-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.client = OpenAI(api_key=self.api_key)
        
        # Validate model selection
        if model not in self.MODELS.values():
            logging.warning(f"Model '{model}' not in latest models list. Available models: {list(self.MODELS.keys())}")
    
    def summarize_diff(self, diff_content, settings=None):
        """
        Summarize a diff for the living note with semantic indexing optimization.
        
        Args:
            diff_content: The diff content to summarize
            settings: Optional living note settings for customization
            
        Returns:
            str: AI-generated summary with semantic metadata
        """
        try:
            # Load settings if not provided
            if settings is None:
                settings = self._load_living_note_settings()
            
            # Build customized system prompt based on settings
            system_prompt = self._build_system_prompt(settings, "diff")
            
            # Adjust max_tokens based on summary length setting
            max_tokens_map = {
                'brief': 300,
                'moderate': 600,
                'detailed': 1000
            }
            max_tokens = max_tokens_map.get(settings.get('summaryLength', 'moderate'), 600)
            
            # Add focus areas to the user prompt if specified
            user_content = f"Please summarize the following diff with semantic metadata:\n\n{diff_content}"
            if settings.get('focusAreas'):
                focus_areas_text = ", ".join(settings['focusAreas'])
                user_content += f"\n\nPay special attention to these focus areas: {focus_areas_text}"
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_content
                    }
                ],
                max_tokens=max_tokens,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Error generating AI summary: {str(e)}"
    
    def _load_living_note_settings(self):
        """Load living note settings from config file."""
        import json
        
        settings_file = Path('config/living_note_settings.json')
        if settings_file.exists():
            try:
                with open(settings_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"Failed to load living note settings: {e}")
        
        # Return default settings
        return {
            'updateFrequency': 'realtime',
            'summaryLength': 'moderate', 
            'writingStyle': 'technical',
            'includeMetrics': True,
            'autoUpdate': True,
            'maxSections': 10,
            'focusAreas': []
        }
    
    def _build_system_prompt(self, settings, content_type="diff"):
        """Build a customized system prompt based on user settings."""
        writing_style = settings.get('writingStyle', 'technical')
        summary_length = settings.get('summaryLength', 'moderate')
        include_metrics = settings.get('includeMetrics', True)
        
        # Base prompt
        base_prompt = "You are an AI assistant for Obby, a comprehensive note monitoring system."
        
        # Style-specific instructions
        style_instructions = {
            'technical': "Use precise technical language and include technical details.",
            'casual': "Use conversational tone and explain concepts in accessible terms.",
            'formal': "Use professional, formal language suitable for documentation.",
            'bullet-points': "Structure your response using clear bullet points and concise statements."
        }
        
        # Length-specific instructions
        length_instructions = {
            'brief': "Keep summaries concise and focus on the most important changes only.",
            'moderate': "Provide balanced summaries with good detail without being verbose.",
            'detailed': "Include comprehensive details and provide thorough analysis of changes."
        }
        
        # Content-type specific format
        if content_type == "diff":
            format_instruction = """
Format your response as:
**Summary**: [Description of what changed]
**Topics**: [Key technical topics, comma-separated]
**Keywords**: [Specific technical terms, function names, concepts, comma-separated]
**Impact**: [brief/moderate/significant - assess the scope of changes]
"""
        else:
            format_instruction = """
Format your response with clear structure and semantic metadata for search optimization.
"""
        
        # Build complete prompt
        prompt_parts = [
            base_prompt,
            style_instructions.get(writing_style, style_instructions['technical']),
            length_instructions.get(summary_length, length_instructions['moderate'])
        ]
        
        if include_metrics:
            prompt_parts.append("Include relevant metrics and quantitative information where applicable.")
        
        prompt_parts.append(format_instruction)
        prompt_parts.append("Focus on what was changed, added, or removed. Make keywords specific and searchable.")
        
        return " ".join(prompt_parts)
    
    def summarize_tree_change(self, tree_change_description):
        """
        Summarize a file tree change for the living note with semantic metadata.
        
        Args:
            tree_change_description: Description of the tree change (creation, deletion, move)
            
        Returns:
            str: AI-generated summary with semantic metadata
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an AI assistant for Obby, a comprehensive note monitoring system. When summarizing file tree changes, provide a structured summary optimized for search and discovery.

Format your response as:
**Summary**: [Concise human-readable summary of the file/directory change]
**Topics**: [2-3 relevant topic keywords like "organization", "structure", "cleanup"]
**Keywords**: [3-5 searchable keywords related to the file operation]
**Impact**: [brief/moderate/significant - assess organizational impact]

Focus on the organizational impact and what it means for project structure."""
                    },
                    {
                        "role": "user",
                        "content": f"Please summarize the following file tree change with semantic metadata:\n\n{tree_change_description}"
                    }
                ],
                max_tokens=400,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Error generating tree change summary: {str(e)}"
    
    def update_living_note(self, living_note_path, summary, change_type="content"):
        """
        Update the living note with the AI summary using structured format.
        
        Args:
            living_note_path: Path to the living note file
            summary: AI-generated summary to add
            change_type: Type of change ("content" or "tree")
        """
        living_note_path = Path(living_note_path)
        
        # Create living note if it doesn't exist
        if not living_note_path.exists():
            living_note_path.parent.mkdir(exist_ok=True)
            from datetime import datetime
            today = datetime.now().strftime("%Y-%m-%d")
            initial_content = f"# Living Note - {today}\n\nThis file contains AI-generated summaries of your development sessions.\n\n---\n\n"
            living_note_path.write_text(initial_content, encoding='utf-8')
        
        from datetime import datetime
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%I:%M %p")
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # Read existing content
        existing_content = ""
        if living_note_path.exists() and living_note_path.stat().st_size > 0:
            existing_content = living_note_path.read_text(encoding='utf-8')
        
        # Check if we need to start a new session or add to existing one
        lines = existing_content.split('\n')
        today_header = f"# Living Note - {date_str}"
        
        # Find if today's session already exists
        session_exists = False
        session_start_line = -1
        for i, line in enumerate(lines):
            if line.strip() == today_header:
                session_exists = True
                session_start_line = i
                break
        
        if session_exists:
            # Add to existing session's detailed changes
            self._add_to_existing_session(living_note_path, summary, change_type, lines, session_start_line)
        else:
            # Create new session
            self._create_new_session(living_note_path, summary, change_type, date_str, time_str, existing_content)
        
        # Extract semantic metadata and create searchable index entry
        try:
            metadata = self.extract_semantic_metadata(summary)
            # Use the current file path if available, otherwise fall back to notes folder
            file_path_for_index = getattr(self, '_current_file_path', str(living_note_path.parent))
            searchable_entry = self.create_searchable_entry(
                metadata, 
                timestamp, 
                change_type,
                file_path=file_path_for_index
            )
            self.save_semantic_index(searchable_entry)
            # Clear the temporary file path
            if hasattr(self, '_current_file_path'):
                delattr(self, '_current_file_path')
        except Exception as e:
            logging.warning(f"Failed to create semantic index entry: {e}")
        
        logging.info(f"Living note updated with structured format and semantic indexing: {living_note_path}")

    def _create_new_session(self, living_note_path, summary, change_type, date_str, time_str, existing_content):
        """Create a new session entry in the structured format."""
        from datetime import datetime
        
        # Generate initial insights
        insights = self._generate_session_insights([summary], [change_type], is_new_session=True)
        
        # Create session header
        session_header = f"""# Living Note - {date_str}

## Session Summary ({time_str})
**Focus**: Development Session
**Changes**: 1 change detected
**Key Progress**: 
- {change_type.title()} change: {summary[:100]}{'...' if len(summary) > 100 else ''}

### Detailed Changes:
- **{datetime.now().strftime('%H:%M:%S')}**: {summary}

## Insights
{insights}

---

"""
        
        # Prepend new session to existing content
        updated_content = session_header + existing_content
        
        with open(living_note_path, "w", encoding='utf-8') as f:
            f.write(updated_content)

    def _add_to_existing_session(self, living_note_path, summary, change_type, lines, session_start_line):
        """Add to an existing session in the structured format."""
        from datetime import datetime
        
        # Find the detailed changes section and collect existing summaries
        detailed_changes_line = -1
        insights_line = -1
        existing_summaries = []
        existing_change_types = []
        
        for i in range(session_start_line, len(lines)):
            if lines[i].strip() == "### Detailed Changes:":
                detailed_changes_line = i
            elif lines[i].strip() == "## Insights":
                insights_line = i
                break
            elif detailed_changes_line != -1 and lines[i].strip().startswith("- **"):
                # Extract existing summaries for insight generation
                parts = lines[i].split("**: ", 1)
                if len(parts) > 1:
                    existing_summaries.append(parts[1])
                    # Try to determine change type from summary content
                    existing_change_types.append("content")  # Default to content
        
        if detailed_changes_line != -1:
            # Add new change to detailed changes section
            new_change = f"- **{datetime.now().strftime('%H:%M:%S')}**: {summary}"
            lines.insert(detailed_changes_line + 1, new_change)
            
            # Update the changes count in session summary
            for i in range(session_start_line, detailed_changes_line + 1):
                if "**Changes**:" in lines[i]:
                    # Extract current count and increment
                    parts = lines[i].split("**Changes**: ")
                    if len(parts) > 1:
                        try:
                            current_count = int(parts[1].split()[0])
                            lines[i] = f"**Changes**: {current_count + 1} changes detected"
                        except (ValueError, IndexError):
                            lines[i] = "**Changes**: Multiple changes detected"
                    break
            
            # Update insights with all summaries including the new one
            all_summaries = existing_summaries + [summary]
            all_change_types = existing_change_types + [change_type]
            new_insights = self._generate_session_insights(all_summaries, all_change_types, is_new_session=False)
            
            # Replace insights section
            if insights_line != -1:
                # Find the end of insights section (next ## or --- or end of file)
                insights_end = len(lines)
                for i in range(insights_line + 1, len(lines)):
                    if lines[i].strip().startswith("##") or lines[i].strip() == "---":
                        insights_end = i
                        break
                
                # Replace insights content
                lines[insights_line + 1:insights_end] = [new_insights, ""]
        
        # Write updated content back to file
        with open(living_note_path, "w", encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def _generate_session_insights(self, summaries, change_types, is_new_session=True):
        """Generate intelligent insights based on session patterns and changes."""
        try:
            # Analyze patterns in the summaries
            content_changes = sum(1 for ct in change_types if ct == "content")
            tree_changes = sum(1 for ct in change_types if ct == "tree")
            total_changes = len(summaries)
            
            # Create context for AI insight generation
            changes_text = "\n".join([f"- {summary}" for summary in summaries])
            
            insight_prompt = f"""Analyze this development session with {total_changes} changes ({content_changes} content, {tree_changes} file structure):

{changes_text}

Generate 2-3 concise insights about:
1. Development patterns or workflow
2. Project progress or focus areas
3. Potential next steps or recommendations

Format as bullet points starting with '-'. Be specific and actionable."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI assistant that analyzes development sessions for patterns and insights. Provide concise, actionable insights about the developer's workflow and progress."
                    },
                    {
                        "role": "user",
                        "content": insight_prompt
                    }
                ],
                max_tokens=300,
                temperature=0.4
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logging.debug(f"AI insight generation failed: {e}")
            # Fallback insights if AI generation fails
            if is_new_session:
                return "- Active development session in progress\n- Monitoring file changes and updates"
            else:
                return f"- Development session with {len(summaries)} changes\n- Mix of content and structural modifications\n- Iterative development pattern observed"

    def extract_semantic_metadata(self, summary_text):
        """
        Extract semantic metadata from AI-generated summaries for indexing.
        
        Args:
            summary_text: The formatted AI summary with semantic metadata
            
        Returns:
            dict: Extracted metadata with topics, keywords, and impact level
        """
        metadata = {
            'summary': '',
            'topics': [],
            'keywords': [],
            'impact': 'brief'
        }
        
        try:
            lines = summary_text.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('**Summary**:'):
                    metadata['summary'] = line.replace('**Summary**:', '').strip()
                elif line.startswith('**Topics**:'):
                    topics_text = line.replace('**Topics**:', '').strip()
                    metadata['topics'] = [t.strip() for t in topics_text.split(',') if t.strip()]
                elif line.startswith('**Keywords**:'):
                    keywords_text = line.replace('**Keywords**:', '').strip()
                    metadata['keywords'] = [k.strip() for k in keywords_text.split(',') if k.strip()]
                elif line.startswith('**Impact**:'):
                    metadata['impact'] = line.replace('**Impact**:', '').strip().lower()
            
            # If no structured metadata found, treat entire text as summary
            if not metadata['summary'] and not metadata['topics']:
                metadata['summary'] = summary_text
                
        except Exception as e:
            logging.warning(f"Error extracting semantic metadata: {e}")
            metadata['summary'] = summary_text
            
        return metadata

    def create_searchable_entry(self, metadata, timestamp, change_type, file_path=None):
        """
        Create a searchable entry combining metadata for future search indexing.
        
        Args:
            metadata: Extracted semantic metadata dictionary
            timestamp: When the change occurred
            change_type: Type of change (content/tree)
            file_path: Path of the changed file (optional)
            
        Returns:
            dict: Searchable entry structure
        """
        from datetime import datetime
        
        searchable_entry = {
            'id': f"{timestamp}_{change_type}",
            'timestamp': timestamp,
            'date': datetime.fromisoformat(timestamp.replace(' ', 'T')).date().isoformat(),
            'time': datetime.fromisoformat(timestamp.replace(' ', 'T')).time().isoformat(),
            'type': change_type,
            'summary': metadata.get('summary', ''),
            'topics': metadata.get('topics', []),
            'keywords': metadata.get('keywords', []),
            'impact': metadata.get('impact', 'brief'),
            'file_path': file_path,
            'searchable_text': self._create_searchable_text(metadata)
        }
        
        return searchable_entry

    def _create_searchable_text(self, metadata):
        """Create a comprehensive searchable text field combining all metadata."""
        components = [
            metadata.get('summary', ''),
            ' '.join(metadata.get('topics', [])),
            ' '.join(metadata.get('keywords', [])),
            metadata.get('impact', '')
        ]
        return ' '.join([comp for comp in components if comp]).lower()

    def save_semantic_index(self, searchable_entry, index_path="notes/semantic_index.json"):
        """
        Save semantic index entry to a JSON file for future search capabilities.
        
        Args:
            searchable_entry: The searchable entry dictionary
            index_path: Path to the semantic index file
        """
        import json
        from pathlib import Path
        
        index_file = Path(index_path)
        
        try:
            # Load existing index or create new one
            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
            else:
                index_data = {'entries': [], 'metadata': {'created': searchable_entry['timestamp'], 'version': '1.0'}}
                # Ensure parent directory exists
                index_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Add new entry
            index_data['entries'].append(searchable_entry)
            index_data['metadata']['last_updated'] = searchable_entry['timestamp']
            index_data['metadata']['total_entries'] = len(index_data['entries'])
            
            # Keep only last 1000 entries to prevent file from growing too large
            if len(index_data['entries']) > 1000:
                index_data['entries'] = index_data['entries'][-1000:]
                index_data['metadata']['total_entries'] = 1000
            
            # Save updated index
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2, ensure_ascii=False)
                
            logging.debug(f"Semantic index updated: {index_path}")
            
        except Exception as e:
            logging.error(f"Error saving semantic index: {e}")
