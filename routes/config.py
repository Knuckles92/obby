"""
Configuration API routes (FastAPI)
Handles application settings and model configuration
"""

import logging
import os
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from database.queries import ConfigQueries
from database.models import ConfigModel

logger = logging.getLogger(__name__)

config_bp = APIRouter(prefix='/api/config', tags=['config'])


@config_bp.get('/')
async def get_config_root():
    """Get current configuration from database (root endpoint)"""
    try:
        config_data = ConfigQueries.get_config()
        logger.info("Retrieved configuration from database")
        return config_data
    except Exception as e:
        logger.error(f"Error loading config from database: {e}")
        from config.settings import (
            CLAUDE_MODEL,
            get_configured_notes_folder,
        )
        notes_folder = get_configured_notes_folder()
        return {
            'aiModel': os.getenv('OBBY_CLAUDE_MODEL', CLAUDE_MODEL),
            'watchPaths': [str(notes_folder)],
            'monitoringDirectory': str(notes_folder),
            'ignorePatterns': ['__pycache__/', '*.pyc', '*.tmp', '.DS_Store'],
        }


@config_bp.put('/')
async def update_config_root(request: Request):
    """Update configuration in database (root endpoint)"""
    data = await request.json()
    try:
        valid_fields = [
            'aiModel',
            'ignorePatterns',
            'monitoringDirectory',
            'periodicCheckEnabled',
        ]
        config_data = {}
        for field in valid_fields:
            if field in data:
                config_data[field] = data[field]

        if 'ignorePatterns' in config_data:
            if not isinstance(config_data['ignorePatterns'], list):
                return JSONResponse({'error': 'Ignore patterns must be a list'}, status_code=400)

        if 'monitoringDirectory' in config_data:
            if not isinstance(config_data['monitoringDirectory'], str):
                return JSONResponse({'error': 'monitoringDirectory must be a string'}, status_code=400)

            monitoring_dir = config_data['monitoringDirectory'].strip()
            if not monitoring_dir:
                return JSONResponse({'error': 'monitoringDirectory cannot be empty'}, status_code=400)
            if monitoring_dir.startswith('output') or monitoring_dir == 'output':
                return JSONResponse({'error': 'Cannot monitor the output directory to prevent feedback loops'}, status_code=400)
            from pathlib import Path
            try:
                normalized_path = str(Path(monitoring_dir))
                config_data['monitoringDirectory'] = normalized_path
            except Exception as e:
                return JSONResponse({'error': f'Invalid directory path: {str(e)}'}, status_code=400)

        if 'periodicCheckEnabled' in config_data:
            if not isinstance(config_data['periodicCheckEnabled'], bool):
                return JSONResponse({'error': 'periodicCheckEnabled must be a boolean'}, status_code=400)

        result = ConfigQueries.update_config(config_data)

        if 'monitoringDirectory' in config_data and result.get('success', False):
            try:
                from utils.watch_handler import WatchHandler
                from pathlib import Path
                project_root = Path(__file__).parent.parent
                watch_handler = WatchHandler(project_root)
                monitoring_dir = config_data['monitoringDirectory']
                watch_handler.watch_patterns.clear()
                watch_handler.watch_patterns.add(f"{monitoring_dir}/")
                _write_watch_patterns_from_config(watch_handler)
                logger.info(f"Updated .obbywatch file to monitor: {monitoring_dir}/")
            except Exception as e:
                logger.error(f"Failed to update .obbywatch file: {e}")

        if 'periodicCheckEnabled' in config_data and result.get('success', False):
            try:
                from backend import global_monitor
                if global_monitor:
                    global_monitor.set_periodic_check_enabled(config_data['periodicCheckEnabled'])
                    logger.info(f"Updated periodic check enabled to: {config_data['periodicCheckEnabled']}")
            except Exception as e:
                logger.error(f"Failed to update periodic monitoring: {e}")

        return result

    except Exception as e:
        return JSONResponse({'error': f'Failed to update configuration: {str(e)}'}, status_code=500)


@config_bp.get('/models')
async def get_models():
    """Return available Claude models."""
    from config.settings import CLAUDE_MODEL

    claude_models = {
        'haiku': 'haiku',
        'sonnet': 'sonnet',
        'opus': 'opus',
    }

    current_model = os.getenv("OBBY_CLAUDE_MODEL", CLAUDE_MODEL).lower()
    if current_model not in claude_models:
        claude_models[current_model] = current_model

    default_model = 'haiku'

    return {
        'models': claude_models,
        'defaultModel': default_model,
        'currentModel': current_model,
    }

@config_bp.api_route('/settings', methods=['GET', 'POST'])
async def handle_config(request: Request):
    """Get or update configuration in database"""
    if request.method == 'GET':
        return await get_config()
    else:
        return await update_config(request)


async def get_config():
    """Get current configuration from database"""
    try:
        config = ConfigQueries.get_config()
        return {
            'config': config,
            'success': True
        }
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


async def update_config(request: Request):
    """Update configuration in database"""
    try:
        data = await request.json()
        if not data:
            return JSONResponse({'error': 'No configuration data provided'}, status_code=400)

        required_fields = ['model', 'check_interval']
        for field in required_fields:
            if field not in data:
                return JSONResponse({'error': f'Missing required field: {field}'}, status_code=400)

        valid_models = ['haiku', 'sonnet', 'opus']
        if data['model'] not in valid_models:
            return JSONResponse({'error': f'Invalid model. Must be one of: {", ".join(valid_models)}'}, status_code=400)

        try:
            check_interval = int(data['check_interval'])
            if check_interval < 1 or check_interval > 3600:
                return JSONResponse({'error': 'Check interval must be between 1 and 3600 seconds'}, status_code=400)
        except (ValueError, TypeError):
            return JSONResponse({'error': 'Check interval must be a valid integer'}, status_code=400)

        success = ConfigQueries.update_config(data)

        if success:
            logger.info("Configuration updated successfully")
            return {'success': True, 'message': 'Configuration updated successfully'}
        else:
            return JSONResponse({'error': 'Failed to update configuration'}, status_code=500)

    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


def _write_watch_patterns_from_config(watch_handler):
    """Write watch patterns to .obbywatch file (helper for config updates)"""
    try:
        content = """# Obby watch file
# This file specifies directories that Obby should monitor for changes
# Use glob patterns (* and ?) and one pattern per line
# Lines starting with # are comments

"""
        for pattern in sorted(watch_handler.watch_patterns):
            content += f"{pattern}\n"

        if not watch_handler.watch_patterns:
            content += """
# Example patterns:
# notes/
# docs/
# *.md
# project_notes/
# research/
# writing/
# *.txt
"""

        with open(watch_handler.watch_file, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Updated .obbywatch file with {len(watch_handler.watch_patterns)} patterns")
    except Exception as e:
        logger.error(f"Error writing watch patterns: {e}")
        raise


@config_bp.get('/transparency-preferences')
async def get_transparency_preferences():
    """Get transparency preferences configuration"""
    try:
        preferences = ConfigModel.get('transparency_preferences', None)
        if preferences is None:
            preferences = {
                'progress_display_mode': 'standard',
                'show_file_exploration': True,
                'show_ai_reasoning': True,
                'show_performance_metrics': True,
                'show_data_sources': True,
                'real_time_updates': True,
                'auto_open_progress': False,
                'store_agent_logs': True,
                'log_retention_days': 7,
                'notification_preferences': {
                    'generation_complete': True,
                    'error_occurred': True,
                    'long_running_analysis': False
                },
                'ui_preferences': {
                    'compact_mode': False,
                    'show_timestamps': True,
                    'show_tool_usage': True,
                    'color_code_phases': True
                }
            }
        return {
            'success': True,
            'data': preferences
        }
    except Exception as e:
        logger.error(f"Failed to get transparency preferences: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@config_bp.post('/transparency-preferences')
async def save_transparency_preferences(request: Request):
    """Save transparency preferences configuration"""
    try:
        data = await request.json()
        required_fields = [
            'progress_display_mode', 'show_file_exploration', 'show_ai_reasoning',
            'show_performance_metrics', 'show_data_sources', 'real_time_updates',
            'auto_open_progress', 'store_agent_logs', 'log_retention_days',
            'notification_preferences', 'ui_preferences'
        ]
        for field in required_fields:
            if field not in data:
                return JSONResponse({'error': f'Missing required field: {field}'}, status_code=400)

        valid_modes = ['minimal', 'standard', 'detailed']
        if data['progress_display_mode'] not in valid_modes:
            return JSONResponse({
                'error': f'Invalid progress_display_mode. Must be one of: {", ".join(valid_modes)}'
            }, status_code=400)

        try:
            log_retention_days = int(data['log_retention_days'])
            if log_retention_days < 1 or log_retention_days > 365:
                return JSONResponse({
                    'error': 'log_retention_days must be between 1 and 365'
                }, status_code=400)
        except (ValueError, TypeError):
            return JSONResponse({'error': 'log_retention_days must be a valid integer'}, status_code=400)

        if not isinstance(data['notification_preferences'], dict):
            return JSONResponse({'error': 'notification_preferences must be an object'}, status_code=400)
        if not isinstance(data['ui_preferences'], dict):
            return JSONResponse({'error': 'ui_preferences must be an object'}, status_code=400)

        ConfigModel.set(
            'transparency_preferences',
            data,
            'Transparency preferences configuration'
        )

        logger.info("Transparency preferences saved successfully")
        return {
            'success': True,
            'message': 'Transparency preferences saved successfully'
        }
    except Exception as e:
        logger.error(f"Failed to save transparency preferences: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)
