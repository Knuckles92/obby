"""
Insights API Routes
Provides AI-powered contextual insights endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import asyncio
import json

from services.insights_service import InsightsService

logger = logging.getLogger(__name__)

insights_bp = APIRouter(prefix="/api/insights", tags=["insights"])
insights_service = InsightsService()


@insights_bp.get("/")
async def get_insights(
    time_range_days: int = Query(default=7, ge=1, le=30, description="Time range in days"),
    max_insights: int = Query(default=12, ge=1, le=50, description="Maximum insights to generate"),
    include_dismissed: bool = Query(default=False, description="Include dismissed insights"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    priority: Optional[str] = Query(default=None, description="Filter by priority")
) -> Dict[str, Any]:
    """
    Retrieve AI-powered contextual insights from the database
    
    This endpoint only returns existing insights from the database.
    To generate new insights, use POST /api/insights/refresh

    Parameters:
    - time_range_days: Number of days to analyze (1-30)
    - max_insights: Maximum number of insights to return (1-50)
    - include_dismissed: Whether to include insights marked as dismissed
    - category: Filter by category (optional)
    - priority: Filter by priority (optional)
    """
    try:
        # Validate category if provided
        valid_categories = ['action', 'pattern', 'relationship', 'temporal', 'opportunity',
                           'quality', 'velocity', 'risk', 'documentation', 'follow-ups']
        if category and category not in valid_categories:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}"
            )

        # Validate priority if provided
        valid_priorities = ['low', 'medium', 'high', 'critical']
        if priority and priority not in valid_priorities:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid priority. Must be one of: {', '.join(valid_priorities)}"
            )

        insights = await insights_service.get_insights(
            time_range_days=time_range_days,
            max_insights=max_insights,
            include_dismissed=include_dismissed,
            category=category,
            priority=priority
        )
        
        return {
            "success": True,
            "data": insights,
            "metadata": {
                "time_range_days": time_range_days,
                "max_insights": max_insights,
                "generated_at": datetime.utcnow().isoformat(),
                "total_insights": len(insights)
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating insights: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate insights")


@insights_bp.post("/{insight_id}/dismiss")
async def dismiss_insight(insight_id: str):
    """Mark an insight as dismissed"""
    try:
        # Validate and convert insight_id to integer
        try:
            insight_id_int = int(insight_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid insight ID format")

        success = await insights_service.dismiss_insight(insight_id_int)
        if success:
            return {"success": True, "message": "Insight dismissed"}
        else:
            raise HTTPException(status_code=404, detail="Insight not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error dismissing insight {insight_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to dismiss insight")


@insights_bp.post("/{insight_id}/archive")
async def archive_insight(insight_id: str):
    """Archive an insight"""
    try:
        # Validate and convert insight_id to integer
        try:
            insight_id_int = int(insight_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid insight ID format")

        success = await insights_service.archive_insight(insight_id_int)
        if success:
            return {"success": True, "message": "Insight archived"}
        else:
            raise HTTPException(status_code=404, detail="Insight not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error archiving insight {insight_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to archive insight")


@insights_bp.post("/refresh")
async def refresh_insights(
    time_range_days: int = Query(default=7, ge=1, le=30, description="Time range in days"),
    max_insights: int = Query(default=12, ge=1, le=50, description="Maximum insights to generate")
) -> Dict[str, Any]:
    """
    Force refresh and generate new AI-powered insights

    This endpoint triggers an agent call to generate fresh insights.
    Progress events will be emitted to SSE connections at /api/insights/progress/events.

    Parameters:
    - time_range_days: Number of days to analyze (1-30)
    - max_insights: Maximum number of insights to generate (1-50)
    """
    try:
        # Create progress callback that emits events to SSE streams
        def progress_callback(event_data: Dict[str, Any]):
            emit_insights_progress_event(event_data)

        result = await insights_service.refresh_insights(
            time_range_days=time_range_days,
            max_insights=max_insights,
            force_refresh=True,
            progress_callback=progress_callback
        )

        if result.get('success'):
            return {
                "success": True,
                "data": result.get('insights', []),
                "message": result.get('message', 'Insights refreshed successfully'),
                "metadata": {
                    "time_range_days": time_range_days,
                    "max_insights": max_insights,
                    "generated_at": datetime.utcnow().isoformat(),
                    "total_insights": len(result.get('insights', [])),
                    "last_refresh": result.get('last_refresh')
                }
            }
        else:
            raise HTTPException(status_code=500, detail=result.get('message', 'Failed to refresh insights'))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing insights: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh insights")


@insights_bp.get("/stats/overview")
async def get_insights_stats():
    """Get overview statistics about insights generation"""
    try:
        stats = await insights_service.get_insights_stats()
        return {
            "success": True,
            "data": stats
        }

    except Exception as e:
        logger.error(f"Error getting insights stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get insights stats")


@insights_bp.get("/{insight_id}/agent-logs")
async def get_insight_agent_logs(insight_id: str):
    """Get detailed agent action logs for a specific insight"""
    try:
        # Validate and convert insight_id to integer
        try:
            insight_id_int = int(insight_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid insight ID format")

        from database.models import InsightModel
        insight_with_logs = InsightModel.get_insight_with_agent_logs(insight_id_int)

        if not insight_with_logs:
            raise HTTPException(status_code=404, detail="Insight not found")

        return {
            "success": True,
            "data": insight_with_logs.get("agent_action_logs", [])
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent logs for insight {insight_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get agent logs")


# Global dictionary to track active progress streams
_active_progress_streams = {}


@insights_bp.get("/progress/events")
async def insights_progress_events():
    """
    Server-Sent Events endpoint for real-time insights generation progress

    This endpoint provides real-time updates during AI insights generation,
    showing data collection, file exploration, analysis phases, and completion.

    Usage:
    - Connect with EventSource: new EventSource('/api/insights/progress/events')
    - Listen for 'message' events with progress data
    - Progress includes phases: data_collection, file_exploration, analysis, generation
    """

    async def event_generator():
        """Generate SSE events for insights progress tracking."""
        session_id = f"insights_{datetime.utcnow().timestamp()}"

        try:
            logger.info(f"New insights progress stream connected: {session_id}")

            # Store the session's event queue
            event_queue = asyncio.Queue()
            _active_progress_streams[session_id] = event_queue

            # Send initial connection event
            await event_queue.put({
                "type": "connection",
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Connected to insights progress stream"
            })

            # Keep connection alive and send events from queue
            try:
                while True:
                    # Wait for event with timeout to keep connection alive
                    try:
                        event = await asyncio.wait_for(event_queue.get(), timeout=30.0)
                        data = json.dumps(event)
                        yield f"data: {data}\n\n"

                        # If this is a completion event, close the stream
                        if event.get("phase") == "generation" and event.get("operation") == "Generation complete":
                            break

                    except asyncio.TimeoutError:
                        # Send heartbeat to keep connection alive
                        heartbeat = {
                            "type": "heartbeat",
                            "session_id": session_id,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        data = json.dumps(heartbeat)
                        yield f"data: {data}\n\n"

            except asyncio.CancelledError:
                logger.info(f"Insights progress stream cancelled: {session_id}")

        except Exception as e:
            logger.error(f"Error in insights progress stream {session_id}: {e}")
            error_event = {
                "type": "error",
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
            try:
                data = json.dumps(error_event)
                yield f"data: {data}\n\n"
            except:
                pass
        finally:
            # Clean up session
            if session_id in _active_progress_streams:
                del _active_progress_streams[session_id]
            logger.info(f"Insights progress stream closed: {session_id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


def emit_insights_progress_event(event_data: Dict[str, Any]):
    """
    Emit a progress event to all active insights progress streams.

    This function should be called by the insights service during
    AI operations to provide real-time progress updates.

    Args:
        event_data: Dictionary containing progress information
                   (phase, operation, details, files_processed, etc.)
    """
    event = {
        "type": "progress",
        "timestamp": datetime.utcnow().isoformat(),
        **event_data
    }

    # Send to all active streams
    disconnected_streams = []
    for session_id, event_queue in _active_progress_streams.items():
        try:
            # Non-blocking put to avoid blocking the main thread
            event_queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning(f"Progress event queue full for session {session_id}")
            disconnected_streams.append(session_id)
        except Exception as e:
            logger.error(f"Error sending progress event to session {session_id}: {e}")
            disconnected_streams.append(session_id)

    # Clean up disconnected streams
    for session_id in disconnected_streams:
        if session_id in _active_progress_streams:
            del _active_progress_streams[session_id]


@insights_bp.post("/progress/test")
async def test_progress_events():
    """
    Test endpoint to simulate progress events for development/testing.
    Generates a sequence of progress events to demonstrate the streaming functionality.
    """
    async def generate_test_events():
        session_id = f"test_{datetime.utcnow().timestamp()}"

        try:
            # Simulate a complete insights generation process
            test_events = [
                {
                    "phase": "analysis",
                    "operation": "Starting Session Summary Generation",
                    "details": {"files_count": 5, "time_range": "7 days", "model": "sonnet"}
                },
                {
                    "phase": "analysis",
                    "operation": "Data Collection",
                    "details": {"total_files": 5, "files": ["file1.py", "file2.py", "file3.py"]}
                },
                {
                    "phase": "file_exploration",
                    "operation": "Using Read tool",
                    "current_file": "src/components/Insights.tsx",
                    "files_processed": 1,
                    "total_files": 5
                },
                {
                    "phase": "file_exploration",
                    "operation": "Using Grep tool",
                    "current_file": "services/insights_service.py",
                    "files_processed": 2,
                    "total_files": 5
                },
                {
                    "phase": "analysis",
                    "operation": "AI Analysis Starting",
                    "details": {"model": "sonnet", "max_turns": 15, "tools_allowed": ["Read", "Grep", "Glob"]}
                },
                {
                    "phase": "analysis",
                    "operation": "AI Analysis Turn 1",
                    "details": {"files_examined": 2, "tool_calls": 1, "expected_files": 5}
                },
                {
                    "phase": "analysis",
                    "operation": "AI Analysis Turn 3",
                    "details": {"files_examined": 4, "tool_calls": 3, "expected_files": 5}
                },
                {
                    "phase": "analysis",
                    "operation": "AI Analysis Complete",
                    "details": {
                        "total_turns": 6,
                        "files_examined": 5,
                        "tool_calls_made": 8,
                        "files_list": ["src/components/Insights.tsx", "services/insights_service.py"],
                        "tools_used": ["Read", "Grep"]
                    }
                },
                {
                    "phase": "generation",
                    "operation": "Generation complete",
                    "details": {
                        "analysis_type": "session_summary",
                        "files_analyzed": 5,
                        "result_length": 1247,
                        "model_used": "sonnet"
                    }
                }
            ]

            for i, event in enumerate(test_events):
                event["session_id"] = session_id
                data = json.dumps(event)
                yield f"data: {data}\n\n"

                # Simulate processing time
                await asyncio.sleep(0.5)

        except Exception as e:
            error_event = {
                "type": "error",
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
            data = json.dumps(error_event)
            yield f"data: {data}\n\n"

    return StreamingResponse(
        generate_test_events(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )