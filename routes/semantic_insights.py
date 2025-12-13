"""
Semantic Insights API Routes
============================

Provides endpoints for:
- Listing and filtering semantic insights
- Getting individual insight details
- Performing user actions (dismiss, pin, mark_done)
- Getting statistics
- Triggering processing
- Checking processing status
"""

import logging
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from typing import Optional
from pydantic import BaseModel

from services.semantic_insights_service import get_semantic_insights_service

logger = logging.getLogger(__name__)

semantic_insights_bp = APIRouter(prefix='/api/semantic-insights', tags=['semantic-insights'])


class ActionRequest(BaseModel):
    """Request body for insight actions."""
    action: str
    data: Optional[dict] = None


@semantic_insights_bp.get('')
async def get_semantic_insights(
    type: Optional[str] = Query(None, description="Filter by insight type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Maximum results to return"),
    offset: int = Query(0, description="Pagination offset")
):
    """
    Get semantic insights with optional filtering.

    Parameters:
    - type: Filter by insight type (e.g., 'stale_todo', 'orphan_mention')
    - status: Filter by status (e.g., 'new', 'viewed', 'dismissed', 'pinned')
    - limit: Maximum number of results (default: 50)
    - offset: Pagination offset (default: 0)

    Returns:
    - insights: List of insight objects
    - meta: Pagination info and counts by type/status
    """
    try:
        service = get_semantic_insights_service()
        result = service.get_insights(
            insight_type=type,
            status=status,
            limit=limit,
            offset=offset
        )

        logger.info(f"Retrieved {len(result.get('insights', []))} semantic insights")
        return {
            'success': True,
            **result
        }

    except Exception as e:
        logger.error(f"Error retrieving semantic insights: {e}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )


@semantic_insights_bp.get('/stats')
async def get_semantic_insights_stats():
    """
    Get statistics about semantic insights.

    Returns counts by type, status, and entity information.
    """
    try:
        service = get_semantic_insights_service()
        stats = service.get_stats()

        return {
            'success': True,
            'stats': stats
        }

    except Exception as e:
        logger.error(f"Error getting semantic insights stats: {e}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )


@semantic_insights_bp.get('/processing-status')
async def get_processing_status():
    """
    Get current processing status.

    Returns scheduler state, last run info, and queue size.
    """
    try:
        service = get_semantic_insights_service()
        status = service.get_processing_status()

        return {
            'success': True,
            'status': status
        }

    except Exception as e:
        logger.error(f"Error getting processing status: {e}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )


@semantic_insights_bp.post('/trigger')
async def trigger_processing():
    """
    Manually trigger semantic processing.

    Runs a processing cycle immediately, ignoring the normal schedule.
    Returns processing summary when complete.
    """
    try:
        service = get_semantic_insights_service()
        result = await service.trigger_processing()

        if 'error' in result:
            return JSONResponse(
                {'success': False, 'error': result['error']},
                status_code=500
            )

        return {
            'success': True,
            'result': result
        }

    except Exception as e:
        logger.error(f"Error triggering processing: {e}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )


@semantic_insights_bp.get('/{insight_id}')
async def get_semantic_insight(insight_id: int):
    """
    Get a single semantic insight by ID.

    Automatically marks the insight as 'viewed' if it was 'new'.
    """
    try:
        service = get_semantic_insights_service()
        insight = service.get_insight_by_id(insight_id)

        if not insight:
            return JSONResponse(
                {'success': False, 'error': 'Insight not found'},
                status_code=404
            )

        return {
            'success': True,
            'insight': insight
        }

    except Exception as e:
        logger.error(f"Error getting semantic insight {insight_id}: {e}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )


@semantic_insights_bp.post('/{insight_id}/action')
async def perform_insight_action(insight_id: int, request: ActionRequest):
    """
    Perform a user action on an insight.

    Available actions:
    - dismiss: Hide the insight
    - pin: Pin the insight to top
    - unpin: Unpin a pinned insight
    - mark_done: Mark todo as completed
    - open_note: Record that user opened the source note
    - restore: Restore a dismissed insight
    """
    try:
        service = get_semantic_insights_service()
        result = service.perform_action(
            insight_id=insight_id,
            action=request.action,
            data=request.data
        )

        if not result.get('success'):
            return JSONResponse(
                {'success': False, 'error': result.get('error', 'Unknown error')},
                status_code=400
            )

        return {
            'success': True,
            **result
        }

    except Exception as e:
        logger.error(f"Error performing action on insight {insight_id}: {e}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )
