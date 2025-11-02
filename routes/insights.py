"""
Insights API routes (FastAPI)
Handles insights calculations, layout configurations, and available insights metadata
"""

import logging
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse
from typing import Optional, List

from services.insights_service import get_insights_service
from database.models import db

logger = logging.getLogger(__name__)

insights_bp = APIRouter(prefix='/api/insights', tags=['insights'])


@insights_bp.get('/available')
async def get_available_insights():
    """Get list of all available insight types with metadata."""
    try:
        service = get_insights_service()
        insights = service.get_available_insights()

        logger.info(f"Retrieved {len(insights)} available insights")
        return {
            'success': True,
            'insights': insights
        }
    except Exception as e:
        logger.error(f"Error retrieving available insights: {e}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )


@insights_bp.get('/calculate')
async def calculate_insights(
    insight_ids: str = Query(..., description="Comma-separated list of insight IDs to calculate"),
    start_date: Optional[str] = Query(None, description="ISO format start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="ISO format end date (YYYY-MM-DD)"),
    days: Optional[int] = Query(None, description="Number of days to look back from now")
):
    """
    Calculate specified insights for a date range.

    Parameters:
    - insight_ids: Comma-separated list of insight IDs (e.g., "file_activity,peak_activity")
    - start_date: Start date in ISO format (YYYY-MM-DD) - optional if 'days' is provided
    - end_date: End date in ISO format (YYYY-MM-DD) - optional if 'days' is provided
    - days: Number of days to look back from now - alternative to start_date/end_date

    Examples:
    - /api/insights/calculate?insight_ids=file_activity,peak_activity&days=7
    - /api/insights/calculate?insight_ids=trending_files&start_date=2025-01-01&end_date=2025-01-07
    """
    try:
        # Parse insight IDs
        ids = [id.strip() for id in insight_ids.split(',')]

        # Determine date range
        if days is not None:
            # Use 'days' parameter to calculate range
            end = datetime.now()
            start = end - timedelta(days=days)
        elif start_date and end_date:
            # Parse provided dates
            try:
                start = datetime.fromisoformat(start_date)
                end = datetime.fromisoformat(end_date)
            except ValueError as e:
                return JSONResponse(
                    {'success': False, 'error': f'Invalid date format: {str(e)}'},
                    status_code=400
                )
        else:
            # Default to last 7 days if no date range specified
            end = datetime.now()
            start = end - timedelta(days=7)

        # Validate date range
        if start > end:
            return JSONResponse(
                {'success': False, 'error': 'start_date must be before end_date'},
                status_code=400
            )

        # Calculate insights
        service = get_insights_service()
        results = service.calculate_multiple(ids, start, end)

        # Format results for API response
        formatted_results = {}
        for insight_id, result in results.items():
            formatted_results[insight_id] = result.to_dict()

        logger.info(f"Calculated {len(formatted_results)} insights from {start} to {end}")
        return {
            'success': True,
            'dateRange': {
                'start': start.isoformat(),
                'end': end.isoformat(),
                'days': (end - start).days
            },
            'insights': formatted_results
        }

    except Exception as e:
        logger.error(f"Error calculating insights: {e}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )


@insights_bp.get('/layout-config')
async def get_layout_config(
    layout: str = Query(..., description="Layout name (e.g., 'masonry', 'dashboard')")
):
    """Get layout configuration for a specific layout view."""
    try:
        # Query database for layout configuration
        query = """
            SELECT layout_name, insight_cards, default_date_range, updated_at
            FROM insights_layout_config
            WHERE layout_name = ?
        """
        result = db.execute_query(query, (layout,))

        if not result:
            # Return default configuration if not found
            service = get_insights_service()
            default_config = service.get_default_layout_config(layout)

            logger.info(f"No config found for layout '{layout}', returning defaults")
            return {
                'success': True,
                'layout': layout,
                'config': default_config,
                'isDefault': True
            }

        # Parse and return stored configuration
        config_row = dict(result[0])  # Convert Row to dict
        insight_cards = json.loads(config_row['insight_cards'])

        logger.info(f"Retrieved config for layout '{layout}'")
        return {
            'success': True,
            'layout': layout,
            'config': {
                'insights': insight_cards,
                'defaultDateRange': config_row['default_date_range'] or '7d'
            },
            'isDefault': False,
            'updatedAt': config_row['updated_at']
        }

    except Exception as e:
        logger.error(f"Error retrieving layout config: {e}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )


@insights_bp.post('/layout-config')
async def save_layout_config(request: Request):
    """
    Save layout configuration for a specific layout view.

    Request body:
    {
        "layout": "masonry",
        "config": {
            "insights": [
                {"id": "file_activity", "position": 0, "enabled": true},
                ...
            ],
            "defaultDateRange": "7d"
        }
    }
    """
    try:
        data = await request.json()

        # Validate request
        if 'layout' not in data or 'config' not in data:
            return JSONResponse(
                {'success': False, 'error': 'Missing required fields: layout, config'},
                status_code=400
            )

        layout = data['layout']
        config = data['config']

        # Validate config structure
        if 'insights' not in config:
            return JSONResponse(
                {'success': False, 'error': 'Config must contain insights array'},
                status_code=400
            )

        # Convert insights to JSON
        insight_cards_json = json.dumps(config['insights'])
        default_date_range = config.get('defaultDateRange', '7d')

        # Upsert configuration
        upsert_query = """
            INSERT INTO insights_layout_config (layout_name, insight_cards, default_date_range, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(layout_name) DO UPDATE SET
                insight_cards = excluded.insight_cards,
                default_date_range = excluded.default_date_range,
                updated_at = CURRENT_TIMESTAMP
        """

        db.execute_update(upsert_query, (layout, insight_cards_json, default_date_range))

        logger.info(f"Saved layout config for '{layout}' with {len(config['insights'])} insights")
        return {
            'success': True,
            'message': f"Layout configuration saved for '{layout}'"
        }

    except Exception as e:
        logger.error(f"Error saving layout config: {e}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )


@insights_bp.get('/schema')
async def get_insight_schema(
    insight_id: str = Query(..., description="ID of the insight to get schema for")
):
    """Get the data schema for a specific insight type."""
    try:
        service = get_insights_service()
        schema = service.get_insight_schema(insight_id)

        if not schema:
            return JSONResponse(
                {'success': False, 'error': f"Insight '{insight_id}' not found"},
                status_code=404
            )

        return {
            'success': True,
            'insightId': insight_id,
            'schema': schema
        }

    except Exception as e:
        logger.error(f"Error retrieving insight schema: {e}")
        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=500
        )
