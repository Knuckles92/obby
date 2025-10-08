import sys
import asyncio

# CRITICAL: Set Windows event loop policy FIRST, before any other imports
# This must be at the very top to work with uvicorn reload mode
if sys.platform == 'win32':
    # Force Windows Proactor event loop policy for subprocess support
    try:
        current_policy = asyncio.get_event_loop_policy()
        if not isinstance(current_policy, asyncio.WindowsProactorEventLoopPolicy):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            print("[STARTUP] Windows: Set WindowsProactorEventLoopPolicy for Claude SDK subprocess support")
        else:
            print("[STARTUP] Windows: WindowsProactorEventLoopPolicy already active")
    except Exception as e:
        print(f"[STARTUP] Windows: Failed to set event loop policy: {e}")
        # Try to set it anyway
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import threading
import logging
import os
from pathlib import Path
import uvicorn

# Fix Windows subprocess encoding issues for Claude CLI
if sys.platform == 'win32':
    # Force UTF-8 encoding for subprocess communication
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # Set console code page to UTF-8 if possible
    try:
        import subprocess as _sp
        _sp.run(['chcp', '65001'], shell=True, capture_output=True, check=False)
    except Exception:
        pass  # Silently fail if chcp doesn't work

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()  # Load .env file if it exists

# Import FastAPI routers
from routes.monitoring import monitoring_bp
from routes.files import files_bp
from routes.living_note import living_note_bp
from routes.summary_note import summary_note_bp
from routes.search import search_bp
from routes.config import config_bp
from routes.data import data_bp
from routes.admin import admin_bp
from routes.watch_config import watch_config_bp
from routes.chat import chat_bp

from routes.api_monitor import APIObbyMonitor
from ai.openai_client import OpenAIClient
from ai.batch_processor import BatchAIProcessor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('obby.log')]
)
logger = logging.getLogger(__name__)

# Ensure Windows event loop supports subprocesses required by Claude CLI
# This is a backup check in case the initial policy setting was bypassed
if sys.platform == 'win32':
    try:
        current_policy = asyncio.get_event_loop_policy()
        if not isinstance(current_policy, asyncio.WindowsProactorEventLoopPolicy):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            logger.info('Backup: Set Windows Proactor event loop policy for Claude CLI compatibility')
        else:
            logger.info('Windows Proactor event loop policy already configured')
    except Exception as loop_err:
        logger.warning(f'Could not set Windows Proactor event loop policy: {loop_err}')

# Log encoding configuration for debugging Windows issues
if sys.platform == 'win32':
    logger.info(f"Windows platform detected - PYTHONIOENCODING: {os.environ.get('PYTHONIOENCODING', 'not set')}")
    logger.info(f"Default encoding: {sys.getdefaultencoding()}, stdout encoding: {sys.stdout.encoding}")

app = FastAPI(title='Obby API', version='1.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# FastAPI startup event to ensure Windows event loop policy is set
@app.on_event("startup")
async def startup_event():
    """Ensure Windows event loop policy is set on startup (handles uvicorn reloader)."""
    if sys.platform == 'win32':
        try:
            current_policy = asyncio.get_event_loop_policy()
            if not isinstance(current_policy, asyncio.WindowsProactorEventLoopPolicy):
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                logger.info('Startup: Set Windows Proactor event loop policy for Claude SDK')
            else:
                logger.info('Startup: Windows Proactor event loop policy already active')
        except Exception as e:
            logger.warning(f'Startup: Could not set Windows event loop policy: {e}')
    
    # Warm up OpenAI client in background to avoid cold start latency
    try:
        def _warmup():
            try:
                client = OpenAIClient.get_instance()
                client.warm_up()
                logger.info('OpenAI client warm-up finished')
            except Exception as e:
                logger.warning(f'OpenAI warm-up failed: {e}')
        threading.Thread(target=_warmup, daemon=True).start()
    except Exception as e:
        logger.debug(f'Failed to spawn warm-up thread: {e}')

# Global monitoring state
monitor_instance = None
monitor_thread = None
monitoring_active = False

# Include routers
app.include_router(monitoring_bp)
app.include_router(files_bp)
app.include_router(living_note_bp)
app.include_router(summary_note_bp)
app.include_router(search_bp)
app.include_router(config_bp)
app.include_router(data_bp)
app.include_router(admin_bp)
app.include_router(watch_config_bp)
app.include_router(chat_bp)


def run_monitor():
    global monitor_instance, monitoring_active
    try:
        if monitor_instance:
            monitor_instance.start()
    except Exception as e:
        logger.error(f"Monitor thread error: {e}")
        monitoring_active = False


@app.get('/api/monitor/diagnostics')
def get_monitor_diagnostics():
    global monitor_instance, monitoring_active
    status = {
        'monitoring_active': monitoring_active,
        'monitor_instance_exists': monitor_instance is not None,
        'file_watcher_running': False,
        'periodic_check_enabled': False,
        'check_interval': 0,
        'watched_directories': [],
        'recent_events_count': 0,
    }
    if monitor_instance:
        try:
            stats = monitor_instance.get_stats()
            status.update({
                'file_watcher_running': getattr(monitor_instance, 'is_running', False),
                'periodic_check_enabled': getattr(monitor_instance, 'periodic_check_enabled', False),
                'check_interval': getattr(monitor_instance, 'check_interval', 0),
                'recent_events_count': stats.get('recent_changes_count', 0),
            })
            if getattr(monitor_instance, 'file_watcher', None) and monitor_instance.file_watcher.handler:
                try:
                    watch_dirs = monitor_instance.file_watcher.handler.watch_handler.get_watch_directories()
                    status['watched_directories'] = [str(d) for d in watch_dirs]
                except Exception as e:
                    logger.debug(f"Could not get watched directories: {e}")
        except Exception as e:
            logger.error(f"Error getting monitor status: {e}")
    return JSONResponse(status_code=200, content=status)


# Static frontend
frontend_dir = Path('frontend/dist')
if frontend_dir.exists():
    app.mount('/assets', StaticFiles(directory=str(frontend_dir / 'assets')), name='assets')


@app.get('/{full_path:path}')
def serve_frontend(full_path: str):
    if full_path.startswith('api/'):
        return JSONResponse({'error': 'API endpoint not found'}, status_code=404)
    if frontend_dir.exists():
        requested = frontend_dir / full_path
        if full_path and requested.exists() and requested.is_file():
            return FileResponse(str(requested))
        index_file = frontend_dir / 'index.html'
        if index_file.exists():
            return FileResponse(str(index_file))
    return JSONResponse(status_code=200, content={
        'message': 'Obby API Server',
        'version': '1.0.0',
        'endpoints': {
            'monitoring': '/api/monitor/*',
            'files': '/api/files/*',
            'living-note': '/api/living-note/*',
            'search': '/api/search/*',
            'config': '/api/config/*',
            'data': '/api/data/*',
            'admin': '/api/admin/*',
        },
        'frontend': 'Build frontend with: cd frontend && npm run build',
    })


def initialize_monitoring():
    global monitor_instance, monitor_thread, monitoring_active
    try:
        monitor_instance = APIObbyMonitor()
        monitoring_active = True
        monitor_thread = threading.Thread(target=run_monitor, daemon=True)
        monitor_thread.start()
        # Propagate state to monitoring routes for consistent status reporting
        try:
            from routes.monitoring import init_monitoring_routes
            init_monitoring_routes(monitor_instance, monitor_thread, monitoring_active)
        except Exception as e:
            logger.debug(f"Could not init monitoring routes: {e}")
        
        # Start Batch AI processor scheduler (optional, controlled via config)
        try:
            global _batch_processor
            _batch_processor = BatchAIProcessor(OpenAIClient.get_instance())
            _batch_processor.start_scheduler()
            logger.info('Batch AI scheduler started')
        except Exception as e:
            logger.warning(f'Failed to start Batch AI scheduler: {e}')
        
        logger.info('File monitoring system initialized successfully')
        return True
    except Exception as e:
        logger.error(f'Failed to initialize monitoring system: {e}')
        monitoring_active = False
        return False


def cleanup_monitoring():
    global monitor_instance, monitoring_active
    try:
        if monitor_instance:
            monitor_instance.stop()
            monitoring_active = False
            logger.info('File monitoring system stopped')
    except Exception as e:
        logger.error(f'Error stopping monitoring system: {e}')


if __name__ == '__main__':
    logger.info('Starting Obby API server on http://localhost:8001')
    try:
        from utils.migrations import migrate_format_md
        mig = migrate_format_md()
        if mig.get('migrated'):
            logger.info('format.md migrated to config/format.md')
    except Exception as e:
        logger.warning(f'Migration step skipped/failed: {e}')

    monitoring_initialized = initialize_monitoring()
    if not monitoring_initialized:
        logger.warning('File monitoring system failed to initialize - continuing without it')

    watcher_enabled = os.getenv('LIVING_NOTE_WATCHER_ENABLED', 'false').lower() == 'true'
    stop_living_note_watcher = None
    if watcher_enabled:
        from routes.living_note import start_living_note_watcher, stop_living_note_watcher as _stop
        start_living_note_watcher()
        stop_living_note_watcher = _stop
    else:
        logger.info('Living note watcher disabled (LIVING_NOTE_WATCHER_ENABLED=false)')

    try:
        # On Windows, disable reload to avoid event loop policy issues with Claude SDK
        # The reload feature can interfere with the event loop policy on Windows
        uvicorn_config = {
            'app': 'backend:app',
            'host': '0.0.0.0',
            'port': 8001,
            'reload': sys.platform != 'win32',  # Disable reload on Windows
        }
        
        # On Windows, explicitly specify loop implementation for subprocess support
        if sys.platform == 'win32':
            uvicorn_config['loop'] = 'asyncio'  # Use asyncio (with our ProactorEventLoopPolicy)
            logger.info('Windows: Using asyncio loop with WindowsProactorEventLoopPolicy for Claude SDK support')
            logger.info('Windows: Reload disabled to prevent event loop policy conflicts')
        else:
            logger.info('Non-Windows: Using default uvicorn configuration with reload enabled')
        
        uvicorn.run(**uvicorn_config)
    finally:
        if stop_living_note_watcher:
            stop_living_note_watcher()
        cleanup_monitoring()
