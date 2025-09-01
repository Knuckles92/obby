"""
Time-Based Query API routes
Handles manual time-based queries with natural language processing
"""

from flask import Blueprint, jsonify, request, Response, stream_with_context
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from database.queries import FileQueries
from database.models import TimeQueryModel
from ai.openai_client import OpenAIClient
from utils.watch_handler import WatchHandler
from config import settings

logger = logging.getLogger(__name__)

time_query_bp = Blueprint('time_query', __name__, url_prefix='/api/time-query')

# Query templates for common time-based queries
QUERY_TEMPLATES = [
    {
        'id': 'daily_summary',
        'name': 'Daily Summary',
        'query': "Summarize today's changes",
        'description': 'Get a summary of all changes made today',
        'timeRange': 'today',
        'outputFormat': 'summary'
    },
    {
        'id': 'weekly_report',
        'name': 'Weekly Report',
        'query': "Analyze this week's productivity",
        'description': 'Comprehensive analysis of this week\'s activity',
        'timeRange': 'thisWeek',
        'outputFormat': 'summary'
    },
    {
        'id': 'monthly_overview',
        'name': 'Monthly Overview',
        'query': "Show last 30 days trends",
        'description': 'High-level trends and patterns from the past month',
        'timeRange': 'last30Days',
        'outputFormat': 'summary'
    },
    {
        'id': 'action_items',
        'name': 'Action Items',
        'query': "Suggest next steps from recent work",
        'description': 'AI-generated action items based on recent changes',
        'timeRange': 'last7Days',
        'outputFormat': 'actionItems'
    },
    {
        'id': 'file_activity',
        'name': 'File Activity',
        'query': "Which files changed most this week",
        'description': 'Most active files and their change patterns',
        'timeRange': 'thisWeek',
        'outputFormat': 'summary'
    },
    {
        'id': 'topic_analysis',
        'name': 'Topic Analysis',
        'query': "What topics did I focus on recently",
        'description': 'Topic and keyword analysis from recent work',
        'timeRange': 'last7Days',
        'outputFormat': 'summary'
    }
]


def parse_natural_time_range(query_text: str, explicit_start: str = None, explicit_end: str = None) -> tuple[datetime, datetime]:
    """Parse natural language time expressions from query text."""
    now = datetime.now()
    
    # If explicit times provided, use them
    if explicit_start and explicit_end:
        try:
            start_time = datetime.fromisoformat(explicit_start.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(explicit_end.replace('Z', '+00:00'))
            return start_time, end_time
        except ValueError:
            logger.warning(f"Failed to parse explicit times: {explicit_start}, {explicit_end}")
    
    query_lower = query_text.lower()
    
    # Today
    if 'today' in query_lower:
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = now
    # Yesterday
    elif 'yesterday' in query_lower:
        yesterday = now - timedelta(days=1)
        start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    # This week
    elif 'this week' in query_lower:
        days_since_monday = now.weekday()
        start_time = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = now
    # Last week
    elif 'last week' in query_lower:
        days_since_monday = now.weekday()
        last_monday = now - timedelta(days=days_since_monday + 7)
        last_sunday = last_monday + timedelta(days=6)
        start_time = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = last_sunday.replace(hour=23, minute=59, second=59, microsecond=999999)
    # Last X days patterns
    elif 'last' in query_lower and 'day' in query_lower:
        # Extract number of days
        import re
        days_match = re.search(r'last\s+(\d+)\s+days?', query_lower)
        if days_match:
            days = int(days_match.group(1))
            start_time = now - timedelta(days=days)
            end_time = now
        else:
            # Default to last 7 days
            start_time = now - timedelta(days=7)
            end_time = now
    # Last X hours
    elif 'last' in query_lower and ('hour' in query_lower or 'hr' in query_lower):
        import re
        hours_match = re.search(r'last\s+(\d+)\s+(?:hours?|hrs?)', query_lower)
        if hours_match:
            hours = int(hours_match.group(1))
            start_time = now - timedelta(hours=hours)
            end_time = now
        else:
            # Default to last 24 hours
            start_time = now - timedelta(hours=24)
            end_time = now
    # This month
    elif 'this month' in query_lower:
        start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_time = now
    # Last month
    elif 'last month' in query_lower:
        first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        first_of_last_month = (first_of_this_month - timedelta(days=1)).replace(day=1)
        start_time = first_of_last_month
        end_time = first_of_this_month - timedelta(microseconds=1)
    else:
        # Default to last 7 days
        start_time = now - timedelta(days=7)
        end_time = now
    
    return start_time, end_time


@time_query_bp.route('/templates', methods=['GET'])
def get_query_templates():
    """Get pre-built query templates."""
    try:
        return jsonify({
            'templates': QUERY_TEMPLATES,
            'total_templates': len(QUERY_TEMPLATES)
        })
    except Exception as e:
        logger.error(f"Failed to get query templates: {e}")
        return jsonify({'error': str(e)}), 500


@time_query_bp.route('/suggestions', methods=['GET'])
def get_query_suggestions():
    """Get AI-powered query suggestions based on recent activity."""
    try:
        # Get recent activity to suggest relevant queries
        recent_diffs = FileQueries.get_recent_diffs(limit=10)
        
        # Basic suggestion logic (could be enhanced with AI)
        suggestions = []
        
        if recent_diffs:
            last_activity = recent_diffs[0]['timestamp']
            last_activity_time = datetime.fromisoformat(last_activity)
            hours_since = (datetime.now() - last_activity_time).total_seconds() / 3600
            
            if hours_since < 1:
                suggestions.append("Summarize the last hour of changes")
            elif hours_since < 24:
                suggestions.append("What did I accomplish today?")
            else:
                suggestions.append("Show me what I worked on this week")
            
            # File-based suggestions
            file_paths = [diff['filePath'] for diff in recent_diffs[:5]]
            unique_extensions = set()
            for path in file_paths:
                if '.' in path:
                    ext = path.split('.')[-1]
                    unique_extensions.add(ext)
            
            if 'py' in unique_extensions:
                suggestions.append("Analyze Python code changes this week")
            if 'js' in unique_extensions or 'ts' in unique_extensions or 'tsx' in unique_extensions:
                suggestions.append("Review frontend changes from the last few days")
        else:
            suggestions = [
                "Summarize today's changes",
                "Show activity from the last 7 days",
                "What files have I been working on recently?"
            ]
        
        return jsonify({
            'suggestions': suggestions,
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get query suggestions: {e}")
        return jsonify({'error': str(e)}), 500


@time_query_bp.route('/execute', methods=['POST'])
def execute_time_query():
    """Execute a time-based query with optional streaming response."""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Query text is required'}), 400
        
        query_text = data['query']
        start_time_str = data.get('startTime')
        end_time_str = data.get('endTime')
        focus_areas = data.get('focusAreas', [])
        output_format = data.get('outputFormat', 'summary')
        stream_response = data.get('stream', False)
        
        # Parse time range
        start_time, end_time = parse_natural_time_range(query_text, start_time_str, end_time_str)
        
        # Create query record
        query_id = TimeQueryModel.create_query(
            query_text, start_time, end_time, 'manual',
            focus_areas, output_format
        )
        
        if not query_id:
            return jsonify({'error': 'Failed to create query record'}), 500
        
        # Update status to processing
        TimeQueryModel.update_query_status(query_id, 'processing')
        
        if stream_response:
            # Stream response for real-time updates
            return Response(
                stream_with_context(stream_time_query_execution(query_id, query_text, start_time, end_time, focus_areas, output_format)),
                mimetype='text/event-stream',
                headers={'Cache-Control': 'no-cache', 'Connection': 'keep-alive'}
            )
        else:
            # Synchronous response
            result = execute_query_analysis(query_id, query_text, start_time, end_time, focus_areas, output_format)
            return jsonify(result)
    
    except Exception as e:
        logger.error(f"Failed to execute time query: {e}")
        return jsonify({'error': str(e)}), 500


def stream_time_query_execution(query_id: int, query_text: str, start_time: datetime, end_time: datetime, 
                               focus_areas: List[str], output_format: str):
    """Stream query execution with real-time progress updates."""
    try:
        yield f"data: {json.dumps({'type': 'progress', 'message': 'Starting analysis...', 'progress': 10})}\n\n"
        
        # Step 1: Get comprehensive analysis
        yield f"data: {json.dumps({'type': 'progress', 'message': 'Gathering file changes...', 'progress': 30})}\n\n"
        
        watch_handler = None
        try:
            watch_handler = WatchHandler()
        except Exception:
            logger.warning("Watch handler not available, proceeding without filtering")
        
        analysis = FileQueries.get_comprehensive_time_analysis(start_time, end_time, focus_areas, watch_handler)
        
        yield f"data: {json.dumps({'type': 'progress', 'message': 'Processing with AI...', 'progress': 60})}\n\n"
        
        # Step 2: AI processing
        ai_result = None
        try:
            openai_client = OpenAIClient()
            if openai_client and openai_client.is_available():
                ai_result = process_with_ai(analysis, query_text, output_format)
        except Exception as e:
            logger.warning(f"AI processing failed: {e}")
        
        yield f"data: {json.dumps({'type': 'progress', 'message': 'Finalizing results...', 'progress': 90})}\n\n"
        
        # Step 3: Combine results
        final_result = combine_analysis_results(analysis, ai_result, output_format)
        
        # Update database
        execution_time = int((datetime.now() - datetime.fromisoformat(analysis['metadata']['analysisTimestamp'])).total_seconds() * 1000)
        TimeQueryModel.update_query_status(
            query_id, 'completed', 
            json.dumps(final_result), 
            {'executionTimeMs': execution_time},
            execution_time
        )
        
        yield f"data: {json.dumps({'type': 'complete', 'result': final_result, 'queryId': query_id})}\n\n"
        
    except Exception as e:
        logger.error(f"Error in streaming execution: {e}")
        TimeQueryModel.update_query_status(query_id, 'failed')
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"


def execute_query_analysis(query_id: int, query_text: str, start_time: datetime, end_time: datetime,
                          focus_areas: List[str], output_format: str) -> Dict[str, Any]:
    """Execute query analysis synchronously."""
    start_exec_time = time.time()
    
    try:
        # Get watch handler for filtering
        watch_handler = None
        try:
            watch_handler = WatchHandler()
        except Exception:
            logger.warning("Watch handler not available, proceeding without filtering")
        
        # Get comprehensive analysis
        analysis = FileQueries.get_comprehensive_time_analysis(start_time, end_time, focus_areas, watch_handler)
        
        # AI processing
        ai_result = None
        try:
            openai_client = OpenAIClient()
            if openai_client and openai_client.is_available():
                ai_result = process_with_ai(analysis, query_text, output_format)
        except Exception as e:
            logger.warning(f"AI processing failed: {e}")
        
        # Combine results
        final_result = combine_analysis_results(analysis, ai_result, output_format)
        
        # Update database
        execution_time_ms = int((time.time() - start_exec_time) * 1000)
        TimeQueryModel.update_query_status(
            query_id, 'completed',
            json.dumps(final_result),
            {'executionTimeMs': execution_time_ms},
            execution_time_ms
        )
        
        return {
            'queryId': query_id,
            'result': final_result,
            'executionTime': execution_time_ms
        }
        
    except Exception as e:
        logger.error(f"Error in query analysis: {e}")
        TimeQueryModel.update_query_status(query_id, 'failed')
        return {'error': str(e), 'queryId': query_id}


def process_with_ai(analysis: Dict[str, Any], query_text: str, output_format: str) -> Optional[str]:
    """Process analysis results with AI for enhanced insights, returning markdown."""
    try:
        openai_client = OpenAIClient()
        
        # Create a comprehensive markdown report prompt
        prompt = f"""
Create a comprehensive markdown report for the following development activity analysis:

**Query:** "{query_text}"
**Time Range:** {analysis['timeRange']['start']} to {analysis['timeRange']['end']}
**Changes:** {analysis['summary']['totalChanges']} across {analysis['summary']['filesAffected']} files
**Lines Added:** {analysis['summary']['linesAdded']}
**Lines Removed:** {analysis['summary']['linesRemoved']}

**Top Topics:** {list(analysis['semanticAnalysis']['topTopics'].keys())[:5] if analysis['semanticAnalysis']['topTopics'] else 'None'}
**Top Keywords:** {list(analysis['semanticAnalysis']['topKeywords'].keys())[:5] if analysis['semanticAnalysis']['topKeywords'] else 'None'}

**Most Active Files:** {[f['file_path'] + ' (' + str(f['change_count']) + ' changes)' for f in analysis['fileMetrics'][:5]] if analysis.get('fileMetrics') else 'None'}

Please create a well-structured markdown report that includes:

1. **## Executive Summary** - 2-3 sentences about the main accomplishments and focus areas
2. **## Key Highlights** - Bullet points of notable changes and achievements  
3. **## File Activity** - Brief overview of the most active files and what changed
4. **## Topics & Focus Areas** - Analysis of the main topics and keywords from the work
5. **## Next Steps** - 3-5 actionable recommendations based on the changes

Use proper markdown formatting with headers, bullet points, code blocks if relevant, and make it readable and informative. Focus on insights and patterns rather than just listing raw data.

Return ONLY the markdown content, no JSON or other formatting.
"""
        
        # Get AI response
        ai_response = openai_client.get_completion(prompt)
        
        if ai_response and ai_response.strip():
            return ai_response.strip()
        
        return None
        
    except Exception as e:
        logger.error(f"AI processing error: {e}")
        return None


def combine_analysis_results(analysis: Dict[str, Any], ai_result: Optional[str], 
                           output_format: str) -> Dict[str, Any]:
    """Combine database analysis with AI-generated markdown report."""
    result = {
        'timeRange': analysis['timeRange'],
        'summary': analysis['summary'],
        'outputFormat': output_format,
        'generatedAt': datetime.now().isoformat()
    }
    
    # Add the markdown content from AI
    if ai_result:
        result['markdownContent'] = ai_result
    else:
        # Fallback markdown if AI is not available
        result['markdownContent'] = f"""# Query Results

## Summary
- **Time Range:** {analysis['timeRange']['start']} to {analysis['timeRange']['end']}
- **Total Changes:** {analysis['summary']['totalChanges']}
- **Files Affected:** {analysis['summary']['filesAffected']}
- **Lines Added:** {analysis['summary']['linesAdded']}
- **Lines Removed:** {analysis['summary']['linesRemoved']}

## Most Active Files
{chr(10).join([f"- **{f['file_path']}** - {f['change_count']} changes" for f in analysis.get('fileMetrics', [])[:5]])}

## Topics & Keywords
**Topics:** {', '.join(list(analysis['semanticAnalysis']['topTopics'].keys())[:5]) if analysis['semanticAnalysis']['topTopics'] else 'None'}

**Keywords:** {', '.join(list(analysis['semanticAnalysis']['topKeywords'].keys())[:5]) if analysis['semanticAnalysis']['topKeywords'] else 'None'}
"""
    
    return result


@time_query_bp.route('/history', methods=['GET'])
def get_query_history():
    """Get recent query history."""
    try:
        limit = request.args.get('limit', 20, type=int)
        queries = TimeQueryModel.get_recent_queries(limit)
        
        return jsonify({
            'queries': queries,
            'total': len(queries)
        })
        
    except Exception as e:
        logger.error(f"Failed to get query history: {e}")
        return jsonify({'error': str(e)}), 500


@time_query_bp.route('/saved', methods=['GET'])
def get_saved_queries():
    """Get user-saved queries."""
    try:
        queries = TimeQueryModel.get_saved_queries()
        
        return jsonify({
            'savedQueries': queries,
            'total': len(queries)
        })
        
    except Exception as e:
        logger.error(f"Failed to get saved queries: {e}")
        return jsonify({'error': str(e)}), 500


@time_query_bp.route('/save', methods=['POST'])
def save_query():
    """Save a query for reuse."""
    try:
        data = request.get_json()
        if not data or 'queryId' not in data or 'name' not in data:
            return jsonify({'error': 'Query ID and name are required'}), 400
        
        query_id = data['queryId']
        name = data['name']
        
        success = TimeQueryModel.save_query(query_id, name)
        
        if success:
            return jsonify({'message': 'Query saved successfully'})
        else:
            return jsonify({'error': 'Failed to save query'}), 500
            
    except Exception as e:
        logger.error(f"Failed to save query: {e}")
        return jsonify({'error': str(e)}), 500


@time_query_bp.route('/<int:query_id>', methods=['GET'])
def get_query_result(query_id: int):
    """Get results of a specific query."""
    try:
        query = TimeQueryModel.get_query(query_id)
        
        if not query:
            return jsonify({'error': 'Query not found'}), 404
        
        return jsonify(query)
        
    except Exception as e:
        logger.error(f"Failed to get query {query_id}: {e}")
        return jsonify({'error': str(e)}), 500


@time_query_bp.route('/<int:query_id>', methods=['DELETE'])
def delete_query(query_id: int):
    """Delete a query from history."""
    try:
        success = TimeQueryModel.delete_query(query_id)
        
        if success:
            return jsonify({'message': 'Query deleted successfully'})
        else:
            return jsonify({'error': 'Query not found'}), 404
            
    except Exception as e:
        logger.error(f"Failed to delete query {query_id}: {e}")
        return jsonify({'error': str(e)}), 500