"""
Data Management API routes
Handles clearing and managing application data
"""

from flask import Blueprint, jsonify, request
import logging
import os
from database.queries import FileQueries, EventQueries

logger = logging.getLogger(__name__)

data_bp = Blueprint('data', __name__, url_prefix='/api/data')


@data_bp.route('/files/clear', methods=['POST'])
def clear_file_data():
    """Clear all file tracking data"""
    try:
        # Clear file tracking data from database
        files_cleared = FileQueries.clear_all_files()
        events_cleared = EventQueries.clear_file_events()
        
        logger.info(f"Cleared {files_cleared} files and {events_cleared} file events from database")
        
        return jsonify({
            'success': True,
            'message': f'Cleared {files_cleared} files and {events_cleared} events from database',
            'files_cleared': files_cleared,
            'events_cleared': events_cleared
        })
    except Exception as e:
        logger.error(f"Failed to clear file data: {e}")
        return jsonify({'error': str(e)}), 500


@data_bp.route('/events/clear', methods=['POST'])
def clear_recent_events():
    """Clear all events from database"""
    try:
        events_cleared = EventQueries.clear_all_events()
        logger.info(f"Cleared {events_cleared} events from database")
        
        return jsonify({
            'success': True,
            'message': f'Cleared {events_cleared} events from database',
            'events_cleared': events_cleared
        })
    except Exception as e:
        logger.error(f"Failed to clear events: {e}")
        return jsonify({'error': str(e)}), 500


@data_bp.route('/diffs/clear', methods=['POST'])
def clear_recent_diffs():
    """Clear all file-based data from database"""
    try:
        # For file-based system, clear all file tracking data
        result = FileQueries.clear_all_file_data()
        logger.info(f"Cleared file data via database: {result}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error clearing file data: {e}")
        return jsonify({'error': f'Failed to clear file data: {str(e)}'}), 500
