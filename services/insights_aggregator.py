"""
Insights Aggregator Service
==========================

Collects and normalizes signals from various data sources to generate
AI-powered contextual insights using Claude Agent SDK.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class InsightsAggregator:
    """
    Aggregates data from multiple sources to generate insights.
    
    Collects signals from:
    - Semantic summaries (entries, topics, keywords)
    - Recent file/version activity (FileVersionModel, ContentDiffModel, FileChangeModel)
    - Monitoring/comprehensive summaries (ComprehensiveSummaryService)
    - Session summary snapshots (SessionSummaryService)
    - Chat/agent transcripts (if stored)
    - Configuration/watch filters (WatchHandler)
    """
    
    def __init__(self):
        """Initialize the insights aggregator."""
        self.claude_client = None
        self.watch_handler = None
        
    def _initialize_dependencies(self):
        """Lazy initialization of dependencies."""
        try:
            # Initialize Claude Agent client
            if not self.claude_client:
                from ai.claude_agent_client import ClaudeAgentClient
                self.claude_client = ClaudeAgentClient(working_dir=Path.cwd())
                
            # Initialize watch handler for filtering
            if not self.watch_handler:
                from utils.watch_handler import WatchHandler
                self.watch_handler = WatchHandler(Path.cwd())
                
        except Exception as e:
            logger.error(f"Failed to initialize aggregator dependencies: {e}")
            
    def collect_semantic_signals(self, time_range_days: int = 7) -> Dict[str, Any]:
        """Collect semantic analysis signals from database."""
        try:
            from database.models import SemanticModel, db
            
            # Calculate time window
            since = datetime.now() - timedelta(days=time_range_days)
            
            # Get recent semantic entries
            query = """
                SELECT se.*, GROUP_CONCAT(st.topic) as topics,
                       GROUP_CONCAT(sk.keyword) as keywords
                FROM semantic_entries se
                LEFT JOIN semantic_topics st ON se.id = st.entry_id
                LEFT JOIN semantic_keywords sk ON se.id = sk.entry_id
                WHERE se.timestamp >= ? AND se.source_type IN ('session_summary', 'comprehensive')
                GROUP BY se.id
                ORDER BY se.timestamp DESC
                LIMIT 50
            """
            
            rows = db.execute_query(query, (since,))
            semantic_entries = []
            
            for row in rows:
                entry = dict(row)
                # Parse topics and keywords
                entry['topics'] = entry['topics'].split(',') if entry['topics'] else []
                entry['keywords'] = entry['keywords'].split(',') if entry['keywords'] else []
                semantic_entries.append(entry)
            
            # Get topic and keyword frequencies
            topic_counts = {}
            keyword_counts = {}
            
            for entry in semantic_entries:
                for topic in entry['topics']:
                    topic = topic.strip()
                    if topic:
                        topic_counts[topic] = topic_counts.get(topic, 0) + 1
                        
                for keyword in entry['keywords']:
                    keyword = keyword.strip()
                    if keyword:
                        keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
            
            return {
                'entries': semantic_entries,
                'topic_counts': topic_counts,
                'keyword_counts': keyword_counts,
                'total_entries': len(semantic_entries)
            }
            
        except Exception as e:
            logger.error(f"Failed to collect semantic signals: {e}")
            return {'entries': [], 'topic_counts': {}, 'keyword_counts': {}, 'total_entries': 0}
    
    def collect_file_activity_signals(self, time_range_days: int = 7) -> Dict[str, Any]:
        """Collect file activity signals from database."""
        try:
            from database.models import FileVersionModel, ContentDiffModel, FileChangeModel, db
            
            # Calculate time window
            since = datetime.now() - timedelta(days=time_range_days)
            
            # Get recent file changes
            changes_query = """
                SELECT 
                    file_path, change_type, COUNT(*) as change_count,
                    SUM(lines_added) as total_lines_added,
                    SUM(lines_removed) as total_lines_removed,
                    MAX(timestamp) as last_changed,
                    MIN(timestamp) as first_changed
                FROM content_diffs
                WHERE timestamp >= ?
                GROUP BY file_path, change_type
                ORDER BY change_count DESC
                LIMIT 20
            """
            
            changes_rows = db.execute_query(changes_query, (since,))
            file_changes = [dict(row) for row in changes_rows]
            
            # Get file versions
            versions_query = """
                SELECT 
                    file_path, COUNT(*) as version_count,
                    MAX(timestamp) as last_version
                FROM file_versions
                WHERE timestamp >= ?
                GROUP BY file_path
                ORDER BY version_count DESC
                LIMIT 20
            """
            
            versions_rows = db.execute_query(versions_query, (since,))
            file_versions = [dict(row) for row in versions_rows]
            
            # Calculate activity metrics
            total_changes = sum(row['change_count'] for row in file_changes)
            total_lines_added = sum(row['total_lines_added'] or 0 for row in file_changes)
            total_lines_removed = sum(row['total_lines_removed'] or 0 for row in file_changes)
            
            # Identify most active files
            most_active_files = sorted(file_changes, key=lambda x: x['change_count'], reverse=True)[:10]
            
            # Identify change patterns
            change_types = {}
            for change in file_changes:
                change_type = change['change_type']
                change_types[change_type] = change_types.get(change_type, 0) + 1
            
            return {
                'file_changes': file_changes,
                'file_versions': file_versions,
                'total_changes': total_changes,
                'total_lines_added': total_lines_added,
                'total_lines_removed': total_lines_removed,
                'most_active_files': most_active_files,
                'change_types': change_types
            }
            
        except Exception as e:
            logger.error(f"Failed to collect file activity signals: {e}")
            return {'file_changes': [], 'file_versions': [], 'total_changes': 0}
    
    def collect_comprehensive_summary_signals(self, time_range_days: int = 7) -> Dict[str, Any]:
        """Collect comprehensive summary signals."""
        try:
            from database.models import ComprehensiveSummaryModel, db
            
            # Ensure migration is applied before querying
            migration_success = False
            try:
                from database.migration_comprehensive_summaries import apply_migration
                migration_success = apply_migration()
                if not migration_success:
                    logger.warning("Comprehensive summaries migration returned False")
            except Exception as migration_error:
                logger.error(f"Failed to ensure comprehensive_summaries migration: {migration_error}", exc_info=True)
            
            # Check if table exists before querying
            table_check_query = """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='comprehensive_summaries'
            """
            table_exists = db.execute_query(table_check_query)
            
            if not table_exists:
                logger.warning("comprehensive_summaries table does not exist, returning empty signals")
                return {'summaries': [], 'impact_distribution': {}, 'total_summaries': 0}
            
            # Calculate time window
            since = datetime.now() - timedelta(days=time_range_days)
            
            # Get recent comprehensive summaries
            query = """
                SELECT * FROM comprehensive_summaries
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 5
            """
            
            rows = db.execute_query(query, (since,))
            summaries = [dict(row) for row in rows]
            
            # Parse JSON fields
            for summary in summaries:
                try:
                    summary['key_topics'] = json.loads(summary['key_topics']) if summary['key_topics'] else []
                    summary['key_keywords'] = json.loads(summary['key_keywords']) if summary['key_keywords'] else []
                except (json.JSONDecodeError, TypeError):
                    summary['key_topics'] = []
                    summary['key_keywords'] = []
            
            # Extract overall impact distribution
            impact_counts = {}
            for summary in summaries:
                impact = summary.get('overall_impact', 'moderate')
                impact_counts[impact] = impact_counts.get(impact, 0) + 1
            
            return {
                'summaries': summaries,
                'impact_distribution': impact_counts,
                'total_summaries': len(summaries)
            }
            
        except Exception as e:
            logger.error(f"Failed to collect comprehensive summary signals: {e}")
            return {'summaries': [], 'impact_distribution': {}, 'total_summaries': 0}
    
    def collect_session_summary_signals(self, time_range_days: int = 7) -> Dict[str, Any]:
        """Collect session summary signals."""
        try:
            from database.models import SemanticModel, db
            
            # Calculate time window
            since = datetime.now() - timedelta(days=time_range_days)
            
            # Get recent session summary entries
            query = """
                SELECT * FROM semantic_entries
                WHERE timestamp >= ? AND source_type = 'session_summary'
                ORDER BY timestamp DESC
                LIMIT 10
            """
            
            rows = db.execute_query(query, (since,))
            session_summaries = [dict(row) for row in rows]
            
            # Extract topics and keywords
            topics = set()
            keywords = set()
            
            for summary in session_summaries:
                summary_topics = summary.get('topics', '').split(',') if summary.get('topics') else []
                summary_keywords = summary.get('keywords', '').split(',') if summary.get('keywords') else []
                
                topics.update([t.strip() for t in summary_topics if t.strip()])
                keywords.update([k.strip() for k in summary_keywords if k.strip()])
            
            return {
                'session_summaries': session_summaries,
                'topics': list(topics),
                'keywords': list(keywords),
                'total_summaries': len(session_summaries)
            }
            
        except Exception as e:
            logger.error(f"Failed to collect session summary signals: {e}")
            return {'session_summaries': [], 'topics': [], 'keywords': [], 'total_summaries': 0}
    
    def normalize_signals_for_agent(self, semantic_signals: Dict, file_activity: Dict,
                                  comprehensive_signals: Dict, session_signals: Dict) -> Dict[str, Any]:
        """Normalize collected signals into agent-friendly input format."""
        try:
            # Build provenance lists
            source_files = set()
            
            # Add files from semantic entries
            for entry in semantic_signals.get('entries', []):
                if entry.get('file_path'):
                    source_files.add(entry['file_path'])
            
            # Add files from file activity
            for change in file_activity.get('file_changes', []):
                if change.get('file_path'):
                    source_files.add(change['file_path'])
            
            # Create file list for agent
            file_list = list(source_files)[:50]  # Limit to prevent overwhelming the agent
            
            # Build context summary
            context_summary = {
                'time_range_days': 7,
                'total_semantic_entries': semantic_signals.get('total_entries', 0),
                'total_file_changes': file_activity.get('total_changes', 0),
                'total_comprehensive_summaries': comprehensive_signals.get('total_summaries', 0),
                'total_session_summaries': session_signals.get('total_summaries', 0),
                'most_active_files': file_activity.get('most_active_files', [])[:5],
                'top_topics': list(dict(sorted(semantic_signals.get('topic_counts', {}).items(), 
                                              key=lambda x: x[1], reverse=True)).keys())[:10],
                'top_keywords': list(dict(sorted(semantic_signals.get('keyword_counts', {}).items(), 
                                                key=lambda x: x[1], reverse=True)).keys())[:10]
            }
            
            return {
                'context_summary': context_summary,
                'source_files': file_list,
                'semantic_entries': semantic_signals.get('entries', [])[:20],  # Limit for agent
                'file_activity': file_activity,
                'comprehensive_summaries': comprehensive_signals.get('summaries', [])[:5],
                'session_summaries': session_signals.get('session_summaries', [])[:5]
            }
            
        except Exception as e:
            logger.error(f"Failed to normalize signals: {e}")
            return {
                'context_summary': {},
                'source_files': [],
                'semantic_entries': [],
                'file_activity': {},
                'comprehensive_summaries': [],
                'session_summaries': []
            }
    
    async def generate_insights_with_agent(self, normalized_signals: Dict[str, Any], 
                                      agent_model: str = 'sonnet') -> List[Dict[str, Any]]:
        """Generate insights using Claude Agent SDK."""
        try:
            self._initialize_dependencies()
            
            if not self.claude_client or not self.claude_client.is_available():
                logger.warning("Claude Agent SDK not available for insights generation")
                return []
            
            # Prepare context for Claude
            context_summary = normalized_signals.get('context_summary', {})
            source_files = normalized_signals.get('source_files', [])
            
            # Build comprehensive prompt for insights generation
            system_prompt = """You are an expert code analyst generating contextual insights for a development project.
            
Your task is to analyze the provided signals and generate 3-5 high-quality insights that help the developer understand patterns, risks, opportunities, and action items.

CATEGORIES (must use exactly these):
- quality: Code quality issues, technical debt, refactoring opportunities
- velocity: Development pace, productivity patterns, bottlenecks  
- risk: Security issues, breaking changes, dependency problems
- documentation: Missing or outdated documentation, knowledge gaps
- follow-ups: Action items, TODOs, pending decisions

PRIORITY LEVELS (must use exactly these):
- critical: Immediate attention required, blocking issues
- high: Important but not blocking, should address soon
- medium: Worth addressing but not urgent
- low: Nice to have, minor improvements

OUTPUT FORMAT (required):
For each insight, provide:
1. **Category**: [category]
2. **Priority**: [priority]  
3. **Title**: [Concise, actionable title]
4. **Content**: [Detailed explanation of what was found and why it matters]
5. **Evidence**: [Specific data points, patterns, or observations that support this insight]
6. **Related Files**: [List of relevant file paths]
7. **Source Section**: [Where this insight originated from]

ANALYSIS INSTRUCTIONS:
- Look for patterns across multiple signals
- Identify relationships between different data sources
- Focus on actionable insights that provide real value
- Consider the developer's workflow and productivity
- Highlight both positive patterns and areas needing attention
- Be specific and evidence-based
- Avoid generic or obvious observations

CONTEXT:
Time Range: Last {time_range_days} days
Semantic Entries: {total_semantic_entries} entries
File Changes: {total_file_changes} changes
Comprehensive Summaries: {total_comprehensive_summaries} summaries
Session Summaries: {total_session_summaries} summaries
Most Active Files: {most_active_files}
Top Topics: {top_topics}
Top Keywords: {top_keywords}

Generate exactly 3-5 insights following the format above.""".format(
                time_range_days=context_summary.get('time_range_days', 7),
                total_semantic_entries=context_summary.get('total_semantic_entries', 0),
                total_file_changes=context_summary.get('total_file_changes', 0),
                total_comprehensive_summaries=context_summary.get('total_comprehensive_summaries', 0),
                total_session_summaries=context_summary.get('total_session_summaries', 0),
                most_active_files=context_summary.get('most_active_files', []),
                top_topics=context_summary.get('top_topics', []),
                top_keywords=context_summary.get('top_keywords', [])
            )
            
            # Prepare user message with signals data
            user_message = f"""Please analyze these development signals and generate insights:

CONTEXT SUMMARY:
{json.dumps(context_summary, indent=2)}

SOURCE FILES:
{json.dumps(source_files, indent=2)}

RECENT SEMANTIC ENTRIES:
{json.dumps(normalized_signals.get('semantic_entries', [])[:10], indent=2)}

RECENT FILE ACTIVITY:
{json.dumps(normalized_signals.get('file_activity', {}), indent=2)}

RECENT COMPREHENSIVE SUMMARIES:
{json.dumps(normalized_signals.get('comprehensive_summaries', []), indent=2)}

RECENT SESSION SUMMARIES:
{json.dumps(normalized_signals.get('session_summaries', []), indent=2)}

Generate 3-5 actionable insights following the specified format."""
            
            # Call Claude with the insights generation prompt
            options = {
                'cwd': str(Path.cwd()),
                'allowed_tools': ["Read", "Grep", "Glob"],
                'max_turns': 15,
                'model': agent_model,
                'system_prompt': system_prompt
            }
            
            response = await self.claude_client.ask_question(user_message)
            
            # Parse Claude's response into structured insights
            insights = self._parse_insights_response(response)
            
            logger.info(f"Generated {len(insights)} insights using Claude Agent SDK")
            return insights
            
        except Exception as e:
            logger.error(f"Failed to generate insights with agent: {e}")
            return []
    
    def _parse_insights_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse Claude's response into structured insights with robust error handling."""
        import re

        try:
            insights = []

            # Try JSON parsing first (in case Claude returns JSON)
            try:
                import json
                json_match = re.search(r'\[[\s\S]*\]', response)
                if json_match:
                    parsed_json = json.loads(json_match.group())
                    if isinstance(parsed_json, list):
                        for item in parsed_json:
                            if self._validate_insight_fields(item):
                                insights.append(item)
                        if insights:
                            logger.info(f"Successfully parsed {len(insights)} insights from JSON")
                            return insights
            except (json.JSONDecodeError, ValueError):
                pass  # Fall through to markdown parsing

            # Markdown parsing with regex for robustness
            # Split by insight boundaries (looking for Category markers)
            insight_pattern = re.compile(
                r'\*\*Category\*\*\s*:\s*(.+?)\s*\n'
                r'\*\*Priority\*\*\s*:\s*(.+?)\s*\n'
                r'\*\*Title\*\*\s*:\s*(.+?)\s*\n'
                r'\*\*Content\*\*\s*:\s*(.+?)(?=\n\*\*|$)',
                re.IGNORECASE | re.DOTALL
            )

            for match in insight_pattern.finditer(response):
                category, priority, title, content = match.groups()

                insight = {
                    'category': self._normalize_category(category.strip()),
                    'priority': self._normalize_priority(priority.strip()),
                    'title': title.strip()[:200],  # Limit title length
                    'content': content.strip()[:1000],  # Limit content length
                }

                # Extract optional fields
                evidence_match = re.search(r'\*\*Evidence\*\*\s*:\s*(.+?)(?=\n\*\*|$)', response[match.end():], re.IGNORECASE)
                if evidence_match:
                    insight['evidence'] = evidence_match.group(1).strip()

                files_match = re.search(r'\*\*Related Files\*\*\s*:\s*(.+?)(?=\n\*\*|$)', response[match.end():], re.IGNORECASE)
                if files_match:
                    files_str = files_match.group(1).strip()
                    insight['related_files'] = [f.strip() for f in re.split(r'[,\n]', files_str) if f.strip()]

                section_match = re.search(r'\*\*Source Section\*\*\s*:\s*(.+?)(?=\n\*\*|$)', response[match.end():], re.IGNORECASE)
                if section_match:
                    insight['source_section'] = section_match.group(1).strip()

                if self._validate_insight_fields(insight):
                    insights.append(insight)

            # Fallback: if no structured insights found, log warning and create generic insight
            if not insights and response.strip():
                logger.warning(f"Failed to parse structured insights from response. Response preview: {response[:200]}")
                insights.append({
                    'category': 'quality',
                    'priority': 'medium',
                    'title': 'Development Activity Detected',
                    'content': 'Recent development activity was detected but could not be parsed into specific insights. Please check logs for details.',
                    'evidence': f'Raw response length: {len(response)} characters',
                    'related_files': [],
                    'source_section': 'aggregated'
                })

            logger.info(f"Successfully parsed {len(insights)} insights from response")
            return insights

        except Exception as e:
            logger.error(f"Failed to parse insights response: {e}", exc_info=True)
            return []

    def _validate_insight_fields(self, insight: Dict[str, Any]) -> bool:
        """Validate that an insight has all required fields."""
        required_fields = ['category', 'priority', 'title', 'content']
        for field in required_fields:
            if field not in insight or not insight[field]:
                logger.warning(f"Insight missing required field: {field}")
                return False
        return True

    def _normalize_category(self, category: str) -> str:
        """Normalize category to valid values."""
        valid_categories = ['action', 'pattern', 'relationship', 'temporal', 'opportunity',
                           'quality', 'velocity', 'risk', 'documentation', 'follow-ups']
        category_lower = category.lower().strip()

        # Try exact match
        if category_lower in valid_categories:
            return category_lower

        # Try partial match
        for valid in valid_categories:
            if valid in category_lower or category_lower in valid:
                return valid

        # Default fallback
        logger.warning(f"Unknown category '{category}', defaulting to 'quality'")
        return 'quality'

    def _normalize_priority(self, priority: str) -> str:
        """Normalize priority to valid values."""
        valid_priorities = ['low', 'medium', 'high', 'critical']
        priority_lower = priority.lower().strip()

        # Try exact match
        if priority_lower in valid_priorities:
            return priority_lower

        # Try partial match
        for valid in valid_priorities:
            if valid in priority_lower or priority_lower in valid:
                return valid

        # Default fallback
        logger.warning(f"Unknown priority '{priority}', defaulting to 'medium'")
        return 'medium'
    
    async def collect_all_signals_and_generate_insights(self, time_range_days: int = 7,
                                                   max_insights: int = 12,
                                                   agent_model: str = 'sonnet') -> List[Dict[str, Any]]:
        """Main method to collect all signals and generate insights."""
        try:
            logger.info(f"Starting insights aggregation for last {time_range_days} days")
            
            # Collect signals from all sources
            semantic_signals = self.collect_semantic_signals(time_range_days)
            file_activity_signals = self.collect_file_activity_signals(time_range_days)
            comprehensive_signals = self.collect_comprehensive_summary_signals(time_range_days)
            session_signals = self.collect_session_summary_signals(time_range_days)
            
            # Normalize signals for agent
            normalized_signals = self.normalize_signals_for_agent(
                semantic_signals, file_activity_signals, comprehensive_signals, session_signals
            )
            
            # Generate insights using Claude
            insights = await self.generate_insights_with_agent(normalized_signals, agent_model)
            
            # Limit to requested max
            insights = insights[:max_insights]
            
            # Add metadata to each insight
            for insight in insights:
                insight['timestamp'] = datetime.now().isoformat()
                insight['generated_by_agent'] = agent_model
                insight['evidence_payload'] = json.dumps({
                    'semantic_entries_count': semantic_signals.get('total_entries', 0),
                    'file_changes_count': file_activity_signals.get('total_changes', 0),
                    'comprehensive_summaries_count': comprehensive_signals.get('total_summaries', 0),
                    'session_summaries_count': session_signals.get('total_summaries', 0),
                    'most_active_files': file_activity_signals.get('most_active_files', [])[:5]
                })
            
            logger.info(f"Generated {len(insights)} insights from aggregated signals")
            return insights
            
        except Exception as e:
            logger.error(f"Failed to collect signals and generate insights: {e}")
            return []