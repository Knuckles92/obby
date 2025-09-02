"""
Configuration API routes (FastAPI)
Handles application settings and model configuration
"""

import logging
import os
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from database.queries import ConfigQueries
from ai.openai_client import OpenAIClient
from openai import OpenAI

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
        # Fallback to defaults
        from config.settings import CHECK_INTERVAL, OPENAI_MODEL, get_configured_notes_folder, AI_UPDATE_INTERVAL, AI_AUTO_UPDATE_ENABLED
        notes_folder = get_configured_notes_folder()
        return {
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
        }


@config_bp.put('/')
async def update_config_root(request: Request):
    """Update configuration in database (root endpoint)"""
    data = await request.json()
    
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
                    return JSONResponse({'error': 'Check interval must be at least 1 second'}, status_code=400)
            except (ValueError, TypeError):
                return JSONResponse({'error': 'Invalid check interval value'}, status_code=400)
        
        if 'ignorePatterns' in config_data:
            if not isinstance(config_data['ignorePatterns'], list):
                return JSONResponse({'error': 'Ignore patterns must be a list'}, status_code=400)
        
        if 'periodicCheckEnabled' in config_data:
            if not isinstance(config_data['periodicCheckEnabled'], bool):
                return JSONResponse({'error': 'periodicCheckEnabled must be a boolean'}, status_code=400)
        
        if 'aiUpdateInterval' in config_data:
            try:
                config_data['aiUpdateInterval'] = int(config_data['aiUpdateInterval'])
                if config_data['aiUpdateInterval'] < 1 or config_data['aiUpdateInterval'] > 168:  # 1 hour to 1 week
                    return JSONResponse({'error': 'AI update interval must be between 1 and 168 hours'}, status_code=400)
            except (ValueError, TypeError):
                return JSONResponse({'error': 'Invalid AI update interval value'}, status_code=400)
        
        if 'aiAutoUpdateEnabled' in config_data:
            if not isinstance(config_data['aiAutoUpdateEnabled'], bool):
                return JSONResponse({'error': 'aiAutoUpdateEnabled must be a boolean'}, status_code=400)
        
        if 'monitoringDirectory' in config_data:
            if not isinstance(config_data['monitoringDirectory'], str):
                return JSONResponse({'error': 'monitoringDirectory must be a string'}, status_code=400)
            
            # Prevent setting monitoring directory to output to avoid feedback loops
            monitoring_dir = config_data['monitoringDirectory'].strip()
            if not monitoring_dir:
                return JSONResponse({'error': 'monitoringDirectory cannot be empty'}, status_code=400)
            
            # Check for potential feedback loops
            if monitoring_dir.startswith('output') or monitoring_dir == 'output':
                return JSONResponse({'error': 'Cannot monitor the output directory to prevent feedback loops'}, status_code=400)
            
            # Normalize the path
            from pathlib import Path
            try:
                normalized_path = str(Path(monitoring_dir))
                config_data['monitoringDirectory'] = normalized_path
            except Exception as e:
                return JSONResponse({'error': f'Invalid directory path: {str(e)}'}, status_code=400)
        
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
        
        return result
    
    except Exception as e:
        return JSONResponse({'error': f'Failed to update configuration: {str(e)}'}, status_code=500)


@config_bp.get('/models')
async def get_models():
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

        return {
            'models': models_map,
            'defaultModel': default_model,
            'currentModel': OPENAI_MODEL
        }
    except Exception as e:
        # Improved fallback chain: user config first, then hardcoded list
        try:
            from config.settings import OPENAI_MODEL
        except Exception:
            OPENAI_MODEL = 'gpt-4.1-mini'  # Match the actual default from settings.py
        
        # Check for environment variable override
        env_model = os.getenv("OBBY_OPENAI_MODEL")
        current_model = env_model if env_model else OPENAI_MODEL
        
        # Build fallback models list starting with user's configured model
        fallback_models = {}
        
        # Add user's configured model first (if it's valid)
        if current_model and current_model in OpenAIClient.MODELS.values():
            fallback_models[current_model] = current_model
        
        # Add remaining hardcoded models
        for name, model_id in OpenAIClient.MODELS.items():
            if model_id not in fallback_models:
                fallback_models[name] = model_id
        
        # Default should be user's configured model, or first available
        default_model = current_model if current_model in fallback_models.values() else next(iter(fallback_models.values()), 'gpt-4.1-mini')
        
        return JSONResponse({
            'error': f'Failed to get models from API: {str(e)}',
            'models': fallback_models,
            'defaultModel': default_model,
            'currentModel': current_model
        }, status_code=500)


@config_bp.get('/openai/ping')
async def openai_ping():
    """Quick connectivity + config check for OpenAI. Performs a tiny chat call.

    Returns:
      - available: bool
      - model: configured model id (if available)
      - reply: short reply from model (if successful)
      - error: error details (if failed)
    """
    try:
        client = OpenAIClient()
        model = getattr(client, 'model', None)
        if not client.is_available():
            return JSONResponse({
                'available': False,
                'model': model,
                'error': 'Client not available; check OPENAI_API_KEY'
            }, status_code=200)

        # Minimal, low-cost call
        reply = client.get_completion(
            "Reply with the single word: ready",
            system_prompt="You are a health check. Reply exactly 'ready' only.",
            max_tokens=10
        )
        return {
            'available': True,
            'model': model,
            'reply': (reply or '').strip()
        }
    except Exception as e:
        return JSONResponse({
            'available': False,
            'model': getattr(OpenAIClient(), 'model', None),
            'error': str(e)
        }, status_code=200)


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
        
        # Validate required fields
        required_fields = ['openai_api_key', 'model', 'check_interval']
        for field in required_fields:
            if field not in data:
                return JSONResponse({'error': f'Missing required field: {field}'}, status_code=400)
        
        # Validate model
        valid_models = [
            'gpt-4', 'gpt-4-turbo', 'gpt-4-turbo-preview', 
            'gpt-3.5-turbo', 'gpt-3.5-turbo-16k'
        ]
        if data['model'] not in valid_models:
            return JSONResponse({'error': f'Invalid model. Must be one of: {", ".join(valid_models)}'}, status_code=400)
        
        # Validate check_interval
        try:
            check_interval = int(data['check_interval'])
            if check_interval < 1 or check_interval > 3600:
                return JSONResponse({'error': 'Check interval must be between 1 and 3600 seconds'}, status_code=400)
        except (ValueError, TypeError):
            return JSONResponse({'error': 'Check interval must be a valid integer'}, status_code=400)
        
        # Update configuration
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
