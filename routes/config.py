"""
Configuration API routes
Handles application settings and model configuration
"""

from flask import Blueprint, jsonify, request
import logging
import os
from database.queries import ConfigQueries
from ai.openai_client import OpenAIClient
from openai import OpenAI

logger = logging.getLogger(__name__)

config_bp = Blueprint('config', __name__, url_prefix='/api/config')


@config_bp.route('/', methods=['GET'])
def get_config_root():
    """Get current configuration from database (root endpoint)"""
    try:
        config_data = ConfigQueries.get_config()
        logger.info("Retrieved configuration from database")
        return jsonify(config_data)
    except Exception as e:
        logger.error(f"Error loading config from database: {e}")
        # Fallback to defaults
        from config.settings import CHECK_INTERVAL, OPENAI_MODEL, get_configured_notes_folder, AI_UPDATE_INTERVAL, AI_AUTO_UPDATE_ENABLED
        notes_folder = get_configured_notes_folder()
        return jsonify({
            'checkInterval': CHECK_INTERVAL,
            'openaiApiKey': os.getenv('OPENAI_API_KEY', ''),
            'aiModel': OPENAI_MODEL,
            'watchPaths': [str(notes_folder)],
            'monitoringDirectory': str(notes_folder),
            'ignorePatterns': ['.git/', '__pycache__/', '*.pyc', '*.tmp', '.DS_Store'],
            'periodicCheckEnabled': True,
            'aiUpdateInterval': AI_UPDATE_INTERVAL,
            'aiAutoUpdateEnabled': AI_AUTO_UPDATE_ENABLED,
            'lastAiUpdateTimestamp': None
        })


@config_bp.route('/', methods=['PUT'])
def update_config_root():
    """Update configuration in database (root endpoint)"""
    data = request.json
    
    try:
        # Validate the configuration data
        valid_fields = ['checkInterval', 'openaiApiKey', 'aiModel', 'ignorePatterns', 'periodicCheckEnabled', 'aiUpdateInterval', 'aiAutoUpdateEnabled', 'lastAiUpdateTimestamp', 'monitoringDirectory']
        config_data = {}
        
        for field in valid_fields:
            if field in data:
                config_data[field] = data[field]
        
        # Validate specific fields
        if 'checkInterval' in config_data:
            try:
                config_data['checkInterval'] = int(config_data['checkInterval'])
                if config_data['checkInterval'] < 1:
                    return jsonify({'error': 'Check interval must be at least 1 second'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid check interval value'}), 400
        
        if 'ignorePatterns' in config_data:
            if not isinstance(config_data['ignorePatterns'], list):
                return jsonify({'error': 'Ignore patterns must be a list'}), 400
        
        if 'periodicCheckEnabled' in config_data:
            if not isinstance(config_data['periodicCheckEnabled'], bool):
                return jsonify({'error': 'periodicCheckEnabled must be a boolean'}), 400
        
        if 'aiUpdateInterval' in config_data:
            try:
                config_data['aiUpdateInterval'] = int(config_data['aiUpdateInterval'])
                if config_data['aiUpdateInterval'] < 1 or config_data['aiUpdateInterval'] > 168:  # 1 hour to 1 week
                    return jsonify({'error': 'AI update interval must be between 1 and 168 hours'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid AI update interval value'}), 400
        
        if 'aiAutoUpdateEnabled' in config_data:
            if not isinstance(config_data['aiAutoUpdateEnabled'], bool):
                return jsonify({'error': 'aiAutoUpdateEnabled must be a boolean'}), 400
        
        if 'monitoringDirectory' in config_data:
            if not isinstance(config_data['monitoringDirectory'], str):
                return jsonify({'error': 'monitoringDirectory must be a string'}), 400
            
            # Prevent setting monitoring directory to output to avoid feedback loops
            monitoring_dir = config_data['monitoringDirectory'].strip()
            if not monitoring_dir:
                return jsonify({'error': 'monitoringDirectory cannot be empty'}), 400
            
            # Check for potential feedback loops
            if monitoring_dir.startswith('output') or monitoring_dir == 'output':
                return jsonify({'error': 'Cannot monitor the output directory to prevent feedback loops'}), 400
            
            # Normalize the path
            from pathlib import Path
            try:
                normalized_path = str(Path(monitoring_dir))
                config_data['monitoringDirectory'] = normalized_path
            except Exception as e:
                return jsonify({'error': f'Invalid directory path: {str(e)}'}), 400
        
        # Update configuration in database
        result = ConfigQueries.update_config(config_data)
        
        # Update environment variable if API key is provided
        if 'openaiApiKey' in config_data and config_data['openaiApiKey']:
            os.environ['OPENAI_API_KEY'] = config_data['openaiApiKey']
        
        # Update .obbywatch file if monitoring directory changed
        if 'monitoringDirectory' in config_data and result.get('success', False):
            try:
                from utils.watch_handler import WatchHandler
                from pathlib import Path
                
                # Get project root and create watch handler
                project_root = Path(__file__).parent.parent
                watch_handler = WatchHandler(project_root)
                
                # Remove old patterns and add new monitoring directory
                monitoring_dir = config_data['monitoringDirectory']
                
                # Clear existing patterns and add the new monitoring directory
                watch_handler.watch_patterns.clear()
                watch_handler.watch_patterns.add(f"{monitoring_dir}/")
                
                # Write updated patterns to .obbywatch file
                _write_watch_patterns_from_config(watch_handler)
                
                logger.info(f"Updated .obbywatch file to monitor: {monitoring_dir}/")
                
            except Exception as e:
                logger.error(f"Failed to update .obbywatch file: {e}")
                # Don't fail the config update just because .obbywatch update failed
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': f'Failed to update configuration: {str(e)}'}), 500


@config_bp.route('/models', methods=['GET'])
def get_models():
    """Get available OpenAI models (dynamically from API, filtered to GPT-5 family when available)."""
    try:
        # Initialize OpenAI client (api key comes from env or was set via settings update)
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        # List all models from OpenAI
        api_models = client.models.list()
        model_ids = [m.id for m in getattr(api_models, 'data', [])]

        # Prefer GPT-5 family if available
        gpt5_models = [mid for mid in model_ids if isinstance(mid, str) and mid.startswith('gpt-5')]

        # Use GPT-5 models if present; otherwise fall back to all returned models
        selected_models = gpt5_models if gpt5_models else model_ids

        # Build mapping of name->id for frontend selector
        models_map = {mid: mid for mid in selected_models}

        # Determine defaults
        from config.settings import OPENAI_MODEL
        default_model = selected_models[0] if selected_models else OPENAI_MODEL

        return jsonify({
            'models': models_map,
            'defaultModel': default_model,
            'currentModel': OPENAI_MODEL
        })
    except Exception as e:
        # Graceful fallback to static list if API call fails
        try:
            from config.settings import OPENAI_MODEL
        except Exception:
            OPENAI_MODEL = 'gpt-4o'
        return jsonify({
            'error': f'Failed to get models: {str(e)}',
            'models': OpenAIClient.MODELS,
            'defaultModel': 'gpt-5-mini',
            'currentModel': OPENAI_MODEL
        }), 500


@config_bp.route('/settings', methods=['GET', 'POST'])
def handle_config():
    """Get or update configuration in database"""
    if request.method == 'GET':
        return get_config()
    else:
        return update_config()


def get_config():
    """Get current configuration from database"""
    try:
        config = ConfigQueries.get_config()
        return jsonify({
            'config': config,
            'success': True
        })
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        return jsonify({'error': str(e)}), 500


def update_config():
    """Update configuration in database"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No configuration data provided'}), 400
        
        # Validate required fields
        required_fields = ['openai_api_key', 'model', 'check_interval']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate model
        valid_models = [
            'gpt-4', 'gpt-4-turbo', 'gpt-4-turbo-preview', 
            'gpt-3.5-turbo', 'gpt-3.5-turbo-16k'
        ]
        if data['model'] not in valid_models:
            return jsonify({'error': f'Invalid model. Must be one of: {", ".join(valid_models)}'}), 400
        
        # Validate check_interval
        try:
            check_interval = int(data['check_interval'])
            if check_interval < 1 or check_interval > 3600:
                return jsonify({'error': 'Check interval must be between 1 and 3600 seconds'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Check interval must be a valid integer'}), 400
        
        # Update configuration
        success = ConfigQueries.update_config(data)
        
        if success:
            logger.info("Configuration updated successfully")
            return jsonify({
                'success': True,
                'message': 'Configuration updated successfully'
            })
        else:
            return jsonify({'error': 'Failed to update configuration'}), 500
            
    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        return jsonify({'error': str(e)}), 500


def _write_watch_patterns_from_config(watch_handler):
    """Write watch patterns to .obbywatch file (helper for config updates)"""
    try:
        content = """# Obby watch file
# This file specifies directories that Obby should monitor for changes
# Use glob patterns (* and ?) and one pattern per line
# Lines starting with # are comments

"""
        
        # Add current patterns
        for pattern in sorted(watch_handler.watch_patterns):
            content += f"{pattern}\n"
        
        # Add example patterns as comments if file is empty
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


# Duplicate get_models function removed
