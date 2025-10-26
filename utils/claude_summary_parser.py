"""
Parser utilities for Claude-generated summaries.

Extracts structured data from Claude's markdown-formatted summaries
according to the CLAUDE_OUTPUT_FORMAT.md specification.
"""

import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ClaudeSummaryParser:
    """Parse Claude's structured summary format into usable data."""

    @staticmethod
    def parse_session_summary(summary_text: str) -> Dict:
        """
        Parse a session summary from Claude into structured data.

        Args:
            summary_text: Full markdown summary from Claude

        Returns:
            Dict with extracted fields:
                - title: Session title (str)
                - summary: Summary text (str)
                - change_pattern: Pattern description (str)
                - impact_scope: Scope value (str)
                - impact_complexity: Complexity value (str)
                - impact_risk: Risk level (str)
                - topics: List of topic strings (List[str])
                - keywords: List of keyword strings (List[str])
                - relationships: Relationship description (str | None)
                - sources: List of dicts with 'path' and 'rationale' (List[Dict])
                - questions: List of question strings (List[str])
                - raw_text: Original summary text (str)
        """
        result = {
            'title': '',
            'summary': '',
            'change_pattern': '',
            'impact_scope': 'moderate',
            'impact_complexity': 'moderate',
            'impact_risk': 'low',
            'topics': [],
            'keywords': [],
            'relationships': None,
            'sources': [],
            'questions': [],
            'raw_text': summary_text
        }

        try:
            # Extract session title (first ## heading)
            title_match = re.search(r'^##\s+(.+)$', summary_text, re.MULTILINE)
            if title_match:
                result['title'] = title_match.group(1).strip()

            # Extract summary field
            summary_match = re.search(
                r'\*\*Summary\*\*:\s*(.+?)(?=\n\n|\*\*|$)',
                summary_text,
                re.DOTALL
            )
            if summary_match:
                result['summary'] = summary_match.group(1).strip()

            # Extract change pattern
            pattern_match = re.search(
                r'\*\*Change Pattern\*\*:\s*(.+?)(?=\n\n|\*\*|$)',
                summary_text,
                re.DOTALL
            )
            if pattern_match:
                result['change_pattern'] = pattern_match.group(1).strip()

            # Extract impact assessment fields
            scope_match = re.search(r'-\s+\*\*Scope\*\*:\s*(\w+)', summary_text)
            if scope_match:
                result['impact_scope'] = scope_match.group(1).lower()

            complexity_match = re.search(r'-\s+\*\*Complexity\*\*:\s*(\w+)', summary_text)
            if complexity_match:
                result['impact_complexity'] = complexity_match.group(1).lower()

            risk_match = re.search(r'-\s+\*\*Risk Level\*\*:\s*(\w+)', summary_text)
            if risk_match:
                result['impact_risk'] = risk_match.group(1).lower()

            # Extract topics (comma-separated)
            topics_match = re.search(
                r'\*\*Topics\*\*:\s*(.+?)(?=\n\n|\*\*|$)',
                summary_text,
                re.DOTALL
            )
            if topics_match:
                topics_text = topics_match.group(1).strip()
                result['topics'] = [t.strip() for t in topics_text.split(',') if t.strip()]

            # Extract keywords (comma-separated)
            keywords_match = re.search(
                r'\*\*Technical Keywords\*\*:\s*(.+?)(?=\n\n|\*\*|$)',
                summary_text,
                re.DOTALL
            )
            if keywords_match:
                keywords_text = keywords_match.group(1).strip()
                result['keywords'] = [k.strip() for k in keywords_text.split(',') if k.strip()]

            # Extract relationships (optional)
            relationships_match = re.search(
                r'\*\*Relationships\*\*:\s*(.+?)(?=\n\n|###|$)',
                summary_text,
                re.DOTALL
            )
            if relationships_match:
                result['relationships'] = relationships_match.group(1).strip()

            # Extract sources section
            sources_section_match = re.search(
                r'###\s+Sources\s*\n((?:-.+\n?)+)',
                summary_text,
                re.MULTILINE
            )
            if sources_section_match:
                sources_text = sources_section_match.group(1)
                # Parse individual source entries
                source_pattern = r'-\s+`([^`]+)`\s+—\s+(.+)'
                for match in re.finditer(source_pattern, sources_text):
                    result['sources'].append({
                        'path': match.group(1).strip(),
                        'rationale': match.group(2).strip()
                    })

            # Extract proposed questions
            questions_section_match = re.search(
                r'###\s+Proposed Questions\s*\n((?:-.+\n?)+)',
                summary_text,
                re.MULTILINE
            )
            if questions_section_match:
                questions_text = questions_section_match.group(1)
                # Parse question bullets
                question_pattern = r'-\s+(.+)'
                for match in re.finditer(question_pattern, questions_text):
                    question = match.group(1).strip()
                    if question:  # Only add non-empty questions
                        result['questions'].append(question)

        except Exception as e:
            logger.error(f"Error parsing Claude summary: {e}", exc_info=True)

        return result

    @staticmethod
    def parse_file_change_summary(summary_text: str) -> Dict:
        """
        Parse a file change summary from Claude.

        Args:
            summary_text: Markdown summary for single file change

        Returns:
            Dict with extracted fields:
                - file: File path (str)
                - change_type: Type of change (str)
                - summary: Summary text (str)
                - topics: List of topics (List[str])
                - keywords: List of keywords (List[str])
                - impact: Impact level (str)
                - related_files: List of related file paths (List[str])
                - raw_text: Original text (str)
        """
        result = {
            'file': '',
            'change_type': '',
            'summary': '',
            'topics': [],
            'keywords': [],
            'impact': 'brief',
            'related_files': [],
            'raw_text': summary_text
        }

        try:
            # Extract file path
            file_match = re.search(r'\*\*File\*\*:\s*`([^`]+)`', summary_text)
            if file_match:
                result['file'] = file_match.group(1).strip()

            # Extract change type
            type_match = re.search(r'\*\*Change Type\*\*:\s*(\w+)', summary_text)
            if type_match:
                result['change_type'] = type_match.group(1).strip()

            # Extract summary
            summary_match = re.search(
                r'\*\*Summary\*\*:\s*(.+?)(?=\n\n|\*\*|$)',
                summary_text,
                re.DOTALL
            )
            if summary_match:
                result['summary'] = summary_match.group(1).strip()

            # Extract topics
            topics_match = re.search(r'\*\*Topics\*\*:\s*(.+?)(?=\n\n|\*\*|$)', summary_text, re.DOTALL)
            if topics_match:
                result['topics'] = [t.strip() for t in topics_match.group(1).split(',') if t.strip()]

            # Extract keywords
            keywords_match = re.search(r'\*\*Keywords\*\*:\s*(.+?)(?=\n\n|\*\*|$)', summary_text, re.DOTALL)
            if keywords_match:
                result['keywords'] = [k.strip() for k in keywords_match.group(1).split(',') if k.strip()]

            # Extract impact
            impact_match = re.search(r'\*\*Impact\*\*:\s*(\w+)', summary_text)
            if impact_match:
                result['impact'] = impact_match.group(1).strip().lower()

            # Extract related files
            related_match = re.search(r'\*\*Related Files\*\*:\s*(.+?)(?=\n\n|\*\*|$)', summary_text, re.DOTALL)
            if related_match:
                related_text = related_match.group(1).strip()
                # Split by commas and clean up
                result['related_files'] = [f.strip().strip('`') for f in related_text.split(',') if f.strip()]

        except Exception as e:
            logger.error(f"Error parsing file change summary: {e}", exc_info=True)

        return result

    @staticmethod
    def extract_semantic_metadata(parsed_summary: Dict) -> Dict:
        """
        Convert parsed summary into semantic metadata for database storage.

        Args:
            parsed_summary: Output from parse_session_summary()

        Returns:
            Dict ready for semantic_entries database table
        """
        return {
            'summary': parsed_summary.get('summary', ''),
            'topics': parsed_summary.get('topics', []),
            'keywords': parsed_summary.get('keywords', []),
            'impact_scope': parsed_summary.get('impact_scope', 'moderate'),
            'impact_complexity': parsed_summary.get('impact_complexity', 'moderate'),
            'impact_risk': parsed_summary.get('impact_risk', 'low'),
            'change_pattern': parsed_summary.get('change_pattern', ''),
            'relationships': parsed_summary.get('relationships'),
        }

    @staticmethod
    def validate_session_summary(summary_text: str) -> tuple[bool, List[str]]:
        """
        Validate that a summary matches the expected format.

        Args:
            summary_text: Summary text to validate

        Returns:
            Tuple of (is_valid, list_of_missing_fields)
        """
        required_markers = [
            ("Title (## heading)", r'^##\s+.+', re.MULTILINE),
            ("**Summary**", r'\*\*Summary\*\*:', 0),
            ("**Change Pattern**", r'\*\*Change Pattern\*\*:', 0),
            ("**Impact Assessment**", r'\*\*Impact Assessment\*\*:', 0),
            ("**Scope**", r'-\s+\*\*Scope\*\*:', 0),
            ("**Complexity**", r'-\s+\*\*Complexity\*\*:', 0),
            ("**Risk Level**", r'-\s+\*\*Risk Level\*\*:', 0),
            ("**Topics**", r'\*\*Topics\*\*:', 0),
            ("**Technical Keywords**", r'\*\*Technical Keywords\*\*:', 0),
            ("### Sources", r'###\s+Sources', 0),
        ]

        missing = []
        for name, pattern, flags in required_markers:
            if not re.search(pattern, summary_text, flags):
                missing.append(name)

        return (len(missing) == 0, missing)
