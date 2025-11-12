"""
Service Management API routes
Handles service status, health checks, and lifecycle management
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import logging
import json
import asyncio
from typing import Optional
from services.service_status_service import get_service_status_service

logger = logging.getLogger(__name__)

services_bp = APIRouter(prefix='/api/services', tags=['services'])


class ServiceActionRequest(BaseModel):
    """Request model for service actions."""
    action: str  # start, stop, restart


@services_bp.get('')
async def get_all_services():
    """Get all registered services with current status."""
    try:
        service_status = get_service_status_service()
        services = service_status.get_all_services()

        return JSONResponse({
            'success': True,
            'services': services,
            'count': len(services)
        })

    except Exception as e:
        logger.error(f"Failed to get services: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@services_bp.get('/{service_id}')
async def get_service_by_id(service_id: int):
    """Get detailed information about a specific service."""
    try:
        service_status = get_service_status_service()
        service = service_status.get_service_by_id(service_id)

        if not service:
            raise HTTPException(status_code=404, detail='Service not found')

        return JSONResponse({
            'success': True,
            'service': service
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get service {service_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@services_bp.get('/name/{service_name}')
async def get_service_by_name(service_name: str):
    """Get service information by name."""
    try:
        service_status = get_service_status_service()
        service = service_status.get_service_by_name(service_name)

        if not service:
            raise HTTPException(status_code=404, detail='Service not found')

        return JSONResponse({
            'success': True,
            'service': service
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get service {service_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@services_bp.post('/{service_id}/restart')
async def restart_service(service_id: int):
    """Restart a service."""
    try:
        service_status = get_service_status_service()
        result = service_status.restart_service(service_id)

        if not result['success']:
            raise HTTPException(status_code=400, detail=result['message'])

        return JSONResponse({
            'success': True,
            'message': result['message']
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restart service {service_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@services_bp.post('/{service_id}/stop')
async def stop_service(service_id: int):
    """Stop a service."""
    try:
        service_status = get_service_status_service()
        result = service_status.stop_service(service_id)

        if not result['success']:
            raise HTTPException(status_code=400, detail=result['message'])

        return JSONResponse({
            'success': True,
            'message': result['message']
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop service {service_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@services_bp.post('/{service_id}/start')
async def start_service(service_id: int):
    """Start a service."""
    try:
        service_status = get_service_status_service()
        result = service_status.start_service(service_id)

        if not result['success']:
            raise HTTPException(status_code=400, detail=result['message'])

        return JSONResponse({
            'success': True,
            'message': result['message']
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start service {service_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@services_bp.get('/{service_id}/health')
async def check_service_health(service_id: int):
    """Check the health of a specific service."""
    try:
        service_status = get_service_status_service()
        result = service_status.check_service_health(service_id)

        return JSONResponse({
            'success': True,
            'healthy': result['healthy'],
            'message': result['message']
        })

    except Exception as e:
        logger.error(f"Failed to check service health {service_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@services_bp.get('/{service_id}/events')
async def get_service_events(service_id: int, limit: int = 100):
    """Get recent events for a specific service."""
    try:
        service_status = get_service_status_service()
        events = service_status.get_service_events(service_id, limit)

        return JSONResponse({
            'success': True,
            'events': events,
            'count': len(events)
        })

    except Exception as e:
        logger.error(f"Failed to get service events {service_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@services_bp.get('/events/all')
async def get_all_events(limit: int = 100):
    """Get recent events for all services."""
    try:
        service_status = get_service_status_service()
        events = service_status.get_service_events(None, limit)

        return JSONResponse({
            'success': True,
            'events': events,
            'count': len(events)
        })

    except Exception as e:
        logger.error(f"Failed to get all service events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@services_bp.get('/stream/status')
async def stream_service_status():
    """Server-Sent Events endpoint for real-time service status updates."""
    async def event_generator():
        """Generate SSE events for service status."""
        try:
            service_status = get_service_status_service()

            while True:
                # Get current status of all services
                services = service_status.get_all_services()

                # Send status update
                data = json.dumps({
                    'timestamp': str(asyncio.get_event_loop().time()),
                    'services': services
                })
                yield f"data: {data}\n\n"

                # Wait 5 seconds before next update
                await asyncio.sleep(5)

        except asyncio.CancelledError:
            logger.info("SSE connection closed by client")
        except Exception as e:
            logger.error(f"Error in service status SSE stream: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )


@services_bp.get('/stream/events')
async def stream_service_events():
    """Server-Sent Events endpoint for real-time service event logging."""
    async def event_generator():
        """Generate SSE events for service events."""
        try:
            service_status = get_service_status_service()
            last_event_id = 0

            while True:
                # Get new events since last check
                all_events = service_status.get_service_events(None, 100)

                # Filter for new events
                new_events = [e for e in all_events if e['id'] > last_event_id]

                if new_events:
                    # Update last event ID
                    last_event_id = max(e['id'] for e in new_events)

                    # Send new events
                    for event in new_events:
                        data = json.dumps(event)
                        yield f"data: {data}\n\n"

                # Wait 2 seconds before checking again
                await asyncio.sleep(2)

        except asyncio.CancelledError:
            logger.info("SSE connection closed by client")
        except Exception as e:
            logger.error(f"Error in service events SSE stream: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )
