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
    include_dismissed: bool = Query(default=False, description="Include dismissed insights")
) -> Dict[str, Any]:
    """
    Generate and retrieve AI-powered contextual insights
    
    Parameters:
    - time_range_days: Number of days to analyze (1-30)
    - max_insights: Maximum number of insights to generate (1-50)
    - include_dismissed: Whether to include insights marked as dismissed
    """
    try:
        insights = await insights_service.get_insights(
            time_range_days=time_range_days,
            max_insights=max_insights,
            include_dismissed=include_dismissed
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
        success = await insights_service.dismiss_insight(insight_id)
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
        success = await insights_service.archive_insight(insight_id)
        if success:
            return {"success": True, "message": "Insight archived"}
        else:
            raise HTTPException(status_code=404, detail="Insight not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error archiving insight {insight_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to archive insight")


@insights_bp.get("/stats/overview")
async def get_insights_stats():
    """Get overview statistics about insights generation"""
    try:
        # This would be enhanced with actual analytics data
        return {
            "success": True,
            "data": {
                "categories": {
                    "action": {"count": 0, "description": "Action items and follow-ups"},
                    "pattern": {"count": 0, "description": "Behavioral patterns and routines"},
                    "relationship": {"count": 0, "description": "Connections between content"},
                    "temporal": {"count": 0, "description": "Time-based insights"},
                    "opportunity": {"count": 0, "description": "Opportunities for improvement"}
                },
                "priorities": {
                    "critical": {"count": 0, "color": "#ef4444"},
                    "high": {"count": 0, "color": "#f97316"}, 
                    "medium": {"count": 0, "color": "#eab308"},
                    "low": {"count": 0, "color": "#22c55e"}
                },
                "last_generated": None,
                "total_generated": 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting insights stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get insights stats")