"""
Data Management API routes (FastAPI)
Handles clearing and managing application data
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
import logging
import os
from database.queries import FileQueries, EventQueries

logger = logging.getLogger(__name__)

data_bp = APIRouter(prefix='/api/data', tags=['data'])


@data_bp.post('/files/clear')
async def clear_file_data():
    """Clear all file tracking data"""
    try:
        # Clear file tracking data from database
        files_cleared = FileQueries.clear_all_files()
        events_cleared = EventQueries.clear_file_events()
        
        logger.info(f"Cleared {files_cleared} files and {events_cleared} file events from database")
        
        return {'success': True, 'message': f'Cleared {files_cleared} files and {events_cleared} events from database', 'files_cleared': files_cleared, 'events_cleared': events_cleared}
    except Exception as e:
        logger.error(f"Failed to clear file data: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@data_bp.post('/events/clear')
async def clear_recent_events():
    """Clear all events from database"""
    try:
        events_cleared = EventQueries.clear_all_events()
        logger.info(f"Cleared {events_cleared} events from database")
        
        return {'success': True, 'message': f'Cleared {events_cleared} events from database', 'events_cleared': events_cleared}
    except Exception as e:
        logger.error(f"Failed to clear events: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@data_bp.post('/diffs/clear')
async def clear_recent_diffs():
    """Clear all file-based data from database"""
    try:
        # For file-based system, clear all file tracking data
        result = FileQueries.clear_all_file_data()
        logger.info(f"Cleared file data via database: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error clearing file data: {e}")
        return JSONResponse({'error': f'Failed to clear file data: {str(e)}'}, status_code=500)
