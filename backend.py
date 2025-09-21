from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import threading
import logging
import os
from pathlib import Path
import uvicorn

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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('obby.log')]
)
logger = logging.getLogger(__name__)

app = FastAPI(title='Obby API', version='1.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

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
        uvicorn.run('backend:app', host='0.0.0.0', port=8001, reload=True)
    finally:
        if stop_living_note_watcher:
            stop_living_note_watcher()
        cleanup_monitoring()
