"""
HTTP client for the Go SSE Hub Service.

This client provides Server-Sent Events functionality for the frontend
to receive real-time updates from the Go SSE Hub Service.
"""

import asyncio
import logging
import json
from typing import List, Callable, Optional
from pathlib import Path

import httpx
import sseclient

logger = logging.getLogger(__name__)


class SSEHubHTTPClient:
    """HTTP client for communicating with the Go SSE Hub Service via HTTP SSE."""

    def __init__(self, base_url: str = "http://localhost:8080"):
        """
        Initialize the SSE Hub HTTP client.

        Args:
            base_url: Base URL of the Go SSE Hub HTTP service
        """
        self.base_url = base_url
        self.client: Optional[httpx.AsyncClient] = None

    async def connect(self):
        """Initialize HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=30.0,
                headers={"User-Agent": "Obby-SSEHub-Python-Client/1.0"}
            )
            logger.info(f"Connected to SSE Hub at {self.base_url}")

    async def close(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None

    async def health_check(self) -> dict:
        """
        Check health status of SSE Hub service.

        Returns:
            Dictionary with health status
        """
        await self.connect()

        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "error": str(e)}

    async def subscribe_to_sse(
        self,
        topics: Optional[List[str]] = None,
        callback: Optional[Callable] = None
    ) -> str:
        """
        Subscribe to Server-Sent Events.

        Args:
            topics: List of topics to subscribe to (optional)
            callback: Async callback function to handle events (optional)

        Returns:
            Connection ID or client identifier
        """
        await self.connect()

        # Set up SSE request
        headers = {
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }

        # Prepare URL with topic parameters
        url = f"{self.base_url}/sse"
        if topics:
            url += f"?topics={','.join(topics)}"

        try:
            async with self.client.stream("GET", url, headers=headers) as response:
                response.raise_for_status()

                # Process SSE events
                client_id = None
                async for line in response.aiter_lines():
                    if line.startswith("event: connected"):
                        # Extract client ID from connected event
                        data_part = line.split("data: ", 1)[1] if ": " in line else None
                        if data_part:
                            client_id = data_part
                        logger.info(f"SSE connection established: {client_id}")

                    elif line.startswith("event: ") and ": " in line:
                        # Parse event
                        event_type = line.split("event: ")[1].split(":", 1)[0].strip()
                        
                        # Get data line
                        data_line = await response.aiter_lines()
                        if data_line.startswith("data: "):
                            data_str = data_line.split("data: ", 1)[1]
                            
                            try:
                                event_data = json.loads(data_str)
                            except json.JSONDecodeError:
                                event_data = {"raw_data": data_str}
                            
                            event = {
                                "event_type": event_type,
                                "data": event_data
                            }
                            
                            if callback:
                                await callback(event)
                            else:
                                logger.info(f"SSE Event: {event}")

                return client_id

        except Exception as e:
            logger.error(f"SSE subscription failed: {e}")
            raise

    async def stream_events(
        self,
        topics: Optional[List[str]] = None,
        event_callback: Optional[Callable] = None
    ):
        """
        Stream events and call callback for each event.

        Args:
            topics: List of topics to subscribe to
            event_callback: Async function to call for each event
        """
        try:
            await self.subscribe_to_sse(topics, event_callback)
        except Exception as e:
            logger.error(f"Event streaming error: {e}")

    # Convenience methods for common operations
    async def subscribe_to_updates(self, callback: Callable):
        """Subscribe to 'updates' topic."""
        return await self.subscribe_to_sse(["updates"], callback)

    async def subscribe_to_notifications(self, callback: Callable):
        """Subscribe to 'notifications' topic."""
        return await self.subscribe_to_sse(["notifications"], callback)

    async def subscribe_to_alerts(self, callback: Callable):
        """Subscribe to 'alerts' topic."""
        return await self.subscribe_to_sse(["alerts"], callback)

    async def subscribe_to_all(self, callback: Callable):
        """Subscribe to all topics."""
        return await self.subscribe_to_sse(["*"], callback)


# Example usage and integration helper
class SSEIntegration:
    """Integration helper for frontend SSE connections."""

    def __init__(self, sse_client: SSEHubHTTPClient):
        self.sse_client = sse_client

    async def setup_session_summary_updates(self, on_update: Callable):
        """Set up real-time session summary updates."""
        async def handle_update(event):
            if event.get("event_type") == "session_update":
                await on_update(event["data"])

        await self.sse_client.subscribe_to_updates(handle_update)

    async def setup_file_change_notifications(self, on_change: Callable):
        """Set up real-time file change notifications."""
        async def handle_change(event):
            if event.get("event_type") == "file_change":
                await on_change(event["data"])

        await self.sse_client.subscribe_to_notifications(handle_change)

    async def setup_system_alerts(self, on_alert: Callable):
        """Set up system alerts and notifications."""
        async def handle_alert(event):
            if event.get("event_type") == "system_alert":
                await on_alert(event["data"])

        await self.sse_client.subscribe_to_alerts(handle_alert)


# Background task management
async def start_sse_background_task(
    sse_client: SSEHubHTTPClient,
    topics: List[str],
    callback: Callable,
    task_name: str = "sse_subscription"
):
    """
    Start SSE subscription as background task.

    Args:
        sse_client: SSE Hub client
        topics: Topics to subscribe to
        callback: Event callback function
        task_name: Name for the background task
    """
    try:
        await sse_client.stream_events(topics, callback)
    except Exception as e:
        logger.error(f"Background SSE task '{task_name}' failed: {e}")


# Utility functions
def create_sse_client(base_url: str = "http://localhost:8080") -> SSEHubHTTPClient:
    """Create and return a configured SSE Hub HTTP client."""
    return SSEHubHTTPClient(base_url=base_url)


async def test_sse_connection(base_url: str = "http://localhost:8080"):
    """Test SSE Hub connection."""
    client = SSEHubHTTPClient(base_url)
    
    try:
        # Test health check
        health = await client.health_check()
        logger.info(f"Health check result: {health}")
        
        # Test SSE subscription
        async def test_callback(event):
            logger.info(f"Received SSE event: {event}")
            # Stop after first event for testing
            return False  # Return False to stop
        
        await client.subscribe_to_sse(["test"], test_callback)
        
    finally:
        await client.close()