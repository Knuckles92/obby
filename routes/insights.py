"""
Insights API Routes
Provides AI-powered contextual insights endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

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
    Use this when you want to generate new insights manually.
    
    Parameters:
    - time_range_days: Number of days to analyze (1-30)
    - max_insights: Maximum number of insights to generate (1-50)
    """
    try:
        result = await insights_service.refresh_insights(
            time_range_days=time_range_days,
            max_insights=max_insights,
            force_refresh=True
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