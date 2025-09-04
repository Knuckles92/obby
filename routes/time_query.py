"""
Time-Based Query API routes
Handles manual time-based queries with natural language processing
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
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

time_query_bp = APIRouter(prefix='/api/time-query', tags=['time-query'])

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


@time_query_bp.get('/templates')
def get_query_templates():
    """Get pre-built query templates."""
    try:
        return {'templates': QUERY_TEMPLATES, 'total_templates': len(QUERY_TEMPLATES)}
    except Exception as e:
        logger.error(f"Failed to get query templates: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@time_query_bp.get('/suggestions')
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
        
        return {'suggestions': suggestions, 'generated_at': datetime.now().isoformat()}
        
    except Exception as e:
        logger.error(f"Failed to get query suggestions: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@time_query_bp.post('/execute')
async def execute_time_query(request: Request):
    """Execute a time-based query with optional streaming response."""
    try:
        data = await request.json()
        if not data or 'query' not in data:
            return JSONResponse({'error': 'Query text is required'}, status_code=400)
        
        query_text = data['query']
        start_time_str = data.get('startTime')
        end_time_str = data.get('endTime')
        focus_areas = data.get('focusAreas', [])
        output_format = data.get('outputFormat', 'summary')
        include_deleted = bool(data.get('includeDeleted', False))
        stream_response = data.get('stream', False)
        
        # Parse time range
        start_time, end_time = parse_natural_time_range(query_text, start_time_str, end_time_str)
        
        # Create query record
        query_id = TimeQueryModel.create_query(
            query_text, start_time, end_time, 'manual',
            focus_areas, output_format
        )
        
        if not query_id:
            return JSONResponse({'error': 'Failed to create query record'}, status_code=500)
        
        # Update status to processing
        TimeQueryModel.update_query_status(query_id, 'processing')
        
        if stream_response:
            # Stream response for real-time updates
            return StreamingResponse(
                stream_time_query_execution(query_id, query_text, start_time, end_time, focus_areas, output_format, include_deleted),
                media_type='text/event-stream',
                headers={'Cache-Control': 'no-cache', 'Connection': 'keep-alive'}
            )
        else:
            # Synchronous response
            result = execute_query_analysis(query_id, query_text, start_time, end_time, focus_areas, output_format, include_deleted)
            return result
    
    except Exception as e:
        logger.error(f"Failed to execute time query: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


def stream_time_query_execution(query_id: int, query_text: str, start_time: datetime, end_time: datetime, 
                               focus_areas: List[str], output_format: str, include_deleted: bool = False):
    """Stream query execution with real-time progress updates."""
    try:
        yield f"data: {json.dumps({'type': 'progress', 'message': 'Starting analysis...', 'progress': 10})}\n\n"
        
        # Step 1: Get comprehensive analysis
        yield f"data: {json.dumps({'type': 'progress', 'message': 'Gathering file changes...', 'progress': 30})}\n\n"
        
        watch_handler = None
        try:
            # Use project root so .obbywatch at repo root is respected
            from pathlib import Path
            project_root = Path(__file__).parent.parent
            watch_handler = WatchHandler(project_root)
        except Exception:
            logger.warning("Watch handler not available, proceeding without filtering")
        
        analysis = FileQueries.get_comprehensive_time_analysis(
            start_time, end_time, focus_areas, watch_handler, exclude_nonexistent=(not include_deleted)
        )
        
        # No provenance decoration here; handled via AI prompt only
        
        yield f"data: {json.dumps({'type': 'progress', 'message': 'Processing with AI...', 'progress': 60})}\n\n"
        
        # Step 2: AI processing
        ai_result = None
        ai_model_used = None
        try:
            # Attempt AI processing unconditionally; internal client will handle availability
            ai_result, ai_error = process_with_ai(analysis, query_text, output_format)
            try:
                # Best effort to capture model used
                ai_model_used = OpenAIClient().model
            except Exception:
                ai_model_used = None
        except Exception as e:
            ai_error = str(e)
            logger.warning(f"AI processing failed: {e}")
        
        yield f"data: {json.dumps({'type': 'progress', 'message': 'Finalizing results...', 'progress': 90})}\n\n"
        
        # Step 3: Combine results
        final_result = combine_analysis_results(analysis, ai_result, output_format, ai_model_used, ai_error)
        
        # Update database
        execution_time = int((datetime.now() - datetime.fromisoformat(analysis['metadata']['analysisTimestamp'])).total_seconds() * 1000)
        TimeQueryModel.update_query_status(
            query_id, 'completed', 
            json.dumps(final_result), 
            {'executionTimeMs': execution_time, 'includeDeleted': include_deleted},
            execution_time
        )
        
        yield f"data: {json.dumps({'type': 'complete', 'result': final_result, 'queryId': query_id})}\n\n"
        
    except Exception as e:
        logger.error(f"Error in streaming execution: {e}")
        TimeQueryModel.update_query_status(query_id, 'failed')
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"


def execute_query_analysis(query_id: int, query_text: str, start_time: datetime, end_time: datetime,
                          focus_areas: List[str], output_format: str, include_deleted: bool = False) -> Dict[str, Any]:
    """Execute query analysis synchronously."""
    start_exec_time = time.time()
    
    try:
        # Get watch handler for filtering
        watch_handler = None
        try:
            from pathlib import Path
            project_root = Path(__file__).parent.parent
            watch_handler = WatchHandler(project_root)
        except Exception:
            logger.warning("Watch handler not available, proceeding without filtering")
        
        # Get comprehensive analysis
        analysis = FileQueries.get_comprehensive_time_analysis(
            start_time, end_time, focus_areas, watch_handler, exclude_nonexistent=(not include_deleted)
        )
        
        # No provenance decoration here; handled via AI prompt only
        
        # AI processing
        ai_markdown: Optional[str] = None
        ai_model_used: Optional[str] = None
        ai_error: Optional[str] = None
        try:
            logger.info(f"Starting AI processing for query: {query_text[:100]}...")
            ai_markdown, ai_error = process_with_ai(analysis, query_text, output_format)
            try:
                ai_model_used = OpenAIClient().model
            except Exception:
                ai_model_used = None
            
            # Log the outcome
            if ai_markdown:
                logger.info(f"AI processing succeeded, got {len(ai_markdown)} characters of markdown")
            else:
                logger.warning(f"AI processing failed, error: {ai_error}")
                
        except Exception as e:
            ai_error = str(e)
            logger.error(f"AI processing exception: {e}")
        
        # Combine results
        if ai_markdown is None:
            logger.warning("AI result is None; returning fallback markdown content")
        final_result = combine_analysis_results(analysis, ai_markdown, output_format, ai_model_used, ai_error)
        
        # Update database
        execution_time_ms = int((time.time() - start_exec_time) * 1000)
        TimeQueryModel.update_query_status(
            query_id, 'completed',
            json.dumps(final_result),
            {'executionTimeMs': execution_time_ms, 'includeDeleted': include_deleted},
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


def process_with_ai(analysis: Dict[str, Any], query_text: str, output_format: str) -> tuple[Optional[str], Optional[str]]:
    """Process analysis with AI, passing user query, recent diffs, and stats.

    Returns a tuple of (markdown, error_text). If AI succeeds, error_text is None.
    """
    try:
        openai_client = OpenAIClient()

        # Build compact stats
        summary = analysis.get('summary', {})
        semantic = analysis.get('semanticAnalysis', {})
        file_metrics = analysis.get('fileMetrics', []) or []

        top_topics = list((semantic.get('topTopics') or {}).keys())[:5]
        top_keywords = list((semantic.get('topKeywords') or {}).keys())[:5]

        # Prepare recent diffs (take last N, truncate total content)
        diffs = analysis.get('diffs', []) or []
        max_diffs = 8
        max_total_chars = 6000
        max_per_diff = 800
        recent_diffs = diffs[-max_diffs:]

        diffs_text_parts = []
        total_chars = 0
        for d in recent_diffs:
            header = f"### {d.get('filePath', 'unknown')} — {d.get('changeType', '')} @ {d.get('timestamp', '')}\n"
            content = d.get('diffContent') or ''
            snippet = content[:max_per_diff]
            part = header + "\n" + snippet + ("\n...\n" if len(content) > len(snippet) else "\n")
            if total_chars + len(part) > max_total_chars:
                remaining = max_total_chars - total_chars
                if remaining > 0:
                    diffs_text_parts.append(part[:remaining])
                    total_chars += remaining
                break
            diffs_text_parts.append(part)
            total_chars += len(part)
        diffs_text = "\n".join(diffs_text_parts) if diffs_text_parts else "(No recent diff content available)"

        # Build files-used context from metrics and diffs
        try:
            from pathlib import Path
            included_paths = set()
            for d in diffs:
                fp = d.get('filePath') or d.get('file_path')
                if fp:
                    included_paths.add(fp)
            for m in (analysis.get('fileMetrics') or []):
                fp = (m.get('file_path') if isinstance(m, dict) else None) or (m.get('filePath') if isinstance(m, dict) else None)
                if fp:
                    included_paths.add(fp)
            files_used = []
            for fp in sorted(included_paths):
                met = next((m for m in (analysis.get('fileMetrics') or []) if isinstance(m, dict) and (m.get('file_path') == fp or m.get('filePath') == fp)), None)
                ccount = (met.get('change_count') if isinstance(met, dict) else None) or (met.get('changes') if isinstance(met, dict) else None)
                add = (met.get('total_lines_added') if isinstance(met, dict) else None)
                rem = (met.get('total_lines_removed') if isinstance(met, dict) else None)
                files_used.append({
                    'path': fp,
                    'change_count': ccount,
                    'lines_added': add,
                    'lines_removed': rem,
                })
        except Exception:
            files_used = []

        # System instruction prioritizes user's request and requires a Sources section
        system_prompt = (
            "You are an expert developer assistant. "
            "Follow the user's instruction exactly for the output. "
            "Use the provided diffs, stats, and file list as context. "
            "Always include a final section titled 'Sources' that lists the files used and a one-sentence rationale for each. "
            "Return markdown only (no JSON/preamble)."
        )

        # User prompt includes query + compact stats + recent diffs
        # Files-used block to guide the Sources section
        files_used_block = "\n".join([
            f"- {f['path']} (changes: {f['change_count'] if f['change_count'] is not None else 'n/a'}, +{f['lines_added'] if f['lines_added'] is not None else 'n/a'}/-{f['lines_removed'] if f['lines_removed'] is not None else 'n/a'})"
            for f in files_used
        ]) or "(No specific files identified)"

        prompt = f"""
User request:
"{query_text}"

Time range: {analysis['timeRange']['start']} → {analysis['timeRange']['end']}
Stats: changes={summary.get('totalChanges', 0)}, files={summary.get('filesAffected', 0)}, lines+={summary.get('linesAdded', 0)}, lines-={summary.get('linesRemoved', 0)}
Change types: {summary.get('changeTypes', {})}
Top topics: {top_topics if top_topics else 'None'}
Top keywords: {top_keywords if top_keywords else 'None'}
Most active files: {[f.get('file_path') for f in file_metrics[:5]] if file_metrics else 'None'}

Files considered in this analysis:
{files_used_block}

Recent diff changes (newest last):
{diffs_text}

Instructions: Produce exactly what the user requested above, using this context. If the request asks for a summary or analysis, keep it concise and useful. Include a final section titled 'Sources' listing the files you drew from and a one-sentence rationale per file.
"""

        # Log a compact trace to help diagnose empty responses
        try:
            logger.info(f"AI prompt: query='{query_text[:80]}...' diffs_chars={len(diffs_text)} stats_changes={summary.get('totalChanges', 0)}")
        except Exception:
            pass

        # Check if client is available before attempting call
        if not openai_client.is_available():
            error_msg = f"OpenAI client not available: api_key={'set' if openai_client.api_key else 'missing'}, client={'initialized' if openai_client.client else 'failed'}"
            logger.error(error_msg)
            return None, error_msg

        logger.info(f"Making AI completion call with model: {openai_client.model}")
        ai_response = openai_client.get_completion(
            prompt,
            system_prompt=system_prompt,
            max_tokens=3000,  # Use more tokens for user queries which often need detailed responses
        )

        if ai_response and ai_response.strip() and not ai_response.strip().lower().startswith('error generating completion:'):
            # Optional safety-net: append Sources if model omitted it
            try:
                from config import settings as cfg
                if cfg.AI_SOURCES_FALLBACK_ENABLED:
                    lower = ai_response.lower()
                    if '## sources' not in lower and '### sources' not in lower:
                        # Use files_used (built above) to synthesize sources
                        file_paths = [f.get('path') for f in files_used if f.get('path')]
                        if file_paths:
                            sources_md = OpenAIClient().generate_sources_section(file_paths, diffs_text)
                            if sources_md and sources_md.strip():
                                ai_response = ai_response.rstrip() + "\n\n" + sources_md.strip()
            except Exception:
                pass
            logger.info(f"AI processing successful, returning {len(ai_response.strip())} characters")
            return ai_response.strip(), None
        
        # Log failure cases for debugging and return last error
        try:
            if not ai_response or not ai_response.strip():
                logger.warning("AI returned empty response; falling back to non-AI summary")
            else:
                logger.error(f"AI responded with error: {ai_response[:200]}")
        except Exception:
            pass
        
        last_error = getattr(openai_client, '_last_error', ai_response or 'Unknown AI processing error')
        logger.error(f"AI processing failed, last_error: {last_error}")
        return None, last_error

    except Exception as e:
        logger.error(f"AI processing error: {e}")
        return None, str(e)


def combine_analysis_results(analysis: Dict[str, Any], ai_result: Optional[str], 
                           output_format: str, model_used: Optional[str] = None,
                           ai_error: Optional[str] = None) -> Dict[str, Any]:
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
    
    # Include AI metadata (model used) if available
    if model_used or ai_error:
        result['ai'] = {
            'model': model_used,
            'provider': 'openai',
            **({'error': ai_error} if ai_error else {})
        }

    return result


@time_query_bp.get('/history')
async def get_query_history(request: Request):
    """Get recent query history."""
    try:
        limit = int(request.query_params.get('limit', 20))
        queries = TimeQueryModel.get_recent_queries(limit)
        
        return {'queries': queries, 'total': len(queries)}
        
    except Exception as e:
        logger.error(f"Failed to get query history: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@time_query_bp.get('/saved')
async def get_saved_queries():
    """Get user-saved queries."""
    try:
        queries = TimeQueryModel.get_saved_queries()
        return {'savedQueries': queries, 'total': len(queries)}
        
    except Exception as e:
        logger.error(f"Failed to get saved queries: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@time_query_bp.post('/save')
async def save_query(request: Request):
    """Save a query for reuse."""
    try:
        data = await request.json()
        if not data or 'queryId' not in data or 'name' not in data:
            return JSONResponse({'error': 'Query ID and name are required'}, status_code=400)
        
        query_id = data['queryId']
        name = data['name']
        
        success = TimeQueryModel.save_query(query_id, name)
        
        if success:
            return {'message': 'Query saved successfully'}
        else:
            return JSONResponse({'error': 'Failed to save query'}, status_code=500)
            
    except Exception as e:
        logger.error(f"Failed to save query: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@time_query_bp.get('/result/{query_id}')
async def get_query_result(query_id: int):
    """Get results of a specific query."""
    try:
        query = TimeQueryModel.get_query(query_id)
        
        if not query:
            return JSONResponse({'error': 'Query not found'}, status_code=404)
        return query
        
    except Exception as e:
        logger.error(f"Failed to get query {query_id}: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@time_query_bp.delete('/result/{query_id}')
async def delete_query(query_id: int):
    """Delete a query from history."""
    try:
        success = TimeQueryModel.delete_query(query_id)
        
        if success:
            return {'message': 'Query deleted successfully'}
        else:
            return JSONResponse({'error': 'Query not found'}, status_code=404)
            
    except Exception as e:
        logger.error(f"Failed to delete query {query_id}: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)
