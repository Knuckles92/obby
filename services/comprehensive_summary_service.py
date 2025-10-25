"""
Comprehensive Summary Service
==============================

Service layer for comprehensive summary generation using Claude Agent SDK.
Encapsulates business logic for aggregating file changes and generating
AI-powered summaries of development activity.
"""

import logging
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class ComprehensiveSummaryService:
    """
    Service for generating comprehensive summaries of file changes.

    Uses Claude Agent SDK for advanced AI summarization with tool-calling
    and reasoning capabilities.
    """

    def __init__(self):
        """Initialize the service (lazy-loads AI client)."""
        self._claude_client = None

    @property
    def claude_client(self):
        """Lazy-load Claude Agent client."""
        if self._claude_client is None:
            try:
                from ai.claude_agent_client import ClaudeAgentClient
                self._claude_client = ClaudeAgentClient(working_dir=Path.cwd())
                logger.info("Claude Agent client initialized for comprehensive summaries")
            except Exception as e:
                logger.error(f"Failed to initialize Claude Agent client: {e}")
                raise
        return self._claude_client

    def is_available(self) -> bool:
        """Check if Claude Agent is available and configured."""
        try:
            return self.claude_client.is_available()
        except Exception:
            return False

    @staticmethod
    def fingerprint_combined(files_count: int, total_changes: int, combined_diff: str) -> str:
        """
        Create fingerprint hash of comprehensive summary inputs.

        Used for deduplication - if fingerprint matches last run, skip AI call.

        Args:
            files_count: Number of files with changes
            total_changes: Total number of changes
            combined_diff: Combined diff content

        Returns:
            SHA256 hex digest of inputs
        """
        try:
            h = hashlib.sha256()
            h.update(str(files_count).encode('utf-8'))
            h.update(str(total_changes).encode('utf-8'))
            h.update((combined_diff or '').encode('utf-8'))
            return h.hexdigest()
        except Exception:
            return ''

    @staticmethod
    def prepare_combined_diff(changes_by_file: Dict, max_len: int = 4000) -> str:
        """
        Prepare a combined diff string with length cap.

        Aggregates all changes across files into a single diff string,
        truncating if necessary to avoid API limits.

        Args:
            changes_by_file: Dict mapping file paths to lists of changes
            max_len: Maximum length of combined diff

        Returns:
            Combined diff string
        """
        diff_parts = []

        for file_path, file_changes in changes_by_file.items():
            diff_parts.append(f"\n=== Changes in {file_path} ===")

            for change in file_changes:
                if change.get('diff_content'):
                    timestamp = change.get('timestamp', 'unknown')
                    diff_parts.append(f"--- Change at {timestamp} ---")
                    diff_parts.append(change['diff_content'])

            diff_parts.append("")  # Add spacing between files

        combined = "\n".join(diff_parts)

        # Truncate if too long to avoid API limits
        if len(combined) > max_len:
            return combined[:max_len] + "\n... (truncated for API limits)"

        return combined

    @staticmethod
    def calculate_time_span(start_time: datetime, end_time: datetime) -> str:
        """
        Calculate human-readable time span between two timestamps.

        Args:
            start_time: Start timestamp
            end_time: End timestamp

        Returns:
            Human-readable time span (e.g., "2 days", "3 hours")
        """
        span = end_time - start_time

        if span.days > 0:
            return f"{span.days} day{'s' if span.days != 1 else ''}"
        elif span.seconds >= 3600:
            hours = span.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''}"
        elif span.seconds >= 60:
            minutes = span.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        else:
            return f"{span.seconds} second{'s' if span.seconds != 1 else ''}"

    @staticmethod
    def prepare_file_summaries(changes_by_file: Dict) -> List[Dict]:
        """
        Prepare individual file summary data.

        Args:
            changes_by_file: Dict mapping file paths to lists of changes

        Returns:
            List of dicts with file summary info
        """
        file_summaries = []

        for file_path, file_changes in changes_by_file.items():
            changes_count = len(file_changes)
            lines_added = sum(c.get('lines_added', 0) for c in file_changes)
            lines_removed = sum(c.get('lines_removed', 0) for c in file_changes)

            highlights: List[str] = []
            for change in file_changes:
                diff_content = change.get('diff_content')
                if not diff_content:
                    continue

                for line in diff_content.splitlines():
                    line = line.strip()
                    if not line or line.startswith('+++') or line.startswith('---'):
                        continue
                    if line.startswith('+'):
                        cleaned = line[1:].strip()
                        if cleaned:
                            highlights.append(cleaned)
                    if len(highlights) >= 3:
                        break
                if len(highlights) >= 3:
                    break

            highlights_text = '; '.join(highlights[:3]) if highlights else ''

            summary = f"{changes_count} change{'s' if changes_count != 1 else ''}"
            if lines_added > 0 or lines_removed > 0:
                summary += f" (+{lines_added}/-{lines_removed} lines)"

            file_summaries.append({
                'file_path': file_path,
                'summary': summary,
                'changes_count': changes_count,
                'lines_added': lines_added,
                'lines_removed': lines_removed,
                'highlights': highlights_text
            })

        return file_summaries

    @staticmethod
    def parse_ai_summary(ai_summary: str) -> Dict:
        """
        Parse structured AI summary response into components.

        Extracts topics, keywords, impact level, and main summary text
        from Claude's response.

        Args:
            ai_summary: Raw AI response text

        Returns:
            Dict with parsed components: summary, topics, keywords, impact
        """
        parsed = {
            'summary': ai_summary,
            'topics': [],
            'keywords': [],
            'impact': 'moderate'
        }

        # Try to extract structured sections
        lines = ai_summary.split('\n')

        for line in lines:
            line = line.strip()

            # Extract topics
            if line.startswith('**Key Topics**:') or line.startswith('**Topics**:'):
                topics_text = line.replace('**Key Topics**:', '').replace('**Topics**:', '').strip()
                parsed['topics'] = [t.strip() for t in topics_text.split(',') if t.strip()]

            # Extract keywords
            elif line.startswith('**Key Keywords**:') or line.startswith('**Keywords**:'):
                keywords_text = line.replace('**Key Keywords**:', '').replace('**Keywords**:', '').strip()
                parsed['keywords'] = [k.strip() for k in keywords_text.split(',') if k.strip()]

            # Extract impact
            elif line.startswith('**Overall Impact**:') or line.startswith('**Impact**:'):
                impact_text = line.replace('**Overall Impact**:', '').replace('**Impact**:', '').strip().lower()
                if impact_text in ['brief', 'moderate', 'significant']:
                    parsed['impact'] = impact_text

            # Extract main summary
            elif line.startswith('**Batch Summary**:') or line.startswith('**Summary**:'):
                parsed['summary'] = line.replace('**Batch Summary**:', '').replace('**Summary**:', '').strip()

        return parsed

    async def generate_comprehensive_summary(
        self,
        changes_by_file: Dict,
        time_range_start: datetime,
        time_range_end: datetime,
        settings: Optional[Dict] = None
    ) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Generate comprehensive summary using Claude Agent SDK.

        Args:
            changes_by_file: Dict mapping file paths to lists of changes
            time_range_start: Start of time range for summary
            time_range_end: End of time range for summary
            settings: Optional settings dict (e.g., {'summaryLength': 'brief'})

        Returns:
            Tuple of (success, summary_data, error_message)
            summary_data contains: summary, topics, keywords, impact
        """
        try:
            if not self.is_available():
                return False, None, "Claude Agent SDK not available"

            # Prepare batch data
            combined_diff = self.prepare_combined_diff(changes_by_file, max_len=4000)
            file_summaries = self.prepare_file_summaries(changes_by_file)
            time_span = self.calculate_time_span(time_range_start, time_range_end)

            # Determine summary length
            summary_length = settings.get('summaryLength', 'brief') if settings else 'brief'

            logger.info(f"Generating comprehensive summary via Claude Agent for {len(changes_by_file)} files")

            # Call Claude Agent using specialized method
            response = await self.claude_client.generate_comprehensive_summary(
                changes_context=combined_diff,
                file_summaries=file_summaries,
                time_span=time_span,
                summary_length=summary_length
            )

            if not response or "Error" in response[:50]:  # Check first 50 chars for errors
                return False, None, response or "Unknown error from Claude Agent"

            # Parse response
            summary_data = self.parse_ai_summary(response)

            logger.info(f"Comprehensive summary generated: {len(summary_data['topics'])} topics, {len(summary_data['keywords'])} keywords")

            return True, summary_data, None

        except Exception as e:
            logger.error(f"Failed to generate comprehensive summary: {e}", exc_info=True)
            return False, None, str(e)


# Singleton instance for easy access
_service_instance = None

def get_comprehensive_summary_service() -> ComprehensiveSummaryService:
    """Get the global comprehensive summary service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = ComprehensiveSummaryService()
    return _service_instance
