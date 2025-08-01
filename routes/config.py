"""
Configuration API routes
Handles application settings and model configuration
"""

from flask import Blueprint, jsonify, request
import logging
import os
from database.queries import ConfigQueries
from ai.openai_client import OpenAIClient

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
        from config.settings import CHECK_INTERVAL, OPENAI_MODEL, NOTES_FOLDER
        return jsonify({
            'checkInterval': CHECK_INTERVAL,
            'openaiApiKey': os.getenv('OPENAI_API_KEY', ''),
            'aiModel': OPENAI_MODEL,
            'watchPaths': [str(NOTES_FOLDER)],
            'ignorePatterns': ['.git/', '__pycache__/', '*.pyc', '*.tmp', '.DS_Store'],
            'periodicCheckEnabled': True
        })


@config_bp.route('/', methods=['PUT'])
def update_config_root():
    """Update configuration in database (root endpoint)"""
    data = request.json
    
    try:
        # Validate the configuration data
        valid_fields = ['checkInterval', 'openaiApiKey', 'aiModel', 'ignorePatterns', 'periodicCheckEnabled']
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
        
        # Update configuration in database
        result = ConfigQueries.update_config(config_data)
        
        # Update environment variable if API key is provided
        if 'openaiApiKey' in config_data and config_data['openaiApiKey']:
            os.environ['OPENAI_API_KEY'] = config_data['openaiApiKey']
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': f'Failed to update configuration: {str(e)}'}), 500


@config_bp.route('/models', methods=['GET'])
def get_models():
    """Get available OpenAI models"""
    try:
        models = OpenAIClient.MODELS
        from config.settings import OPENAI_MODEL
        return jsonify({
            'models': models,
            'defaultModel': 'gpt-4o',
            'currentModel': OPENAI_MODEL
        })
    except Exception as e:
        return jsonify({
            'error': f'Failed to get models: {str(e)}',
            'models': {},
            'defaultModel': 'gpt-4o',
            'currentModel': 'gpt-4o'
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


# Duplicate get_models function removed
